package cr4.sh.JerkNotes.service;

import cr4.sh.JerkNotes.config.AppConfig;
import cr4.sh.JerkNotes.model.Note;
import lombok.AllArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.UUID;
import java.io.IOException;
import java.nio.file.*;
import java.util.ArrayList;
import java.util.List;

@Service
@AllArgsConstructor
public class NoteService {
    private final AppConfig appConfig;
    public String saveNote(String text, String title, String userId) throws IOException {
        Path filePath = Paths.get(appConfig.getBaseNoteDir(), userId);
        Note note = new Note(text, title, filePath);
        return note.save();
    }

    public Note getNote(String uuid, String userId) throws IOException, ClassNotFoundException {
        Path filePath = Paths.get(appConfig.getBaseNoteDir(), userId, uuid);
        return new Note(filePath);
    }

    public String deleteNote(String uuid, String userId) throws IOException {
        Path filePath = Paths.get(appConfig.getBaseNoteDir(), userId, uuid);
        Note note = new Note(filePath);
        return note.delete();
    }

    public List<String> listNotes(String userId) throws IOException {
        List<String> noteIds = new ArrayList<>();
        Path dirPath = Paths.get(appConfig.getBaseNoteDir(),userId);

        try (DirectoryStream<Path> stream = Files.newDirectoryStream(dirPath)) {
            for (Path entry : stream) {
                if (!entry.toString().endsWith(".tar") && Files.isRegularFile(entry)) {
                    noteIds.add(entry.getFileName().toString());
                }
            }
        } catch (IOException e) {
            System.err.println("Error reading directory: " + e.getMessage());
        }
        return noteIds;
    }

    public String backupNotes(String userId) throws IOException {
        List<String> noteIds = listNotes(userId);

        for (String noteId : noteIds) {
            Path filePath = Paths.get(appConfig.getBaseNoteDir(), userId, noteId);
            Note note = new Note(filePath);
            note.backup();
        }
        return "Successfully backuped";
    }

    public String restoreNotes(String userId) throws IOException {
        List<String> backupFiles = new ArrayList<>();
        Path dirPath = Paths.get(appConfig.getBaseNoteDir(),userId);

        try (DirectoryStream<Path> stream = Files.newDirectoryStream(dirPath)) {
            for (Path entry : stream) {
                if (entry.toString().endsWith(".tar")) {
                    backupFiles.add(entry.toString());
                }
            }
        } catch (IOException e) {
            return "Failed to restore from backup";
        }

        for (String backupFile : backupFiles) {
            try {
                String uuidString = backupFile.substring(43, backupFile.length() - 4);
                UUID.fromString(uuidString);

                Note note = new Note();
                note.restoreFromBackup(backupFile);
            } catch (IllegalArgumentException | StringIndexOutOfBoundsException e) {
                // Trash
                continue;
            }
        }
        return "Successfully restored from backup";
    }
}
