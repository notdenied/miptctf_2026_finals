package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/gorilla/mux"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"

	"github.com/storage/service/internal/config"
	"github.com/storage/service/internal/handlers"
	"github.com/storage/service/internal/middleware"
	"github.com/storage/service/internal/storage"
)

func main() {
	cfg := config.Load()

	db, err := gorm.Open(postgres.Open(cfg.DatabaseURL), &gorm.Config{})
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to connect to database: %v\n", err)
		os.Exit(1)
	}

	sqlDB, err := db.DB()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to get database instance: %v\n", err)
		os.Exit(1)
	}
	defer sqlDB.Close()

	if err := sqlDB.Ping(); err != nil {
		fmt.Fprintf(os.Stderr, "Failed to ping database: %v\n", err)
		os.Exit(1)
	}

	storageBackend, err := storage.NewFileSystemStorage(cfg.StoragePath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to initialize storage: %v\n", err)
		os.Exit(1)
	}

	ctx := context.Background()
	cleaner := storage.NewCleaner(storageBackend, 16*time.Minute, 4*time.Minute)
	cleaner.Start(ctx)

	handler := handlers.NewHandler(db, storageBackend)

	router := mux.NewRouter()

	router.Use(middleware.RecoveryMiddleware)

	router.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `{"status":"healthy","service":"storage"}`)
	}).Methods("GET")

	api := router.PathPrefix("/").Subrouter()

	api.HandleFunc("/bucket", handler.GetBucketInfo).Methods("GET")
	api.HandleFunc("/objects", handler.ListObjects).Methods("GET")
	api.HandleFunc("/objects/{key:.*}", handler.GetObject).Methods("GET")
	api.HandleFunc("/objects/{key:.*}", handler.PutObject).Methods("PUT", "POST")
	api.HandleFunc("/objects/{key:.*}", handler.DeleteObject).Methods("DELETE")

	api.HandleFunc("/uploads", handler.InitiateMultipartUpload).Methods("POST")
	api.HandleFunc("/uploads/{uploadId}", handler.CompleteMultipartUpload).Methods("POST")
	api.HandleFunc("/uploads/{uploadId}", handler.AbortMultipartUpload).Methods("DELETE")

	server := &http.Server{
		Addr:         fmt.Sprintf(":%s", cfg.Port),
		Handler:      router,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	if err := server.ListenAndServe(); err != nil {
		fmt.Fprintf(os.Stderr, "Server failed to start: %v\n", err)
		os.Exit(1)
	}
}
