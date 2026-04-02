package cr4.sh.JerkNotes.service;

import cr4.sh.JerkNotes.config.AppConfig;
import lombok.AllArgsConstructor;
import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.net.MalformedURLException;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

@Service
@AllArgsConstructor
public class FileService {
    private final AppConfig appConfig;
    public Resource download(String fileName, String userId) {
        try {
            Path filePath = Paths.get(appConfig.getBaseFileDir(), userId, fileName);
            Resource resource = new UrlResource(filePath.toUri());

            if(resource.exists()) {
                return resource;
            } else {
                return null;
            }
        } catch (MalformedURLException ex) {
            return null;
        }
    }

    public String upload(MultipartFile file, String userId) {
        try {
            if (file.isEmpty()) {
                return "Failed to upload";
            }
            String fileName = StringUtils.cleanPath(file.getOriginalFilename());

            Path outputPath = Paths.get(appConfig.getBaseFileDir(), userId);
            Files.copy(file.getInputStream(), outputPath.resolve(fileName));
            return "Successfully uploaded";
        } catch (IOException | NullPointerException e) {
            return "Failed to upload";
        }
    }

    public List<String> listFiles(String userId) throws IOException {
        List<String> noteIds = new ArrayList<>();
        Path dirPath = Paths.get(appConfig.getBaseFileDir(),userId);

        try (DirectoryStream<Path> stream = Files.newDirectoryStream(dirPath)) {
            for (Path entry : stream) {
                noteIds.add(entry.getFileName().toString());
            }
        } catch (IOException e) {
            return new ArrayList<>();
        }
        return noteIds;
    }
}
