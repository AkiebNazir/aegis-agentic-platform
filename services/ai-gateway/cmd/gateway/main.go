package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/AkiebNazir/aegis-agentic-platform/services/ai-gateway/internal/cache"
	"github.com/AkiebNazir/aegis-agentic-platform/services/ai-gateway/internal/middleware"
	"github.com/AkiebNazir/aegis-agentic-platform/services/ai-gateway/internal/router"
)

type ChatRequest struct {
	Prompt      string `json:"prompt"`
	UseGraphRAG bool   `json:"use_graph_rag"`
}

type ChatResponse struct {
	Answer      string `json:"answer"`
	CacheTier   string `json:"cache_tier"`
	SourceAgent string `json:"source_agent"`
	LatencyMS   int64  `json:"latency_ms"`
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	redisAddr := getEnv("REDIS_ADDR", "localhost:6379")
	semanticURL := getEnv("SEMANTIC_CACHE_URL", "http://localhost:8002")
	orchestratorAddr := getEnv("ORCHESTRATOR_GRPC_ADDR", "localhost:50051")
	port := getEnv("PORT", "8080")

	l1Cache := cache.NewL1RedisCache(redisAddr, 1*time.Hour)
	l2Cache := cache.NewL2SemanticClient(semanticURL, 0.15)

	orchClient, err := router.NewOrchestratorClient(orchestratorAddr)
	if err != nil {
		log.Fatalf("failed to initialize gRPC orchestrator client: %v", err)
	}
	defer orchClient.Close()

	// Demo tenant API keys (replace with Vault/KMS in production)
	validKeys := map[string]string{
		"aegis-dev-key-1": "tenant-fintech-amex",
		"aegis-dev-key-2": "tenant-retail-wmt",
	}
	rateLimiter := middleware.NewTenantRateLimiter(50, 100)

	chatHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
			return
		}

		start := time.Now()
		tenantID := middleware.GetTenantID(r.Context())

		var req ChatRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Prompt == "" {
			http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
			return
		}

		w.Header().Set("Content-Type", "application/json")

		// 1. L1 Exact-Match Cache (Redis)
		if ans, hit := l1Cache.Get(r.Context(), tenantID, req.Prompt); hit {
			json.NewEncoder(w).Encode(ChatResponse{
				Answer:      ans,
				CacheTier:   "L1_REDIS_EXACT",
				SourceAgent: "gateway-cache",
				LatencyMS:   time.Since(start).Milliseconds(),
			})
			return
		}

		// 2. L2 Vector Semantic Cache (ChromaDB + Redis)
		if ans, hit := l2Cache.Lookup(r.Context(), tenantID, req.Prompt); hit {
			_ = l1Cache.Set(r.Context(), tenantID, req.Prompt, ans)
			json.NewEncoder(w).Encode(ChatResponse{
				Answer:      ans,
				CacheTier:   "L2_SEMANTIC_VECTOR",
				SourceAgent: "semantic-cache",
				LatencyMS:   time.Since(start).Milliseconds(),
			})
			return
		}

		// 3. Cache Miss -> Forward over gRPC to 04-agent-orchestrator
		reqID := l1Cache.HashKey(tenantID, req.Prompt)
		resp, err := orchClient.ForwardPrompt(r.Context(), reqID, tenantID, req.Prompt, req.UseGraphRAG)
		if err != nil {
			http.Error(w, `{"error":"upstream orchestrator error"}`, http.StatusBadGateway)
			return
		}

		_ = l1Cache.Set(r.Context(), tenantID, req.Prompt, resp.Answer)

		json.NewEncoder(w).Encode(ChatResponse{
			Answer:      resp.Answer,
			CacheTier:   "MISS_LIVE_INFERENCE",
			SourceAgent: resp.SourceAgent,
			LatencyMS:   time.Since(start).Milliseconds(),
		})
	})

	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok","service":"ai-gateway"}`))
	})
	mux.Handle("/v1/chat", middleware.APIKeyAuth(validKeys)(rateLimiter.Middleware(chatHandler)))

	srv := &http.Server{
		Addr:         ":" + port,
		Handler:      mux,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 30 * time.Second,
	}

	go func() {
		log.Printf("ai-gateway listening on :%s", port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("server error: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_ = srv.Shutdown(ctx)
	log.Println("ai-gateway shut down gracefully")
}
