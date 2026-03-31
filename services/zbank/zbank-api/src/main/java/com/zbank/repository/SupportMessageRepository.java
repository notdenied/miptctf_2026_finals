package com.zbank.repository;

import com.zbank.model.SupportMessage;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface SupportMessageRepository extends JpaRepository<SupportMessage, Long> {
    List<SupportMessage> findByUserIdOrderByCreatedAtAsc(Long userId);
}
