#!/usr/bin/env python3
"""
EHDS MCP Server
An MCP server exposing EHDS-compliant health data space assets to LLM agents.
Provides structured access to HealthDCAT-AP catalogue metadata and FHIR-on-RDF clinical data.
"""

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from SPARQLWrapper import SPARQLWrapper, JSON

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SPARQL_ENDPOINT = "http://localhost:48242/ehds/sparql"

GRAPH_CATALOGUE   = "https://ehds-prototype.example.org/graph/catalogue"

# At the top of server.py, after the other imports:
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from datasets import DATASETS

DATASET_GRAPHS = {v["uri"]: v["graph"] for v in DATASETS.values()}

#DATASET_GRAPHS = {
#    "https://ehds-prototype.example.org/dataset-diabetes-cohort": GRAPH_DIABETES,
#    "https://ehds-prototype.example.org/dataset-hypertension-cohort": GRAPH_HYPERTENSION,
#    "https://ehds-prototype.example.org/dataset-metabolic-syndrome-cohort": GRAPH_METABOLIC,
#}


PREFIXES = """
PREFIX fhir:  <http://hl7.org/fhir/>
PREFIX dcat:  <http://www.w3.org/ns/dcat#>
PREFIX dct:   <http://purl.org/dc/terms/>
PREFIX hdcat: <https://healthdcat-ap.github.io/healthdcat-ap/release/5/>
PREFIX odrl:  <http://www.w3.org/ns/odrl/2/>
PREFIX xsd:   <http://www.w3.org/2001/XMLSchema#>
PREFIX ehds:  <https://ehds-prototype.example.org/>
"""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ehds-mcp")

# ---------------------------------------------------------------------------
# SPARQL helper
# ---------------------------------------------------------------------------

def sparql_query(query: str) -> list[dict]:
    """Execute a SPARQL SELECT query and return bindings as list of dicts."""
    sparql = SPARQLWrapper(SPARQL_ENDPOINT)
    sparql.setQuery(PREFIXES + "\n" + query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    bindings = results.get("results", {}).get("bindings", [])
    return [{k: v["value"] for k, v in row.items()} for row in bindings]


def get_clinical_graph(dataset_uri: str) -> str | None:
    """Resolve a dataset URI to its named graph URI."""
    # Direct lookup first
    if dataset_uri in DATASET_GRAPHS:
        return DATASET_GRAPHS[dataset_uri]
    # Suffix match for abbreviated URIs
    for k, v in DATASET_GRAPHS.items():
        if dataset_uri.endswith(k.split("/")[-1]):
            return v
    # Fallback: query the catalogue
    rows = sparql_query(f"""
SELECT ?graph WHERE {{
  GRAPH <{GRAPH_CATALOGUE}> {{
    <{dataset_uri}> dcat:distribution ?dist .
    ?dist hdcat:namedGraph ?graph .
  }}
}}""")
    return rows[0]["graph"] if rows else None

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

app = Server("ehds-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="ehds_list_datasets",
            description=(
                "List all datasets in the EHDS catalogue with their titles, descriptions, "
                "population sizes, health categories, and access conditions."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="ehds_describe_dataset",
            description=(
                "Get full HealthDCAT-AP metadata for a specific dataset, including temporal "
                "coverage, keywords, data standard, and distribution details."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_uri": {
                        "type": "string",
                        "description": "The URI of the dataset to describe"
                    }
                },
                "required": ["dataset_uri"]
            }
        ),
        Tool(
            name="ehds_check_policy",
            description=(
                "Return the ODRL usage policy for a dataset: permitted purposes, "
                "prohibitions, and obligations."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_uri": {
                        "type": "string",
                        "description": "The URI of the dataset"
                    }
                },
                "required": ["dataset_uri"]
            }
        ),
        Tool(
            name="ehds_search_datasets",
            description=(
                "Search the catalogue for datasets matching a keyword or health category. "
                "Returns matching dataset URIs and titles."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Keyword to search for in dataset titles and descriptions"
                    }
                },
                "required": ["keyword"]
            }
        ),
        Tool(
            name="ehds_get_patients",
            description=(
                "List patients in a dataset with key demographic attributes: "
                "gender, birth date, and city."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_uri": {
                        "type": "string",
                        "description": "The URI of the dataset"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of patients to return (default 10)",
                        "default": 10
                    }
                },
                "required": ["dataset_uri"]
            }
        ),
        Tool(
            name="ehds_get_condition_stats",
            description=(
                "Get aggregate statistics for a SNOMED condition in a dataset: "
                "patient count, gender breakdown, and age distribution."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_uri": {
                        "type": "string",
                        "description": "The URI of the dataset"
                    },
                    "snomed_code": {
                        "type": "string",
                        "description": "SNOMED CT code for the condition (e.g. '44054006' for Type 2 Diabetes)"
                    }
                },
                "required": ["dataset_uri", "snomed_code"]
            }
        ),
        Tool(
            name="ehds_query_clinical",
            description=(
                "Execute a SPARQL SELECT query against the clinical data of a specific dataset. "
                "Use this for custom queries not covered by other tools. "
                "The named graph for the dataset is automatically injected."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_uri": {
                        "type": "string",
                        "description": "The URI of the dataset to query"
                    },
                    "sparql_query": {
                        "type": "string",
                        "description": "SPARQL SELECT query. Use GRAPH ?g { ... } pattern. The graph URI will be provided."
                    }
                },
                "required": ["dataset_uri", "sparql_query"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        result = await dispatch_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def dispatch_tool(name: str, args: dict) -> Any:
    if name == "ehds_list_datasets":
        return tool_list_datasets()
    elif name == "ehds_describe_dataset":
        return tool_describe_dataset(args["dataset_uri"])
    elif name == "ehds_check_policy":
        return tool_check_policy(args["dataset_uri"])
    elif name == "ehds_search_datasets":
        return tool_search_datasets(args["keyword"])
    elif name == "ehds_get_patients":
        return tool_get_patients(args["dataset_uri"], args.get("limit", 10))
    elif name == "ehds_get_condition_stats":
        return tool_get_condition_stats(args["dataset_uri"], args["snomed_code"])
    elif name == "ehds_query_clinical":
        return tool_query_clinical(args["dataset_uri"], args["sparql_query"])
    else:
        raise ValueError(f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def tool_list_datasets() -> dict:
    rows = sparql_query(f"""
SELECT ?dataset ?title ?description ?population ?healthCategory ?license WHERE {{
  GRAPH <{GRAPH_CATALOGUE}> {{
    ?dataset a dcat:Dataset ;
             dct:title ?title ;
             dct:description ?description .
    OPTIONAL {{ ?dataset hdcat:populationSize ?population . }}
    OPTIONAL {{ ?dataset hdcat:healthCategory ?healthCategory . }}
    OPTIONAL {{ ?dataset dct:license ?license . }}
  }}
}}""")
    return {"datasets": rows, "count": len(rows)}


def tool_describe_dataset(dataset_uri: str) -> dict:
    rows = sparql_query(f"""
SELECT ?p ?o WHERE {{
  GRAPH <{GRAPH_CATALOGUE}> {{
    <{dataset_uri}> ?p ?o .
  }}
}}""")
    if not rows:
        return {"error": f"Dataset not found: {dataset_uri}"}

    # Also get distribution details
    dist_rows = sparql_query(f"""
SELECT ?distTitle ?accessURL ?namedGraph ?format WHERE {{
  GRAPH <{GRAPH_CATALOGUE}> {{
    <{dataset_uri}> dcat:distribution ?dist .
    OPTIONAL {{ ?dist dct:title ?distTitle . }}
    OPTIONAL {{ ?dist dcat:accessURL ?accessURL . }}
    OPTIONAL {{ ?dist hdcat:namedGraph ?namedGraph . }}
    OPTIONAL {{ ?dist dct:format ?format . }}
  }}
}}""")

    # Get temporal coverage
    temporal_rows = sparql_query(f"""
SELECT ?start ?end WHERE {{
  GRAPH <{GRAPH_CATALOGUE}> {{
    <{dataset_uri}> dct:temporal ?period .
    OPTIONAL {{ ?period dcat:startDate ?start . }}
    OPTIONAL {{ ?period dcat:endDate ?end . }}
  }}
}}""")

    props = {}
    for row in rows:
        p = row["p"].split("/")[-1].split("#")[-1]
        props[p] = row["o"]

    return {
        "dataset_uri": dataset_uri,
        "properties": props,
        "distributions": dist_rows,
        "temporal_coverage": temporal_rows[0] if temporal_rows else {}
    }


def tool_check_policy(dataset_uri: str) -> dict:
    rows = sparql_query(f"""
SELECT ?policy ?policyTitle ?policyDescription WHERE {{
  GRAPH <{GRAPH_CATALOGUE}> {{
    <{dataset_uri}> odrl:hasPolicy ?policy .
    OPTIONAL {{ ?policy dct:title ?policyTitle . }}
    OPTIONAL {{ ?policy dct:description ?policyDescription . }}
  }}
}}""")

    if not rows:
        return {"error": f"No policy found for dataset: {dataset_uri}"}

    policy_uri = rows[0].get("policy", "")

    # Get permissions
    perm_rows = sparql_query(f"""
SELECT ?action ?purposeValue WHERE {{
  GRAPH <{GRAPH_CATALOGUE}> {{
    <{policy_uri}> odrl:permission ?perm .
    ?perm odrl:action ?action .
    OPTIONAL {{
      ?perm odrl:constraint ?c .
      ?c odrl:rightOperand ?purposeValue .
    }}
  }}
}}""")    

    # Get prohibitions

    prohib_rows = sparql_query(f"""
SELECT ?action ?purposeValue WHERE {{
  GRAPH <{GRAPH_CATALOGUE}> {{
    <{policy_uri}> odrl:prohibition ?prohib .
    ?prohib odrl:action ?action .
    OPTIONAL {{
      ?prohib odrl:constraint ?c .
      ?c odrl:rightOperand ?purposeValue .
    }}
  }}
}}""")

    # Get obligations
    oblig_rows = sparql_query(f"""
SELECT ?action WHERE {{
  GRAPH <{GRAPH_CATALOGUE}> {{
    <{policy_uri}> odrl:obligation ?oblig .
    ?oblig odrl:action ?action .
  }}
}}""")

    return {
        "policy_uri": policy_uri,
        "title": rows[0].get("policyTitle", ""),
        "description": rows[0].get("policyDescription", ""),
        "permissions": perm_rows,
        "prohibitions": prohib_rows,
        "obligations": oblig_rows
    }


def tool_search_datasets(keyword: str) -> dict:
    keyword_lower = keyword.lower()
    rows = sparql_query(f"""
SELECT ?dataset ?title ?description WHERE {{
  GRAPH <{GRAPH_CATALOGUE}> {{
    ?dataset a dcat:Dataset ;
             dct:title ?title ;
             dct:description ?description .
    FILTER (
      CONTAINS(LCASE(STR(?title)), "{keyword_lower}") ||
      CONTAINS(LCASE(STR(?description)), "{keyword_lower}")
    )
  }}
}}""")
    return {"keyword": keyword, "matches": rows, "count": len(rows)}


def tool_get_patients(dataset_uri: str, limit: int = 10) -> dict:
    graph = get_clinical_graph(dataset_uri)
    if not graph:
        return {"error": f"Cannot resolve clinical graph for: {dataset_uri}"}

    rows = sparql_query(f"""
SELECT ?patient ?gender ?birthDate ?city WHERE {{
  GRAPH <{graph}> {{
    ?patient a fhir:Patient .
    OPTIONAL {{ ?patient fhir:gender ?gender . }}
    OPTIONAL {{ ?patient fhir:birthDate ?birthDate . }}
    OPTIONAL {{
      ?patient fhir:address ?addr .
      ?addr fhir:city ?city .
    }}
  }}
}}
LIMIT {limit}""")

    return {
        "dataset_uri": dataset_uri,
        "clinical_graph": graph,
        "patients": rows,
        "count": len(rows)
    }


def tool_get_condition_stats(dataset_uri: str, snomed_code: str) -> dict:
    graph = get_clinical_graph(dataset_uri)
    if not graph:
        return {"error": f"Cannot resolve clinical graph for: {dataset_uri}"}

    # Patient count with this condition
    count_rows = sparql_query(f"""
SELECT (COUNT(DISTINCT ?patient) AS ?count) WHERE {{
  GRAPH <{graph}> {{
    ?condition a fhir:Condition ;
               fhir:code ?coding ;
               fhir:subject ?patient .
    ?coding fhir:code "{snomed_code}" .
  }}
}}""")

    # Gender breakdown
    gender_rows = sparql_query(f"""
SELECT ?gender (COUNT(DISTINCT ?patient) AS ?count) WHERE {{
  GRAPH <{graph}> {{
    ?condition a fhir:Condition ;
               fhir:code ?coding ;
               fhir:subject ?patient .
    ?coding fhir:code "{snomed_code}" .
    ?patient fhir:gender ?gender .
  }}
}} GROUP BY ?gender""")

    # Condition display name
    display_rows = sparql_query(f"""
SELECT DISTINCT ?display WHERE {{
  GRAPH <{graph}> {{
    ?condition a fhir:Condition ;
               fhir:code ?coding .
    ?coding fhir:code "{snomed_code}" ;
            fhir:display ?display .
  }}
}} LIMIT 1""")

    return {
        "dataset_uri": dataset_uri,
        "snomed_code": snomed_code,
        "condition_display": display_rows[0]["display"] if display_rows else snomed_code,
        "patient_count": count_rows[0]["count"] if count_rows else "0",
        "gender_breakdown": gender_rows
    }


def tool_query_clinical(dataset_uri: str, sparql_query_str: str) -> dict:
    graph = get_clinical_graph(dataset_uri)
    if not graph:
        return {"error": f"Cannot resolve clinical graph for: {dataset_uri}"}

    # Inject graph URI as a comment so the LLM knows which graph to use
    annotated_query = f"# Clinical graph: {graph}\n{sparql_query_str}"

    try:
        rows = sparql_query(annotated_query)
        return {
            "dataset_uri": dataset_uri,
            "clinical_graph": graph,
            "results": rows,
            "count": len(rows)
        }
    except Exception as e:
        return {"error": str(e), "clinical_graph": graph}


# ---------------------------------------------------------------------------
# Entry point — stdio (local) or SSE/HTTP (remote)
# ---------------------------------------------------------------------------

async def main_stdio():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EHDS Linked Health Data Portal</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #f8fafc; color: #1e293b; line-height: 1.6; }
  header { background: #0f172a; color: white; padding: 2rem; }
  header h1 { font-size: 1.6rem; font-weight: 700; }
  header p  { color: #94a3b8; margin-top: 0.4rem; font-size: 0.95rem; }
  main { max-width: 900px; margin: 2rem auto; padding: 0 1.5rem; }
  .badge { display: inline-block; background: #e0f2fe; color: #0369a1;
           font-size: 0.75rem; padding: 0.2rem 0.6rem; border-radius: 9999px;
           margin-right: 0.4rem; font-weight: 600; }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px,1fr));
           gap: 1rem; margin: 1.5rem 0; }
  .card  { background: white; border: 1px solid #e2e8f0; border-radius: 10px;
           padding: 1.2rem; }
  .card h2 { font-size: 1rem; font-weight: 600; margin-bottom: 0.4rem; }
  .card p  { font-size: 0.88rem; color: #64748b; margin-bottom: 0.8rem; }
  .card a  { display: inline-block; background: #0f172a; color: white;
             padding: 0.4rem 0.9rem; border-radius: 6px; font-size: 0.85rem;
             text-decoration: none; }
  .card a:hover { background: #1e293b; }
  .stats { display: flex; gap: 1.5rem; flex-wrap: wrap; margin: 1rem 0; }
  .stat  { text-align: center; }
  .stat .n { font-size: 1.8rem; font-weight: 700; color: #0f172a; }
  .stat .l { font-size: 0.8rem; color: #64748b; }
  section { margin-top: 2rem; }
  section h2 { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.8rem;
               border-bottom: 1px solid #e2e8f0; padding-bottom: 0.4rem; }
  code { background: #f1f5f9; padding: 0.1rem 0.4rem; border-radius: 4px;
         font-size: 0.85rem; }
  pre  { background: #f1f5f9; padding: 1rem; border-radius: 8px; overflow-x: auto;
         font-size: 0.83rem; margin: 0.5rem 0; }
  footer { text-align: center; color: #94a3b8; font-size: 0.82rem;
           padding: 2rem; margin-top: 3rem; border-top: 1px solid #e2e8f0; }
</style>
</head>
<body>
<header>
  <h1>EHDS Linked Health Data Portal</h1>
  <p>First open EHDS-compliant linked health data resource for LLM agent evaluation</p>
  <div style="margin-top:0.8rem">
    <span class="badge">HealthDCAT-AP R5</span>
    <span class="badge">FHIR R4 on RDF</span>
    <span class="badge">ODRL policies</span>
    <span class="badge">MCP connector</span>
    <span class="badge">CC-BY 4.0</span>
  </div>
</header>
<main>
  <div class="stats" style="margin-top:1.5rem">
    <div class="stat"><div class="n">500+</div><div class="l">Unique patients</div></div>
    <div class="stat"><div class="n">21.2M</div><div class="l">RDF triples</div></div>
    <div class="stat"><div class="n">30</div><div class="l">Clinical cohorts</div></div>
    <div class="stat"><div class="n">7</div><div class="l">MCP tools</div></div>
    <div class="stat"><div class="n">50</div><div class="l">Benchmark queries</div></div>
  </div>

  <div class="cards">
    <div class="card">
      <h2>MCP Connector</h2>
      <p>Connect any MCP-compatible AI agent — Claude, mcphost, or Python SDK — to query the data space.</p>
      <a href="/connector">Connect via SSE</a>
    </div>
    <div class="card">
      <h2>SPARQL Explorer</h2>
      <p>Write and run SPARQL queries against the HealthDCAT-AP catalogue and FHIR-on-RDF clinical data.</p>
      <a href="/sparql/">Open SPARQL UI</a>
    </div>
    <div class="card">
      <h2>Supplements</h2>
      <p>Benchmark queries, evaluation harness, FHIR-to-RDF pipeline, and annotation guide — all files from the paper.</p>
      <a href="/supplements">Browse files</a>
    </div>
    <div class="card">
      <h2>RAG Vector Store</h2>
      <p>Download the pre-built ChromaDB vector store for RAG-condition evaluation.</p>
      <a href="/rag">Download ChromaDB</a>
    </div>
    <div class="card">
      <h2>Knowledge Graph</h2>
      <p>Explore the EHDS data space interactively — datasets, ODRL policies, and clinical relationships visualised as a force-directed graph.</p>
      <a href="/visualization">Open Explorer</a>
    </div>
  </div>

<section>
    <h2>Datasets</h2>
<table style="width:100%;border-collapse:collapse;font-size:0.85rem;margin-top:0.5rem">
  <thead>
    <tr style="background:#f1f5f9;border-bottom:2px solid #e2e8f0">
      <th style="text-align:left;padding:0.5rem 0.8rem">Graph</th>
      <th style="text-align:left;padding:0.5rem 0.8rem">Condition</th>
      <th style="text-align:left;padding:0.5rem 0.8rem">SNOMED CT</th>
      <th style="text-align:right;padding:0.5rem 0.8rem">Patients</th>
    </tr>
  </thead>
  <tbody>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/diabetes</code></td><td>Type 2 Diabetes Mellitus</td><td>44054006</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/hypertension</code></td><td>Essential Hypertension</td><td>59621000</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/metabolic-syndrome</code></td><td>Metabolic Syndrome</td><td>237602007</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/obesity</code></td><td>Obesity</td><td>162864005</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/hyperlipidemia</code></td><td>Hyperlipidemia</td><td>55822004</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/prediabetes</code></td><td>Prediabetes</td><td>714628002</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/hypothyroidism</code></td><td>Hypothyroidism</td><td>83664006</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/anemia</code></td><td>Anemia</td><td>271737000</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/heart-failure</code></td><td>Heart Failure</td><td>88805009</td><td style="text-align:right">15</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/stroke</code></td><td>Stroke</td><td>230690007</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/myocardial-infarction</code></td><td>Myocardial Infarction</td><td>22298006</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/ischemic-heart-disease</code></td><td>Ischaemic Heart Disease</td><td>414545008</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/atrial-fibrillation</code></td><td>Atrial Fibrillation</td><td>49436004</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem;color:#94a3b8"><code>graph/dementia</code></td><td style="color:#94a3b8">Dementia</td><td style="color:#94a3b8">52448006</td><td style="text-align:right;color:#94a3b8">0</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/anxiety</code></td><td>Anxiety</td><td>80583007</td><td style="text-align:right">10</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/ptsd</code></td><td>PTSD</td><td>47505003</td><td style="text-align:right">10</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/alzheimers</code></td><td>Alzheimer's Disease</td><td>26929004</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/osteoporosis</code></td><td>Osteoporosis</td><td>64859006</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/rheumatoid-arthritis</code></td><td>Rheumatoid Arthritis</td><td>69896004</td><td style="text-align:right">38</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/chronic-kidney-disease</code></td><td>Chronic Kidney Disease</td><td>431855005</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/asthma</code></td><td>Asthma</td><td>195967001</td><td style="text-align:right">28</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/copd</code></td><td>COPD</td><td>87433001</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/sleep-apnea</code></td><td>Sleep Apnea</td><td>73430006</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/uti</code></td><td>Urinary Tract Infection</td><td>197927001</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/breast-cancer</code></td><td>Breast Cancer</td><td>254837009</td><td style="text-align:right">10</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/prostate-cancer</code></td><td>Prostate Cancer</td><td>126906006</td><td style="text-align:right">10</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/colorectal-cancer</code></td><td>Colorectal Cancer</td><td>363406005</td><td style="text-align:right">10</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/osteoarthritis</code></td><td>Osteoarthritis</td><td>57676002</td><td style="text-align:right">40</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/substance-use-disorder</code></td><td>Substance Use Disorder</td><td>6525002</td><td style="text-align:right">10</td></tr>
    <tr><td style="padding:0.4rem 0.8rem"><code>graph/chronic-pain</code></td><td>Chronic Pain</td><td>82423001</td><td style="text-align:right">10</td></tr>
    <tr style="background:#f8fafc;border-top:2px solid #e2e8f0">
      <td style="padding:0.4rem 0.8rem"><code>graph/catalogue</code></td>
      <td colspan="2" style="color:#64748b">HealthDCAT-AP Release 5 metadata catalogue</td>
      <td style="text-align:right;color:#64748b">—</td>
    </tr>
  </tbody>
</table>
</section>

  <section>
    <h2>Quick Start</h2>
    <p style="font-size:0.9rem;margin-bottom:0.5rem"><strong>Claude.ai:</strong> Settings → Connectors → Add custom connector</p>
    <pre>https://mcp.linkeddata.es/connector</pre>
    <p style="font-size:0.9rem;margin:0.8rem 0 0.5rem"><strong>mcphost:</strong></p>
    <pre>echo '{"mcpServers":{"ehds":{"url":"https://mcp.linkeddata.es/connector"}}}' > ~/.mcp.json
mcphost -m ollama:llama3.2</pre>
    <p style="font-size:0.9rem;margin:0.8rem 0 0.5rem"><strong>Python:</strong></p>
    <pre>from mcp import ClientSession
from mcp.client.sse import sse_client

async with sse_client("https://mcp.linkeddata.es/connector") as (r, w):
    async with ClientSession(r, w) as session:
        await session.initialize()
        result = await session.call_tool("ehds_list_datasets", {})</pre>
  </section>

  <section>
    <h2>Citation</h2>
    <pre>Manab et al. (2026). EHDS Linked Health Data Portal.
ISWC 2026 Resource Track. https://mcp.linkeddata.es</pre>
  </section>
</main>
<footer>
  Ontology Engineering Group, Universidad Politécnica de Madrid &nbsp;|&nbsp;
  HARNESS Project, Horizon Europe 101169409 &nbsp;|&nbsp;
  <a href="https://github.com/manabcodes/H-Mantis" style="color:#94a3b8">GitHub</a>
</footer>
</body>
</html>"""


SPARQL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SPARQL Explorer — EHDS Portal</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #f8fafc; color: #1e293b; }
  header { background: #0f172a; color: white; padding: 1rem 1.5rem;
           display: flex; align-items: center; gap: 1rem; }
  header a { color: #94a3b8; text-decoration: none; font-size: 0.9rem; }
  header h1 { font-size: 1.1rem; font-weight: 600; }
  main { max-width: 1100px; margin: 1.5rem auto; padding: 0 1.5rem; }
  .layout { display: grid; grid-template-columns: 220px 1fr; gap: 1.2rem; }
  .sidebar h3 { font-size: 0.8rem; font-weight: 600; color: #64748b;
                text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }
  .example { background: white; border: 1px solid #e2e8f0; border-radius: 6px;
             padding: 0.6rem; margin-bottom: 0.5rem; cursor: pointer; font-size: 0.8rem; }
  .example:hover { background: #f1f5f9; }
  .example strong { display: block; color: #0f172a; margin-bottom: 0.2rem; }
  .example span { color: #64748b; }
  .editor-area { display: flex; flex-direction: column; gap: 0.8rem; }
  .graphs { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.2rem; }
  .graph-btn { background: #e0f2fe; color: #0369a1; border: none; border-radius: 4px;
               padding: 0.25rem 0.6rem; font-size: 0.78rem; cursor: pointer; font-weight: 500; }
  .graph-btn:hover { background: #bae6fd; }
  textarea { width: 100%; height: 180px; font-family: "SF Mono", "Fira Code", monospace;
             font-size: 0.85rem; padding: 0.8rem; border: 1px solid #e2e8f0;
             border-radius: 8px; resize: vertical; background: white; }
  textarea:focus { outline: 2px solid #0369a1; border-color: transparent; }
  .toolbar { display: flex; gap: 0.6rem; align-items: center; }
  button#run { background: #0f172a; color: white; border: none; border-radius: 6px;
               padding: 0.5rem 1.2rem; font-size: 0.9rem; cursor: pointer; font-weight: 500; }
  button#run:hover { background: #1e293b; }
  button#run:disabled { background: #94a3b8; cursor: not-allowed; }
  select#format { border: 1px solid #e2e8f0; border-radius: 6px; padding: 0.45rem 0.7rem;
                  font-size: 0.85rem; background: white; }
  #status { font-size: 0.82rem; color: #64748b; }
  #results { margin-top: 0.5rem; }
  table { width: 100%; border-collapse: collapse; background: white;
          border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;
          font-size: 0.83rem; }
  th { background: #f1f5f9; font-weight: 600; text-align: left;
       padding: 0.6rem 0.8rem; border-bottom: 1px solid #e2e8f0; }
  td { padding: 0.5rem 0.8rem; border-bottom: 1px solid #f1f5f9;
       word-break: break-all; max-width: 400px; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #f8fafc; }
  .uri { color: #0369a1; }
  .literal { color: #166534; }
  .error { background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px;
           padding: 1rem; color: #dc2626; font-size: 0.85rem; }
  .count { font-size: 0.82rem; color: #64748b; margin-bottom: 0.5rem; }
</style>
</head>
<body>
<header>
  <a href="/">← EHDS Portal</a>
  <h1>SPARQL Explorer</h1>
</header>
<main>
  <div class="layout">
    <div class="sidebar">
      <div class="graphs">
<h3>Named Graphs</h3>
<select id="graph-select" style="width:100%;border:1px solid #e2e8f0;border-radius:6px;padding:0.4rem 0.6rem;font-size:0.82rem;background:white;margin-bottom:0.5rem">
  <option value="">— select graph —</option>
  <option value="catalogue">catalogue</option>
  <option value="diabetes">diabetes</option>
  <option value="hypertension">hypertension</option>
  <option value="metabolic-syndrome">metabolic-syndrome</option>
  <option value="obesity">obesity</option>
  <option value="hyperlipidemia">hyperlipidemia</option>
  <option value="prediabetes">prediabetes</option>
  <option value="hypothyroidism">hypothyroidism</option>
  <option value="anemia">anemia</option>
  <option value="heart-failure">heart-failure</option>
  <option value="stroke">stroke</option>
  <option value="myocardial-infarction">myocardial-infarction</option>
  <option value="ischemic-heart-disease">ischemic-heart-disease</option>
  <option value="atrial-fibrillation">atrial-fibrillation</option>
  <option value="dementia">dementia</option>
  <option value="anxiety">anxiety</option>
  <option value="ptsd">ptsd</option>
  <option value="alzheimers">alzheimers</option>
  <option value="osteoporosis">osteoporosis</option>
  <option value="rheumatoid-arthritis">rheumatoid-arthritis</option>
  <option value="chronic-kidney-disease">chronic-kidney-disease</option>
  <option value="asthma">asthma</option>
  <option value="copd">copd</option>
  <option value="sleep-apnea">sleep-apnea</option>
  <option value="uti">uti</option>
  <option value="breast-cancer">breast-cancer</option>
  <option value="prostate-cancer">prostate-cancer</option>
  <option value="colorectal-cancer">colorectal-cancer</option>
  <option value="osteoarthritis">osteoarthritis</option>
  <option value="substance-use-disorder">substance-use-disorder</option>
  <option value="chronic-pain">chronic-pain</option>
</select>
<button class="graph-btn" onclick="insertGraph(document.getElementById('graph-select').value)" style="width:100%">Insert at cursor</button>
      </div>
      <h3 style="margin-top:1rem">Examples</h3>
      <div class="example" onclick="setQuery(Q1)">
        <strong>List datasets</strong>
        <span>HealthDCAT-AP catalogue</span>
      </div>
      <div class="example" onclick="setQuery(Q2)">
        <strong>Dataset policies</strong>
        <span>ODRL permissions</span>
      </div>
      <div class="example" onclick="setQuery(Q3)">
        <strong>Patient count</strong>
        <span>By gender per cohort</span>
      </div>
      <div class="example" onclick="setQuery(Q4)">
        <strong>Top medications</strong>
        <span>Diabetes cohort</span>
      </div>
      <div class="example" onclick="setQuery(Q5)">
        <strong>HbA1c values</strong>
        <span>Recent observations</span>
      </div>
      <div class="example" onclick="setQuery(Q6)">
        <strong>Triple counts</strong>
        <span>All named graphs</span>
      </div>
    </div>
    <div class="editor-area">
      <textarea id="query" spellcheck="false">SELECT ?dataset ?title ?population WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <https://healthdcat-ap.github.io/healthdcat-ap/release/5/populationSize> ?population .
  }
}</textarea>
      <div class="toolbar">
        <button id="run" onclick="runQuery()">Run Query</button>
        <select id="format">
          <option value="application/sparql-results+json">JSON</option>
          <option value="application/sparql-results+xml">XML</option>
          <option value="text/csv">CSV</option>
        </select>
        <span id="status"></span>
      </div>
      <div id="results"></div>
    </div>
  </div>
</main>
<script>
const Q1 = `SELECT ?dataset ?title ?population ?license WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset a <http://www.w3.org/ns/dcat#Dataset> ;
             <http://purl.org/dc/terms/title> ?title ;
             <https://healthdcat-ap.github.io/healthdcat-ap/release/5/populationSize> ?population .
    OPTIONAL { ?dataset <http://purl.org/dc/terms/license> ?license . }
  }
}`;

const Q2 = `SELECT ?dataset ?action ?purpose WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/catalogue> {
    ?dataset <http://www.w3.org/ns/odrl/2/hasPolicy> ?policy .
    ?policy <http://www.w3.org/ns/odrl/2/permission> ?perm .
    ?perm <http://www.w3.org/ns/odrl/2/action> ?action .
    OPTIONAL {
      ?perm <http://www.w3.org/ns/odrl/2/constraint> ?c .
      ?c <http://www.w3.org/ns/odrl/2/rightOperand> ?purpose .
    }
  }
}`;

const Q3 = `SELECT ?gender (COUNT(DISTINCT ?patient) AS ?count) WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/diabetes> {
    ?patient a <http://hl7.org/fhir/Patient> ;
             <http://hl7.org/fhir/gender> ?gender .
  }
} GROUP BY ?gender`;

const Q4 = `SELECT ?display (COUNT(DISTINCT ?patient) AS ?patients) WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/diabetes> {
    ?med a <http://hl7.org/fhir/MedicationRequest> ;
         <http://hl7.org/fhir/medicationCode> ?coding ;
         <http://hl7.org/fhir/subject> ?patient .
    ?coding <http://hl7.org/fhir/display> ?display .
  }
} GROUP BY ?display ORDER BY DESC(?patients) LIMIT 10`;

const Q5 = `SELECT ?patient ?value ?unit ?date WHERE {
  GRAPH <https://ehds-prototype.example.org/graph/diabetes> {
    ?obs a <http://hl7.org/fhir/Observation> ;
         <http://hl7.org/fhir/code> ?coding ;
         <http://hl7.org/fhir/subject> ?patient ;
         <http://hl7.org/fhir/valueQuantity> ?vq ;
         <http://hl7.org/fhir/effectiveDateTime> ?date .
    ?coding <http://hl7.org/fhir/code> "4548-4" .
    ?vq <http://hl7.org/fhir/value> ?value ;
        <http://hl7.org/fhir/unit> ?unit .
  }
} ORDER BY DESC(?date) LIMIT 10`;

const Q6 = `SELECT ?g (COUNT(*) AS ?triples) WHERE {
  GRAPH ?g { ?s ?p ?o }
} GROUP BY ?g ORDER BY DESC(?triples)`;

function setQuery(q) {
  document.getElementById('query').value = q;
}

function insertGraph(name) {
  const uri = `https://ehds-prototype.example.org/graph/${name}`;
  const ta = document.getElementById('query');
  const pos = ta.selectionStart;
  const val = ta.value;
  ta.value = val.slice(0, pos) + `<${uri}>` + val.slice(pos);
}

async function runQuery() {
  const query = document.getElementById('query').value.trim();
  const format = document.getElementById('format').value;
  const btn = document.getElementById('run');
  const status = document.getElementById('status');
  const results = document.getElementById('results');

  if (!query) return;
  btn.disabled = true;
  status.textContent = 'Running...';
  results.innerHTML = '';

  const t0 = Date.now();
  try {
    const resp = await fetch('/sparql?query=' + encodeURIComponent(query), {
      headers: { 'Accept': 'application/sparql-results+json' }
    });
    const elapsed = ((Date.now() - t0) / 1000).toFixed(2);

    if (!resp.ok) {
      const text = await resp.text();
      results.innerHTML = `<div class="error"><strong>Error ${resp.status}:</strong><br>${text}</div>`;
      status.textContent = '';
      return;
    }

    const data = await resp.json();
    const vars = data.head.vars;
    const bindings = data.results.bindings;

    status.textContent = `${bindings.length} results in ${elapsed}s`;

    if (bindings.length === 0) {
      results.innerHTML = '<p style="color:#64748b;font-size:0.9rem">No results.</p>';
      return;
    }

    let html = `<p class="count">${bindings.length} row${bindings.length !== 1 ? 's' : ''}</p>`;
    html += '<table><thead><tr>';
    vars.forEach(v => { html += `<th>${v}</th>`; });
    html += '</tr></thead><tbody>';

    bindings.forEach(row => {
      html += '<tr>';
      vars.forEach(v => {
        const cell = row[v];
        if (!cell) { html += '<td></td>'; return; }
        if (cell.type === 'uri') {
          const short = cell.value.replace('https://ehds-prototype.example.org/', 'ehds:')
                                  .replace('http://hl7.org/fhir/', 'fhir:')
                                  .replace('http://www.w3.org/ns/dcat#', 'dcat:')
                                  .replace('http://purl.org/dc/terms/', 'dct:')
                                  .replace('http://snomed.info/id/', 'snomed:')
                                  .replace('http://www.w3.org/ns/odrl/2/', 'odrl:');
          html += `<td><span class="uri" title="${cell.value}">${short}</span></td>`;
        } else {
          const val = cell.value.length > 80 ? cell.value.slice(0, 80) + '…' : cell.value;
          html += `<td><span class="literal">${val}</span></td>`;
        }
      });
      html += '</tr>';
    });
    html += '</tbody></table>';
    results.innerHTML = html;

  } catch(e) {
    results.innerHTML = `<div class="error">${e.message}</div>`;
    status.textContent = '';
  } finally {
    btn.disabled = false;
  }
}
</script>
</body>
</html>"""
## Changes to mcp/server.py
## Two additions: a SUPPLEMENTS_HTML page and a /supplements route.
## Everything else in server.py is unchanged.

# ─────────────────────────────────────────────────────────────
# 1.  Add this constant near SPARQL_HTML / LANDING_HTML
# ─────────────────────────────────────────────────────────────

SUPPLEMENTS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Supplements — EHDS Portal</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #f8fafc; color: #1e293b; }
  header { background: #0f172a; color: white; padding: 1rem 1.5rem;
           display: flex; align-items: center; gap: 1rem; }
  header a { color: #94a3b8; text-decoration: none; font-size: 0.9rem; }
  header h1 { font-size: 1.1rem; font-weight: 600; }
  main { max-width: 860px; margin: 2rem auto; padding: 0 1.5rem; }
  .intro { font-size: 0.9rem; color: #64748b; margin-bottom: 1.5rem; }
  .file-list { background: white; border: 1px solid #e2e8f0; border-radius: 10px;
               overflow: hidden; }
  .file-row { display: flex; align-items: center; gap: 1rem;
              padding: 0.85rem 1.2rem; border-bottom: 1px solid #f1f5f9; }
  .file-row:last-child { border-bottom: none; }
  .file-row:hover { background: #f8fafc; }
  .icon { font-size: 1.3rem; flex-shrink: 0; width: 2rem; text-align: center; }
  .meta { flex: 1; min-width: 0; }
  .meta .name { font-weight: 600; font-size: 0.92rem; color: #0f172a; }
  .meta .desc { font-size: 0.82rem; color: #64748b; margin-top: 0.15rem;
                white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .meta .path { font-size: 0.75rem; color: #94a3b8; font-family: monospace;
                margin-top: 0.1rem; }
  .size  { font-size: 0.8rem; color: #94a3b8; flex-shrink: 0; width: 4.5rem;
           text-align: right; }
  .dl { flex-shrink: 0; }
  .dl a { display: inline-block; background: #0f172a; color: white;
          padding: 0.35rem 0.85rem; border-radius: 6px; font-size: 0.82rem;
          text-decoration: none; }
  .dl a:hover { background: #1e293b; }
  .section-label { font-size: 0.75rem; font-weight: 700; color: #94a3b8;
                   text-transform: uppercase; letter-spacing: 0.06em;
                   padding: 0.5rem 1.2rem 0.3rem;
                   background: #f8fafc; border-bottom: 1px solid #f1f5f9; }
</style>
</head>
<body>
<header>
  <a href="/">← EHDS Portal</a>
  <h1>Supplements</h1>
</header>
<main>
  <p class="intro">
    Supplementary materials for the ISWC 2025 Resource Track paper.
    All files are part of the
    <a href="https://github.com/manabcodes/H-Mantis" style="color:#0369a1">ehds-linked-data-portal</a>
    repository and released under GNU GPL v3.
  </p>

  <div class="file-list">

    <div class="section-label">Documentation</div>

    <div class="file-row">
      <div class="icon">📄</div>
      <div class="meta">
        <div class="name">Dataset Description</div>
        <div class="desc">30 clinical cohorts, ODRL policies, HealthDCAT-AP catalogue schema, named graph structure, and infrastructure overview</div>
        <div class="path">dataset_description.pdf</div>
      </div>
      <div class="size">—</div>
      <div class="dl"><a href="/supplements/dataset_description.pdf">Download</a></div>
    </div>

    <div class="file-row">
      <div class="icon">📄</div>
      <div class="meta">
        <div class="name">Annotation Guide</div>
        <div class="desc">Atomic fact extraction protocol, completeness and hallucination scoring rules, and five worked examples with highlighted responses</div>
        <div class="path">annotation_guide.pdf</div>
      </div>
      <div class="size">—</div>
      <div class="dl"><a href="/supplements/annotation_guide.pdf">Download</a></div>
    </div>

    <div class="section-label">Evaluation harness</div>

    <div class="file-row">
      <div class="icon">🐍</div>
      <div class="meta">
        <div class="name">evaluation_50_queries.py</div>
        <div class="desc">Runs all 50 benchmark queries under baseline, RAG, and MCP conditions; writes per-query JSON results</div>
        <div class="path">eval/evaluation_50_queries.py</div>
      </div>
      <div class="size">—</div>
      <div class="dl"><a href="/supplements/evaluation_50_queries.py">Download</a></div>
    </div>

    <div class="file-row">
      <div class="icon">🐍</div>
      <div class="meta">
        <div class="name">benchmark.py</div>
        <div class="desc">50 benchmark queries with embedded SPARQL ground-truth derivations; authoritative source for all ground truth values</div>
        <div class="path">eval/benchmark.py</div>
      </div>
      <div class="size">—</div>
      <div class="dl"><a href="/supplements/benchmark.py">Download</a></div>
    </div>

    <div class="file-row">
      <div class="icon">📊</div>
      <div class="meta">
        <div class="name">benchmark.csv</div>
        <div class="desc">Flat CSV version of the benchmark ground truth, one row per query</div>
        <div class="path">eval/benchmark.csv</div>
      </div>
      <div class="size">—</div>
      <div class="dl"><a href="/supplements/benchmark.csv">Download</a></div>
    </div>

    <div class="section-label">Data pipeline</div>

    <div class="file-row">
      <div class="icon">🐍</div>
      <div class="meta">
        <div class="name">fhir_to_rdf.py</div>
        <div class="desc">Converts Synthea FHIR R4 JSON bundles to RDF Turtle, preserving Patient, Condition, Observation, MedicationRequest, and Encounter resources</div>
        <div class="path">fhir_to_rdf.py</div>
      </div>
      <div class="size">—</div>
      <div class="dl"><a href="/supplements/fhir_to_rdf.py">Download</a></div>
    </div>

    <div class="section-label">MCP connector</div>

    <div class="file-row">
      <div class="icon">🐍</div>
      <div class="meta">
        <div class="name">server.py</div>
        <div class="desc">MCP server exposing seven typed tools over SSE; compatible with Claude, mcphost, DeepSeek, and the Python MCP SDK</div>
        <div class="path">mcp/server.py</div>
      </div>
      <div class="size">—</div>
      <div class="dl"><a href="/supplements/server.py">Download</a></div>
    </div>

  </div>
</main>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────
# 2.  Inside main_sse(), add two things:
#
#     a) A handler that serves files from the repo root
#     b) Two new routes — one for the browser page, one for file downloads
#
#     Add these immediately after the existing route definitions,
#     before the Starlette() constructor call.
# ─────────────────────────────────────────────────────────────

# --- paste this block inside main_sse(), after the existing handlers ---

import pathlib

# Absolute path to the repository root (one level up from mcp/)
REPO_ROOT = pathlib.Path("/home/meem/ehds-linked-data-portal")


# Map URL filename → filesystem path relative to repo root.
# Add any future supplement files here.
SUPPLEMENT_FILES = {
    "dataset_description.pdf":   REPO_ROOT / "dataset_description.pdf",
    "annotation_guide.pdf":      REPO_ROOT / "annotation_guide.pdf",
    "evaluation_50_queries.py":  REPO_ROOT / "eval" / "evaluation_50_queries.py",
    "benchmark.py":              REPO_ROOT / "eval" / "benchmark.py",
    "benchmark.csv":             REPO_ROOT / "eval" / "benchmark.csv",
    "fhir_to_rdf.py":            REPO_ROOT / "fhir_to_rdf.py",
    "server.py":                 REPO_ROOT / "mcp" / "server.py",
}

MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".py":  "text/plain; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
}

# --- then add these two entries to the routes list inside Starlette() ---

#   Route("/supplements",            endpoint=supplements_browser),
#   Route("/supplements/{filename}", endpoint=supplements_file),


# ─────────────────────────────────────────────────────────────
# 3.  In LANDING_HTML, add this card after the visualization card
#     (copy into the .cards div, after the Knowledge Graph card)
# ─────────────────────────────────────────────────────────────



def main_sse(host: str = "0.0.0.0", port: int = 48243):
    import shutil
    import httpx
    import uvicorn
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import HTMLResponse, FileResponse, Response
    from visualization import VIZ_HTML


    sse = SseServerTransport("/messages/")

    async def supplements_browser(request):
        return HTMLResponse(SUPPLEMENTS_HTML)

    async def supplements_file(request):
        filename = request.path_params["filename"]
        filepath = SUPPLEMENT_FILES.get(filename)
        if filepath is None or not filepath.exists():
            return Response("Not found", status_code=404)
        suffix = filepath.suffix.lower()
        media_type = MEDIA_TYPES.get(suffix, "application/octet-stream")
        return FileResponse(str(filepath), media_type=media_type, filename=filename)

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

    async def landing(request):
        return HTMLResponse(LANDING_HTML)

    async def sparql_ui(request):
        return HTMLResponse(SPARQL_HTML)

    async def sparql_proxy(request):
        params = dict(request.query_params)
        accept = request.headers.get("Accept", "application/sparql-results+json")
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(
                "http://localhost:48242/ehds/sparql",
                params=params,
                headers={"Accept": accept},
            )
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type=resp.headers.get("content-type", "application/json"),
        )

    async def rag_download(request):
        zip_path = "/home/meem/ehds-mcp/rag/chroma_db.zip"
        db_path  = "/home/meem/ehds-mcp/rag/chroma_db"
        if not __import__("pathlib").Path(zip_path).exists():
            logger.info("Building chroma_db.zip for download...")
            shutil.make_archive(zip_path.replace(".zip", ""), "zip", db_path)
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename="ehds_chroma_db.zip",
        )

    starlette_app = Starlette(
        routes=[
            Route("/",        endpoint=landing),
            Route("/sparql",  endpoint=sparql_proxy),
            Route("/sparql/", endpoint=sparql_ui),
            Route("/connector",     endpoint=handle_sse),
            Route("/supplements",            endpoint=supplements_browser),   # ← add
            Route("/supplements/{filename}", endpoint=supplements_file),      # ← add
            Route("/rag",     endpoint=rag_download),
            Mount("/messages/", app=sse.handle_post_message),
            Route("/visualization",     endpoint=lambda r: HTMLResponse(VIZ_HTML)),
        ]
    )

    logger.info(f"Starting EHDS MCP server (SSE) on {host}:{port}")
    uvicorn.run(starlette_app, host=host, port=port)


if __name__ == "__main__":
    import sys
    import asyncio

    if "--sse" in sys.argv:
        port = 48243
        for arg in sys.argv:
            if arg.startswith("--port="):
                port = int(arg.split("=")[1])
        main_sse(port=port)
    else:
        asyncio.run(main_stdio())
