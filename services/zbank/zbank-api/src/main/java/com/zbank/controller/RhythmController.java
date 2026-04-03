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

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/rhythm")
@RequiredArgsConstructor
public class RhythmController {

    private final RhythmService rhythmService;
    private final UserRepository userRepository;

    // ── Posts ─────────────────────────────────────────────────────────────────

    /**
     * Creates a new post. Accepts either:
     *   - "visibility": "PUBLIC" | "FRIENDS" | "PROTECTED"
     *   - "isPrivate": true/false  (legacy, maps to FRIENDS/PUBLIC)
     * PROTECTED posts receive an auto-generated 8-char hex accessKey in the response.
     */
    @PostMapping("/posts")
    public ResponseEntity<?> createPost(@RequestBody Map<String, Object> body) {
        User user = getCurrentUser();
        try {
            String content = body.get("content").toString();

            // Resolve visibility: explicit field takes priority over legacy isPrivate
            String visibility;
            if (body.containsKey("visibility")) {
                visibility = body.get("visibility").toString().toUpperCase();
            } else {
                boolean isPrivate = Boolean.parseBoolean(
                        body.getOrDefault("isPrivate", "false").toString());
                visibility = isPrivate ? "FRIENDS" : "PUBLIC";
            }

            RhythmPost post = rhythmService.createPost(user, content, visibility);
            return ResponseEntity.ok(postToMapWithSecret(post));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    /** Returns all posts created by the current user (including private ones). */
    @GetMapping("/posts")
    public ResponseEntity<?> getMyPosts() {
        User user = getCurrentUser();
        List<Map<String, Object>> posts = rhythmService.getUserPosts(user.getId(), user.getId())
                .stream().map(this::postToMap).collect(Collectors.toList());
        return ResponseEntity.ok(posts);
    }

    /** Returns public posts of another user; also includes private posts if they are friends with the viewer. */
    @GetMapping("/posts/user/{username}")
    public ResponseEntity<?> getUserPosts(@PathVariable String username) {
        User viewer = getCurrentUser();
        User target = userRepository.findByUsername(username)
                .orElseThrow(() -> new IllegalArgumentException("User not found"));
        List<Map<String, Object>> posts = rhythmService.getUserPosts(target.getId(), viewer.getId())
                .stream().map(this::postToMap).collect(Collectors.toList());
        return ResponseEntity.ok(posts);
    }

    /** Returns the combined post feed of all accepted friends of the current user. */
    @GetMapping("/feed")
    public ResponseEntity<?> getFeed() {
        User user = getCurrentUser();
        List<Map<String, Object>> posts = rhythmService.getFeed(user.getId())
                .stream().map(this::postToMap).collect(Collectors.toList());
        return ResponseEntity.ok(posts);
    }

    /**
     * Searches posts accessible to the current user.
     */
    @PostMapping("/posts/search")
    public ResponseEntity<?> searchPosts(@RequestBody Map<String, String> filters) {
        User user = getCurrentUser();
        try {
            List<Map<String, Object>> results = rhythmService
                    .searchPosts(user.getId(), filters)
                    .stream().map(this::postToMap).collect(Collectors.toList());
            return ResponseEntity.ok(results);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.status(404).body(Map.of("error", e.getMessage()));
        }
    }

    /**
     * Returns a single post by its UUID (shareable link).
     * Access rules:
     *   PUBLIC    – always accessible
     *   FRIENDS   – owner or accepted friend only
     *   PROTECTED – owner always; others must supply ?key={8-char accessKey}
     * The owner always sees the accessKey in the response.
     */
    @GetMapping("/posts/{postUuid}")
    public ResponseEntity<?> getPostByUuid(@PathVariable String postUuid,
                                            @RequestParam(required = false) String key) {
        User user = getCurrentUser();
        try {
            RhythmPost post = rhythmService.getPostByUuid(postUuid, key, user.getId());
            Map<String, Object> result = postToMap(post);
            // Return accessKey to the owner so they can re-share it
            if (post.getUser().getId().equals(user.getId()) && post.getAccessKey() != null) {
                result = new LinkedHashMap<>(result);
                result.put("accessKey", post.getAccessKey());
            }
            return ResponseEntity.ok(result);
        } catch (SecurityException e) {
            return ResponseEntity.status(403).body(Map.of("error", e.getMessage()));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.status(404).body(Map.of("error", e.getMessage()));
        }
    }

    // ── Friends ───────────────────────────────────────────────────────────────

    /** Sends a friend request to another user by username. */
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

    /** Accepts an incoming friend request by its id. Only the addressee may accept. */
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

    /** Returns all accepted friendships of the current user. */
    @GetMapping("/friends")
    public ResponseEntity<?> getFriends() {
        User user = getCurrentUser();
        List<Map<String, Object>> friends = rhythmService.getFriendships(user.getId())
                .stream().map(this::friendshipToMap).collect(Collectors.toList());
        return ResponseEntity.ok(friends);
    }

    /** Returns friend requests received by the current user that are still pending. */
    @GetMapping("/friends/pending")
    public ResponseEntity<?> getPendingRequests() {
        User user = getCurrentUser();
        List<Map<String, Object>> pending = rhythmService.getPendingRequests(user.getId())
                .stream().map(this::friendshipToMap).collect(Collectors.toList());
        return ResponseEntity.ok(pending);
    }

    // ── Serialization helpers ─────────────────────────────────────────────────

    private Map<String, Object> postToMap(RhythmPost post) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id",         post.getId());
        m.put("postUuid",   post.getPostUuid());
        m.put("content",    post.getContent());
        m.put("visibility", post.getVisibility());
        m.put("username",   post.getUser().getUsername());
        m.put("createdAt",  post.getCreatedAt().toString());
        return m;
    }

    /** Like postToMap, but also includes accessKey (returned to the creator). */
    private Map<String, Object> postToMapWithSecret(RhythmPost post) {
        Map<String, Object> m = postToMap(post);
        if (post.getAccessKey() != null) {
            m.put("accessKey", post.getAccessKey());
        }
        return m;
    }

    private Map<String, Object> friendshipToMap(Friendship f) {
        return Map.of(
                "id",        f.getId(),
                "requester", f.getRequester().getUsername(),
                "accepter",  f.getAccepter().getUsername(),
                "status",    f.getStatus(),
                "createdAt", f.getCreatedAt().toString()
        );
    }

    private User getCurrentUser() {
        String username = SecurityContextHolder.getContext().getAuthentication().getName();
        return userRepository.findByUsername(username).orElseThrow();
    }
}
