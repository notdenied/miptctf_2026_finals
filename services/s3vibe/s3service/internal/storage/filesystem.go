package storage

import (
	"crypto/md5"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"time"

	"github.com/kennygrant/sanitize"
)

type FileSystemStorage struct {
	basePath string
}

func NewFileSystemStorage(basePath string) (*FileSystemStorage, error) {
	if err := os.MkdirAll(basePath, 0755); err != nil {
		return nil, fmt.Errorf("failed to create storage directory: %w", err)
	}

	return &FileSystemStorage{
		basePath: basePath,
	}, nil
}

func (fs *FileSystemStorage) PutObject(bucketID, key string, data io.Reader) (string, int64, error) {
	bucketPath := sanitize.Path(fs.basePath + "/" + bucketID)
	if err := os.MkdirAll(bucketPath, 0755); err != nil {
		return "", 0, fmt.Errorf("failed to create bucket directory: %w", err)
	}

	objectPath := sanitize.Path(fs.basePath + "/" + bucketID + "/" + key)

	objectDir := filepath.Dir(objectPath)
	if err := os.MkdirAll(objectDir, 0755); err != nil {
		return "", 0, fmt.Errorf("failed to create object directory: %w", err)
	}

	file, err := os.Create(objectPath)
	if err != nil {
		return "", 0, fmt.Errorf("failed to create object file: %w", err)
	}
	defer file.Close()

	hash := md5.New()
	multiWriter := io.MultiWriter(file, hash)

	size, err := io.Copy(multiWriter, data)
	if err != nil {
		os.Remove(objectPath)
		return "", 0, fmt.Errorf("failed to write object data: %w", err)
	}

	etag := hex.EncodeToString(hash.Sum(nil))

	return etag, size, nil
}

func (fs *FileSystemStorage) GetObject(bucketID, key string) (io.ReadCloser, int64, error) {
	objectPath := sanitize.Path(fs.basePath + "/" + bucketID + "/" + key)
	info, err := os.Stat(objectPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, 0, fmt.Errorf("object not found")
		}
		return nil, 0, fmt.Errorf("failed to stat object: %w", err)
	}

	file, err := os.Open(objectPath)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to open object: %w", err)
	}

	return file, info.Size(), nil
}

func (fs *FileSystemStorage) DeleteObject(bucketID, key string) error {
	objectPath := sanitize.Path(fs.basePath + "/" + bucketID + "/" + key)

	if err := os.Remove(objectPath); err != nil {
		if os.IsNotExist(err) {
			return fmt.Errorf("object not found")
		}
		return fmt.Errorf("failed to delete object: %w", err)
	}

	return nil
}

func (fs *FileSystemStorage) ListObjects(bucketID, prefix string) ([]ObjectInfo, error) {
	bucketPath := sanitize.Path(fs.basePath + "/" + bucketID)

	if _, err := os.Stat(bucketPath); os.IsNotExist(err) {
		return []ObjectInfo{}, nil
	}

	searchPath := bucketPath
	if prefix != "" {
		searchPath = sanitize.Path(fs.basePath + "/" + bucketID + "/" + prefix)
	}

	entries, err := os.ReadDir(searchPath)
	if err != nil {
		if os.IsNotExist(err) {
			return []ObjectInfo{}, nil
		}
		return nil, fmt.Errorf("failed to read directory: %w", err)
	}

	var objects []ObjectInfo
	seenFolders := make(map[string]bool)

	for _, entry := range entries {
		entryPath := sanitize.Path(searchPath + "/" + entry.Name())
		relPath, _ := filepath.Rel(bucketPath, entryPath)
		key := filepath.ToSlash(relPath)

		if entry.IsDir() {
			if !seenFolders[key] {
				seenFolders[key] = true
				info, err := entry.Info()
				modTime := time.Now()
				if err == nil {
					modTime = info.ModTime()
				}
				objects = append(objects, ObjectInfo{
					Key:          key + "/",
					Size:         0,
					LastModified: modTime,
				})
			}
		} else {
			if entry.Name() == ".keep" {
				continue
			}
			info, err := entry.Info()
			if err != nil {
				continue
			}
			objects = append(objects, ObjectInfo{
				Key:          key,
				Size:         info.Size(),
				LastModified: info.ModTime(),
			})
		}
	}

	return objects, nil
}

func (fs *FileSystemStorage) DeleteBucket(bucketID string) error {
	bucketPath := sanitize.Path(fs.basePath + "/" + bucketID)

	if err := os.RemoveAll(bucketPath); err != nil {
		return fmt.Errorf("failed to delete bucket: %w", err)
	}

	return nil
}
