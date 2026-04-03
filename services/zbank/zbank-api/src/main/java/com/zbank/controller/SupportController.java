package com.zbank.controller;

import com.zbank.model.SupportMessage;
import com.zbank.model.User;
import com.zbank.repository.UserRepository;
import com.zbank.service.SupportService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/support")
@RequiredArgsConstructor
public class SupportController {

    private final SupportService supportService;
    private final UserRepository userRepository;

    /** Sends a support message from the current user and returns the updated conversation. */
    @PostMapping("/messages")
    public ResponseEntity<?> sendMessage(@RequestBody Map<String, String> body) {
        User user = getCurrentUser();
        String message = body.get("message");
        if (message == null || message.isBlank()) {
            return ResponseEntity.badRequest().body(Map.of("error", "Message is required"));
        }

        List<SupportMessage> messages = supportService.sendMessage(user, message);
        return ResponseEntity.ok(messages.stream().map(this::toMap).collect(Collectors.toList()));
    }

    /** Returns the full support conversation history of the current user. */
    @GetMapping("/messages")
    public ResponseEntity<?> getMessages() {
        User user = getCurrentUser();
        List<Map<String, Object>> messages = supportService.getMessages(user.getId())
                .stream().map(this::toMap).collect(Collectors.toList());
        return ResponseEntity.ok(messages);
    }

    private Map<String, Object> toMap(SupportMessage msg) {
        return Map.of(
                "id", msg.getId(),
                "message", msg.getMessage(),
                "isBot", msg.getIsBot(),
                "createdAt", msg.getCreatedAt().toString()
        );
    }

    private User getCurrentUser() {
        String username = SecurityContextHolder.getContext().getAuthentication().getName();
        return userRepository.findByUsername(username).orElseThrow();
    }
}
