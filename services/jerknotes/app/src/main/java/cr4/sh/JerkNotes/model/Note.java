package cr4.sh.JerkNotes.model;

import lombok.*;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.UUID;

@Data
public class Note implements Serializable {
    private String filePath;
    private UUID noteId;
    private String text;
    private String title;

    public Note() {
    }


    public Note(String text, String title, Path userBaseNoteDir) {
        this.text = text;
        this.title = title;
        this.noteId = UUID.randomUUID();
        this.filePath = Paths.get(userBaseNoteDir.toString(), this.noteId.toString()).toString();
    }

    public Note(Path notePath) throws IOException {
        if (!Files.exists(notePath)) {
            throw new IOException("Note not found");
        }

        try (ObjectInputStream ois = new ObjectInputStream(Files.newInputStream(notePath))) {
            Note note = (Note) ois.readObject();
            this.text = note.getText();
            this.title = note.getTitle();
            this.noteId = note.getNoteId();
            this.filePath = note.getFilePath();

        } catch (IOException | ClassNotFoundException e) {
            throw new IOException("Error loading note: " + e.getMessage(), e);
        }
    }


    public String save() throws IOException {
        try (ObjectOutputStream oos = new ObjectOutputStream(Files.newOutputStream(Paths.get(filePath), StandardOpenOption.CREATE_NEW))) {
            oos.writeObject(this);
            return "Note Created: " + noteId;
        } catch (IOException e) {
            throw new IOException("Error saving note: " + e.getMessage(), e);
        }
    }

    public String delete() throws IOException {
        if (!Files.exists(Paths.get(filePath))) {
            return "no such file";
        }

        File file = new File(filePath);
        if (!file.delete()) {
            return "failed to delete";}
        return "deleted";
    }

    public void backup() {
        try {
            String[] cmd = {"bash", "-c", String.format("tar -cf %s.tar %s", filePath, filePath)};
            Process p = Runtime.getRuntime().exec(cmd);
            int code = p.waitFor();
            if (code != 0) {
                throw new IOException("Failed to backup");
            }
        }
        catch(IOException | InterruptedException e) {
            return;
        }
    }

    public void restoreFromBackup(String backFile) {
        try {
            String[] cmd = {"bash", "-c", String.format("tar -xf %s", backFile)};
            Process p = Runtime.getRuntime().exec(cmd);
            int code = p.waitFor();
            if (code != 0) {
                throw new IOException("Failed to backup");
            }
        }
        catch(IOException | InterruptedException e) {
            return;
        }
    }
}
