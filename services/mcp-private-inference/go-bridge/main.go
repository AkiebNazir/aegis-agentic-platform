package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"strings"
	"time"
)

type ServiceStatus struct {
	Service        string  `json:"service"`
	Status         string  `json:"status"`
	CircuitBreaker string  `json:"circuit_breaker"`
	P99LatencyMS   float64 `json:"p99_latency_ms"`
	CheckedAt      string  `json:"checked_at"`
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8090"
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok","service":"mcp-go-bridge"}`))
	})

	// Endpoint consumed by Python MCP ops_diagnostics tool
	mux.HandleFunc("/internal/services/", func(w http.ResponseWriter, r *http.Request) {
		parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
		if len(parts) < 4 || parts[3] != "status" {
			http.Error(w, `{"error":"invalid path"}`, http.StatusNotFound)
			return
		}

		serviceName := parts[2]
		resp := ServiceStatus{
			Service:        serviceName,
			Status:         "OPERATIONAL",
			CircuitBreaker: "CLOSED",
			P99LatencyMS:   42.5,
			CheckedAt:      time.Now().UTC().Format(time.RFC3339),
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	})

	log.Printf("mcp-go-bridge listening on :%s", port)
	log.Fatal(http.ListenAndServe(":"+port, mux))
}
