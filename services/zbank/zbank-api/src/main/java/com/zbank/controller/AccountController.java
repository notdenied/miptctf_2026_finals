package com.zbank.controller;

import com.zbank.model.Account;
import com.zbank.model.User;
import com.zbank.repository.UserRepository;
import com.zbank.service.AccountService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/accounts")
@RequiredArgsConstructor
public class AccountController {

    private final AccountService accountService;
    private final UserRepository userRepository;

    /** Returns all accounts belonging to the current user. */
    @GetMapping
    public ResponseEntity<?> getAccounts() {
        User user = getCurrentUser();
        List<Map<String, Object>> accounts = accountService.getUserAccounts(user.getId())
                .stream()
                .map(this::toMap)
                .collect(Collectors.toList());
        return ResponseEntity.ok(accounts);
    }

    /** Creates a new account for the current user with the given name. */
    @PostMapping
    public ResponseEntity<?> createAccount(@RequestBody Map<String, String> body) {
        User user = getCurrentUser();
        String name = body.getOrDefault("name", "Новый счёт");
        Account account = accountService.createAccount(user, name);
        return ResponseEntity.ok(toMap(account));
    }

    /** Returns a single account by id. Returns 403 if the account belongs to another user. */
    @GetMapping("/{id}")
    public ResponseEntity<?> getAccount(@PathVariable Long id) {
        User user = getCurrentUser();
        Account account = accountService.getById(id);
        if (!account.getUser().getId().equals(user.getId())) {
            return ResponseEntity.status(403).body(Map.of("error", "Access denied"));
        }
        return ResponseEntity.ok(toMap(account));
    }

    private Map<String, Object> toMap(Account a) {
        return Map.of(
                "id", a.getId(),
                "name", a.getName(),
                "balance", a.getBalance(),
                "createdAt", a.getCreatedAt().toString()
        );
    }

    private User getCurrentUser() {
        String username = SecurityContextHolder.getContext().getAuthentication().getName();
        return userRepository.findByUsername(username).orElseThrow();
    }
}
