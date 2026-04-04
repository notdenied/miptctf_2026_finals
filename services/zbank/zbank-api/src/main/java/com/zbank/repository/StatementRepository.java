package com.zbank.repository;

import com.zbank.model.Statement;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface StatementRepository extends JpaRepository<Statement, Long> {

    List<Statement> findByAccountIdOrderByCreatedAtDesc(Long accountId);

    Optional<Statement> findByS3Key(String s3Key);

    /** Returns the oldest PENDING or PROCESSING statement that has not yet exhausted its retry budget. */
    Optional<Statement> findFirstByStatusInAndAttemptsLessThanOrderByCreatedAtAsc(List<String> statuses, int maxAttempts);
}
