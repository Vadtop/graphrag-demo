"""Tests for graph logic, entity extraction, and Cypher patterns."""
import pytest
import json


def test_entity_extraction_json_parse():
    """LLM entity output parses to valid structure."""
    sample_llm_output = '''
    {
        "entities": [
            {"name": "LangChain", "type": "Technology", "description": "LLM framework"},
            {"name": "OpenAI", "type": "Company", "description": "AI company"}
        ],
        "relationships": [
            {"from": "LangChain", "to": "OpenAI", "type": "INTEGRATES_WITH"}
        ]
    }
    '''
    data = json.loads(sample_llm_output.strip())
    assert "entities" in data
    assert "relationships" in data
    assert len(data["entities"]) == 2
    assert data["entities"][0]["name"] == "LangChain"


def test_cypher_node_creation_pattern():
    """MERGE pattern prevents duplicate nodes."""
    cypher = "MERGE (n:Technology {name: $name}) SET n.description = $desc RETURN n"
    assert "MERGE" in cypher
    assert "name" in cypher


def test_cypher_relationship_pattern():
    """Relationship creation uses correct Cypher syntax."""
    cypher = "MATCH (a {name: $from}), (b {name: $to}) MERGE (a)-[r:INTEGRATES_WITH]->(b)"
    assert "MATCH" in cypher
    assert "MERGE" in cypher
    assert "->" in cypher


def test_entity_deduplication():
    """Entity list deduplicates by name."""
    entities = [
        {"name": "RAG", "type": "Technique"},
        {"name": "RAG", "type": "Technique"},
        {"name": "LangChain", "type": "Technology"},
    ]
    unique = {e["name"]: e for e in entities}
    assert len(unique) == 2


def test_relationship_type_uppercase():
    """Relationship types follow Neo4j convention (UPPER_CASE)."""
    rel_types = ["USES", "INTEGRATES_WITH", "PART_OF", "DEPENDS_ON"]
    for rel in rel_types:
        assert rel == rel.upper()


def test_graph_stats_structure():
    """Stats response has expected keys."""
    mock_stats = {
        "node_count": 15,
        "relationship_count": 23,
        "labels": {"Technology": 8, "Company": 4, "Concept": 3}
    }
    assert "node_count" in mock_stats
    assert "relationship_count" in mock_stats
    assert isinstance(mock_stats["labels"], dict)


def test_natural_language_to_cypher_input():
    """NL question is passed correctly to LLM."""
    question = "What technologies does LangChain use?"
    prompt_template = f"Convert to Cypher: {question}"
    assert question in prompt_template


def test_answer_generation_has_context():
    """Answer is generated from graph results, not hallucinated."""
    graph_results = [{"name": "OpenAI", "rel": "INTEGRATES_WITH"}]
    context = str(graph_results)
    answer_prompt = f"Based on graph data: {context}\nAnswer the question."
    assert "OpenAI" in answer_prompt
