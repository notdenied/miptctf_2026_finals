package com.zbank.service;

import com.zbank.model.Account;
import com.zbank.model.Fundraising;
import com.zbank.repository.AccountRepository;
import com.zbank.repository.FundraisingRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class FundraisingService {

    private final FundraisingRepository fundraisingRepository;
    private final AccountRepository accountRepository;

    @Transactional
    public Fundraising create(Account account, String title, String description, BigDecimal targetAmount) {
        Fundraising fundraising = Fundraising.builder()
                .account(account)
                .linkCode(UUID.randomUUID().toString().substring(0, 8))
                .title(title)
                .description(description)
                .targetAmount(targetAmount)
                .build();
        return fundraisingRepository.save(fundraising);
    }

    public Fundraising getByCode(String code) {
        return fundraisingRepository.findByLinkCode(code)
                .orElseThrow(() -> new IllegalArgumentException("Fundraising not found"));
    }

    @Transactional
    public void contribute(String code, Long fromAccountId, BigDecimal amount) {
        if (amount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("Amount must be positive");
        }

        Fundraising fundraising = getByCode(code);
        if (!fundraising.getActive()) {
            throw new IllegalArgumentException("Fundraising is no longer active");
        }

        Long toAccountId = fundraising.getAccount().getId();

        Long firstId = Math.min(fromAccountId, toAccountId);
        Long secondId = Math.max(fromAccountId, toAccountId);

        Account first = accountRepository.findByIdForUpdate(firstId)
                .orElseThrow(() -> new IllegalArgumentException("Account not found"));
        Account second = accountRepository.findByIdForUpdate(secondId)
                .orElseThrow(() -> new IllegalArgumentException("Account not found"));

        Account fromAccount = fromAccountId.equals(firstId) ? first : second;
        Account toAccount = toAccountId.equals(firstId) ? first : second;

        if (fromAccount.getBalance().compareTo(amount) < 0) {
            throw new IllegalArgumentException("Insufficient funds");
        }

        fromAccount.setBalance(fromAccount.getBalance().subtract(amount));
        toAccount.setBalance(toAccount.getBalance().add(amount));

        accountRepository.save(fromAccount);
        accountRepository.save(toAccount);
    }
}
