package com.zbank.repository;

import com.zbank.model.Fundraising;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface FundraisingRepository extends JpaRepository<Fundraising, Long> {
    Optional<Fundraising> findByLinkCode(String linkCode);
}
