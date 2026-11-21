package router

import (
	"context"
	"time"

	pb "github.com/AkiebNazir/aegis-agentic-platform/services/ai-gateway/pb"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

type OrchestratorClient struct {
	conn   *grpc.ClientConn
	client pb.AgentOrchestratorClient
}

func NewOrchestratorClient(target string) (*OrchestratorClient, error) {
	conn, err := grpc.NewClient(target, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return nil, err
	}
	return &OrchestratorClient{
		conn:   conn,
		client: pb.NewAgentOrchestratorClient(conn),
	}, nil
}

func (o *OrchestratorClient) ForwardPrompt(ctx context.Context, reqID, tenantID, prompt string, useGraphRAG bool) (*pb.PromptResponse, error) {
	rpcCtx, cancel := context.WithTimeout(ctx, 20*time.Second)
	defer cancel()

	return o.client.ProcessPrompt(rpcCtx, &pb.PromptRequest{
		RequestId:   reqID,
		TenantId:    tenantID,
		Prompt:      prompt,
		UseGraphRag: useGraphRAG,
	})
}

func (o *OrchestratorClient) Close() error {
	return o.conn.Close()
}
