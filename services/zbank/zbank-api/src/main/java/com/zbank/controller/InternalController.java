package com.zbank.controller;

import com.zbank.model.Statement;
import com.zbank.service.StatementService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.Optional;

/**
 * Internal API consumed by the statement-worker container.
 */
@RestController
@RequestMapping("/api/internal")
@RequiredArgsConstructor
@Slf4j
public class InternalController {

    private final StatementService statementService;

    // ── Queue management ──────────────────────────────────────────────────────

    /**
     * Returns the next PENDING statement that still has remaining retry attempts.
     * Returns 204 No Content when the queue is empty.
     */
    @GetMapping("/statements/next")
    public ResponseEntity<?> getNextPending() {
        Optional<Statement> next = statementService.getNextPending();
        if (next.isEmpty()) {
            return ResponseEntity.noContent().build();
        }
        Statement s = next.get();
        return ResponseEntity.ok(toMap(s));
    }

    /**
     * Returns the current status and attempt count of a specific statement.
     */
    @GetMapping("/statements/{id}/status")
    public ResponseEntity<?> getStatus(@PathVariable Long id) {
        try {
            Statement s = statementService.getById(id);
            return ResponseEntity.ok(Map.of(
                    "id",       s.getId(),
                    "status",   s.getStatus(),
                    "attempts", s.getAttempts(),
                    "format",   s.getFormat(),
                    "s3Key",    s.getS3Key() != null ? s.getS3Key() : ""
            ));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.status(404).body(Map.of("error", e.getMessage()));
        }
    }

    /**
     * Synchronously processes a statement: generates the file and uploads it to MinIO.
     * Returns 200 on success, 500 on any processing error.
     * The worker should call PUT /attempts on a 500 response.
     */
    @PostMapping("/statements/{id}/process")
    public ResponseEntity<?> processStatement(@PathVariable Long id) {
        try {
            statementService.processStatement(id);
            Statement s = statementService.getById(id);
            return ResponseEntity.ok(Map.of(
                    "id",     s.getId(),
                    "status", s.getStatus(),
                    "s3Key",  s.getS3Key() != null ? s.getS3Key() : ""
            ));
        } catch (Exception e) {
            log.error("Processing failed for statement {}: {}", id, e.getMessage());
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }

    /**
     * Increments the attempt counter for a statement.
     * Automatically sets status to FAILED when the counter reaches the maximum.
     */
    @PutMapping("/statements/{id}/attempts")
    public ResponseEntity<?> incrementAttempts(@PathVariable Long id) {
        try {
            Statement s = statementService.incrementAttempts(id);
            return ResponseEntity.ok(Map.of(
                    "id",       s.getId(),
                    "status",   s.getStatus(),
                    "attempts", s.getAttempts()
            ));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.status(404).body(Map.of("error", e.getMessage()));
        }
    }

    /**
     * Directly updates the status (and optionally s3Key) of a statement.
     * Used by the worker to confirm DONE or mark FAILED.
     */
    @PutMapping("/statements/{id}/status")
    public ResponseEntity<?> updateStatus(@PathVariable Long id,
                                           @RequestBody Map<String, String> body) {
        try {
            Statement s = statementService.updateStatus(id, body.get("status"), body.get("s3Key"));
            return ResponseEntity.ok(Map.of(
                    "id",     s.getId(),
                    "status", s.getStatus()
            ));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.status(404).body(Map.of("error", e.getMessage()));
        }
    }

    // ── Health ────────────────────────────────────────────────────────────────

    /** Liveness check used by the worker to wait for the API to become ready. */
    @GetMapping("/health")
    public ResponseEntity<?> health() {
        return ResponseEntity.ok(Map.of("status", "ok", "internal", true));
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private Map<String, Object> toMap(Statement s) {
        return Map.of(
                "id",       s.getId(),
                "status",   s.getStatus(),
                "format",   s.getFormat(),
                "attempts", s.getAttempts(),
                "accountId", s.getAccount().getId()
        );
    }
}
