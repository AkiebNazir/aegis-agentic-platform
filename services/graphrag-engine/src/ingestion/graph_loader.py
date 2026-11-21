import os
from typing import List, Dict
from neo4j import GraphDatabase


class Neo4jGraphLoader:
    """Manages Neo4j service topology and entity-relationship ingestion/queries."""

    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password123")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def seed_topology(self) -> None:
        """Seeds sample enterprise microservice topology into Neo4j."""
        cypher = """
        MERGE (gw:Service {name: 'PaymentGateway', tier: 'tier-1'})
        MERGE (fe:Service {name: 'FraudEngine', tier: 'tier-1'})
        MERGE (lb:Service {name: 'LoyaltyBenefitService', tier: 'tier-1'})
        MERGE (pg:Database {name: 'LedgerPostgres', engine: 'PostgreSQL'})
        MERGE (rd:Cache {name: 'SessionRedis', engine: 'Redis'})
        MERGE (gw)-[:CALLS {protocol: 'gRPC', timeout_ms: 500}]->(fe)
        MERGE (gw)-[:CALLS {protocol: 'gRPC', timeout_ms: 800}]->(lb)
        MERGE (gw)-[:WRITES_TO]->(pg)
        MERGE (lb)-[:READS_FROM]->(rd)
        """
        with self.driver.session() as session:
            session.run(cypher)

    def query_related_topology(self, query_text: str) -> List[str]:
        """Traverses 1-to-2 hop relationships for entities mentioned in the query."""
        cypher = """
        MATCH (n)-[r]->(m)
        WHERE toLower($q) CONTAINS toLower(n.name)
           OR toLower($q) CONTAINS toLower(m.name)
        RETURN n.name AS source, type(r) AS rel, properties(r) AS props, m.name AS target
        LIMIT 10
        """
        facts: List[str] = []
        with self.driver.session() as session:
            result = session.run(cypher, q=query_text)
            for row in result:
                props = row["props"]
                prop_str = f" {props}" if props else ""
                facts.append(f"{row['source']} -[{row['rel']}{prop_str}]-> {row['target']}")
        return facts