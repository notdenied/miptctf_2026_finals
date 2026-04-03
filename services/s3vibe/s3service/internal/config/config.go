package config

import (
	"os"
)

type Config struct {
	DatabaseURL string
	StoragePath string
	Port        string
}

func Load() *Config {
	return &Config{
		DatabaseURL: getEnv("DATABASE_URL", "postgresql://storageadmin:storagepass@postgres:5432/storage"),
		StoragePath: getEnv("STORAGE_PATH", "/data/storage"),
		Port:        getEnv("PORT", "8080"),
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
