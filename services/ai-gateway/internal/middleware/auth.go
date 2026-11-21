package middleware

import (
	"context"
	"net/http"
	"strings"
)

type contextKey string

const TenantIDKey contextKey = "tenant_id"

// APIKeyAuth validates the Bearer token / X-API-Key and injects tenant_id into the request context.
func APIKeyAuth(validKeys map[string]string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			apiKey := r.Header.Get("X-API-Key")
			if apiKey == "" {
				authHeader := r.Header.Get("Authorization")
				if strings.HasPrefix(authHeader, "Bearer ") {
					apiKey = strings.TrimPrefix(authHeader, "Bearer ")
				}
			}

			tenantID, ok := validKeys[apiKey]
			if !ok {
				http.Error(w, `{"error":"unauthorized: invalid or missing API key"}`, http.StatusUnauthorized)
				return
			}

			ctx := context.WithValue(r.Context(), TenantIDKey, tenantID)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

func GetTenantID(ctx context.Context) string {
	if v, ok := ctx.Value(TenantIDKey).(string); ok {
		return v
	}
	return "default-tenant"
}
