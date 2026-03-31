package com.zbank.service;

import com.zbank.model.Account;
import com.zbank.model.Statement;
import com.zbank.model.Transaction;
import com.zbank.repository.StatementRepository;
import com.zbank.repository.TransactionRepository;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.GetObjectArgs;
import io.minio.BucketExistsArgs;
import io.minio.MakeBucketArgs;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class StatementService {

    private final StatementRepository statementRepository;
    private final TransactionRepository transactionRepository;
    private final MinioClient minioClient;

    @Value("${minio.bucket:statements}")
    private String bucketName;

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
        statement = statementRepository.save(statement);

        // Launch async job
        processStatementAsync(statement.getId(), account.getId(), format.toLowerCase());

        return statement;
    }

    @Async
    public void processStatementAsync(Long statementId, Long accountId, String format) {
        try {
            Statement statement = statementRepository.findById(statementId).orElseThrow();
            statement.setStatus("PROCESSING");
            statementRepository.save(statement);

            // Get transactions
            List<Transaction> transactions = transactionRepository
                    .findByFromAccountIdOrToAccountIdOrderByCreatedAtDesc(accountId, accountId);

            // Generate content
            String content = generateContent(transactions, accountId, format);

            // Ensure bucket exists
            ensureBucket();

            // Upload to S3
            String s3Key = "statements/" + accountId + "/" + UUID.randomUUID() + "." + format;
            byte[] bytes = content.getBytes(StandardCharsets.UTF_8);

            minioClient.putObject(PutObjectArgs.builder()
                    .bucket(bucketName)
                    .object(s3Key)
                    .stream(new ByteArrayInputStream(bytes), bytes.length, -1)
                    .contentType(getContentType(format))
                    .build());

            statement.setS3Key(s3Key);
            statement.setStatus("DONE");
            statementRepository.save(statement);

            log.info("Statement {} completed, uploaded to {}", statementId, s3Key);

        } catch (Exception e) {
            log.error("Statement processing failed for {}", statementId, e);
            try {
                Statement statement = statementRepository.findById(statementId).orElseThrow();
                statement.setStatus("FAILED");
                statementRepository.save(statement);
            } catch (Exception ex) {
                log.error("Failed to update statement status", ex);
            }
        }
    }

    public Statement getById(Long id) {
        return statementRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Statement not found"));
    }

    public InputStream downloadStatement(Statement statement) {
        try {
            return minioClient.getObject(GetObjectArgs.builder()
                    .bucket(bucketName)
                    .object(statement.getS3Key())
                    .build());
        } catch (Exception e) {
            throw new RuntimeException("Failed to download statement", e);
        }
    }

    private void ensureBucket() throws Exception {
        if (!minioClient.bucketExists(BucketExistsArgs.builder().bucket(bucketName).build())) {
            minioClient.makeBucket(MakeBucketArgs.builder().bucket(bucketName).build());
        }
    }

    private String generateContent(List<Transaction> transactions, Long accountId, String format) {
        return switch (format) {
            case "csv" -> generateCsv(transactions, accountId);
            case "json" -> generateJson(transactions, accountId);
            case "txt" -> generateTxt(transactions, accountId);
            default -> throw new IllegalArgumentException("Unknown format");
        };
    }

    private String generateCsv(List<Transaction> transactions, Long accountId) {
        StringBuilder sb = new StringBuilder();
        sb.append("id,date,from_account,to_account,amount,description\n");
        for (Transaction t : transactions) {
            sb.append(String.format("%d,%s,%d,%d,%s,%s\n",
                    t.getId(), t.getCreatedAt(),
                    t.getFromAccount().getId(), t.getToAccount().getId(),
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
            sb.append(String.format("{\"id\":%d,\"date\":\"%s\",\"from\":%d,\"to\":%d,\"amount\":%s,\"description\":\"%s\"}",
                    t.getId(), t.getCreatedAt(),
                    t.getFromAccount().getId(), t.getToAccount().getId(),
                    t.getAmount(), t.getDescription() != null ? t.getDescription() : ""));
        }
        sb.append("]}");
        return sb.toString();
    }

    private String generateTxt(List<Transaction> transactions, Long accountId) {
        StringBuilder sb = new StringBuilder();
        sb.append("=== Выписка по счёту ").append(accountId).append(" ===\n\n");
        for (Transaction t : transactions) {
            sb.append(String.format("ID: %d | Дата: %s | Со счёта: %d | На счёт: %d | Сумма: %s₽ | %s\n",
                    t.getId(), t.getCreatedAt(),
                    t.getFromAccount().getId(), t.getToAccount().getId(),
                    t.getAmount(), t.getDescription() != null ? t.getDescription() : ""));
        }
        return sb.toString();
    }

    private String getContentType(String format) {
        return switch (format) {
            case "csv" -> "text/csv";
            case "json" -> "application/json";
            case "txt" -> "text/plain";
            default -> "application/octet-stream";
        };
    }
}
