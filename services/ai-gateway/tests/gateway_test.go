package tests

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/AkiebNazir/aegis-agentic-platform/services/ai-gateway/internal/middleware"
)

func TestAPIKeyAuthAndRateLimiter(t *testing.T) {
	keys := map[string]string{"valid-key": "tenant-1"}
	limiter := middleware.NewTenantRateLimiter(1, 1)

	protected := middleware.APIKeyAuth(keys)(limiter.Middleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})))

	// 1. Missing API key -> 401
	req := httptest.NewRequest(http.MethodPost, "/v1/chat", nil)
	rr := httptest.NewRecorder()
	protected.ServeHTTP(rr, req)
	if rr.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", rr.Code)
	}

	// 2. Valid API key -> 200
	req2 := httptest.NewRequest(http.MethodPost, "/v1/chat", nil)
	req2.Header.Set("X-API-Key", "valid-key")
	rr2 := httptest.NewRecorder()
	protected.ServeHTTP(rr2, req2)
	if rr2.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr2.Code)
	}

	// 3. Immediate burst exceeded -> 429
	rr3 := httptest.NewRecorder()
	protected.ServeHTTP(rr3, req2)
	if rr3.Code != http.StatusTooManyRequests {
		t.Fatalf("expected 429, got %d", rr3.Code)
	}
}
