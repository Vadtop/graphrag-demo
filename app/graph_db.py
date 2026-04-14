import logging
from app.config import settings

logger = logging.getLogger(__name__)

_driver = None


def get_driver():
    global _driver
    if _driver is not None:
        return _driver
    from neo4j import GraphDatabase

    _driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    logger.info(f"Connected to Neo4j at {settings.neo4j_uri}")
    return _driver


def close_driver():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def run_cypher(cypher: str, params: dict = None) -> list[dict]:
    driver = get_driver()
    with driver.session() as session:
        result = session.run(cypher, params or {})
        return [record.data() for record in result]


def init_schema():
    cyphers = [
        "CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE",
        "CREATE CONSTRAINT source_name IF NOT EXISTS FOR (s:Source) REQUIRE s.name IS UNIQUE",
    ]
    for c in cyphers:
        try:
            run_cypher(c)
        except Exception:
            pass
    logger.info("Neo4j schema initialized")


def get_stats() -> dict:
    node_count = run_cypher("MATCH (n) RETURN count(n) as cnt")[0]["cnt"]
    rel_count = run_cypher("MATCH ()-[r]->() RETURN count(r) as cnt")[0]["cnt"]

    labels = {}
    for row in run_cypher("MATCH (n) RETURN labels(n) as lbls, count(n) as cnt"):
        for lbl in row["lbls"]:
            labels[lbl] = labels.get(lbl, 0) + row["cnt"]

    rel_types = {}
    for row in run_cypher("MATCH ()-[r]->() RETURN type(r) as t, count(r) as cnt"):
        rel_types[row["t"]] = row["cnt"]

    return {
        "total_nodes": node_count,
        "total_relationships": rel_count,
        "node_labels": labels,
        "relationship_types": rel_types,
    }


def clear_graph():
    run_cypher("MATCH (n) DETACH DELETE n")
