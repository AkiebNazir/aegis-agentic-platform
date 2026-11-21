COMPOSE := docker compose -f deploy/docker-compose.yml

.PHONY: help up up-gpu down logs \
        up-infra up-gateway up-mcp up-graphrag up-orchestrator \
        proto test-all

help:
	@echo "Aegis Agentic Platform - Available Commands:"
	@echo "  --- Full System ---"
	@echo "  make up               Start all 4 AI services + Redis, ChromaDB, Neo4j"
	@echo "  make up-gpu           Start full system + local vLLM GPU container"
	@echo "  make down             Stop and remove all containers"
	@echo "  make logs             Tail logs across all running services"
	@echo ""
	@echo "  --- Standalone Services (Run Separately) ---"
	@echo "  make up-infra         Start only Redis, ChromaDB, and Neo4j"
	@echo "  make up-gateway       Start only 01-ai-gateway (+ Redis & ChromaDB)"
	@echo "  make up-mcp           Start only mcp-private-inference (+ Go bridge)"
	@echo "  make up-graphrag      Start only graphrag-engine (+ Neo4j & ChromaDB)"
	@echo "  make up-orchestrator  Start only agent-orchestrator (+ Redis)"
	@echo ""
	@echo "  --- Build & Quality ---"
	@echo "  make proto            Generate Go and Python gRPC stubs"
	@echo "  make test-all         Run Go and Python unit test suites"

# --- Full Platform ---
up:
	$(COMPOSE) --profile all up -d --build

up-gpu:
	$(COMPOSE) --profile all --profile gpu up -d --build

down:
	$(COMPOSE) --profile "*" down

logs:
	$(COMPOSE) --profile "*" logs -f

# --- Standalone Project Targets ---
up-infra:
	$(COMPOSE) --profile infra up -d

up-gateway:
	$(COMPOSE) --profile gateway up -d --build

up-mcp:
	$(COMPOSE) --profile mcp up -d --build

up-graphrag:
	$(COMPOSE) --profile graphrag up -d --build

up-orchestrator:
	$(COMPOSE) --profile orchestrator up -d --build

# --- gRPC Contract Generation ---
proto:
	@echo "Generating Go stubs for 01-ai-gateway..."
	protoc --go_out=services/01-ai-gateway --go_opt=paths=source_relative \
	       --go-grpc_out=services/01-ai-gateway --go-grpc_opt=paths=source_relative \
	       -I contracts/proto contracts/proto/gateway.proto
	@echo "Generating Python stubs for graphrag-engine..."
	python -m grpc_tools.protoc -I contracts/proto \
	       --python_out=services/graphrag-engine/src \
	       --grpc_python_out=services/graphrag-engine/src \
	       contracts/proto/graphrag.proto
	@echo "Generating Python stubs for agent-orchestrator..."
	python -m grpc_tools.protoc -I contracts/proto \
	       --python_out=services/agent-orchestrator/src \
	       --grpc_python_out=services/agent-orchestrator/src \
	       contracts/proto/gateway.proto contracts/proto/graphrag.proto

# --- Test Suites ---
test-all:
	@echo "Running Golang tests (01-ai-gateway)..."
	cd services/01-ai-gateway && go test ./...
	@echo "Running Python tests (graphrag-engine)..."
	cd services/graphrag-engine && pytest
	@echo "Running Python tests (agent-orchestrator)..."
	cd services/agent-orchestrator && pytest