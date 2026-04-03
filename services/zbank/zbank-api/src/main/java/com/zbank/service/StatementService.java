package com.zbank.service;

import com.zbank.model.Account;
import com.zbank.model.Statement;
import com.zbank.model.Transaction;
import com.zbank.repository.StatementRepository;
import com.zbank.repository.TransactionRepository;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.GetObjectArgs;
import io.minio.GetPresignedObjectUrlArgs;
import io.minio.BucketExistsArgs;
import io.minio.MakeBucketArgs;
import io.minio.http.Method;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Service
@Slf4j
public class StatementService {

    private static final int MAX_ATTEMPTS = 3;

    private final StatementRepository statementRepository;
    private final TransactionRepository transactionRepository;
    private final MinioClient minioClient;

    /** Separate MinioClient configured with the public endpoint — used only for presigning. */
    private final MinioClient presignMinioClient;

    @Value("${minio.bucket:statements}")
    private String bucketName;

    public StatementService(StatementRepository statementRepository,
                            TransactionRepository transactionRepository,
                            MinioClient minioClient,
                            @Qualifier("presignMinioClient") MinioClient presignMinioClient) {
        this.statementRepository   = statementRepository;
        this.transactionRepository = transactionRepository;
        this.minioClient           = minioClient;
        this.presignMinioClient    = presignMinioClient;
    }

    // ── Public API ────────────────────────────────────────────────────────────

    /**
     * Creates a new statement record with status PENDING.
     * The actual processing is delegated to the statement-worker container
     * which polls the internal API.
     */
    @Transactional
    public Statement createStatement(Account account, String format) {
        if (!List.of("csv", "json", "txt").contains(format.toLowerCase())) {
            throw new IllegalArgumentException("Unsupported format. Use csv, json, or txt");
        }
        Statement statement = Statement.builder()
                .account(account)
                .format(format.toLowerCase())
                .status("PENDING")
                .build();
        return statementRepository.save(statement);
    }

    /** Returns a statement by id; throws if not found. */
    public Statement getById(Long id) {
        return statementRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Statement not found"));
    }

    /** Returns a statement by its s3Key; throws if not found. */
    public Statement getByS3Key(String s3Key) {
        return statementRepository.findByS3Key(s3Key)
                .orElseThrow(() -> new IllegalArgumentException("Statement not found"));
    }

    /** Streams the file content from MinIO by its s3Key. */
    public InputStream downloadStatement(String s3Key) {
        try {
            return minioClient.getObject(GetObjectArgs.builder()
                    .bucket(bucketName)
                    .object(s3Key)
                    .build());
        } catch (Exception e) {
            throw new RuntimeException("Failed to download statement", e);
        }
    }

    /**
     * Generates a presigned GET URL for the statement file valid for 1 hour.
     * The URL is built using the public MinIO endpoint so the client can access
     * it directly without going through the Spring Boot API.
     */
    public String getPresignedUrl(Statement statement) {
        try {
            return presignMinioClient.getPresignedObjectUrl(
                    GetPresignedObjectUrlArgs.builder()
                            .method(Method.GET)
                            .bucket(bucketName)
                            .object(statement.getS3Key())
                            .expiry(1, TimeUnit.HOURS)
                            .build()
            );
        } catch (Exception e) {
            throw new RuntimeException("Failed to generate presigned URL", e);
        }
    }

    // ── Worker-facing methods (called via InternalController) ─────────────────

    /**
     * Returns the next PENDING statement that still has attempts remaining,
     * ordered by creation time (oldest first).
     */
    public Optional<Statement> getNextPending() {
        return statementRepository.findNextPending(MAX_ATTEMPTS);
    }

    /**
     * Synchronously processes a statement: generates content, uploads to MinIO,
     * updates status to DONE.
     * Throws on any error so the caller (InternalController) can return 500
     * and the worker will increment the attempt counter.
     */
    @Transactional
    public void processStatement(Long statementId) throws Exception {
        Statement statement = getById(statementId);
        statement.setStatus("PROCESSING");
        statementRepository.save(statement);

        Long accountId = statement.getAccount().getId();
        List<Transaction> transactions = transactionRepository
                .findByFromAccountIdOrToAccountIdOrderByCreatedAtDesc(accountId, accountId);

        String content = generateContent(transactions, accountId, statement.getFormat());

        ensureBucket();

        String s3Key = "statements/" + accountId + "/" + UUID.randomUUID() + "." + statement.getFormat();
        byte[] bytes = content.getBytes(StandardCharsets.UTF_8);

        minioClient.putObject(PutObjectArgs.builder()
                .bucket(bucketName)
                .object(s3Key)
                .stream(new ByteArrayInputStream(bytes), bytes.length, -1)
                .contentType(getContentType(statement.getFormat()))
                .build());

        statement.setS3Key(s3Key);
        statement.setStatus("DONE");
        statementRepository.save(statement);

        log.info("Statement {} processed successfully, key={}", statementId, s3Key);
    }

    /**
     * Increments the attempt counter for a statement.
     * If the counter reaches MAX_ATTEMPTS, status is set to FAILED.
     */
    @Transactional
    public Statement incrementAttempts(Long statementId) {
        Statement statement = getById(statementId);
        statement.setAttempts(statement.getAttempts() + 1);
        if (statement.getAttempts() >= MAX_ATTEMPTS) {
            statement.setStatus("FAILED");
            log.warn("Statement {} exhausted {} attempts, marking FAILED", statementId, MAX_ATTEMPTS);
        }
        return statementRepository.save(statement);
    }

    /**
     * Directly updates the status (and optionally the S3 key) of a statement.
     * Used by InternalController for explicit status overrides.
     */
    @Transactional
    public Statement updateStatus(Long statementId, String status, String s3Key) {
        Statement statement = getById(statementId);
        statement.setStatus(status);
        if (s3Key != null) statement.setS3Key(s3Key);
        return statementRepository.save(statement);
    }

    // ── Content generation ────────────────────────────────────────────────────

    private String generateContent(List<Transaction> transactions, Long accountId, String format) {
        return switch (format) {
            case "csv"  -> generateCsv(transactions, accountId);
            case "json" -> generateJson(transactions, accountId);
            case "txt"  -> generateTxt(transactions, accountId);
            default -> throw new IllegalArgumentException("Unknown format: " + format);
        };
    }

    private String generateCsv(List<Transaction> transactions, Long accountId) {
        StringBuilder sb = new StringBuilder();
        sb.append("id,date,from_account,to_account,amount,description\n");
        for (Transaction t : transactions) {
            String from = t.getFromAccount() != null ? String.valueOf(t.getFromAccount().getId()) : "";
            String to   = t.getToAccount()   != null ? String.valueOf(t.getToAccount().getId())   : "";
            sb.append(String.format("%d,%s,%s,%s,%s,%s\n",
                    t.getId(), t.getCreatedAt(), from, to,
                    t.getAmount(), t.getDescription() != null ? t.getDescription() : ""));
        }
        return sb.toString();
    }

    private String generateJson(List<Transaction> transactions, Long accountId) {
        StringBuilder sb = new StringBuilder();
        sb.append("{\"account_id\":").append(accountId).append(",\"transactions\":[");
        for (int i = 0; i < transactions.size(); i++) {
            Transaction t = transactions.get(i);
            if (i > 0) sb.append(",");
            String from = t.getFromAccount() != null ? String.valueOf(t.getFromAccount().getId()) : "null";
            String to   = t.getToAccount()   != null ? String.valueOf(t.getToAccount().getId())   : "null";
            sb.append(String.format("{\"id\":%d,\"date\":\"%s\",\"from\":%s,\"to\":%s,\"amount\":%s,\"description\":\"%s\"}",
                    t.getId(), t.getCreatedAt(), from, to,
                    t.getAmount(), t.getDescription() != null ? t.getDescription() : ""));
        }
        sb.append("]}");
        return sb.toString();
    }

    private String generateTxt(List<Transaction> transactions, Long accountId) {
        StringBuilder sb = new StringBuilder();
        sb.append("=== Account Statement: ").append(accountId).append(" ===\n\n");
        for (Transaction t : transactions) {
            String from = t.getFromAccount() != null ? String.valueOf(t.getFromAccount().getId()) : "—";
            String to   = t.getToAccount()   != null ? String.valueOf(t.getToAccount().getId())   : "—";
            sb.append(String.format("ID: %d | Date: %s | From: %s | To: %s | Amount: %s₽ | %s\n",
                    t.getId(), t.getCreatedAt(), from, to,
                    t.getAmount(), t.getDescription() != null ? t.getDescription() : ""));
        }
        return sb.toString();
    }

    private String getContentType(String format) {
        return switch (format) {
            case "csv"  -> "text/csv";
            case "json" -> "application/json";
            case "txt"  -> "text/plain";
            default     -> "application/octet-stream";
        };
    }

    private void ensureBucket() throws Exception {
        if (!minioClient.bucketExists(BucketExistsArgs.builder().bucket(bucketName).build())) {
            minioClient.makeBucket(MakeBucketArgs.builder().bucket(bucketName).build());
        }
    }
}
