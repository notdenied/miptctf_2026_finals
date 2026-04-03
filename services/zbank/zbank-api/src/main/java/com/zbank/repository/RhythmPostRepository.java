package com.zbank.repository;

import com.zbank.model.RhythmPost;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface RhythmPostRepository extends JpaRepository<RhythmPost, Long> {

    List<RhythmPost> findByUserIdOrderByCreatedAtDesc(Long userId);

    Optional<RhythmPost> findByPostUuid(String postUuid);

    /** Returns only PUBLIC posts of a given user (for non-friend viewers). */
    @Query("SELECT p FROM RhythmPost p WHERE p.user.id = :userId AND p.visibility = 'PUBLIC' ORDER BY p.createdAt DESC")
    List<RhythmPost> findPublicPostsByUserId(@Param("userId") Long userId);

    /**
     * Feed query: own posts (all visibility) + friends' PUBLIC and FRIENDS posts +
     * everyone's PUBLIC posts. PROTECTED posts of others are excluded.
     */
    @Query("SELECT p FROM RhythmPost p WHERE " +
           "(p.user.id = :userId) OR " +
           "(p.user.id IN :friendIds AND p.visibility IN ('PUBLIC', 'FRIENDS')) OR " +
           "(p.user.id IN :allIds AND p.visibility = 'PUBLIC') " +
           "ORDER BY p.createdAt DESC")
    List<RhythmPost> findFeedPosts(
            @Param("userId")    Long userId,
            @Param("friendIds") List<Long> friendIds,
            @Param("allIds")    List<Long> allIds);

    /**
     * Search pool: all posts accessible to the viewer.
     * Includes own posts (all visibility), friends' PUBLIC+FRIENDS posts, and everyone's PUBLIC posts.
     * PROTECTED posts of other users are intentionally excluded.
     */
    @Query("SELECT p FROM RhythmPost p WHERE " +
           "(p.user.id = :viewerId) OR " +
           "(p.visibility = 'PUBLIC') OR " +
           "(p.visibility = 'FRIENDS' AND p.user.id IN :friendIds) " +
           "ORDER BY p.createdAt DESC")
    List<RhythmPost> findAccessiblePosts(
            @Param("viewerId")  Long viewerId,
            @Param("friendIds") List<Long> friendIds);
}
