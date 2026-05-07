# EHDS Linked Health Data Portal

An open benchmark resource for evaluating web AI agents in the context of the European Health Data Space (EHDS), established by Regulation (EU) 2025/327. The portal combines a synthetic FHIR-on-RDF clinical knowledge graph, a HealthDCAT-AP catalogue with machine-readable ODRL usage policies, and a reusable Model Context Protocol (MCP) connector — all openly accessible at **[https://mcp.linkeddata.es](https://mcp.linkeddata.es)**.

This repository contains the evaluation harness, benchmark queries, and data pipeline scripts described in the accompanying ISWC 2025 Resource Track paper.

---

## What is this?

AI agents querying health data spaces need to do three things correctly: find relevant datasets, understand what they are legally permitted to do with them, and retrieve clinical facts accurately. Existing benchmarks test none of these together. This resource does.

The portal exposes 30 synthetic clinical cohorts (573 unique patients, 21.2 million RDF triples) governed by 8 ODRL usage policies and described by a HealthDCAT-AP Release 5 catalogue. A 50-query benchmark with SPARQL-derived ground truth evaluates agents under three grounding conditions: ungrounded baseline, retrieval-augmented generation (RAG) over a pre-built vector store, and structured access via the MCP connector.

---

## Repository contents

```
ehds-linked-data-portal/
├── eval/
│   ├── benchmark.csv              # 50 benchmark queries with ground truth (CSV)
│   ├── benchmark.py               # Same queries with embedded SPARQL derivations
│   └── evaluation_50_queries.py   # Evaluation harness — runs all three conditions
├── mcp/
│   ├── server.py                  # MCP connector (7 typed tools, SSE transport)
│   ├── datasets.py                # Dataset registration and catalogue utilities
│   └── visualization.py           # Graph visualisation utilities
├── rag/
│   ├── chroma_db/                 # Pre-built ChromaDB vector store (all-MiniLM-L6-v2)
│   └── chroma_db.zip              # Same store as a portable archive
├── fhir_to_rdf.py                 # FHIR R4 JSON → RDF Turtle conversion pipeline
├── dataset_description.pdf        # Full description of cohorts, policies, and schema
├── annotation_guide.pdf           # Scoring protocol for completeness and hallucination
├── LICENSE
└── README.md
```

---

## Quickstart

### Prerequisites

- Python 3.10+
- API key for the model(s) you want to evaluate (Anthropic, DeepSeek, or a local Ollama instance)
- No infrastructure setup required — the SPARQL endpoint and MCP connector are hosted at `https://mcp.linkeddata.es`

### Install dependencies

```bash
pip install -r requirements.txt
```

### Set your API key

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # for Claude
export DEEPSEEK_API_KEY=...           # for DeepSeek
# For Ollama, no key needed — set OLLAMA_HOST if not running on localhost
```

### Run the full evaluation

```bash
python eval/evaluation_50_queries.py
```

This runs all 50 queries under all three conditions (baseline, RAG, MCP) for the configured model(s) and writes results to `eval/results/`. A single run takes a few minutes for the baseline and RAG conditions; the MCP condition is slower due to tool call round-trips (see paper Table 7 for latency figures).

### Run a single condition

```bash
python eval/evaluation_50_queries.py --condition mcp
python eval/evaluation_50_queries.py --condition rag
python eval/evaluation_50_queries.py --condition baseline
```

### Run a single query category

```bash
python eval/evaluation_50_queries.py --category policy
# categories: discovery, policy, clinical, comparative
```

### Add a new model

In `eval/evaluation_50_queries.py`, extend the `RUNNERS` dictionary with two lines:

```python
RUNNERS["my-model"] = MyModelRunner(api_key=os.environ["MY_API_KEY"])
```

---

## RAG condition

The pre-built ChromaDB vector store is included in `rag/chroma_db/`, embedded with `all-MiniLM-L6-v2` over catalogue metadata and per-patient summary text. No download is required. A portable archive is also available at `rag/chroma_db.zip` and at `https://mcp.linkeddata.es/rag`.

The harness loads the vector store from `rag/chroma_db/` by default. To use a different path:

```bash
python eval/evaluation_50_queries.py --condition rag --rag-path /path/to/chroma_db
```

---

## MCP condition

The MCP connector at `https://mcp.linkeddata.es/connector` is publicly available and requires no authentication. The harness connects to it automatically. The connector exposes seven tools:

| Tool | Description |
|---|---|
| `ehds_list_datasets` | List all datasets with HealthDCAT-AP metadata |
| `ehds_describe_dataset` | Full metadata for one dataset |
| `ehds_check_policy` | ODRL permissions, prohibitions, and obligations |
| `ehds_search_datasets` | Keyword search over the catalogue |
| `ehds_get_patients` | Patient demographics for a cohort |
| `ehds_get_condition_stats` | Aggregate statistics for a SNOMED-coded condition |
| `ehds_query_clinical` | Free SPARQL over the clinical named graphs |

To connect an AI agent manually — for example, to explore the portal interactively in Claude — add `https://mcp.linkeddata.es/connector` as an MCP connector in claude.ai settings. No installation required.

---

## Results format

Each run produces a JSON file in `eval/results/` with one entry per query:

```json
{
  "query_id": "P2",
  "condition": "mcp",
  "model": "claude-sonnet-4-6",
  "answer": "...",
  "tools_called": ["ehds_check_policy"],
  "completeness": 1.0,
  "hallucination_rate": 0.0,
  "combined_score": 1.0,
  "latency_seconds": 18.4
}
```

Scores are computed automatically against the ground truth in `benchmark.py`. See `supplements/annotation_guide.pdf` for the full scoring protocol.

---

## Verifying ground truth

Every ground truth value is derived from a SPARQL query against the live RDF store and is independently verifiable. The interactive SPARQL endpoint is at:

**[https://mcp.linkeddata.es/sparql/](https://mcp.linkeddata.es/sparql/)**

Example — confirm the total unique patient count:

```sparql
SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE {
  GRAPH ?g { ?p a <http://hl7.org/fhir/Patient> . }
  FILTER(?g != <https://ehds-prototype.example.org/graph/catalogue>)
}
```

---

## Extending the benchmark

**Add queries** — append entries to the `QUERIES` list in `eval/benchmark.py` with an `id`, `category`, `query`, `ground_truth_sparql`, and `ground_truth`. Add the corresponding row to `eval/benchmark.csv`.

**Add clinical cohorts** — generate new patients with [Synthea](https://synthetichealth.github.io/synthea/), convert to RDF with `fhir_to_rdf.py`, load into Fuseki as a new named graph, and register in the HealthDCAT-AP catalogue with `mcp/datasets.py`. The MCP connector resolves datasets dynamically from the catalogue and requires no code changes.

---

## Citing this work

```bibtex
@inproceedings{manab2025ehds,
  title     = {An Open Linked Data Portal for Benchmarking Web {AI} Agents
               in the {European Health Data Space}},
  author    = {Manab, Meem Arafat and Rodr{\'i}guez-Doncel, V{\'i}ctor},
  year      = {2026}
}
```

---

## Acknowledgements

This work was supported by the HARNESS project (Horizon Europe grant 101169409) and the MALTA project (PID2024-159504OB-I00, MICIU/AEI). All data is synthetic; no real patient records are included. Released under GNU GPL v3.
