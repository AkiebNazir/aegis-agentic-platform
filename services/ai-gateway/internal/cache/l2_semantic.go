package cache

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

// L2SemanticClient queries the ChromaDB / Vector Semantic Cache endpoint
// to intercept paraphrased prompts (targeting ~30% redundant LLM traffic offload).
type L2SemanticClient struct {
	baseURL    string
	httpClient *http.Client
	threshold  float64
}

type semanticLookupReq struct {
	TenantID  string  `json:"tenant_id"`
	Prompt    string  `json:"prompt"`
	Threshold float64 `json:"threshold"`
}

type semanticLookupResp struct {
	Hit    bool   `json:"hit"`
	Answer string `json:"answer"`
}

func NewL2SemanticClient(baseURL string, threshold float64) *L2SemanticClient {
	return &L2SemanticClient{
		baseURL:    baseURL,
		httpClient: &http.Client{Timeout: 2 * time.Second},
		threshold:  threshold,
	}
}

func (c *L2SemanticClient) Lookup(ctx context.Context, tenantID, prompt string) (string, bool) {
	if c.baseURL == "" {
		return "", false
	}

	body, _ := json.Marshal(semanticLookupReq{
		TenantID:  tenantID,
		Prompt:    prompt,
		Threshold: c.threshold,
	})

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, fmt.Sprintf("%s/semantic/lookup", c.baseURL), bytes.NewReader(body))
	if err != nil {
		return "", false
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil || resp.StatusCode != http.StatusOK {
		return "", false
	}
	defer resp.Body.Close()

	var result semanticLookupResp
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", false
	}
	return result.Answer, result.Hit
}
