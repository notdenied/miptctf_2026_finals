package com.zbank.repository;

import com.zbank.model.RhythmPost;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import java.util.List;

public interface RhythmPostRepository extends JpaRepository<RhythmPost, Long> {
    List<RhythmPost> findByUserIdOrderByCreatedAtDesc(Long userId);

    @Query("SELECT p FROM RhythmPost p WHERE p.user.id = :userId AND p.isPrivate = false ORDER BY p.createdAt DESC")
    List<RhythmPost> findPublicPostsByUserId(@Param("userId") Long userId);

    @Query("SELECT p FROM RhythmPost p WHERE " +
           "(p.user.id IN :friendIds AND p.isPrivate = true) OR " +
           "(p.user.id IN :allIds AND p.isPrivate = false) " +
           "ORDER BY p.createdAt DESC")
    List<RhythmPost> findFeedPosts(@Param("friendIds") List<Long> friendIds, @Param("allIds") List<Long> allIds);
}
