package cr4.sh.JerkNotes.repository;

import cr4.sh.JerkNotes.model.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Long>, CustomUserRepository  {
    User findByUsername(String username);

}


