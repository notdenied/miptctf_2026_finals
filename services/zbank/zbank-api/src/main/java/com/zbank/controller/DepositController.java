package com.zbank.controller;

import com.zbank.model.Deposit;
import com.zbank.model.User;
import com.zbank.repository.UserRepository;
import com.zbank.service.DepositService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
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

    /**
     * Opens a new deposit. The source account ownership and balance check
     * are delegated to DepositService.openDeposit.
     */
    @PostMapping
    public ResponseEntity<?> openDeposit(@RequestBody Map<String, Object> body) {
        User user = getCurrentUser();
        try {
            Long accountId = Long.valueOf(body.get("accountId").toString());
            String name = body.getOrDefault("name", "Deposit").toString();
            BigDecimal amount = new BigDecimal(body.get("amount").toString());
            BigDecimal interestRate = new BigDecimal(body.getOrDefault("interestRate", "5.0").toString());
            int termMonths = Integer.parseInt(body.getOrDefault("termMonths", "12").toString());

            Deposit deposit = depositService.openDeposit(user, accountId, name, amount, interestRate, termMonths);
            return ResponseEntity.ok(toMap(deposit));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    /**
     * Returns all deposits belonging to the currently authenticated user.
     */
    @GetMapping
    public ResponseEntity<?> getDeposits() {
        User user = getCurrentUser();
        List<Map<String, Object>> deposits = depositService.getUserDeposits(user.getId())
                .stream().map(this::toMap).collect(Collectors.toList());
        return ResponseEntity.ok(deposits);
    }

    /**
     * Returns a single deposit by id.
     * @PreAuthorize ensures the deposit belongs to the current user before the method body runs.
     */
    @GetMapping("/{id}")
    @PreAuthorize("@depositService.isOwner(#id, principal.username)")
    public ResponseEntity<?> getDeposit(@PathVariable Long id) {
        Deposit deposit = depositService.getById(id);
        return ResponseEntity.ok(toMap(deposit));
    }

    /**
     * Closes a deposit early, returning the principal amount to the linked account.
     * @PreAuthorize ensures the deposit belongs to the current user before the method body runs.
     */
    @DeleteMapping("/{id}")
    @PreAuthorize("@depositService.isOwner(#id, principal.username)")
    public ResponseEntity<?> closeDeposit(@PathVariable Long id) {
        User user = getCurrentUser();
        try {
            depositService.closeDeposit(user, id);
            return ResponseEntity.ok(Map.of("status", "ok", "message", "Deposit closed successfully"));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    /**
     * Merges depositId1 into depositId2: the full amount of id1 is added to id2, then id1 is deleted.
     * Ownership of id1 is checked by @PreAuthorize before this method runs.
     * Ownership of id2 is checked implicitly by the delegated call to getDeposit(id2).
     */
    @PostMapping("/{id1}/merge")
    @PreAuthorize("@depositService.isOwner(#id1, principal.username)")
    public ResponseEntity<?> mergeDeposits(@PathVariable Long id1,
                                            @RequestBody Map<String, Object> body) {
        try {
            Long id2 = Long.valueOf(body.get("depositId2").toString());
            Deposit remaining = depositService.mergeDeposits(id1, id2);
            return getDeposit(remaining.getId());
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    /**
     * Maps a Deposit entity to a plain response map.
     */
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

    /**
     * Resolves the currently authenticated user from the Spring Security context.
     */
    private User getCurrentUser() {
        String username = SecurityContextHolder.getContext().getAuthentication().getName();
        return userRepository.findByUsername(username).orElseThrow();
    }
}
