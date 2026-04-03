package com.zbank.controller;

import com.zbank.model.Account;
import com.zbank.model.Fundraising;
import com.zbank.model.User;
import com.zbank.repository.UserRepository;
import com.zbank.service.AccountService;
import com.zbank.service.FundraisingService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.Map;

@RestController
@RequestMapping("/api/fundraising")
@RequiredArgsConstructor
public class FundraisingController {

    private final FundraisingService fundraisingService;
    private final AccountService accountService;
    private final UserRepository userRepository;

    /** Creates a new fundraising campaign linked to the given account. Returns a shareable link code. */
    @PostMapping
    public ResponseEntity<?> create(@RequestBody Map<String, Object> body) {
        User user = getCurrentUser();
        try {
            Long accountId = Long.valueOf(body.get("accountId").toString());
            String title = body.get("title").toString();
            String description = body.getOrDefault("description", "").toString();
            BigDecimal targetAmount = body.containsKey("targetAmount") ?
                    new BigDecimal(body.get("targetAmount").toString()) : null;

            Account account = accountService.getById(accountId);
            if (!account.getUser().getId().equals(user.getId())) {
                return ResponseEntity.status(403).body(Map.of("error", "Account is not yours"));
            }

            Fundraising fundraising = fundraisingService.create(account, title, description, targetAmount);
            return ResponseEntity.ok(Map.of(
                    "id", fundraising.getId(),
                    "linkCode", fundraising.getLinkCode(),
                    "title", fundraising.getTitle(),
                    "description", fundraising.getDescription() != null ? fundraising.getDescription() : "",
                    "targetAmount", fundraising.getTargetAmount() != null ? fundraising.getTargetAmount() : 0,
                    "active", fundraising.getActive()
            ));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    /** Returns public info about a fundraising campaign by its link code. No authentication required. */
    @GetMapping("/{code}/view")
    public ResponseEntity<?> view(@PathVariable String code) {
        try {
            Fundraising f = fundraisingService.getByCode(code);
            return ResponseEntity.ok(Map.of(
                    "linkCode", f.getLinkCode(),
                    "title", f.getTitle(),
                    "description", f.getDescription() != null ? f.getDescription() : "",
                    "targetAmount", f.getTargetAmount() != null ? f.getTargetAmount() : 0,
                    "active", f.getActive(),
                    "accountId", f.getAccount().getId()
            ));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    /** Transfers the given amount from the contributor's account to the fundraising campaign's account. */
    @PostMapping("/{code}/contribute")
    public ResponseEntity<?> contribute(@PathVariable String code, @RequestBody Map<String, Object> body) {
        try {
            Long fromAccountId = Long.valueOf(body.get("fromAccountId").toString());
            BigDecimal amount = new BigDecimal(body.get("amount").toString());

            fundraisingService.contribute(code, fromAccountId, amount);
            return ResponseEntity.ok(Map.of("status", "ok", "message", "Contribution successful"));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    private User getCurrentUser() {
        String username = SecurityContextHolder.getContext().getAuthentication().getName();
        return userRepository.findByUsername(username).orElseThrow();
    }
}
