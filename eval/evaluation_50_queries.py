"""
run_eval.py — Step 2 of the EHDS-MCP evaluation harness.

Runs 50 queries × 3 conditions × 2 models and writes eval_results.json.

Conditions:
  baseline  — LLM answers from parametric memory only (no tools, no context)
  rag       — LLM answers with top-5 chunks from ChromaDB (sentence-transformers)
  mcp       — LLM answers via MCP tools against live Fuseki

Models:
  ollama    — llama3.2:latest via local Ollama API
  claude    — claude-sonnet-4-20250514 via Anthropic API

Output:
  eval/results/eval_results.json   — one entry per query, all 6 condition×model combos
  eval/results/eval_summary.csv    — per-query latency summary

Usage:
  python3 run_eval.py                              # all queries, all conditions, all models
  python3 run_eval.py --conditions baseline rag    # subset of conditions
  python3 run_eval.py --models claude              # Claude only
  python3 run_eval.py --query-ids D1 D2 C1         # specific queries

Resume: if eval_results.json already exists, completed entries are skipped.

Dependencies (should all be installed):
  pip install anthropic ollama chromadb sentence-transformers mcp --break-system-packages

Environment:
  ANTHROPIC_API_KEY must be set.

Architecture note:
  RAG queries Fuseki directly via SPARQLWrapper (no MCP server involvement).
  MCP condition goes through the MCP SSE server at localhost:48243.
  The two paths are fully independent.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import anthropic
import chromadb
import ollama as ollama_client
from sentence_transformers import SentenceTransformer
from mcp import ClientSession
from mcp.client.sse import sse_client

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MCP_SERVER_URL  = "http://localhost:48243/sse"
CHROMA_PATH     = "/home/meem/ehds-mcp/rag/chroma_db"
COLLECTION_NAME = "ehds_chunks"
EMBED_MODEL     = "all-MiniLM-L6-v2"
OLLAMA_MODEL    = "llama3.2"
CLAUDE_MODEL    = "claude-sonnet-4-20250514"
RESULTS_DIR     = Path(__file__).parent / "results"
DEEPSEEK_MODEL = "deepseek-reasoner"  # or deepseek-chat for not using R1

RAG_PROMPT = """\
You are an assistant for the European Health Data Space (EHDS).
Answer the question based ONLY on the following context.
If the answer is not in the context, say "I don't have enough information."

Context:
{retrieved_chunks}

Question: {query}

Answer:"""

BASELINE_SYSTEM = (
    "You are an assistant for the European Health Data Space (EHDS). "
    "Answer the user's question as accurately as you can."
)

MCP_SYSTEM = (
    "You are an assistant for the European Health Data Space (EHDS). "
    "Use the available EHDS tools to answer the question accurately. "
    "Never construct, guess, or abbreviate URIs. "
    "There are 30 clinical cohort datasets in this data space. "
    "If unsure which dataset to use, first call ehds_list_datasets."
    "never guess or construct URIs manually. "
    "Use the exact URIs returned by ehds_list_datasets when calling other tools."
)

# ---------------------------------------------------------------------------
# Evaluation queries (50 total — knowledge base Section 5)
# ---------------------------------------------------------------------------

from benchmark import QUERIES  # adjust path as needed

# ---------------------------------------------------------------------------
# Lazy-loaded shared resources
# ---------------------------------------------------------------------------

_embed_model = None
_chroma_collection = None
_anthropic_client = None
_deepseek_client = None


def get_embed_model():
    global _embed_model
    if _embed_model is None:
        print(f"  [init] Loading embedding model {EMBED_MODEL}...")
        _embed_model = SentenceTransformer(EMBED_MODEL)
    return _embed_model


def get_chroma_collection():
    global _chroma_collection
    if _chroma_collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        _chroma_collection = client.get_collection(COLLECTION_NAME)
        print(f"  [init] ChromaDB loaded ({_chroma_collection.count()} docs)")
    return _chroma_collection


def get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        _anthropic_client = anthropic.Anthropic(api_key=key)
    return _anthropic_client

def get_deepseek():
    global _deepseek_client
    if _deepseek_client is None:
        import openai
        key = os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError("DEEPSEEK_API_KEY not set")
        _deepseek_client = openai.OpenAI(
            api_key=key,
            base_url="https://api.deepseek.com"
        )
    return _deepseek_client

# ---------------------------------------------------------------------------
# BASELINE
# ---------------------------------------------------------------------------

def run_baseline_ollama(query: str) -> dict:
    t0 = time.time()
    resp = ollama_client.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": query}],
    )
    return {
        "answer": resp["message"]["content"],
        "tools_called": [],
        "latency_seconds": round(time.time() - t0, 2),
    }


def run_baseline_claude(query: str) -> dict:
    t0 = time.time()
    resp = get_anthropic().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=BASELINE_SYSTEM,
        messages=[{"role": "user", "content": query}],
    )
    return {
        "answer": resp.content[0].text,
        "tools_called": [],
        "latency_seconds": round(time.time() - t0, 2),
    }

def run_baseline_deepseek(query: str) -> dict:
    t0 = time.time()
    resp = get_deepseek().chat.completions.create(
        model=DEEPSEEK_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": BASELINE_SYSTEM},
            {"role": "user", "content": query}
        ],
    )
    return {
        "answer": resp.choices[0].message.content,
        "tools_called": [],
        "latency_seconds": round(time.time() - t0, 2),
    }


def run_rag_deepseek(query: str) -> dict:
    chunks = retrieve_chunks(query)
    prompt = RAG_PROMPT.format(retrieved_chunks="\n\n".join(chunks), query=query)
    t0 = time.time()
    resp = get_deepseek().chat.completions.create(
        model=DEEPSEEK_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return {
        "answer": resp.choices[0].message.content,
        "chunks_retrieved": chunks,
        "latency_seconds": round(time.time() - t0, 2),
    }


async def _mcp_deepseek_async(query: str) -> dict:
    t0 = time.time()
    tools_called = []
    client = get_deepseek()

    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            mcp_tools = await session.list_tools()
            openai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema,
                    },
                }
                for t in mcp_tools.tools
            ]

            messages = [
                {"role": "system", "content": MCP_SYSTEM},
                {"role": "user", "content": query}
            ]

            for _ in range(5):
                resp = client.chat.completions.create(
                    model=DEEPSEEK_MODEL,
                    max_tokens=1024,
                    tools=openai_tools,
                    messages=messages,
                )
                msg = resp.choices[0].message
                messages.append(msg)

                if not msg.tool_calls:
                    break

                for tc in msg.tool_calls:
                    name = tc.function.name
                    args = json.loads(tc.function.arguments)
                    tools_called.append({"tool": name, "args": args})
                    result = await session.call_tool(name, args)
                    result_text = result.content[0].text if result.content else "No result"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_text,
                    })

            answer = msg.content or ""

    return {
        "answer": answer,
        "tools_called": tools_called,
        "latency_seconds": round(time.time() - t0, 2),
    }

def run_mcp_deepseek(query: str) -> dict:
    return asyncio.run(_mcp_deepseek_async(query))

# ---------------------------------------------------------------------------
# RAG
# ---------------------------------------------------------------------------

def retrieve_chunks(query: str, n: int = 5) -> list[str]:
    emb    = get_embed_model().encode([query]).tolist()
    result = get_chroma_collection().query(query_embeddings=emb, n_results=n)
    return result["documents"][0]


def run_rag_ollama(query: str) -> dict:
    chunks  = retrieve_chunks(query)
    prompt  = RAG_PROMPT.format(retrieved_chunks="\n\n".join(chunks), query=query)
    t0 = time.time()
    resp = ollama_client.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return {
        "answer": resp["message"]["content"],
        "chunks_retrieved": chunks,
        "latency_seconds": round(time.time() - t0, 2),
    }


def run_rag_claude(query: str) -> dict:
    chunks  = retrieve_chunks(query)
    prompt  = RAG_PROMPT.format(retrieved_chunks="\n\n".join(chunks), query=query)
    t0 = time.time()
    resp = get_anthropic().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return {
        "answer": resp.content[0].text,
        "chunks_retrieved": chunks,
        "latency_seconds": round(time.time() - t0, 2),
    }


# ---------------------------------------------------------------------------
# MCP — Ollama (async agentic loop)
# ---------------------------------------------------------------------------

async def _mcp_ollama_async(query: str) -> dict:
    t0 = time.time()
    tools_called = []

    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            mcp_tools = await session.list_tools()
            ollama_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema,
                    },
                }
                for t in mcp_tools.tools
            ]

            messages = [{"role": "user", "content": query}]

            for _ in range(5):  # max 5 agentic rounds
                resp = ollama_client.chat(
                    model=OLLAMA_MODEL,
                    messages=messages,
                    tools=ollama_tools,
                )
                msg = resp["message"]
                messages.append(msg)

                if not msg.get("tool_calls"):
                    break

                for tc in msg["tool_calls"]:
                    fn   = tc["function"]
                    name = fn["name"]
                    args = fn["arguments"]
                    if isinstance(args, str):
                        args = json.loads(args)

                    tools_called.append({"tool": name, "args": args})
                    result = await session.call_tool(name, args)
                    result_text = result.content[0].text if result.content else "No result"
                    messages.append({"role": "tool", "content": result_text})

            # Last assistant message without tool_calls is the final answer
            answer = next(
                (m.get("content", "") for m in reversed(messages)
                 if m.get("role") == "assistant" and not m.get("tool_calls")),
                ""
            )

    return {
        "answer": answer,
        "tools_called": tools_called,
        "latency_seconds": round(time.time() - t0, 2),
    }


def run_mcp_ollama(query: str) -> dict:
    return asyncio.run(_mcp_ollama_async(query))


# ---------------------------------------------------------------------------
# MCP — Claude (async agentic loop)
# ---------------------------------------------------------------------------

async def _mcp_claude_async(query: str) -> dict:
    t0 = time.time()
    tools_called = []
    client = get_anthropic()

    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            mcp_tools = await session.list_tools()
            anthropic_tools = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.inputSchema,
                }
                for t in mcp_tools.tools
            ]

            messages = [{"role": "user", "content": query}]
            resp = None

            for _ in range(5):  # max 5 agentic rounds
                resp = client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=1024,
                    system=MCP_SYSTEM,
                    tools=anthropic_tools,
                    messages=messages,
                )
                messages.append({"role": "assistant", "content": resp.content})

                if resp.stop_reason == "end_turn":
                    break

                if resp.stop_reason != "tool_use":
                    break

                tool_results = []
                for block in resp.content:
                    if block.type != "tool_use":
                        continue
                    tools_called.append({"tool": block.name, "args": block.input})
                    result = await session.call_tool(block.name, block.input)
                    result_text = result.content[0].text if result.content else "No result"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_text,
                    })

                messages.append({"role": "user", "content": tool_results})

            # Extract final text
            answer = ""
            if resp:
                for block in resp.content:
                    if hasattr(block, "text"):
                        answer += block.text

    return {
        "answer": answer,
        "tools_called": tools_called,
        "latency_seconds": round(time.time() - t0, 2),
    }


def run_mcp_claude(query: str) -> dict:
    return asyncio.run(_mcp_claude_async(query))


# ---------------------------------------------------------------------------
# Dispatch tables
# ---------------------------------------------------------------------------

RUNNERS = {
    ("baseline", "ollama"): run_baseline_ollama,
    ("baseline", "claude"): run_baseline_claude,
    ("rag",      "ollama"): run_rag_ollama,
    ("rag",      "claude"): run_rag_claude,
    ("mcp",      "ollama"): run_mcp_ollama,
    ("mcp",      "claude"): run_mcp_claude,
    ("baseline", "deepseek"): run_baseline_deepseek,
    ("rag",      "deepseek"): run_rag_deepseek,
    ("mcp",      "deepseek"): run_mcp_deepseek,
}

RESULT_KEY = {
    ("baseline", "ollama"): "baseline_ollama",
    ("baseline", "claude"): "baseline_claude",
    ("rag",      "ollama"): "rag_ollama",
    ("rag",      "claude"): "rag_claude",
    ("mcp",      "ollama"): "mcp_ollama",
    ("mcp",      "claude"): "mcp_claude",
    ("baseline", "deepseek"): "baseline_deepseek",
    ("rag",      "deepseek"): "rag_deepseek",
    ("mcp",      "deepseek"): "mcp_deepseek",
}
# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="EHDS-MCP evaluation harness")
    parser.add_argument("--conditions", nargs="+",
                        choices=["baseline", "rag", "mcp"],
                        default=["baseline", "rag", "mcp"])
    parser.add_argument("--models", nargs="+",
                    choices=["ollama", "claude", "deepseek"],
                    default=["ollama", "claude", "deepseek"])
    parser.add_argument("--query-ids", nargs="+",
                        help="Run only specific query IDs, e.g. D1 D2 C1")
    parser.add_argument("--output",
                        default=str(RESULTS_DIR / "eval_results.json"))
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    queries = QUERIES
    if args.query_ids:
        ids = set(args.query_ids)
        queries = [q for q in QUERIES if q["id"] in ids]
        if not queries:
            print(f"No queries matched: {args.query_ids}", file=sys.stderr)
            sys.exit(1)

    combos = [(c, m) for c in args.conditions for m in args.models]

    print(f"[run_eval] Queries    : {[q['id'] for q in queries]}")
    print(f"[run_eval] Conditions : {[RESULT_KEY[c] for c in combos]}")
    print(f"[run_eval] Output     : {args.output}")
    print()

    # Pre-load RAG resources once if needed
    if any(c == "rag" for c, _ in combos):
        get_embed_model()
        get_chroma_collection()

    # Load existing results for resume support
    output_path = Path(args.output)
    if output_path.exists():
        with open(output_path) as f:
            existing = {r["query_id"]: r for r in json.load(f)}
        print(f"[run_eval] Resuming — {len(existing)} queries already have results\n")
    else:
        existing = {}

    for q in queries:
        qid = q["id"]
        print(f"── {qid} ({q['category']}): {q['query'][:70]}")

        if qid not in existing:
            existing[qid] = {
                "query_id":    qid,
                "query":       q["query"],
                "category":    q["category"],
                "ground_truth": q["ground_truth"],
                "results":     {},
            }

        entry = existing[qid]

        for cond, model in combos:
            key = RESULT_KEY[(cond, model)]
            if key in entry["results"]:
                print(f"  {key}: already done, skipping")
                continue

            print(f"  {key}: running...", end="", flush=True)
            try:
                result = RUNNERS[(cond, model)](q["query"])
                print(f" {result['latency_seconds']}s")
            except Exception as e:
                print(f" ERROR: {e}")
                result = {
                    "answer": f"ERROR: {e}",
                    "tools_called": [],
                    "latency_seconds": 0.0,
                    "error": str(e),
                }

            entry["results"][key] = result

            # Write after every result so we can resume on crash
            with open(output_path, "w") as f:
                json.dump(list(existing.values()), f, indent=2, default=str)

        print()

    # CSV summary
    csv_path = RESULTS_DIR / "eval_summary.csv"
    keys = [RESULT_KEY[c] for c in combos]
    with open(csv_path, "w") as f:
        f.write(",".join(["query_id", "category"] + [f"{k}_latency" for k in keys]) + "\n")
        for entry in existing.values():
            row = [entry["query_id"], entry["category"]]
            for k in keys:
                row.append(str(entry["results"].get(k, {}).get("latency_seconds", "")))
            f.write(",".join(row) + "\n")

    print(f"[run_eval] Complete.")
    print(f"  Results : {output_path}")
    print(f"  Summary : {csv_path}")
    print()
    print("Next: manually annotate each result in eval_results.json:")
    print('  "completeness": 0.0-1.0  — fraction of ground_truth facts present in answer')
    print('  "hallucination": 0.0-1.0 — fraction of factual claims in answer NOT in RDF')
    print('  "tool_accuracy": 0 or 1  — MCP conditions only: correct tool(s) called?')


if __name__ == "__main__":
    main()
