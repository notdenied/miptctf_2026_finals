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
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class DepositService {

    private final DepositRepository depositRepository;
    private final AccountRepository accountRepository;

    /**
     * Opens a new deposit for the given user.
     * Deducts the specified amount from the linked account and persists the deposit record.
     * Throws IllegalArgumentException if the account is not found, does not belong to the user,
     * or has insufficient funds.
     */
    @Transactional
    public Deposit openDeposit(User user, Long accountId, String name,
                                BigDecimal amount, BigDecimal interestRate, int termMonths) {
        if (amount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("Amount must be positive");
        }

        // Use SELECT FOR UPDATE to prevent race conditions on concurrent balance modifications
        Account account = accountRepository.findByIdForUpdate(accountId)
                .orElseThrow(() -> new IllegalArgumentException("Account not found"));

        if (!account.getUser().getId().equals(user.getId())) {
            throw new IllegalArgumentException("Account does not belong to user");
        }

        if (account.getBalance().compareTo(amount) < 0) {
            throw new IllegalArgumentException("Insufficient funds");
        }

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

    /**
     * Returns all deposits belonging to the given user, ordered by creation date descending.
     */
    public List<Deposit> getUserDeposits(Long userId) {
        return depositRepository.findByUserIdOrderByCreatedAtDesc(userId);
    }

    /**
     * Returns a deposit by id. Throws IllegalArgumentException if not found.
     */
    public Deposit getById(Long id) {
        return depositRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Deposit not found"));
    }

    /**
     * Guard method used by @PreAuthorize expressions.
     * Returns true if the deposit with the given id belongs to the user identified by username.
     * Returns false (rather than throwing) when the deposit is not found — Spring Security
     * will then respond with 403 automatically.
     */
    public boolean isOwner(Long depositId, String username) {
        Optional<Deposit> deposit = depositRepository.findById(depositId);
        return deposit.isPresent() && deposit.get().getUser().getUsername().equals(username);
    }

    /**
     * Merges two deposits: the amount of depositId1 is added to depositId2,
     * then depositId1 is deleted. depositId2 always survives.
     *
     * Ownership of depositId1 is verified by the caller via @PreAuthorize.
     * Ownership of depositId2 is verified by the controller when it calls getDeposit(id2).
     */
    @Transactional
    public Deposit mergeDeposits(Long depositId1, Long depositId2) {
        if (depositId1.equals(depositId2)) {
            throw new IllegalArgumentException("Cannot merge a deposit with itself");
        }

        Deposit d1 = getById(depositId1); // deposit to dissolve
        Deposit d2 = getById(depositId2); // deposit to keep (always the survivor)

        d2.setAmount(d2.getAmount().add(d1.getAmount()));
        depositRepository.save(d2);

        depositRepository.delete(d1);

        return d2;
    }

    /**
     * Closes a deposit early, returning only the principal (no interest) to the linked account.
     * Throws IllegalArgumentException if the deposit does not belong to the given user.
     */
    @Transactional
    public void closeDeposit(User user, Long depositId) {
        Deposit deposit = getById(depositId);

        if (!deposit.getUser().getId().equals(user.getId())) {
            throw new IllegalArgumentException("Deposit does not belong to user");
        }

        // SELECT FOR UPDATE to safely update the account balance
        Account account = accountRepository.findByIdForUpdate(deposit.getAccount().getId())
                .orElseThrow(() -> new IllegalArgumentException("Account not found"));

        account.setBalance(account.getBalance().add(deposit.getAmount()));
        accountRepository.save(account);

        depositRepository.delete(deposit);
    }
}
