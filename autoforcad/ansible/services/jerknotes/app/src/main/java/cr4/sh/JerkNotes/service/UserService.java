package cr4.sh.JerkNotes.service;

import cr4.sh.JerkNotes.model.User;
import cr4.sh.JerkNotes.model.MailUser;
import cr4.sh.JerkNotes.repository.MailUserRepository;
import cr4.sh.JerkNotes.repository.FileSystemRepository;
import cr4.sh.JerkNotes.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.nio.file.FileSystem;
import java.util.Optional;
import java.util.UUID;
import org.w3c.dom.UserDataHandler;

@Service
public class UserService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final MailUserRepository mailUserRepository;
    private final FileSystemRepository fileSystemRepository;

    @Autowired
    public UserService(UserRepository userRepository, PasswordEncoder passwordEncoder, MailUserRepository mailUserRepository, FileSystemRepository fileSystemRepository) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.mailUserRepository = mailUserRepository;
        this.fileSystemRepository = fileSystemRepository;

    }

    public void registerUser(String username, String rawPassword) throws Exception {
        User existingUser = userRepository.findByUsername(username);
        if (existingUser != null) {
            throw new Exception("Пользователь с такой почтой уже существует.");
        }
        User user = new User();
        user.setUsername(username);
        user.setUserId(UUID.randomUUID());
        user.setPassword(passwordEncoder.encode(rawPassword)); // Хэшируем пароль
        userRepository.save(user);

        fileSystemRepository.createUserDirectories(user);
    }

    public User saveUser(User user) {
        return userRepository.save(user);
    }

    public void updatePasswordUser(String username, String password) throws Exception {
        User user = userRepository.findUserByUsername(username);
        if (user == null) {
            throw new Exception("Пользователь с такой почтой не существует.");
        }
        user.setPassword(passwordEncoder.encode(password));
        userRepository.save(user);
    }
    
}
