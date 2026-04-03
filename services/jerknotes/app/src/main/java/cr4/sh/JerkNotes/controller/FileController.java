package cr4.sh.JerkNotes.controller;

import cr4.sh.JerkNotes.config.MyUserDetails;
import cr4.sh.JerkNotes.model.Note;
import cr4.sh.JerkNotes.service.FileService;
import cr4.sh.JerkNotes.service.NoteService;
import lombok.AllArgsConstructor;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/files")
@AllArgsConstructor
public class FileController {
    private final FileService fileService;
    @GetMapping(value = "/download/{fileName:.+}")
    public ResponseEntity<Resource> download(@PathVariable String fileName) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        MyUserDetails MyUserDetails = (MyUserDetails) authentication.getPrincipal();
        Resource resource = fileService.download(fileName, MyUserDetails.getUserId());
        if (resource == null) {
            return ResponseEntity.ok().body(null);
        }

        String contentType = null;
        try {
            contentType = Files.probeContentType(resource.getFile().toPath());
        } catch (IOException ex) {
            return null;
        }
        return ResponseEntity.ok()
                .contentType(contentType != null ? MediaType.parseMediaType(contentType) : MediaType.APPLICATION_OCTET_STREAM)
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + resource.getFilename() + "\"")
                .body(resource);
    }


    @PostMapping(value = "/upload")
    public ResponseEntity<String> upload(@RequestParam("file") MultipartFile file) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        MyUserDetails MyUserDetails = (MyUserDetails) authentication.getPrincipal();

        return ResponseEntity.ok().body(fileService.upload(file, MyUserDetails.getUserId()));
    }

    @GetMapping("/list")
    public List<String> listNotes() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        MyUserDetails MyUserDetails = (MyUserDetails) authentication.getPrincipal();

        try {
            return fileService.listFiles(MyUserDetails.getUserId());
        } catch (IOException e) {
            return new ArrayList<>();
        }
    }
}
