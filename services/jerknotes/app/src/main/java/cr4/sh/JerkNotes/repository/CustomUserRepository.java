package cr4.sh.JerkNotes.repository;

import cr4.sh.JerkNotes.model.User;

public interface CustomUserRepository {
    User findUserByUsername(String username);
}
