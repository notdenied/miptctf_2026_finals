package cr4.sh.JerkNotes.repository;

import org.springframework.data.jpa.repository.JpaRepository;

import cr4.sh.JerkNotes.model.Mail;

public interface MailRepository extends JpaRepository<Mail, String> {
    Mail findByRecipientId_Email(String email);
}
