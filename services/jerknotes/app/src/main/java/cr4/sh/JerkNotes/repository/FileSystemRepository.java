package cr4.sh.JerkNotes.repository;

import cr4.sh.JerkNotes.config.AppConfig;
import cr4.sh.JerkNotes.model.User;
import lombok.AllArgsConstructor;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

@AllArgsConstructor
@Service
public class FileSystemRepository {
    private final AppConfig appConfig;

    public void createUserDirectories(User user) throws Exception {
        String baseNoteDir = appConfig.getBaseNoteDir();
        String baseFileDir = appConfig.getBaseFileDir();

        if (baseNoteDir == null || baseNoteDir.isEmpty() || baseFileDir == null || baseFileDir.isEmpty()) {
            throw new Exception("Base dirs are not configured");
        }

        Path noteDir = Paths.get(appConfig.getBaseNoteDir(), user.getUserId().toString());
        Path fileDir = Paths.get(appConfig.getBaseFileDir(), user.getUserId().toString());
        try {
            Files.createDirectories(noteDir);
            Files.createDirectories(fileDir);
        } catch (IOException e) {
            throw new Exception("Error creating directories': " + e.getMessage());
        } catch (SecurityException e){
            throw new Exception("Error creating directory: Insufficient permissions.");
        }
    }
}
