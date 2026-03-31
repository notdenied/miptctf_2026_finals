package com.zbank.service;

import com.zbank.model.Account;
import com.zbank.model.Deposit;
import com.zbank.model.User;
import com.zbank.repository.AccountRepository;
import com.zbank.repository.DepositRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;

@Service
@RequiredArgsConstructor
public class DepositService {

    private final DepositRepository depositRepository;
    private final AccountRepository accountRepository;

    @Transactional
    public Deposit openDeposit(User user, Long accountId, String name,
                                BigDecimal amount, BigDecimal interestRate, int termMonths) {
        if (amount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("Amount must be positive");
        }

        Account account = accountRepository.findByIdForUpdate(accountId)
                .orElseThrow(() -> new IllegalArgumentException("Account not found"));

        if (!account.getUser().getId().equals(user.getId())) {
            throw new IllegalArgumentException("Account does not belong to user");
        }

        if (account.getBalance().compareTo(amount) < 0) {
            throw new IllegalArgumentException("Insufficient funds");
        }

        // Deduct from account
        account.setBalance(account.getBalance().subtract(amount));
        accountRepository.save(account);

        Deposit deposit = Deposit.builder()
                .user(user)
                .account(account)
                .name(name)
                .amount(amount)
                .interestRate(interestRate)
                .termMonths(termMonths)
                .build();
        return depositRepository.save(deposit);
    }

    public List<Deposit> getUserDeposits(Long userId) {
        return depositRepository.findByUserIdOrderByCreatedAtDesc(userId);
    }

    public Deposit getById(Long id) {
        return depositRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Deposit not found"));
    }
}
