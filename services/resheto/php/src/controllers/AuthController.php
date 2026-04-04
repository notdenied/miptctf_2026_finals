<?php

class AuthController
{
    public static function register(array $params): void
    {
        $data = Session::getJsonBody();

        $username   = trim($data['username'] ?? '');
        $password   = $data['password'] ?? '';
        $fullName   = trim($data['full_name'] ?? $username);
        $clearance  = (int) ($data['clearance_level'] ?? 1);
        $department = trim($data['department'] ?? 'General');

        if ($username === '' || $password === '') {
            http_response_code(400);
            echo json_encode(['error' => 'Username and password are required']);
            return;
        }

        if (strlen($username) > 64 || strlen($password) > 128) {
            http_response_code(400);
            echo json_encode(['error' => 'Input too long']);
            return;
        }

        $clearance = max(1, min(5, $clearance));

        $db = Database::getConnection();

        // Check uniqueness
        $stmt = $db->prepare('SELECT id FROM staff WHERE username = ?');
        $stmt->execute([$username]);
        if ($stmt->fetch()) {
            http_response_code(409);
            echo json_encode(['error' => 'Username already exists']);
            return;
        }

        $hash = password_hash($password, PASSWORD_BCRYPT);

        $stmt = $db->prepare(
            'INSERT INTO staff (username, password_hash, full_name, clearance_level, department)
             VALUES (?, ?, ?, ?, ?) RETURNING id, created_at'
        );
        $stmt->execute([$username, $hash, $fullName, $clearance, $department]);
        $row = $stmt->fetch();

        Session::setUser((int) $row['id'], $username, $clearance);

        echo json_encode([
            'id'              => (int) $row['id'],
            'username'        => $username,
            'full_name'       => $fullName,
            'clearance_level' => $clearance,
            'department'      => $department,
            'created_at'      => $row['created_at'],
        ]);
    }

    public static function login(array $params): void
    {
        $data = Session::getJsonBody();

        $username = trim($data['username'] ?? '');
        $password = $data['password'] ?? '';

        if ($username === '' || $password === '') {
            http_response_code(400);
            echo json_encode(['error' => 'Username and password are required']);
            return;
        }

        $db   = Database::getConnection();
        $stmt = $db->prepare('SELECT id, username, password_hash, full_name, clearance_level, department, created_at FROM staff WHERE username = ?');
        $stmt->execute([$username]);
        $user = $stmt->fetch();

        if (!$user || !password_verify($password, $user['password_hash'])) {
            http_response_code(401);
            echo json_encode(['error' => 'Invalid credentials']);
            return;
        }

        Session::setUser((int) $user['id'], $user['username'], (int) $user['clearance_level']);

        echo json_encode([
            'id'              => (int) $user['id'],
            'username'        => $user['username'],
            'full_name'       => $user['full_name'],
            'clearance_level' => (int) $user['clearance_level'],
            'department'      => $user['department'],
            'created_at'      => $user['created_at'],
        ]);
    }

    public static function me(array $params): void
    {
        $uid = Session::requireAuth();

        $db   = Database::getConnection();
        $stmt = $db->prepare('SELECT id, username, full_name, clearance_level, department, created_at FROM staff WHERE id = ?');
        $stmt->execute([$uid]);
        $user = $stmt->fetch();

        if (!$user) {
            http_response_code(404);
            echo json_encode(['error' => 'User not found']);
            return;
        }

        $user['id']              = (int) $user['id'];
        $user['clearance_level'] = (int) $user['clearance_level'];
        echo json_encode($user);
    }

    public static function logout(array $params): void
    {
        Session::destroy();
        echo json_encode(['ok' => true]);
    }
}
