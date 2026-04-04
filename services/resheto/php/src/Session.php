<?php

/**
 * Session helper — wraps PHP session with convenience methods.
 */
class Session
{
    public static function getUserId(): ?int
    {
        return isset($_SESSION['user_id']) ? (int) $_SESSION['user_id'] : null;
    }

    public static function getUsername(): ?string
    {
        return $_SESSION['username'] ?? null;
    }

    public static function getClearanceLevel(): int
    {
        return (int) ($_SESSION['clearance_level'] ?? 0);
    }

    public static function setUser(int $id, string $username, int $clearance): void
    {
        $_SESSION['user_id']         = $id;
        $_SESSION['username']        = $username;
        $_SESSION['clearance_level'] = $clearance;
    }

    public static function destroy(): void
    {
        session_destroy();
        $_SESSION = [];
    }

    public static function requireAuth(): int
    {
        $uid = self::getUserId();
        if ($uid === null) {
            http_response_code(401);
            echo json_encode(['error' => 'Authentication required']);
            exit;
        }
        return $uid;
    }

    /**
     * Reads JSON request body.
     */
    public static function getJsonBody(): array
    {
        $raw = file_get_contents('php://input');
        return json_decode($raw, true) ?: [];
    }

    /**
     * Generates a UUID v4.
     */
    public static function uuid(): string
    {
        $data    = random_bytes(16);
        $data[6] = chr(ord($data[6]) & 0x0f | 0x40);
        $data[8] = chr(ord($data[8]) & 0x3f | 0x80);
        return vsprintf('%s%s-%s-%s-%s-%s%s%s', str_split(bin2hex($data), 4));
    }
}
