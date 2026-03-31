package com.zbank.controller;

import com.zbank.model.Statement;
import com.zbank.repository.StatementRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Internal API endpoints that are protected by the X-Local-Job header.
 * These are only accessible from within the container (background jobs).
 * lighttpd blocks the X-Local-Job header from external requests.
 */
@RestController
@RequestMapping("/api/internal")
@RequiredArgsConstructor
public class InternalController {

    private final StatementRepository statementRepository;

    @PutMapping("/statements/{id}/status")
    public ResponseEntity<?> updateStatementStatus(
            @PathVariable Long id,
            @RequestBody Map<String, String> body) {
        Statement statement = statementRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Statement not found"));
        statement.setStatus(body.get("status"));
        if (body.containsKey("s3Key")) {
            statement.setS3Key(body.get("s3Key"));
        }
        statementRepository.save(statement);
        return ResponseEntity.ok(Map.of("status", "updated"));
    }

    @GetMapping("/health")
    public ResponseEntity<?> health() {
        return ResponseEntity.ok(Map.of("status", "ok", "internal", true));
    }
}
