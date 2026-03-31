package com.zbank.controller;

import com.zbank.model.Deposit;
import com.zbank.model.User;
import com.zbank.repository.UserRepository;
import com.zbank.service.DepositService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/deposits")
@RequiredArgsConstructor
public class DepositController {

    private final DepositService depositService;
    private final UserRepository userRepository;

    @PostMapping
    public ResponseEntity<?> openDeposit(@RequestBody Map<String, Object> body) {
        User user = getCurrentUser();
        try {
            Long accountId = Long.valueOf(body.get("accountId").toString());
            String name = body.getOrDefault("name", "Вклад").toString();
            BigDecimal amount = new BigDecimal(body.get("amount").toString());
            BigDecimal interestRate = new BigDecimal(body.getOrDefault("interestRate", "5.0").toString());
            int termMonths = Integer.parseInt(body.getOrDefault("termMonths", "12").toString());

            Deposit deposit = depositService.openDeposit(user, accountId, name, amount, interestRate, termMonths);
            return ResponseEntity.ok(toMap(deposit));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping
    public ResponseEntity<?> getDeposits() {
        User user = getCurrentUser();
        List<Map<String, Object>> deposits = depositService.getUserDeposits(user.getId())
                .stream().map(this::toMap).collect(Collectors.toList());
        return ResponseEntity.ok(deposits);
    }

    @GetMapping("/{id}")
    public ResponseEntity<?> getDeposit(@PathVariable Long id) {
        User user = getCurrentUser();
        Deposit deposit = depositService.getById(id);
        if (!deposit.getUser().getId().equals(user.getId())) {
            return ResponseEntity.status(403).body(Map.of("error", "Access denied"));
        }
        return ResponseEntity.ok(toMap(deposit));
    }

    private Map<String, Object> toMap(Deposit d) {
        return Map.of(
                "id", d.getId(),
                "name", d.getName(),
                "amount", d.getAmount(),
                "interestRate", d.getInterestRate(),
                "termMonths", d.getTermMonths(),
                "accountId", d.getAccount().getId(),
                "createdAt", d.getCreatedAt().toString()
        );
    }

    private User getCurrentUser() {
        String username = SecurityContextHolder.getContext().getAuthentication().getName();
        return userRepository.findByUsername(username).orElseThrow();
    }
}
