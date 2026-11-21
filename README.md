# Aegis Agentic Platform

A polyglot, enterprise-grade **Agentic AI & LLM Infrastructure** monorepo built in **Golang** and **Python**. Each core capability is architected as an **independently runnable microservice** (with its own `Dockerfile`, dependencies, and test suite) that composes into a unified, low-latency AI mesh via **gRPC / Protobuf** and **Model Context Protocol (MCP)**.

---

## System Architecture

```mermaid
flowchart LR
    Client([Client / API Caller]) -->|HTTP POST /v1/chat| GW

    subgraph S1 [01-ai-gateway :8080 - Golang]
        GW[Auth & Token-Bucket Rate Limiter] --> L1[(L1 Redis Exact Cache)]
        L1 -->|Miss| L2[L2 Semantic Cache Lookup]
    end

    L2 -->|Miss via gRPC :50051| ORCH

    subgraph S4 [agent-orchestrator :50051 - Python]
        ORCH[Swarm Router & CrewAI Handoffs] --> JUDGE{LangChain Evaluator\nLLM-as-a-Judge}
        JUDGE -->|Fail + Critique| ORCH
        ORCH <--> STATE[(Redis State Checkpoints)]
    end

    ORCH -->|gRPC :50052| GRAG

    subgraph S3 [graphrag-engine :50052 / :8003 - Python]
        GRAG[LangGraph Hybrid Retrieval] --> NEO[(Neo4j Service Graph)]
        GRAG --> CHROMA[(ChromaDB Vector Runbooks)]
    end

    ORCH -->|OpenAI-Compat API| VLLM
    MCP -->|HTTP :8003| GRAG

    subgraph S2 [mcp-private-inference - Python + Go]
        MCP[Python MCP Server] <--> GOBRIDGE[Go Backend Bridge :8090]
        VLLM[Private vLLM / DeepSeek-R1 :8001]
    end