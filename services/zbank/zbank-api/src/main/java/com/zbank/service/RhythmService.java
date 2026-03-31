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

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class RhythmService {

    private final RhythmPostRepository postRepository;
    private final FriendshipRepository friendshipRepository;
    private final UserRepository userRepository;

    @Transactional
    public RhythmPost createPost(User user, String content, boolean isPrivate) {
        if (content == null || content.length() > 200) {
            throw new IllegalArgumentException("Post content must be between 1 and 200 characters");
        }
        if (content.isBlank()) {
            throw new IllegalArgumentException("Post content cannot be empty");
        }

        RhythmPost post = RhythmPost.builder()
                .user(user)
                .content(content)
                .isPrivate(isPrivate)
                .build();
        return postRepository.save(post);
    }

    public List<RhythmPost> getUserPosts(Long userId, Long viewerId) {
        if (userId.equals(viewerId)) {
            return postRepository.findByUserIdOrderByCreatedAtDesc(userId);
        }

        // Check if viewer is a friend
        boolean isFriend = friendshipRepository.findFriendship(userId, viewerId)
                .map(f -> "ACCEPTED".equals(f.getStatus()))
                .orElse(false);

        if (isFriend) {
            return postRepository.findByUserIdOrderByCreatedAtDesc(userId);
        } else {
            return postRepository.findPublicPostsByUserId(userId);
        }
    }

    public List<RhythmPost> getFeed(Long userId) {
        List<Long> friendIds = getFriendIds(userId);
        List<Long> allIds = new ArrayList<>(friendIds);
        allIds.add(userId);

        if (allIds.isEmpty()) {
            return postRepository.findByUserIdOrderByCreatedAtDesc(userId);
        }

        return postRepository.findFeedPosts(friendIds.isEmpty() ? List.of(-1L) : friendIds, allIds);
    }

    @Transactional
    public Friendship sendFriendRequest(User requester, String accepterUsername) {
        User accepter = userRepository.findByUsername(accepterUsername)
                .orElseThrow(() -> new IllegalArgumentException("User not found: " + accepterUsername));

        if (requester.getId().equals(accepter.getId())) {
            throw new IllegalArgumentException("Cannot send friend request to yourself");
        }

        // Check existing friendship
        var existing = friendshipRepository.findFriendship(requester.getId(), accepter.getId());
        if (existing.isPresent()) {
            throw new IllegalArgumentException("Friendship already exists");
        }

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

    private List<Long> getFriendIds(Long userId) {
        return friendshipRepository.findAcceptedFriendships(userId).stream()
                .map(f -> f.getRequester().getId().equals(userId) ?
                        f.getAccepter().getId() : f.getRequester().getId())
                .collect(Collectors.toList());
    }
}
