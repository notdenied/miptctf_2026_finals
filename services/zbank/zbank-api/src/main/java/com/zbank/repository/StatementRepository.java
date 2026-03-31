package com.zbank.repository;

import com.zbank.model.Statement;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface StatementRepository extends JpaRepository<Statement, Long> {
    List<Statement> findByAccountIdOrderByCreatedAtDesc(Long accountId);
}
