<?php

/**
 * PDO database singleton
 */
class Database
{
    private static ?PDO $pdo = null;

    public static function getConnection(): PDO
    {
        if (self::$pdo === null) {
            $host = $_ENV['DB_HOST'] ?? getenv('DB_HOST') ?: 'postgres';
            $name = $_ENV['DB_NAME'] ?? getenv('DB_NAME') ?: 'resheto';
            $user = $_ENV['DB_USER'] ?? getenv('DB_USER') ?: 'resheto';
            $pass = $_ENV['DB_PASS'] ?? getenv('DB_PASS') ?: 'resheto';

            $dsn = "pgsql:host={$host};dbname={$name}";

            self::$pdo = new PDO($dsn, $user, $pass, [
                PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_EMULATE_PREPARES   => true,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            ]);
        }

        return self::$pdo;
    }
}
