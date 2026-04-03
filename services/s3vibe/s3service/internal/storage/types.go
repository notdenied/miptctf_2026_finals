package storage

import (
	"io"
	"time"
)

type Storage interface {
	PutObject(bucketID, key string, data io.Reader) (etag string, size int64, err error)
	GetObject(bucketID, key string) (io.ReadCloser, int64, error)
	DeleteObject(bucketID, key string) error
	ListObjects(bucketID, prefix string) ([]ObjectInfo, error)
	DeleteBucket(bucketID string) error
}

type ObjectInfo struct {
	Key          string    `json:"Key"`
	Size         int64     `json:"Size"`
	LastModified time.Time `json:"LastModified"`
	ETag         string    `json:"ETag,omitempty"`
	ContentType  string    `json:"ContentType,omitempty"`
}
