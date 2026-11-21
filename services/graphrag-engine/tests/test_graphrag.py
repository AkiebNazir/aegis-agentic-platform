from src.retrieval.reranker import filter_and_rerank_vectors, synthesize_hybrid_context


def test_filter_and_rerank_vectors():
    hits = [
        ("Noisy irrelevant doc", 0.92),
        ("PaymentGateway P99 latency runbook", 0.14),
        ("FraudEngine gRPC pool remediation", 0.28),
    ]
    ranked = filter_and_rerank_vectors(hits, max_distance=0.65)
    assert len(ranked) == 2
    assert ranked[0] == "PaymentGateway P99 latency runbook"


def test_synthesize_hybrid_context():
    merged = synthesize_hybrid_context(
        graph_facts=["PaymentGateway -[CALLS]-> FraudEngine"],
        vector_chunks=["Scale FraudEngine replicas."],
    )
    assert "Structural Service Topology (Neo4j)" in merged
    assert "PaymentGateway -[CALLS]-> FraudEngine" in merged
    assert "Scale FraudEngine replicas." in merged