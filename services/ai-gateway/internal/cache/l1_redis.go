package cache

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

type L1RedisCache struct {
	client *redis.Client
	ttl    time.Duration
}

func NewL1RedisCache(addr string, ttl time.Duration) *L1RedisCache {
	rdb := redis.NewClient(&redis.Options{Addr: addr})
	return &L1RedisCache{client: rdb, ttl: ttl}
}

func (c *L1RedisCache) HashKey(tenantID, prompt string) string {
	h := sha256.Sum256([]byte(tenantID + ":" + prompt))
	return fmt.Sprintf("aegis:l1:%s", hex.EncodeToString(h[:]))
}

func (c *L1RedisCache) Get(ctx context.Context, tenantID, prompt string) (string, bool) {
	val, err := c.client.Get(ctx, c.HashKey(tenantID, prompt)).Result()
	if err != nil {
		return "", false
	}
	return val, true
}

func (c *L1RedisCache) Set(ctx context.Context, tenantID, prompt, answer string) error {
	return c.client.Set(ctx, c.HashKey(tenantID, prompt), answer, c.ttl).Err()
}
