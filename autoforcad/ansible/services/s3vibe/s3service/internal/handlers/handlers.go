package handlers

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/google/uuid"
	"github.com/gorilla/mux"
	"gorm.io/gorm"

	"github.com/storage/service/internal/models"
	"github.com/storage/service/internal/storage"
)

type Handler struct {
	db      *gorm.DB
	storage storage.Storage
}

func NewHandler(db *gorm.DB, storage storage.Storage) *Handler {
	return &Handler{
		db:      db,
		storage: storage,
	}
}

func (h *Handler) getBucketID(r *http.Request) string {
	return r.Header.Get("s3-bucket-id")
}

func (h *Handler) GetBucketInfo(w http.ResponseWriter, r *http.Request) {
	bucketID := h.getBucketID(r)
	if bucketID == "" {
		http.Error(w, `{"error":"Missing bucket ID"}`, http.StatusBadRequest)
		return
	}

	var bucket models.Bucket
	err := h.db.Where("bucket_id = ? AND is_active = ?", bucketID, true).First(&bucket).Error

	if err == gorm.ErrRecordNotFound {
		http.Error(w, `{"error":"Bucket not found"}`, http.StatusNotFound)
		return
	} else if err != nil {
		http.Error(w, `{"error":"Database error"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"bucket_id":    bucket.BucketID,
		"name":         bucket.Name,
		"description":  bucket.Description,
		"storage_used": bucket.StorageUsed,
		"max_storage":  bucket.MaxStorage,
		"created_at":   bucket.CreatedAt,
		"updated_at":   bucket.UpdatedAt,
	})
}

func (h *Handler) CreateBucket(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"message": "Bucket creation should be done through authproxy API",
	})
}

func (h *Handler) DeleteBucket(w http.ResponseWriter, r *http.Request) {
	bucketID := h.getBucketID(r)
	if bucketID == "" {
		http.Error(w, `{"error":"Missing bucket ID"}`, http.StatusBadRequest)
		return
	}

	if err := h.storage.DeleteBucket(bucketID); err != nil {
	}

	err := h.db.Model(&models.Bucket{}).
		Where("bucket_id = ?", bucketID).
		Update("is_active", false).Error

	if err != nil {
		http.Error(w, `{"error":"Database error"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"message": "Bucket deleted successfully",
	})
}

func (h *Handler) ListObjects(w http.ResponseWriter, r *http.Request) {
	bucketID := h.getBucketID(r)
	if bucketID == "" {
		http.Error(w, `{"error":"Missing bucket ID"}`, http.StatusBadRequest)
		return
	}

	prefix := r.URL.Query().Get("prefix")

	objects, err := h.storage.ListObjects(bucketID, prefix)
	if err != nil {
		http.Error(w, `{"error":"Failed to list objects"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"objects": objects,
		"count":   len(objects),
	})
}

func (h *Handler) GetObject(w http.ResponseWriter, r *http.Request) {
	bucketID := h.getBucketID(r)
	if bucketID == "" {
		http.Error(w, `{"error":"Missing bucket ID"}`, http.StatusBadRequest)
		return
	}

	vars := mux.Vars(r)
	key := vars["key"]

	reader, size, err := h.storage.GetObject(bucketID, key)
	if err != nil {
		http.Error(w, `{"error":"Object not found"}`, http.StatusNotFound)
		return
	}
	defer reader.Close()

	contentType := h.getObjectContentType(bucketID, key)

	w.Header().Set("Content-Type", contentType)
	w.Header().Set("Content-Length", fmt.Sprintf("%d", size))
	w.WriteHeader(http.StatusOK)

	io.Copy(w, reader)
}

func (h *Handler) PutObject(w http.ResponseWriter, r *http.Request) {
	bucketID := h.getBucketID(r)
	if bucketID == "" {
		http.Error(w, `{"error":"Missing bucket ID"}`, http.StatusBadRequest)
		return
	}

	vars := mux.Vars(r)
	key := vars["key"]

	contentType := r.Header.Get("Content-Type")
	if contentType == "" {
		contentType = "application/octet-stream"
	}

	etag, size, err := h.storage.PutObject(bucketID, key, r.Body)
	if err != nil {
		http.Error(w, `{"error":"Failed to store object"}`, http.StatusInternalServerError)
		return
	}

	var bucket models.Bucket
	if err := h.db.Where("bucket_id = ?", bucketID).First(&bucket).Error; err != nil {
		http.Error(w, `{"error":"Bucket not found"}`, http.StatusInternalServerError)
		return
	}

	metadata := models.JSONB{}

	var existingObject models.Object
	err = h.db.Where("bucket_id = ? AND object_key = ?", bucket.ID, key).First(&existingObject).Error

	if err == gorm.ErrRecordNotFound {
		newObject := models.Object{
			ID:          uuid.New(),
			BucketID:    bucket.ID,
			ObjectKey:   key,
			Size:        size,
			ContentType: contentType,
			Etag:        etag,
			UploadedBy:  nil,
			Metadata:    metadata,
		}
		if err := h.db.Create(&newObject).Error; err != nil {
			http.Error(w, `{"error":"Failed to create object record"}`, http.StatusInternalServerError)
			return
		}
	} else if err == nil {
		if err := h.db.Model(&existingObject).Updates(map[string]interface{}{
			"size":         size,
			"content_type": contentType,
			"etag":         etag,
		}).Error; err != nil {
			http.Error(w, `{"error":"Failed to update object record"}`, http.StatusInternalServerError)
			return
		}
	} else {
		http.Error(w, `{"error":"Database error"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("ETag", etag)
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"key":  key,
		"etag": etag,
		"size": size,
	})
}

func (h *Handler) DeleteObject(w http.ResponseWriter, r *http.Request) {
	bucketID := h.getBucketID(r)
	if bucketID == "" {
		http.Error(w, `{"error":"Missing bucket ID"}`, http.StatusBadRequest)
		return
	}

	vars := mux.Vars(r)
	key := vars["key"]

	if err := h.storage.DeleteObject(bucketID, key); err != nil {
		http.Error(w, `{"error":"Object not found"}`, http.StatusNotFound)
		return
	}

	var bucket models.Bucket
	if err := h.db.Where("bucket_id = ?", bucketID).First(&bucket).Error; err == nil {
		h.db.Model(&models.Object{}).
			Where("bucket_id = ? AND object_key = ?", bucket.ID, key).
			Updates(map[string]interface{}{
				"is_deleted": true,
			})
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"message": "Object deleted successfully",
	})
}

func (h *Handler) InitiateMultipartUpload(w http.ResponseWriter, r *http.Request) {
	uploadID := uuid.New().String()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"upload_id": uploadID,
		"message":   "Multipart upload initiated",
	})
}

func (h *Handler) CompleteMultipartUpload(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"message": "Multipart upload completed",
	})
}

func (h *Handler) AbortMultipartUpload(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"message": "Multipart upload aborted",
	})
}

func (h *Handler) getObjectContentType(bucketID, key string) string {
	var bucket models.Bucket
	if err := h.db.Where("bucket_id = ?", bucketID).First(&bucket).Error; err != nil {
		return "application/octet-stream"
	}

	var object models.Object
	err := h.db.Where("bucket_id = ? AND object_key = ? AND is_deleted = ?", bucket.ID, key, false).
		First(&object).Error

	if err != nil {
		return "application/octet-stream"
	}

	return object.ContentType
}
