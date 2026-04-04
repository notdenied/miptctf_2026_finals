package com.zbank.controller;

import com.zbank.model.Account;
import com.zbank.model.Statement;
import com.zbank.model.User;
import com.zbank.repository.UserRepository;
import com.zbank.service.AccountService;
import com.zbank.service.StatementService;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.InputStreamResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import java.io.InputStream;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/statements")
@RequiredArgsConstructor
public class StatementController {

    private final StatementService statementService;
    private final AccountService accountService;
    private final UserRepository userRepository;

    /** Lists all statements for the current user's accounts, newest first. */
    @GetMapping
    public ResponseEntity<?> listStatements() {
        User user = getCurrentUser();
        List<Account> accounts = accountService.getUserAccounts(user.getId());
        List<Map<String, Object>> result = new java.util.ArrayList<>();
        for (Account account : accounts) {
            List<Statement> stmts = statementService.getByAccountId(account.getId());
            for (Statement s : stmts) {
                Map<String, Object> map = new LinkedHashMap<>();
                map.put("id", s.getId());
                map.put("status", s.getStatus());
                map.put("format", s.getFormat());
                map.put("s3Key", s.getS3Key() != null ? s.getS3Key() : "");
                map.put("accountId", account.getId());
                map.put("accountName", account.getName());
                map.put("requestedAt", s.getCreatedAt() != null ? s.getCreatedAt().toString() : "");
                result.add(map);
            }
        }
        return ResponseEntity.ok(result);
    }

    /** Creates a new statement job for the given account and format (csv/json/txt). Returns statement id and initial status. */
    @PostMapping
    public ResponseEntity<?> createStatement(@RequestBody Map<String, Object> body) {
        User user = getCurrentUser();
        try {
            Long accountId = Long.valueOf(body.get("accountId").toString());
            String format = body.getOrDefault("format", "csv").toString();

            Account account = accountService.getById(accountId);
            if (!account.getUser().getId().equals(user.getId())) {
                return ResponseEntity.status(403).body(Map.of("error", "Access denied"));
            }

            Statement statement = statementService.createStatement(account, format);
            return ResponseEntity.ok(Map.of(
                    "id", statement.getId(),
                    "status", statement.getStatus(),
                    "format", statement.getFormat()
            ));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    /** Returns current status and s3Key of a statement owned by the current user. */
    @GetMapping("/{id}")
    public ResponseEntity<?> getStatement(@PathVariable Long id) {
        User user = getCurrentUser();
        Statement statement = statementService.getById(id);
        if (!statement.getAccount().getUser().getId().equals(user.getId())) {
            return ResponseEntity.status(403).body(Map.of("error", "Access denied"));
        }
        return ResponseEntity.ok(Map.of(
                "id", statement.getId(),
                "status", statement.getStatus(),
                "format", statement.getFormat(),
                "s3Key", statement.getS3Key() != null ? statement.getS3Key() : ""
        ));
    }

    /** Streams the generated file from MinIO by its s3Key. */
    @GetMapping("/download")
    public ResponseEntity<?> downloadByS3Key(@RequestParam String s3Key) {
        try {
            Statement statement = statementService.getByS3Key(s3Key);
            if (!"DONE".equals(statement.getStatus())) {
                return ResponseEntity.badRequest().body(Map.of("error", "Statement is not ready yet"));
            }
            InputStream stream = statementService.downloadStatement(s3Key);
            return ResponseEntity.ok()
                    .header(HttpHeaders.CONTENT_DISPOSITION,
                            "attachment; filename=statement." + statement.getFormat())
                    .contentType(MediaType.APPLICATION_OCTET_STREAM)
                    .body(new InputStreamResource(stream));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.status(404).body(Map.of("error", e.getMessage()));
        }
    }

    private User getCurrentUser() {
        String username = SecurityContextHolder.getContext().getAuthentication().getName();
        return userRepository.findByUsername(username).orElseThrow();
    }
}
