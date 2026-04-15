# Cypher Query Examples

## After ingesting text, try these queries:

### Find all entities of a specific type
```cypher
MATCH (e:Technology) RETURN e.name, e.description LIMIT 10
```

### Find relationships between entities
```cypher
MATCH (a)-[r]->(b) RETURN a.name, type(r), b.name LIMIT 20
```

### Multi-hop: what is connected to "RAG"?
```cypher
MATCH (a {name: "RAG"})-[r*1..2]-(b) RETURN a.name, b.name, r LIMIT 15
```

### Count by entity type
```cypher
MATCH (n) RETURN labels(n) as type, count(n) as count ORDER BY count DESC
```

## REST API Examples

### Ingest text
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "LangChain is a framework for building LLM applications. It integrates with OpenAI, HuggingFace, and vector databases like ChromaDB and Qdrant. RAG uses LangChain retrievers to fetch relevant documents."}'
```

### Ask natural language question
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What does LangChain integrate with?"}'
```

### List entities
```bash
curl "http://localhost:8000/entities?label=Technology"
```

### Raw Cypher
```bash
curl -X POST http://localhost:8000/cypher \
  -H "Content-Type: application/json" \
  -d '{"query": "MATCH (n) RETURN labels(n), n.name LIMIT 10"}'
```
