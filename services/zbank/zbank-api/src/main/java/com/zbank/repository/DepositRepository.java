package com.zbank.repository;

import com.zbank.model.Deposit;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface DepositRepository extends JpaRepository<Deposit, Long> {
    List<Deposit> findByUserIdOrderByCreatedAtDesc(Long userId);
}
