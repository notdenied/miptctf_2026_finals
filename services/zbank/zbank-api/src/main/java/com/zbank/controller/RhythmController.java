package com.zbank.controller;

import com.zbank.model.Friendship;
import com.zbank.model.RhythmPost;
import com.zbank.model.User;
import com.zbank.repository.UserRepository;
import com.zbank.service.RhythmService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/rhythm")
@RequiredArgsConstructor
public class RhythmController {

    private final RhythmService rhythmService;
    private final UserRepository userRepository;

    @PostMapping("/posts")
    public ResponseEntity<?> createPost(@RequestBody Map<String, Object> body) {
        User user = getCurrentUser();
        try {
            String content = body.get("content").toString();
            boolean isPrivate = Boolean.parseBoolean(body.getOrDefault("isPrivate", "false").toString());

            RhythmPost post = rhythmService.createPost(user, content, isPrivate);
            return ResponseEntity.ok(postToMap(post));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/posts")
    public ResponseEntity<?> getMyPosts() {
        User user = getCurrentUser();
        List<Map<String, Object>> posts = rhythmService.getUserPosts(user.getId(), user.getId())
                .stream().map(this::postToMap).collect(Collectors.toList());
        return ResponseEntity.ok(posts);
    }

    @GetMapping("/posts/user/{username}")
    public ResponseEntity<?> getUserPosts(@PathVariable String username) {
        User viewer = getCurrentUser();
        User target = userRepository.findByUsername(username)
                .orElseThrow(() -> new IllegalArgumentException("User not found"));
        List<Map<String, Object>> posts = rhythmService.getUserPosts(target.getId(), viewer.getId())
                .stream().map(this::postToMap).collect(Collectors.toList());
        return ResponseEntity.ok(posts);
    }

    @GetMapping("/feed")
    public ResponseEntity<?> getFeed() {
        User user = getCurrentUser();
        List<Map<String, Object>> posts = rhythmService.getFeed(user.getId())
                .stream().map(this::postToMap).collect(Collectors.toList());
        return ResponseEntity.ok(posts);
    }

    @PostMapping("/friends/request")
    public ResponseEntity<?> sendFriendRequest(@RequestBody Map<String, String> body) {
        User user = getCurrentUser();
        try {
            String targetUsername = body.get("username");
            Friendship friendship = rhythmService.sendFriendRequest(user, targetUsername);
            return ResponseEntity.ok(friendshipToMap(friendship));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    @PostMapping("/friends/accept")
    public ResponseEntity<?> acceptFriendRequest(@RequestBody Map<String, Object> body) {
        User user = getCurrentUser();
        try {
            Long friendshipId = Long.valueOf(body.get("friendshipId").toString());
            Friendship friendship = rhythmService.acceptFriendRequest(friendshipId, user.getId());
            return ResponseEntity.ok(friendshipToMap(friendship));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/friends")
    public ResponseEntity<?> getFriends() {
        User user = getCurrentUser();
        List<Map<String, Object>> friends = rhythmService.getFriendships(user.getId())
                .stream().map(this::friendshipToMap).collect(Collectors.toList());
        return ResponseEntity.ok(friends);
    }

    @GetMapping("/friends/pending")
    public ResponseEntity<?> getPendingRequests() {
        User user = getCurrentUser();
        List<Map<String, Object>> pending = rhythmService.getPendingRequests(user.getId())
                .stream().map(this::friendshipToMap).collect(Collectors.toList());
        return ResponseEntity.ok(pending);
    }

    private Map<String, Object> postToMap(RhythmPost post) {
        return Map.of(
                "id", post.getId(),
                "content", post.getContent(),
                "isPrivate", post.getIsPrivate(),
                "username", post.getUser().getUsername(),
                "createdAt", post.getCreatedAt().toString()
        );
    }

    private Map<String, Object> friendshipToMap(Friendship f) {
        return Map.of(
                "id", f.getId(),
                "requester", f.getRequester().getUsername(),
                "accepter", f.getAccepter().getUsername(),
                "status", f.getStatus(),
                "createdAt", f.getCreatedAt().toString()
        );
    }

    private User getCurrentUser() {
        String username = SecurityContextHolder.getContext().getAuthentication().getName();
        return userRepository.findByUsername(username).orElseThrow();
    }
}
