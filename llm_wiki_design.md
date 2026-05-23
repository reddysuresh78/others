<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Yes

Below is a concrete blueprint for **DB + vector search + wiki** with a LangGraph-style router. The short version is: model exact facts in SQL, keep raw text in chunks for retrieval, maintain a compiled markdown wiki for durable synthesis, and let a planner decide which of those three substrates to use per question.[^1][^2]

## Data model

A practical schema uses Postgres for document metadata and structured facts, pgvector or a dedicated vector store for chunk embeddings, and markdown files for wiki pages. pgvector keeps text, metadata, and embeddings in one transactional system, which simplifies consistency and filtering.[^3][^1]

**Core SQL tables**

```sql
CREATE TABLE documents (
  doc_id            BIGSERIAL PRIMARY KEY,
  source_uri        TEXT UNIQUE NOT NULL,
  source_type       TEXT NOT NULL,         -- pdf, docx, email, ticket, wiki, webpage
  title             TEXT,
  checksum          TEXT NOT NULL,
  language          TEXT,
  created_at        TIMESTAMPTZ,
  ingested_at       TIMESTAMPTZ DEFAULT now(),
  owner             TEXT,
  security_label    TEXT,                  -- public, internal, confidential
  metadata          JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE chunks (
  chunk_id          BIGSERIAL PRIMARY KEY,
  doc_id            BIGINT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
  chunk_index       INT NOT NULL,
  text              TEXT NOT NULL,
  token_count       INT,
  embedding         vector(1536),
  tsv               tsvector,
  page_num          INT,
  section_path      TEXT,
  metadata          JSONB DEFAULT '{}'::jsonb,
  UNIQUE (doc_id, chunk_index)
);

CREATE INDEX chunks_embedding_hnsw
ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX chunks_tsv_gin
ON chunks USING gin (tsv);

CREATE INDEX chunks_metadata_gin
ON chunks USING gin (metadata);

CREATE TABLE entities (
  entity_id         BIGSERIAL PRIMARY KEY,
  canonical_name    TEXT NOT NULL,
  entity_type       TEXT NOT NULL,         -- person, org, product, issue, policy
  aliases           TEXT[] DEFAULT '{}',
  wiki_slug         TEXT,
  metadata          JSONB DEFAULT '{}'::jsonb,
  UNIQUE (canonical_name, entity_type)
);

CREATE TABLE document_entities (
  doc_id            BIGINT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
  entity_id         BIGINT NOT NULL REFERENCES entities(entity_id) ON DELETE CASCADE,
  mention_count     INT DEFAULT 1,
  PRIMARY KEY (doc_id, entity_id)
);

CREATE TABLE facts (
  fact_id           BIGSERIAL PRIMARY KEY,
  subject_entity_id BIGINT REFERENCES entities(entity_id),
  predicate         TEXT NOT NULL,
  object_text       TEXT,
  object_num        NUMERIC,
  object_date       DATE,
  unit              TEXT,
  valid_from        DATE,
  valid_to          DATE,
  doc_id            BIGINT REFERENCES documents(doc_id),
  chunk_id          BIGINT REFERENCES chunks(chunk_id),
  confidence        REAL,
  metadata          JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE query_cache (
  cache_key         TEXT PRIMARY KEY,
  question          TEXT NOT NULL,
  answer            TEXT NOT NULL,
  citations         JSONB NOT NULL,
  created_at        TIMESTAMPTZ DEFAULT now()
);
```

This structure gives you exact queryability for aggregates, metadata filtering, and entity joins, while keeping chunk-level evidence linked back to source documents for grounding.[^2][^1]

## Wiki layout

Karpathy’s pattern is useful here as the **compiled knowledge** layer: markdown pages for entities, concepts, timelines, comparisons, contradictions, and dashboards, all linked and readable by both humans and the LLM. His gist comment also notes markdown-first dashboards for recent sources, timelines, contradictions, and open questions, which is a strong pattern for operationalizing the wiki.[^4][^2]

A simple wiki filesystem:

```text
wiki/
  index.md
  entities/
    vendor-acme.md
    product-foo.md
  concepts/
    incident-classification.md
    customer-onboarding.md
  timelines/
    vendor-acme-timeline.md
  comparisons/
    vendor-acme-vs-vendor-beta.md
  dashboards/
    contradictions.md
    open-questions.md
    recent-sources.md
  sources/
    2026-05-23-source-123.md
  log.md
```

**Example wiki page frontmatter**

```yaml
---
title: Vendor Acme
type: entity
entity_type: org
entity_id: 42
aliases: [Acme Inc., ACME]
last_updated: 2026-05-23
source_docs: [1201, 1218, 1304]
related_pages:
  - /timelines/vendor-acme-timeline
  - /comparisons/vendor-acme-vs-vendor-beta
open_questions:
  - "Has Acme resolved the SLA breach from Q1?"
contradictions:
  - "Security certification date differs across two sources"
---
```

**Suggested page sections**

- Summary
- Key facts
- Timeline
- Relationships
- Contradictions
- Open questions
- Sources

That keeps the wiki optimized for synthesis, not raw storage.[^4][^2]

## Ingestion flow

Ingestion should write to all three representations: SQL metadata/facts, vector chunks, and wiki pages. Karpathy’s gist describes ingestion as reading a new source, writing a summary page, updating the index, updating relevant entity/concept pages, and appending to the log; a single source may touch many wiki pages.[^5][^2]

Recommended pipeline:

1. **Acquire source**: file upload, email sync, crawler, API pull.[^2]
2. **Parse**: OCR/PDF/doc/email to normalized text plus structural sections.[^1]
3. **Classify and tag**: detect source type, language, date, owner, security label.[^1]
4. **Chunk**: 400 to 800 tokens with 50 to 100 token overlap; Qdrant’s LangGraph tutorial uses recursive chunking with overlap to preserve context.[^2]
5. **Embed**: generate embeddings for chunks and store them with metadata filters.[^1][^2]
6. **Extract entities and facts**: NER plus schema-guided extraction into `entities`, `document_entities`, and `facts`.
7. **Update wiki**:
    - write source summary page,
    - update relevant entity/concept/timeline/comparison pages,
    - update dashboards such as contradictions and open questions,
    - append `log.md`.[^4][^2]
8. **Quality pass**:
    - deduplicate near-identical chunks,
    - flag contradictory facts,
    - mark low-confidence extractions for review.

A clean ingest worker contract:

```python
class IngestResult(TypedDict):
    doc_id: int
    chunk_ids: list[int]
    entity_ids: list[int]
    fact_ids: list[int]
    updated_wiki_pages: list[str]
    warnings: list[str]
```


## Query router

Your router should classify a question before retrieval. Agentic RAG systems work better than linear “retrieve then answer” flows because they can choose among multiple tools and data sources based on the question type. LangGraph is particularly good for this because it keeps a shared state and supports tool routing.[^6][^2]

**Intent classes**

- `aggregate`: count, total, average, trend, by group, date range
- `lookup`: exact fact or record lookup
- `evidence`: “show me source”, “quote”, “where does it say”
- `synthesis`: summarize, compare, pros/cons, common themes
- `timeline`: what changed over time
- `diagnostic`: why, root cause, contradictions
- `actionable`: recommend next steps based on data
- `ambiguous`: missing entity/date/metric; ask follow-up

**Routing rules**

```python
def route_question(q: str) -> str:
    if asks_for_count_sum_avg_groupby(q):
        return "sql"
    if asks_for_exact_source_or_quote(q):
        return "retrieve"
    if asks_for_compare_timeline_rootcause_summary(q):
        return "wiki_plus_retrieve"
    if mixes_numeric_and_explanatory_parts(q):
        return "sql_plus_retrieve_plus_wiki"
    return "retrieve"
```

Good examples:

- “How many sev-1 incidents in Q1?” → `sql`
- “What does policy X say about retention?” → `retrieve`
- “How has vendor Acme changed over time?” → `wiki_plus_retrieve`
- “How many sev-1 incidents did Acme cause in Q1, and why?” → `sql_plus_retrieve_plus_wiki`


## LangGraph skeleton

Qdrant’s tutorial shows the core pattern: a state object, an agent node, tool nodes, and a router that decides whether to call tools or finish. You can extend that to your hybrid pipeline with SQL, search, and wiki tools.[^2]

```python
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, START, END

class QAState(TypedDict):
    question: str
    intent: Optional[str]
    entities: List[str]
    filters: dict
    plan: List[dict]
    sql_result: Optional[dict]
    search_results: List[dict]
    wiki_pages: List[dict]
    answer: Optional[str]
    citations: List[dict]
    needs_clarification: bool
    clarification_question: Optional[str]

def classify_node(state: QAState) -> QAState:
    # LLM or rules-based classifier
    state["intent"] = classify_intent(state["question"])
    state["entities"] = extract_entities(state["question"])
    state["filters"] = extract_filters(state["question"])
    state["needs_clarification"] = missing_required_slots(state)
    if state["needs_clarification"]:
        state["clarification_question"] = build_clarification_question(state)
    return state

def plan_node(state: QAState) -> QAState:
    state["plan"] = build_plan(
        intent=state["intent"],
        entities=state["entities"],
        filters=state["filters"],
        question=state["question"],
    )
    return state

def sql_node(state: QAState) -> QAState:
    sql_query = generate_safe_sql(state["question"], state["entities"], state["filters"])
    state["sql_result"] = run_sql(sql_query)
    return state

def retrieve_node(state: QAState) -> QAState:
    state["search_results"] = hybrid_search(
        query=state["question"],
        entities=state["entities"],
        filters=state["filters"],
        top_k=12
    )
    return state

def wiki_node(state: QAState) -> QAState:
    state["wiki_pages"] = read_relevant_wiki_pages(
        question=state["question"],
        entities=state["entities"],
        top_k=6
    )
    return state

def synthesize_node(state: QAState) -> QAState:
    state["answer"], state["citations"] = synthesize_answer(
        question=state["question"],
        sql_result=state["sql_result"],
        search_results=state["search_results"],
        wiki_pages=state["wiki_pages"],
    )
    return state

def route_after_classify(state: QAState):
    if state["needs_clarification"]:
        return "clarify"
    return "plan"

def route_after_plan(state: QAState):
    plan_types = {step["tool"] for step in state["plan"]}
    if plan_types == {"sql"}:
        return "sql"
    if plan_types == {"retrieve"}:
        return "retrieve"
    if plan_types == {"wiki"}:
        return "wiki"
    return "multi"

graph = StateGraph(QAState)
graph.add_node("classify", classify_node)
graph.add_node("plan", plan_node)
graph.add_node("sql", sql_node)
graph.add_node("retrieve", retrieve_node)
graph.add_node("wiki", wiki_node)
graph.add_node("synthesize", synthesize_node)

graph.add_edge(START, "classify")
graph.add_conditional_edges("classify", route_after_classify, {
    "clarify": END,
    "plan": "plan"
})
graph.add_conditional_edges("plan", route_after_plan, {
    "sql": "sql",
    "retrieve": "retrieve",
    "wiki": "wiki",
    "multi": "sql"
})
graph.add_edge("sql", "retrieve")
graph.add_edge("retrieve", "wiki")
graph.add_edge("wiki", "synthesize")
graph.add_edge("synthesize", END)

compiled = graph.compile()
```

This graph is intentionally simple: you can later add reranking, answer verification, and self-correction loops.[^6][^2]

## Tool contracts

Keep each tool deterministic and narrow.

**1) SQL tool**

- Input: intent, entities, date range, metric, grouping
- Output: rows, aggregates, executed SQL, confidence
- Rule: numbers only come from SQL, never estimated from retrieved text.[^1]

**2) Hybrid retrieval tool**

- Use vector + full-text search + metadata filters; Encore’s Postgres example notes pgvector works well alongside SQL filtering, and the tutorial suggests adding hybrid search with `tsvector` for better results.[^1]
- Output: top chunks with doc id, section, score, snippet

**3) Wiki reader**

- Input: entities/topics
- Output: markdown page excerpts, related pages, contradictions, open questions
- Rule: wiki is framing and synthesis, not sole evidence for exact quotes.[^2]

**4) Reranker**

- Cross-encoder or LLM rerank before final synthesis for top 20 → top 6

**5) Answer synthesizer**

- Uses strict source roles:
    - SQL for exact counts and math
    - Retrieval for quotes and evidence
    - Wiki for context, consistency, timeline, contradictions


## Retrieval query examples

**Hybrid retrieval SQL**

```sql
WITH q AS (
  SELECT $1::vector AS emb, plainto_tsquery('english', $2) AS tsq
)
SELECT
  c.chunk_id,
  c.doc_id,
  d.title,
  c.section_path,
  1 - (c.embedding <=> q.emb) AS vec_score,
  ts_rank_cd(c.tsv, q.tsq) AS bm25_score,
  (0.7 * (1 - (c.embedding <=> q.emb)) + 0.3 * ts_rank_cd(c.tsv, q.tsq)) AS final_score,
  left(c.text, 800) AS snippet
FROM chunks c
JOIN documents d ON d.doc_id = c.doc_id
CROSS JOIN q
WHERE d.security_label IN ('public','internal')
  AND (q.tsq IS NULL OR c.tsv @@ q.tsq)
  AND (d.metadata->>'vendor' = COALESCE($3, d.metadata->>'vendor'))
ORDER BY final_score DESC
LIMIT 20;
```

Hybrid retrieval generally improves recall over vector-only search, especially for exact terms, numbers, and entity names.[^1]

**Aggregate example**

```sql
SELECT
  date_trunc('month', created_at) AS month,
  count(*) AS sev1_count
FROM incidents
WHERE severity = 'sev1'
  AND vendor_name = 'Acme'
  AND created_at >= '2026-01-01'
  AND created_at <  '2026-04-01'
GROUP BY 1
ORDER BY 1;
```


## Answer policy

Use a strict hierarchy:

1. If a question needs counting, summing, averaging, filtering, or grouping, run SQL first.[^1]
2. If the user asks for a quote or exact wording, retrieve chunks and cite the source doc.[^1]
3. If the user asks for “why,” “compare,” “what changed,” or “summarize across many docs,” read wiki pages plus retrieval evidence.[^4][^2]
4. If answers from different layers conflict:
    - SQL wins for numeric truth,
    - raw documents win for exact wording,
    - wiki can be marked stale and scheduled for refresh.[^2]

**Synthesis prompt skeleton**

```text
You are answering with three evidence layers.

Rules:
- SQL output is authoritative for numeric claims.
- Retrieved source chunks are authoritative for quotes and exact document statements.
- Wiki pages are authoritative only for synthesized context and prior compiled understanding.
- If sources disagree, explicitly say so.
- Never invent counts from text retrieval.
- Return answer + evidence bullets + unresolved questions.
```


## Operational jobs

To keep the system healthy, add background jobs:

- **wiki lint pass**: detect stale pages, orphan pages, missing backlinks, contradictions, unresolved open questions; this follows Karpathy’s maintenance idea closely.[^5][^2]
- **fact reconciliation**: dedupe facts and resolve conflicts
- **embedding refresh**: re-embed if model changes
- **cache warmup**: store frequent query plans and results
- **access-control sync**: keep SQL and vector metadata aligned with source permissions


## Practical stack

A sensible production stack for your background:

- **PostgreSQL + pgvector** if you want one operational store; Encore’s guide argues this reduces sync complexity because embeddings and metadata live together.[^1]
- **Qdrant** if you expect separate vector scaling or more advanced vector operations; their LangGraph tutorial demonstrates tool-based routing with vector stores and web search.[^2]
- **LangGraph** for orchestration and stateful multi-step execution.[^6][^2]
- **Markdown wiki in Git** for auditability, human review, and persistent compiled knowledge.[^4][^2]


## Recommendation

For your use case, I’d implement this minimal viable version first:

- Postgres tables: `documents`, `chunks`, `entities`, `document_entities`, `facts`
- pgvector + `tsvector` hybrid search
- `wiki/` with `entities/`, `timelines/`, `dashboards/`, `sources/`
- LangGraph nodes: `classify -> plan -> sql/retrieve/wiki -> synthesize`
- background workers: `ingest`, `wiki_update`, `lint`

That gets you a system that can answer:

- exact numeric questions,
- source-grounded retrieval questions,
- cross-document synthesis questions,
- mixed questions like “how many, and why?”[^2][^1]

Would you like the next step as actual Python code files for:

1. SQLAlchemy models,
2. LangGraph router,
3. ingestion worker,
4. wiki page templates?
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2

[^2]: https://www.youtube.com/watch?v=RQsLXmenr48\&vl=en

[^3]: https://encore.dev/articles/how-to-build-rag-pipeline

[^4]: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f?permalink_comment_id=6089370

[^5]: https://www.linkedin.com/posts/cloudwithraj_who-knew-agi-is-just-a-couple-markdown-files-activity-7449471498236354560-JGgN

[^6]: https://docs.langchain.com/oss/python/langgraph/agentic-rag

[^7]: https://qdrant.tech/documentation/tutorials-build-essentials/agentic-rag-langgraph/

[^8]: https://www.elastic.co/search-labs/blog/local-rag-agent-elasticsearch-langgraph-llama3

[^9]: https://www.linkedin.com/posts/shyam-sundar-domakonda_agenticai-rag-hybridsearch-activity-7420305064625561600-0PxT

[^10]: https://www.youtube.com/watch?v=60XDTWhklLA

[^11]: https://www.reddit.com/r/Rag/comments/1oakglq/should_i_use_pgvector_or_build_a_full_llamaindex/

[^12]: https://datacouch.io/blog/hybrid-rag-with-langgraph-qdrant-advanced-tutorial/

[^13]: https://blog.stackademic.com/postgresql-pgvector-spring-ai-your-first-production-ready-rag-pipeline-2025-edition-5aa921bdfec6

[^14]: https://pub.towardsai.net/andrej-karpathy-killed-rag-or-did-he-the-llm-wiki-pattern-7824d876e790

[^15]: https://arxiv.org/html/2408.04948v1

[^16]: https://blog.devgenius.io/empowering-conversations-with-your-data-langgraph-rag-and-openai-leveraging-bigquery-ee034bcb8916

[^17]: https://www.pgedge.com/blog/building-a-rag-server-with-postgresql-part-1-loading-your-content

