package cr4.sh.JerkNotes.service;


import java.sql.Timestamp;
import java.time.Instant;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.Random;
import java.time.Duration;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import cr4.sh.JerkNotes.model.Mail;
import cr4.sh.JerkNotes.model.MailUser;
import cr4.sh.JerkNotes.model.RecoveryCode;
import cr4.sh.JerkNotes.model.User;
import cr4.sh.JerkNotes.repository.MailRepository;
import cr4.sh.JerkNotes.repository.MailUserRepository;
import cr4.sh.JerkNotes.repository.ResetCodeRepository;
import cr4.sh.JerkNotes.repository.UserRepository;


@Service
public class ResetPassword {
    private final UserRepository userRepository;
    private final MailRepository mailRepository;
    private final MailUserRepository mailUserRepository;
    private final ResetCodeRepository resetCodeRepository;
    private static final String CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    private static final int STRING_LENGTH = 10;

    @Autowired
    public ResetPassword(UserRepository userRepository, MailRepository mailRepository, MailUserRepository mailUserRepository, ResetCodeRepository resetCodeRepository) {
        this.userRepository = userRepository;
        this.mailRepository = mailRepository;
        this.mailUserRepository = mailUserRepository;
        this.resetCodeRepository = resetCodeRepository;
    }

    public void SendReset(String username) throws Exception{
        User existUserApp = userRepository.findByUsername(username);
        MailUser existUserMail = mailUserRepository.findByEmail(username);
        if (existUserApp == null || existUserMail == null) {
            throw new Exception("Пользователь не найден");
        }
        String resCode = generateRandomString();
        RecoveryCode resCodeObj = new RecoveryCode();

        resCodeObj.setCode(resCode);
        resCodeObj.setUser(existUserApp);
        resCodeObj.setCreatedAt(LocalDateTime.now());
        resetCodeRepository.save(resCodeObj);

        Mail letter = new Mail();
        letter.setSubject("Password Reset");
        Timestamp currentTimestamp = Timestamp.from(Instant.now());
        letter.setTimestamp(currentTimestamp);
        letter.setRecipientId(existUserMail);
        letter.setContent(String.format("Here is your reset code: %s. He is will alive 20 minutes.", resCode ));
        mailRepository.save(letter);

        LocalDateTime expirationTime = LocalDateTime.now().minusMinutes(20);
        resetCodeRepository.deleteExpiredCodes(expirationTime);
    }
    
    public Mail saveMail(Mail letter) {
        return mailRepository.save(letter);
    }

    public boolean CheckResetCode(String code, String username) {
        User user = userRepository.findByUsername(username);
        if (user == null) {
            return false;
        }
    
        List<RecoveryCode> codes = resetCodeRepository.findByUserId(user.getId());
        if (codes.isEmpty()) {
            return false;
        }
    
        LocalDateTime now = LocalDateTime.now();
    
        for (RecoveryCode recoveryCode : codes) {
            if (recoveryCode.getCode().equals(code)) {
                Duration duration = Duration.between(recoveryCode.getCreatedAt(), now);
                if (duration.toMinutes() <= 20) {
                    resetCodeRepository.deleteById(recoveryCode.getId());
                    return true; 
                }
            }
        }
    
        return false;
    }

    public String generateRandomString() {
        long currentTimeSeconds = Instant.now().getEpochSecond();
        Random random = new Random(currentTimeSeconds);
        StringBuilder randomString = new StringBuilder(STRING_LENGTH);
        for (int i = 0; i < STRING_LENGTH; i++) {
            int index = random.nextInt(CHARACTERS.length());
            randomString.append(CHARACTERS.charAt(index));
        }
        return randomString.toString();
    }

}

