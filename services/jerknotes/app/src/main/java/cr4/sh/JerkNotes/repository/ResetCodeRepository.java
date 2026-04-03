package cr4.sh.JerkNotes.repository;

import cr4.sh.JerkNotes.model.RecoveryCode;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface ResetCodeRepository extends JpaRepository<RecoveryCode, Long> {
    
    List<RecoveryCode> findByUserId(Long userId);

    Optional<RecoveryCode> findByCode(String code);

    void deleteByUserId(Long userId);


    @Modifying
    @Transactional
    @Query("DELETE FROM RecoveryCode r WHERE r.createdAt < :expirationTime")
    void deleteExpiredCodes(LocalDateTime expirationTime);
}
