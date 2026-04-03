package com.zbank.controller;

import com.zbank.model.Account;
import com.zbank.model.Transaction;
import com.zbank.model.User;
import com.zbank.repository.UserRepository;
import com.zbank.service.AccountService;
import com.zbank.service.ChartService;
import com.zbank.service.TransactionService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/charts")
@RequiredArgsConstructor
public class ChartController {

    private final ChartService chartService;
    private final TransactionService transactionService;
    private final AccountService accountService;
    private final UserRepository userRepository;

    /** Generates a spending pie chart for the given account. */
    @PostMapping("/spending")
    public ResponseEntity<?> generateSpendingChart(@RequestBody Map<String, Object> body) {
        User user = getCurrentUser();
        try {
            Long accountId = Long.valueOf(body.get("accountId").toString());
            String message = body.getOrDefault("message", "Chart").toString();

            Account account = accountService.getById(accountId);
            if (!account.getUser().getId().equals(user.getId())) {
                return ResponseEntity.status(403).body(Map.of("error", "Access denied"));
            }

            List<Transaction> transactions = transactionService.getAccountTransactions(accountId);
            List<Map<String, Object>> spendingData = new ArrayList<>();
            for (Transaction tx : transactions) {
                Map<String, Object> entry = new HashMap<>();
                entry.put("date", tx.getCreatedAt().toString());
                entry.put("amount", tx.getAmount());
                entry.put("type", tx.getFromAccount().getId().equals(accountId) ? "expense" : "income");
                entry.put("description", tx.getDescription() != null ? tx.getDescription() : "");
                spendingData.add(entry);
            }

            Map<String, Object> chartResult = chartService.generateSpendingChart(spendingData, message);
            return ResponseEntity.ok(chartResult);
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    /** Returns a previously generated chart by its UUID. No auth needed — the UUID is an unguessable capability token. */
    @GetMapping("/{chartId}")
    public ResponseEntity<?> getChart(@PathVariable String chartId) {
        try {
            Map<String, Object> chart = chartService.getChart(chartId);
            return ResponseEntity.ok(chart);
        } catch (Exception e) {
            return ResponseEntity.status(404).body(Map.of("error", "Chart not found"));
        }
    }

    private User getCurrentUser() {
        String username = SecurityContextHolder.getContext().getAuthentication().getName();
        return userRepository.findByUsername(username).orElseThrow();
    }
}
