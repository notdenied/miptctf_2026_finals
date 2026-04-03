package com.zbank.repository;

import com.zbank.model.Statement;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface StatementRepository extends JpaRepository<Statement, Long> {

    List<Statement> findByAccountIdOrderByCreatedAtDesc(Long accountId);

    Optional<Statement> findByS3Key(String s3Key);

    /** Returns the oldest PENDING statement that has not yet exhausted its retry budget. */
    @Query("SELECT s FROM Statement s WHERE s.status = 'PENDING' AND s.attempts < :maxAttempts ORDER BY s.createdAt ASC")
    Optional<Statement> findNextPending(@Param("maxAttempts") int maxAttempts);
}
