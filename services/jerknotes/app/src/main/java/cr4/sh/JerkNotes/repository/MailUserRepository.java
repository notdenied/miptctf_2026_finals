package cr4.sh.JerkNotes.repository;

import org.springframework.data.jpa.repository.JpaRepository;

import cr4.sh.JerkNotes.model.MailUser;

public interface MailUserRepository extends JpaRepository<MailUser, Long> {
    MailUser findByEmail(String email);
}
