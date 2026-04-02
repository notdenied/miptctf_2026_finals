package cr4.sh.JerkNotes.controller;

import cr4.sh.JerkNotes.config.MyUserDetails;
import cr4.sh.JerkNotes.model.Note;
import cr4.sh.JerkNotes.service.NoteService;
import lombok.AllArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/notes")
@AllArgsConstructor
public class NoteController {
    private final NoteService noteService;

    @PostMapping("/add")
    public String addNote(@RequestParam String text, @RequestParam(required = false) String title) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        MyUserDetails MyUserDetails = (MyUserDetails) authentication.getPrincipal();
        if (text == null || text.isEmpty()){
            return "Failed to create note";
        }
        if (title == null || title.isEmpty()) {
            title = "Заметка";
        }
        try {
            return noteService.saveNote(text, title, MyUserDetails.getUserId());
        } catch (IOException e) {
            return "Failed to create note";
        }
    }

    @GetMapping("/get")
    public Note getNote(@RequestParam UUID id) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        MyUserDetails MyUserDetails = (MyUserDetails) authentication.getPrincipal();

        try {
            return noteService.getNote(id.toString(), MyUserDetails.getUserId());
        } catch (IOException | ClassNotFoundException e) {
            return null;
        }
    }

    @DeleteMapping("/delete")
    public String deleteNote(@RequestParam UUID id) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        MyUserDetails MyUserDetails = (MyUserDetails) authentication.getPrincipal();

        try {
            return noteService.deleteNote(id.toString(), MyUserDetails.getUserId());
        } catch (IOException e) {
            return "Failed to delete";
        }
    }

    @GetMapping("/list")
    public List<String> listNotes() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        MyUserDetails MyUserDetails = (MyUserDetails) authentication.getPrincipal();

        try {
            return noteService.listNotes(MyUserDetails.getUserId());
        } catch (IOException e) {
            return new ArrayList<>();
        }
    }

    @PostMapping("/backup")
    public String backupNotes() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        MyUserDetails MyUserDetails = (MyUserDetails) authentication.getPrincipal();

        try {
            return noteService.backupNotes(MyUserDetails.getUserId());
        } catch (IOException e) {
            return "Failed to backup";
        }
    }

    @PostMapping("/restore")
    public String restoreNotes() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        MyUserDetails MyUserDetails = (MyUserDetails) authentication.getPrincipal();

        try {
            return noteService.restoreNotes(MyUserDetails.getUserId());
        } catch (IOException e) {
            return "Failed to restore from backup";
        }
    }
}
