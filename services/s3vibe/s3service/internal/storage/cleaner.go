package storage

import (
	"context"
	"os"
	"path/filepath"
	"sync"
	"sync/atomic"
	"time"
)

type Cleaner struct {
	storage       *FileSystemStorage
	maxAge        time.Duration
	interval      time.Duration
	batchSize     int
	maxGoroutines int
	mu            sync.RWMutex
	running       atomic.Bool
}

func NewCleaner(storage *FileSystemStorage, maxAge, interval time.Duration) *Cleaner {
	return &Cleaner{
		storage:       storage,
		maxAge:        maxAge,
		interval:      interval,
		batchSize:     100,
		maxGoroutines: 4,
	}
}

func (c *Cleaner) Start(ctx context.Context) {
	if !c.running.CompareAndSwap(false, true) {
		return
	}

	go c.run(ctx)
}

func (c *Cleaner) run(ctx context.Context) {
	defer c.running.Store(false)

	ticker := time.NewTicker(c.interval)
	defer ticker.Stop()

	c.cleanup(ctx)

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			c.cleanup(ctx)
		}
	}
}

func (c *Cleaner) cleanup(ctx context.Context) {
	c.mu.RLock()
	basePath := c.storage.basePath
	c.mu.RUnlock()

	now := time.Now()
	threshold := now.Add(-c.maxAge)

	fileChan := make(chan string, c.batchSize)
	var wg sync.WaitGroup

	for i := 0; i < c.maxGoroutines; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			c.deleteWorker(ctx, fileChan)
		}()
	}

	filepath.WalkDir(basePath, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return nil
		}

		select {
		case <-ctx.Done():
			return filepath.SkipAll
		default:
		}

		if d.IsDir() {
			return nil
		}

		info, err := d.Info()
		if err != nil {
			return nil
		}

		if info.ModTime().Before(threshold) {
			select {
			case fileChan <- path:
			case <-ctx.Done():
				return filepath.SkipAll
			}
		}

		return nil
	})

	close(fileChan)
	wg.Wait()
}

func (c *Cleaner) deleteWorker(ctx context.Context, files <-chan string) {
	for {
		select {
		case <-ctx.Done():
			return
		case path, ok := <-files:
			if !ok {
				return
			}
			os.Remove(path)
		}
	}
}
