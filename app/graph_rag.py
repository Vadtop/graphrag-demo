import logging
from app.config import settings
from app.graph_db import run_cypher

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Extract entities and relationships from the text.
Return ONLY valid JSON with this structure:
{
  "entities": [{"name": "...", "label": "...", "properties": {...}}],
  "relationships": [{"from": "...", "to": "...", "type": "...", "properties": {...}}]
}

Entity labels should be one of: Technology, Concept, Person, Organization, Tool, Method
Relationship types should be one of: USES, PART_OF, RELATES_TO, DEPENDS_ON, IMPLEMENTS, ENABLES

Text:
{text}
"""


def _call_llm(prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content


def extract_and_ingest(text: str, source: str = "manual") -> dict:
    prompt = EXTRACTION_PROMPT.format(text=text)
    raw = _call_llm(prompt)

    import json

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])
    except (json.JSONDecodeError, ValueError):
        logger.error(f"Failed to parse LLM extraction output: {raw[:200]}")
        return {"entities_extracted": 0, "relationships_extracted": 0, "source": source}

    entities = data.get("entities", [])
    relationships = data.get("relationships", [])

    run_cypher("MERGE (s:Source {name: $name})", {"name": source})

    for ent in entities:
        props = ent.get("properties", {})
        props_str = ", ".join(f'{k}: "{v}"' for k, v in props.items()) if props else ""
        extra = f", {props_str}" if props_str else ""
        label = ent.get("label", "Entity")
        name = ent["name"]
        run_cypher(
            f"MERGE (e:{label} {{name: $name{extra}}}) MERGE (s:Source {{name: $source}}) MERGE (s)-[:CONTAINS]->(e)",
            {"name": name, "source": source, **props},
        )

    for rel in relationships:
        from_name = rel["from"]
        to_name = rel["to"]
        rel_type = rel["type"]
        props = rel.get("properties", {})
        props_str = ", ".join(f'{k}: "{v}"' for k, v in props.items()) if props else ""
        extra = f", {props_str}" if props_str else ""
        run_cypher(
            f"MATCH (a {{name: $from}}) MATCH (b {{name: $to}}) MERGE (a)-[:{rel_type} {{}}]->(b)",
            {"from": from_name, "to": to_name},
        )

    logger.info(
        f"Ingested: {len(entities)} entities, {len(relationships)} relationships from {source}"
    )
    return {
        "entities_extracted": len(entities),
        "relationships_extracted": len(relationships),
        "source": source,
    }


CYPHER_GEN_PROMPT = """You are a Neo4j Cypher expert. Generate a Cypher query for the given question.
The graph has nodes with labels: Entity, Technology, Concept, Person, Organization, Tool, Method, Source
All nodes have a "name" property. Additional properties may exist.
Relationships: USES, PART_OF, RELATES_TO, DEPENDS_ON, IMPLEMENTS, ENABLES, CONTAINS

Return ONLY the Cypher query, nothing else. No markdown, no explanation.

Question: {question}
"""


def ask_graph(question: str) -> dict:
    cypher_raw = _call_llm(CYPHER_GEN_PROMPT.format(question=question))
    cypher = cypher_raw.strip().strip("`").strip()
    if cypher.lower().startswith("cypher"):
        cypher = cypher[6:].strip()

    logger.info(f"Generated Cypher: {cypher}")

    try:
        results = run_cypher(cypher)
    except Exception as e:
        logger.error(f"Cypher execution failed: {e}")
        return {
            "answer": f"Cypher query failed: {e}",
            "cypher_used": cypher,
            "sources": [],
        }

    if not results:
        return {
            "answer": "No results found in the knowledge graph.",
            "cypher_used": cypher,
            "sources": [],
        }

    result_str = "\n".join(str(r) for r in results)
    sources = []
    for r in results:
        for v in r.values():
            if isinstance(v, dict) and "name" in v:
                sources.append(v["name"])
            elif isinstance(v, str):
                sources.append(v)
    sources = list(set(sources))

    answer_prompt = f"""Answer the question based on these graph query results.

Question: {question}

Results:
{result_str}

Answer concisely:"""

    answer = _call_llm(answer_prompt)
    return {"answer": answer, "cypher_used": cypher, "sources": sources}
