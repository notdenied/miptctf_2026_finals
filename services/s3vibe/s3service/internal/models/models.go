package models

import (
	"database/sql/driver"
	"encoding/json"
	"errors"
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type JSONB map[string]interface{}

func (j *JSONB) Scan(value interface{}) error {
	if value == nil {
		*j = make(JSONB)
		return nil
	}
	bytes, ok := value.([]byte)
	if !ok {
		return errors.New("failed to unmarshal JSONB value")
	}
	result := make(JSONB)
	err := json.Unmarshal(bytes, &result)
	*j = result
	return err
}

func (j JSONB) Value() (driver.Value, error) {
	if j == nil {
		return nil, nil
	}
	return json.Marshal(j)
}

type Bucket struct {
	ID          uuid.UUID `gorm:"type:uuid;primaryKey;default:uuid_generate_v4()"`
	BucketID    string    `gorm:"type:varchar(255);uniqueIndex;not null"`
	UserID      uuid.UUID `gorm:"type:uuid;not null"`
	Name        string    `gorm:"type:varchar(255);not null"`
	Description string    `gorm:"type:text"`
	CreatedAt   time.Time `gorm:"type:timestamp with time zone;default:CURRENT_TIMESTAMP;autoCreateTime"`
	UpdatedAt   time.Time `gorm:"type:timestamp with time zone;default:CURRENT_TIMESTAMP;autoUpdateTime"`
	StorageUsed int64     `gorm:"type:bigint;default:0"`
	MaxStorage  int64     `gorm:"type:bigint;default:10737418240"`
	IsActive    bool      `gorm:"type:boolean;default:true"`
}

func (Bucket) TableName() string {
	return "buckets"
}

type Object struct {
	ID          uuid.UUID  `gorm:"type:uuid;primaryKey;default:uuid_generate_v4()"`
	BucketID    uuid.UUID  `gorm:"type:uuid;not null"`
	ObjectKey   string     `gorm:"type:varchar(1024);not null"`
	Size        int64      `gorm:"type:bigint;not null"`
	ContentType string     `gorm:"type:varchar(255)"`
	Etag        string     `gorm:"type:varchar(255)"`
	UploadedBy  *uuid.UUID `gorm:"type:uuid"`
	CreatedAt   time.Time  `gorm:"type:timestamp with time zone;default:CURRENT_TIMESTAMP;autoCreateTime"`
	UpdatedAt   time.Time  `gorm:"type:timestamp with time zone;default:CURRENT_TIMESTAMP;autoUpdateTime"`
	Metadata    JSONB      `gorm:"type:jsonb"`
	IsDeleted   bool       `gorm:"type:boolean;default:false"`
}

func (Object) TableName() string {
	return "objects"
}

func (o *Object) BeforeCreate(tx *gorm.DB) error {
	if o.Metadata == nil {
		o.Metadata = make(JSONB)
	}
	return nil
}
