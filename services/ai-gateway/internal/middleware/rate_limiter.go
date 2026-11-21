package middleware

import (
	"net/http"
	"sync"

	"golang.org/x/time/rate"
)

type TenantRateLimiter struct {
	mu       sync.RWMutex
	limiters map[string]*rate.Limiter
	rps      rate.Limit
	burst    int
}

func NewTenantRateLimiter(rps float64, burst int) *TenantRateLimiter {
	return &TenantRateLimiter{
		limiters: make(map[string]*rate.Limiter),
		rps:      rate.Limit(rps),
		burst:    burst,
	}
}

func (trl *TenantRateLimiter) getLimiter(tenantID string) *rate.Limiter {
	trl.mu.RLock()
	limiter, exists := trl.limiters[tenantID]
	trl.mu.RUnlock()
	if exists {
		return limiter
	}

	trl.mu.Lock()
	defer trl.mu.Unlock()
	limiter = rate.NewLimiter(trl.rps, trl.burst)
	trl.limiters[tenantID] = limiter
	return limiter
}

func (trl *TenantRateLimiter) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		tenantID := GetTenantID(r.Context())
		if !trl.getLimiter(tenantID).Allow() {
			w.Header().Set("Retry-After", "1")
			http.Error(w, `{"error":"rate limit exceeded for tenant"}`, http.StatusTooManyRequests)
			return
		}
		next.ServeHTTP(w, r)
	})
}
