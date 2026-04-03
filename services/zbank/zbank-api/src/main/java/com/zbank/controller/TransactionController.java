package com.zbank.controller;

import com.zbank.model.Account;
import com.zbank.model.Transaction;
import com.zbank.model.User;
import com.zbank.repository.UserRepository;
import com.zbank.service.AccountService;
import com.zbank.service.TransactionService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.*;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/transactions")
@RequiredArgsConstructor
public class TransactionController {

    private final TransactionService transactionService;
    private final AccountService accountService;
    private final UserRepository userRepository;

    /** Transfers funds between two accounts. The source account must belong to the current user. */
    @PostMapping
    public ResponseEntity<?> transfer(@RequestBody Map<String, Object> body) {
        User user = getCurrentUser();
        try {
            Long fromAccountId = Long.valueOf(body.get("fromAccountId").toString());
            Long toAccountId = Long.valueOf(body.get("toAccountId").toString());
            BigDecimal amount = new BigDecimal(body.get("amount").toString());
            String description = (String) body.getOrDefault("description", "");

            // Verify ownership of source account
            Account fromAccount = accountService.getById(fromAccountId);
            if (!fromAccount.getUser().getId().equals(user.getId())) {
                return ResponseEntity.status(403).body(Map.of("error", "Source account is not yours"));
            }

            Transaction tx = transactionService.transfer(fromAccountId, toAccountId, amount, description);
            return ResponseEntity.ok(Map.of(
                    "id", tx.getId(),
                    "fromAccountId", tx.getFromAccount().getId(),
                    "toAccountId", tx.getToAccount().getId(),
                    "amount", tx.getAmount(),
                    "description", tx.getDescription() != null ? tx.getDescription() : "",
                    "createdAt", tx.getCreatedAt().toString()
            ));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    /** Records a spend (outgoing payment) from the given account. No destination account is required. */
    @PostMapping("/spend")
    public ResponseEntity<?> spend(@RequestBody Map<String, Object> body) {
        User user = getCurrentUser();
        try {
            Long accountId = Long.valueOf(body.get("accountId").toString());
            BigDecimal amount = new BigDecimal(body.get("amount").toString());
            String description = (String) body.getOrDefault("description", "Payment");

            Transaction tx = transactionService.spend(user, accountId, amount, description);
            return ResponseEntity.ok(Map.of(
                    "id", tx.getId(),
                    "fromAccountId", tx.getFromAccount().getId(),
                    "amount", tx.getAmount(),
                    "description", tx.getDescription() != null ? tx.getDescription() : "",
                    "createdAt", tx.getCreatedAt().toString()
            ));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    /** Returns all transactions for a given account. The account must belong to the current user. */
    @GetMapping("/account/{accountId}")
    public ResponseEntity<?> getTransactions(@PathVariable Long accountId) {
        User user = getCurrentUser();
        Account account = accountService.getById(accountId);
        if (!account.getUser().getId().equals(user.getId())) {
            return ResponseEntity.status(403).body(Map.of("error", "Access denied"));
        }

        List<Map<String, Object>> txList = transactionService.getAccountTransactions(accountId)
                .stream()
                .map(this::txToMap)
                .collect(Collectors.toList());
        return ResponseEntity.ok(txList);
    }

    private Map<String, Object> txToMap(Transaction tx) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("id", tx.getId());
        map.put("fromAccountId", tx.getFromAccount() != null ? tx.getFromAccount().getId() : null);
        map.put("toAccountId", tx.getToAccount() != null ? tx.getToAccount().getId() : null);
        map.put("amount", tx.getAmount());
        map.put("description", tx.getDescription() != null ? tx.getDescription() : "");
        map.put("createdAt", tx.getCreatedAt().toString());
        return map;
    }

    private User getCurrentUser() {
        String username = SecurityContextHolder.getContext().getAuthentication().getName();
        return userRepository.findByUsername(username).orElseThrow();
    }
}
