import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from app.config import settings
from app.models import (
    IngestRequest,
    IngestResponse,
    CypherQueryRequest,
    CypherQueryResponse,
    GraphQueryRequest,
    GraphQueryResponse,
    GraphStatsResponse,
)
from app.graph_db import init_schema, run_cypher, get_stats, close_driver
from app.graph_rag import extract_and_ingest, ask_graph

logger = logging.getLogger(__name__)

SAMPLE_DATA = [
    (
        "RAG (Retrieval-Augmented Generation) uses vector databases like Qdrant and ChromaDB. "
        "It retrieves relevant documents and feeds them to an LLM for grounded generation. "
        "LangChain provides RAG chains that combine retrieval with generation."
    ),
    (
        "LoRA fine-tuning uses low-rank adaptation to reduce trainable parameters. "
        "Unsloth accelerates LoRA training with custom Triton kernels. "
        "QLoRA combines 4-bit quantization with LoRA adapters for efficient GPU usage. "
        "PEFT library manages parameter-efficient fine-tuning."
    ),
    (
        "Neo4j is a graph database that stores entities and relationships. "
        "Cypher is its query language for pattern matching. "
        "GraphRAG combines knowledge graphs with LLMs for multi-hop reasoning. "
        "LangChain provides GraphCypherQAChain for natural language to Cypher translation."
    ),
    (
        "Docker containers provide reproducible environments for ML deployments. "
        "FastAPI serves ML models as REST APIs with automatic documentation. "
        "HuggingFace Transformers library loads pre-trained models for inference. "
        "sentence-transformers generates embeddings for semantic search."
    ),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Neo4j schema...")
    init_schema()
    for i, text in enumerate(SAMPLE_DATA):
        try:
            extract_and_ingest(text, source=f"sample_{i + 1}")
        except Exception as e:
            logger.warning(
                f"Could not ingest sample data (LLM may be unavailable): {e}"
            )
            break
    logger.info("Startup complete")
    yield
    close_driver()


app = FastAPI(
    title="GraphRAG Demo",
    description="Knowledge graph + LLM: extract entities, query with Cypher, ask in natural language",
    version="1.0",
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {
        "service": "GraphRAG Demo",
        "version": "1.0",
        "endpoints": {
            "POST /ingest": "Ingest text → extract entities/relations → store in Neo4j",
            "POST /cypher": "Execute raw Cypher query",
            "POST /ask": "Ask question in natural language → Cypher → answer",
            "GET /entities": "List all entities in the graph",
            "GET /graph/stats": "Graph statistics (nodes, relationships, labels)",
            "GET /health": "Health check (Neo4j connection)",
        },
    }


@app.post("/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest):
    result = extract_and_ingest(req.text, source=req.source)
    return IngestResponse(**result)


@app.post("/cypher", response_model=CypherQueryResponse)
async def cypher_query(req: CypherQueryRequest):
    try:
        results = run_cypher(req.cypher, req.params)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cypher error: {e}")
    return CypherQueryResponse(
        results=results, cypher=req.cypher, row_count=len(results)
    )


@app.post("/ask", response_model=GraphQueryResponse)
async def ask(req: GraphQueryRequest):
    result = ask_graph(req.question)
    return GraphQueryResponse(**result)


@app.get("/entities")
async def list_entities(label: str | None = None):
    if label:
        results = run_cypher(
            f"MATCH (e:{label}) RETURN e.name as name, labels(e) as labels LIMIT 100"
        )
    else:
        results = run_cypher(
            "MATCH (e) WHERE NOT 'Source' IN labels(e) RETURN e.name as name, labels(e) as labels LIMIT 100"
        )
    return {"entities": results, "count": len(results)}


@app.get("/graph/stats", response_model=GraphStatsResponse)
async def graph_stats():
    stats = get_stats()
    return GraphStatsResponse(**stats)


@app.get("/health")
async def health():
    try:
        result = run_cypher("RETURN 1 as ok")
        return {"neo4j": bool(result), "status": "ok"}
    except Exception as e:
        return {"neo4j": False, "status": "error", "detail": str(e)}
