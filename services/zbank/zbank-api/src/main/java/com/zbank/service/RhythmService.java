package com.zbank.service;

import com.zbank.model.Friendship;
import com.zbank.model.RhythmPost;
import com.zbank.model.User;
import com.zbank.repository.FriendshipRepository;
import com.zbank.repository.RhythmPostRepository;
import com.zbank.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class RhythmService {

    private final RhythmPostRepository postRepository;
    private final FriendshipRepository friendshipRepository;
    private final UserRepository userRepository;

    private static final SecureRandom SECURE_RANDOM = new SecureRandom();
    private static final List<String> VALID_VISIBILITIES = List.of("PUBLIC", "FRIENDS", "PROTECTED");

    // ── Post management ───────────────────────────────────────────────────────

    /**
     * Creates a new post. Visibility must be PUBLIC, FRIENDS, or PROTECTED.
     * PROTECTED posts are assigned a random 8-char hex access key automatically.
     */
    @Transactional
    public RhythmPost createPost(User user, String content, String visibility) {
        if (content == null || content.isBlank()) {
            throw new IllegalArgumentException("Post content cannot be empty");
        }
        if (content.length() > 200) {
            throw new IllegalArgumentException("Post content must be at most 200 characters");
        }
        if (!VALID_VISIBILITIES.contains(visibility)) {
            throw new IllegalArgumentException("visibility must be PUBLIC, FRIENDS, or PROTECTED");
        }

        String accessKey = "PROTECTED".equals(visibility) ? generateAccessKey() : null;

        RhythmPost post = RhythmPost.builder()
                .user(user)
                .content(content)
                .postUuid(UUID.randomUUID().toString())
                .visibility(visibility)
                .accessKey(accessKey)
                .build();
        return postRepository.save(post);
    }

    /**
     * Returns posts visible to the viewer for the given user's profile.
     * Friends see FRIENDS+PUBLIC posts; strangers see only PUBLIC posts.
     */
    public List<RhythmPost> getUserPosts(Long userId, Long viewerId) {
        if (userId.equals(viewerId)) {
            return postRepository.findByUserIdOrderByCreatedAtDesc(userId);
        }

        boolean isFriend = friendshipRepository.findFriendship(userId, viewerId)
                .map(f -> "ACCEPTED".equals(f.getStatus()))
                .orElse(false);

        return isFriend
                ? postRepository.findByUserIdOrderByCreatedAtDesc(userId)
                : postRepository.findPublicPostsByUserId(userId);
    }

    /** Returns the combined feed of the user and their accepted friends. */
    public List<RhythmPost> getFeed(Long userId) {
        List<Long> friendIds = getFriendIds(userId);
        List<Long> allIds = new ArrayList<>(friendIds);
        allIds.add(userId);
        return postRepository.findFeedPosts(
                userId,
                friendIds.isEmpty() ? List.of(-1L) : friendIds,
                allIds);
    }

    /**
     * Retrieves a post by its UUID, enforcing access control:
     * <ul>
     *   <li>PUBLIC  – always accessible</li>
     *   <li>FRIENDS – accessible to owner and accepted friends</li>
     *   <li>PROTECTED – accessible to owner; others must supply the correct key</li>
     * </ul>
     */
    public RhythmPost getPostByUuid(String postUuid, String providedKey, Long viewerId) {
        RhythmPost post = postRepository.findByPostUuid(postUuid)
                .orElseThrow(() -> new IllegalArgumentException("Post not found"));

        switch (post.getVisibility()) {
            case "PUBLIC":
                return post;

            case "FRIENDS":
                if (post.getUser().getId().equals(viewerId)) return post;
                boolean isFriend = friendshipRepository.findFriendship(post.getUser().getId(), viewerId)
                        .map(f -> "ACCEPTED".equals(f.getStatus()))
                        .orElse(false);
                if (isFriend) return post;
                throw new SecurityException("Access denied");

            case "PROTECTED":
                if (post.getUser().getId().equals(viewerId)) return post;
                if (providedKey != null && providedKey.equals(post.getAccessKey())) return post;
                throw new SecurityException("Access denied — valid key required");

            default:
                throw new SecurityException("Access denied");
        }
    }

    /**
     * Searches posts accessible to the viewer using a flexible filter map.
     */
    public List<RhythmPost> searchPosts(Long viewerId, Map<String, String> filters) {
        List<RhythmPost> all = postRepository.findAll();

        List<RhythmPost> matched = all.stream()
                .filter(post -> filters.entrySet().stream().allMatch(entry -> {
                    try {
                        String value = getFieldValue(post, entry.getKey());
                        return value != null && value.startsWith(entry.getValue());
                    } catch (Exception ignored) {
                        return true; // unknown / inaccessible field — skip
                    }
                }))
                .collect(Collectors.toList());

        if (matched.isEmpty()) {
            throw new IllegalArgumentException("No posts found matching the given filters");
        }

        List<Long> friendIds = getFriendIds(viewerId);
        return matched.stream()
                .filter(post -> canView(post, viewerId, friendIds))
                .collect(Collectors.toList());
    }

    /** Returns true when {@code viewerId} is allowed to read {@code post}. */
    private boolean canView(RhythmPost post, Long viewerId, List<Long> friendIds) {
        if (post.getUser().getId().equals(viewerId)) return true;
        return switch (post.getVisibility()) {
            case "PUBLIC"    -> true;
            case "FRIENDS"  -> friendIds.contains(post.getUser().getId());
            default         -> false; // PROTECTED and unknown: deny
        };
    }

    /**
     * Resolves a (possibly dot-separated) field path on {@code obj} by walking
     * getter methods via reflection.
     * Each segment is tried as {@code getX()} first, then {@code isX()} for booleans.
     */
    private static String getFieldValue(Object obj, String fieldPath) throws Exception {
        String[] parts = fieldPath.split("\\.", 2);
        String segment = parts[0];
        String getter  = "get" + Character.toUpperCase(segment.charAt(0)) + segment.substring(1);

        java.lang.reflect.Method method;
        try {
            method = obj.getClass().getMethod(getter);
        } catch (NoSuchMethodException e) {
            // Fall back to isX() for boolean fields
            String boolGetter = "is" + Character.toUpperCase(segment.charAt(0)) + segment.substring(1);
            method = obj.getClass().getMethod(boolGetter);
        }

        Object result = method.invoke(obj);
        if (result == null) return null;

        // Recurse into the next segment if dot-path continues
        if (parts.length > 1) return getFieldValue(result, parts[1]);

        return result.toString();
    }

    // ── Friend management ─────────────────────────────────────────────────────

    @Transactional
    public Friendship sendFriendRequest(User requester, String accepterUsername) {
        User accepter = userRepository.findByUsername(accepterUsername)
                .orElseThrow(() -> new IllegalArgumentException("User not found: " + accepterUsername));

        if (requester.getId().equals(accepter.getId())) {
            throw new IllegalArgumentException("Cannot send friend request to yourself");
        }

        friendshipRepository.findFriendship(requester.getId(), accepter.getId()).ifPresent(f -> {
            throw new IllegalArgumentException("Friendship already exists");
        });

        Friendship friendship = Friendship.builder()
                .requester(requester)
                .accepter(accepter)
                .status("PENDING")
                .build();
        return friendshipRepository.save(friendship);
    }

    @Transactional
    public Friendship acceptFriendRequest(Long friendshipId, Long accepterId) {
        Friendship friendship = friendshipRepository.findById(friendshipId)
                .orElseThrow(() -> new IllegalArgumentException("Friendship request not found"));

        if (!friendship.getAccepter().getId().equals(accepterId)) {
            throw new IllegalArgumentException("Only the recipient can accept the request");
        }
        if (!"PENDING".equals(friendship.getStatus())) {
            throw new IllegalArgumentException("Request is not pending");
        }

        friendship.setStatus("ACCEPTED");
        return friendshipRepository.save(friendship);
    }

    public List<Friendship> getPendingRequests(Long userId) {
        return friendshipRepository.findPendingRequests(userId);
    }

    public List<Friendship> getFriendships(Long userId) {
        return friendshipRepository.findAcceptedFriendships(userId);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private List<Long> getFriendIds(Long userId) {
        return friendshipRepository.findAcceptedFriendships(userId).stream()
                .map(f -> f.getRequester().getId().equals(userId)
                        ? f.getAccepter().getId()
                        : f.getRequester().getId())
                .collect(Collectors.toList());
    }

    /** Generates a random 8-character lowercase hex string (4 bytes). */
    private static String generateAccessKey() {
        byte[] bytes = new byte[4];
        SECURE_RANDOM.nextBytes(bytes);
        StringBuilder sb = new StringBuilder(8);
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}
