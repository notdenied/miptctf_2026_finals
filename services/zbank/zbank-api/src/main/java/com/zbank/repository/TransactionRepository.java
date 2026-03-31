package com.zbank.repository;

import com.zbank.model.Transaction;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface TransactionRepository extends JpaRepository<Transaction, Long> {
    List<Transaction> findByFromAccountIdOrToAccountIdOrderByCreatedAtDesc(Long fromAccountId, Long toAccountId);
    List<Transaction> findByFromAccountIdOrderByCreatedAtDesc(Long fromAccountId);
}
