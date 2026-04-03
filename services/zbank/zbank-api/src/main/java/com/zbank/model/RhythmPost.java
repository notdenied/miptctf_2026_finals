package com.zbank.model;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "rhythm_posts")
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class RhythmPost {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(nullable = false, length = 200)
    private String content;

    /** Shareable public identifier (UUID v4). Used in link-based post access. */
    @Column(name = "post_uuid", unique = true, nullable = false, length = 36)
    private String postUuid;

    /**
     * Visibility mode:
     *   PUBLIC    – visible to anyone
     *   FRIENDS   – visible to the owner and their accepted friends
     *   PROTECTED – accessible only via direct link with the matching access key
     */
    @Builder.Default
    @Column(name = "visibility", nullable = false, length = 20)
    private String visibility = "PUBLIC";

    /**
     * 8-char hex access key for PROTECTED posts.
     * Must be provided as ?key=... when fetching the post by its postUuid.
     * Null for PUBLIC and FRIENDS posts.
     */
    @Column(name = "access_key", length = 8)
    private String accessKey;

    @Builder.Default
    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();
}
