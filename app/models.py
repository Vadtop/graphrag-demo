from pydantic import BaseModel


class IngestRequest(BaseModel):
    text: str
    source: str = "manual"


class IngestResponse(BaseModel):
    entities_extracted: int
    relationships_extracted: int
    source: str


class CypherQueryRequest(BaseModel):
    cypher: str
    params: dict = {}


class CypherQueryResponse(BaseModel):
    results: list[dict]
    cypher: str
    row_count: int


class GraphQueryRequest(BaseModel):
    question: str


class GraphQueryResponse(BaseModel):
    answer: str
    cypher_used: str
    sources: list[str]


class EntityResponse(BaseModel):
    name: str
    label: str
    properties: dict


class GraphStatsResponse(BaseModel):
    total_nodes: int
    total_relationships: int
    node_labels: dict[str, int]
    relationship_types: dict[str, int]
