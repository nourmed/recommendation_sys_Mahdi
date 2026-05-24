"""
=============================================================
RAG Benchmark — Plant Advisor (RAGAS end-to-end evaluation)
=============================================================
Embedding model : all-mpnet-base-v2  (sentence-transformers, local)
LLM             : gpt-4o             (OpenAI)
Vector DB       : Qdrant             (Docker, localhost:6333)
Collection      : auto-discovered at runtime

Run:
    python benchmark/rag_benchmark.py

Outputs (all inside ./benchmark/):
    eval_questions.json  – generated Q&A pairs
    rag_results.json     – RAG pipeline answers
    ragas_scores.json    – per-metric RAGAS scores
    ragas_report.txt     – human-readable diagnostic report
=============================================================
"""

import os
import json
import random
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional

# ── third-party ──────────────────────────────────────────────
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from sentence_transformers import SentenceTransformer, CrossEncoder
from openai import OpenAI, APITimeoutError, APIConnectionError
import datasets
from ragas import evaluate
# RAGAS 0.2+ uses instantiated metric objects
try:
    from ragas.metrics import (
        Faithfulness,
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
    )
    RAGAS_NEW_API = True
except ImportError:
    # fallback for older ragas < 0.2
    from ragas.metrics import (
        faithfulness as Faithfulness,
        answer_relevancy as AnswerRelevancy,
        context_precision as ContextPrecision,
        context_recall as ContextRecall,
    )
    RAGAS_NEW_API = False

# RAGAS 0.2+ recommends llm_factory
try:
    from ragas.llms import llm_factory
    HAS_LLM_FACTORY = True
except ImportError:
    HAS_LLM_FACTORY = False

# ── logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("rag_benchmark")

# ── load .env ─────────────────────────────────────────────────
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# Always use localhost:6333 — Qdrant runs in Docker on this machine
# (the .env QDRANT_HOST points to the old remote server — ignored here)
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

# ── constants ─────────────────────────────────────────────────
EMBED_MODEL = "BAAI/bge-base-en-v1.5"          # Top-tier retrieval model
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2" # Cross-Encoder for precision
LLM_MODEL = "gpt-4o"                       # OpenAI judge + generator
FETCH_K = 15                               # Increase recall by fetching more
FINAL_K = 5                                # Rerank down to top 5 for precision
NUM_CHUNKS = 20                            # chunks to sample for dataset
QUESTIONS_PER_CHUNK = 2                        # Q&A pairs per chunk
BENCHMARK_DIR = Path(__file__).resolve().parent
TIMEOUT_SECS = 60                           # per OpenAI call

# ── output paths ──────────────────────────────────────────────
BENCHMARK_DIR.mkdir(exist_ok=True)
EVAL_QUESTIONS_PATH = BENCHMARK_DIR / "eval_questions.json"
RAG_RESULTS_PATH = BENCHMARK_DIR / "rag_results.json"
RAGAS_SCORES_PATH = BENCHMARK_DIR / "ragas_scores.json"
RAGAS_REPORT_PATH = BENCHMARK_DIR / "ragas_report.txt"


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def get_qdrant_client() -> QdrantClient:
    """Connect to local Qdrant Docker instance."""
    log.info(f"Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT} …")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=30)
    # quick health check
    collections = client.get_collections().collections
    log.info(f"Qdrant OK — found {len(collections)} collection(s)")
    return client, collections


def discover_collection(collections) -> str:
    """Return the first available collection name."""
    if not collections:
        raise RuntimeError("No collections found in Qdrant. Make sure data is loaded.")
    name = collections[0].name
    log.info(f"Using collection: '{name}'")
    return name


def load_embedding_model() -> SentenceTransformer:
    """Load all-mpnet-base-v2 locally (downloads once, cached by HuggingFace)."""
    log.info(f"Loading embedding model: {EMBED_MODEL} …")
    model = SentenceTransformer(EMBED_MODEL)
    log.info("Embedding model ready.")
    return model


def embed_text(model: SentenceTransformer, text: str) -> List[float]:
    """Embed a single text string → list[float]."""
    return model.encode(text, normalize_embeddings=True).tolist()


def call_openai(client: OpenAI, messages: List[Dict], max_tokens: int = 512) -> str:
    """
    Wrapper around OpenAI chat completion with retry on timeout/connection errors.
    Returns the assistant reply as a string.
    """
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.2,
                timeout=TIMEOUT_SECS,
            )
            return response.choices[0].message.content.strip()
        except (APITimeoutError, APIConnectionError) as e:
            wait = 10 * (attempt + 1)
            log.warning(f"OpenAI error (attempt {attempt+1}/3): {e} — retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError("OpenAI API failed after 3 retries.")


# ══════════════════════════════════════════════════════════════
# STEP 1 — Generate Evaluation Dataset
# ══════════════════════════════════════════════════════════════

def step1_generate_dataset(
    qdrant_client: QdrantClient,
    collection_name: str,
    openai_client: OpenAI,
) -> List[Dict]:
    """
    Sample ~NUM_CHUNKS random points from Qdrant, then ask GPT-4o to
    generate QUESTIONS_PER_CHUNK realistic questions + ground-truth answers
    per chunk. Returns a list of {question, ground_truth} dicts.
    """
    log.info("=" * 60)
    log.info("STEP 1 — Generating evaluation dataset …")
    log.info("=" * 60)

    # ── fetch collection info to know total point count ──────
    info = qdrant_client.get_collection(collection_name)
    total_points = info.points_count
    log.info(f"Collection '{collection_name}' has {total_points} points.")

    if total_points == 0:
        raise RuntimeError("Collection is empty — nothing to benchmark.")

    # ── scroll random sample of chunks ───────────────────────
    # Qdrant scroll with random offset gives a diverse sample
    sample_size = min(NUM_CHUNKS, total_points)
    log.info(f"Sampling {sample_size} random chunks …")

    all_points, _ = qdrant_client.scroll(
        collection_name=collection_name,
        limit=total_points,          # fetch all IDs first
        with_payload=True,
        with_vectors=False,
    )

    # randomly pick a subset
    sampled = random.sample(all_points, min(sample_size, len(all_points)))

    qa_pairs: List[Dict] = []

    for idx, point in enumerate(sampled):
        # ── extract chunk text from payload ──────────────────
        payload = point.payload or {}
        # try common field names used in agricultural RAG pipelines
        chunk_text = (
            payload.get("text")
            or payload.get("content")
            or payload.get("chunk")
            or payload.get("page_content")
            or ""
        )
        if not chunk_text or len(chunk_text) < 50:
            log.warning(f"Chunk {idx} has no usable text — skipping.")
            continue

        # truncate very long chunks to avoid excessive token usage
        chunk_text = chunk_text[:2000]

        log.info(f"Generating Q&A for chunk {idx+1}/{len(sampled)} …")

        # ── ask GPT-4o to produce Q&A pairs ──────────────────
        system_prompt = (
            "You are an agricultural knowledge expert. "
            "Given a text chunk, generate exactly "
            f"{QUESTIONS_PER_CHUNK} distinct, realistic questions that a farmer or "
            "agronomist might ask, and provide a concise ground-truth answer for "
            "each question strictly based on the chunk. "
            "Return ONLY a JSON array, no prose:\n"
            '[\n  {"question": "...", "ground_truth": "..."},\n  ...\n]'
        )
        user_prompt = f"CHUNK:\n{chunk_text}"

        try:
            raw = call_openai(
                openai_client,
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens=800,
            )
            # parse the JSON array
            pairs = json.loads(raw)
            for pair in pairs:
                if "question" in pair and "ground_truth" in pair:
                    qa_pairs.append({
                        "question":     pair["question"],
                        "ground_truth": pair["ground_truth"],
                    })
        except json.JSONDecodeError as e:
            log.warning(f"JSON parse error for chunk {idx}: {e} — skipping chunk.")
        except Exception as e:
            log.warning(f"Error generating Q&A for chunk {idx}: {e} — skipping.")

    log.info(f"Generated {len(qa_pairs)} Q&A pairs total.")

    # ── save to file ──────────────────────────────────────────
    with open(EVAL_QUESTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(qa_pairs, f, indent=2, ensure_ascii=False)
    log.info(f"Saved → {EVAL_QUESTIONS_PATH}")

    return qa_pairs


# ══════════════════════════════════════════════════════════════
# STEP 2 — Run the RAG Pipeline
# ══════════════════════════════════════════════════════════════

def step2_run_rag(
    qa_pairs: List[Dict],
    qdrant_client: QdrantClient,
    collection_name: str,
    embed_model: SentenceTransformer,
    openai_client: OpenAI,
) -> List[Dict]:
    """
    For each question:
      1. Embed with all-mpnet-base-v2
      2. Retrieve FETCH_K chunks from Qdrant
      3. Rerank using CrossEncoder to get top FINAL_K chunks
      4. Send question + contexts to GPT-4o
      5. Collect {question, answer, contexts, ground_truth}
    """
    log.info("=" * 60)
    log.info("STEP 2 — Running Improved RAG pipeline …")
    log.info("=" * 60)

    # ── Load Reranker Model ──────────────────────────────────
    log.info(f"Loading reranker model: {RERANKER_MODEL} …")
    reranker = CrossEncoder(RERANKER_MODEL)
    
    rag_results: List[Dict] = []

    for i, qa in enumerate(qa_pairs):
        question     = qa["question"]
        ground_truth = qa["ground_truth"]

        log.info(f"[{i+1}/{len(qa_pairs)}] Q: {question[:80]} …")

        # ── embed question ────────────────────────────────────
        try:
            query_vector = embed_text(embed_model, question)
        except Exception as e:
            log.warning(f"Embedding failed for question {i}: {e} — skipping.")
            continue

        # ── retrieve FETCH_K from Qdrant ──────────────────────
        try:
            hits = qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=FETCH_K,
                with_payload=True,
            )
        except (UnexpectedResponse, Exception) as e:
            log.warning(f"Qdrant search failed for question {i}: {e} — skipping.")
            continue

        # ── extract context strings ───────────────────────────
        fetched_contexts: List[str] = []
        for hit in hits:
            payload = hit.payload or {}
            text = (
                payload.get("text")
                or payload.get("content")
                or payload.get("chunk")
                or payload.get("page_content")
                or ""
            )
            if text:
                fetched_contexts.append(text[:1500])

        if not fetched_contexts:
            log.warning(f"No contexts retrieved for question {i} — skipping.")
            continue

        # ── rerank using CrossEncoder ─────────────────────────
        pairs = [[question, ctx] for ctx in fetched_contexts]
        scores = reranker.predict(pairs)
        
        # Sort contexts by score descending and take top FINAL_K
        ranked_pairs = sorted(zip(scores, fetched_contexts), key=lambda x: x[0], reverse=True)
        contexts = [ctx for score, ctx in ranked_pairs[:FINAL_K]]

        # ── build context block for GPT ───────────────────────
        context_block = "\n\n---\n\n".join(
            f"[Context {j+1}]: {ctx}" for j, ctx in enumerate(contexts)
        )

        # ── call GPT-4o with improved prompt ──────────────────
        system_prompt = (
            "You are a highly capable agricultural expert assistant. "
            "Your task is to answer the user's question clearly, concisely, and "
            "STRICTLY using only the provided context. "
            "If the context does not contain enough information to answer the question, "
            "explicitly state 'I cannot answer this based on the provided context.' "
            "Do NOT hallucinate or bring in outside knowledge."
        )
        user_prompt = (
            f"Here is the context retrieved from the database:\n{context_block}\n\n"
            f"Based ONLY on the context above, answer the following question:\n"
            f"QUESTION: {question}\n\n"
            "ANSWER:"
        )

        try:
            answer = call_openai(
                openai_client,
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens=512,
            )
        except Exception as e:
            log.warning(f"GPT answer failed for question {i}: {e} — skipping.")
            continue

        rag_results.append({
            "question":     question,
            "answer":       answer,
            "contexts":     contexts,    # list[str] required by RAGAS
            "ground_truth": ground_truth,
        })

    log.info(f"RAG pipeline complete — {len(rag_results)} results collected.")

    # ── save ──────────────────────────────────────────────────
    with open(RAG_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(rag_results, f, indent=2, ensure_ascii=False)
    log.info(f"Saved → {RAG_RESULTS_PATH}")

    return rag_results


# ══════════════════════════════════════════════════════════════
# STEP 3 — Evaluate with RAGAS
# ══════════════════════════════════════════════════════════════

def step3_ragas_evaluate(rag_results: List[Dict]) -> Dict[str, float]:
    """
    Convert rag_results to a HuggingFace Dataset, then run RAGAS evaluate()
    with gpt-4o as the judge LLM.
    Returns a dict of {metric_name: score}.
    """
    log.info("=" * 60)
    log.info("STEP 3 — Running RAGAS evaluation …")
    log.info("=" * 60)

    if not rag_results:
        raise RuntimeError("No RAG results to evaluate.")

    # ── build HuggingFace Dataset ─────────────────────────────
    dataset_dict = {
        "question":     [r["question"]     for r in rag_results],
        "answer":       [r["answer"]       for r in rag_results],
        "contexts":     [r["contexts"]     for r in rag_results],
        "ground_truth": [r["ground_truth"] for r in rag_results],
    }
    hf_dataset = datasets.Dataset.from_dict(dataset_dict)
    log.info(f"HuggingFace Dataset created: {len(hf_dataset)} rows.")

    # ── configure RAGAS judge LLM ─────────────────────────────
    # RAGAS 0.2+ recommends llm_factory; fallback to LangChain wrapper
    if HAS_LLM_FACTORY:
        from openai import OpenAI as _OAI
        ragas_llm = llm_factory(LLM_MODEL, client=_OAI(api_key=OPENAI_API_KEY))
    else:
        from langchain_openai import ChatOpenAI
        try:
            from ragas.llms import LangchainLLMWrapper
        except ImportError:
            from ragas.llms.base import LangchainLLMWrapper
        ragas_llm = LangchainLLMWrapper(
            ChatOpenAI(model=LLM_MODEL, api_key=OPENAI_API_KEY, temperature=0)
        )

    # ── instantiate metric objects (RAGAS 0.2+ API) ───────────
    metrics = [
        Faithfulness(),
        AnswerRelevancy(),
        ContextPrecision(),
        ContextRecall(),
    ]

    # inject the judge LLM into each metric
    for metric in metrics:
        metric.llm = ragas_llm

    log.info("Running RAGAS evaluate() — this may take several minutes …")
    result = evaluate(hf_dataset, metrics=metrics)

    # ── extract scores ─────────────────────────────────────────
    # RAGAS 0.2+ returns an EvaluationResult. 
    # The safest way to get aggregated scores is either mapping the result directly
    # if it supports dict casting, or falling back to string representations.
    
    scores: Dict[str, float] = {}
    try:
        # Try casting to dict (supported in some versions)
        if hasattr(result, "to_pandas"):
            df = result.to_pandas()
            # The columns are the metric names, we want the mean of numeric columns
            numeric_cols = df.select_dtypes(include='number').columns
            result_dict = df[numeric_cols].mean().to_dict()
        else:
            result_dict = dict(result)
            
        log.info(f"Extracted result dict: {result_dict}")
    except Exception as e:
        log.warning(f"Failed to cast result to dict: {e}. Falling back to string parsing.")
        # If dict casting fails, fallback to printing/parsing or default 0s
        result_dict = {}
        for metric in metrics:
            result_dict[metric.name] = 0.0 # fallback

    # canonical key names for the report
    KEY_MAP = {
        "faithfulness":      ["faithfulness", "Faithfulness"],
        "answer_relevancy":  ["answer_relevancy", "answer_relevance", "AnswerRelevancy"],
        "context_precision": ["context_precision", "ContextPrecision"],
        "context_recall":    ["context_recall", "ContextRecall"],
    }
    
    # We normalise the extracted dict keys for matching
    result_lower = {str(k).lower(): v for k, v in result_dict.items()}
    
    for canonical, aliases in KEY_MAP.items():
        val = None
        for alias in aliases:
            val = result_lower.get(alias.lower())
            if val is not None:
                break
        scores[canonical] = round(float(val), 4) if val is not None else None

    log.info(f"RAGAS scores: {scores}")

    # ── save ──────────────────────────────────────────────────
    with open(RAGAS_SCORES_PATH, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2)
    log.info(f"Saved → {RAGAS_SCORES_PATH}")

    return scores


# ══════════════════════════════════════════════════════════════
# STEP 4 — Generate Diagnostic Report
# ══════════════════════════════════════════════════════════════

def step4_generate_report(scores: Dict[str, float]):
    """
    Print and save a human-readable report with per-metric diagnostics.
    Flags any metric below 0.7 with an actionable recommendation.
    """
    log.info("=" * 60)
    log.info("STEP 4 — Generating diagnostic report …")
    log.info("=" * 60)

    THRESHOLD = 0.7

    # metric display name → stored key
    METRIC_META = {
        "faithfulness":       "faithfulness",
        "answer_relevancy":   "answer_relevancy",
        "context_precision":  "context_precision",
        "context_recall":     "context_recall",
    }

    DIAGNOSTICS = {
        "faithfulness":      "⚠️  GPT is hallucinating — tighten the system prompt.",
        "answer_relevancy":  "⚠️  Answers are off-topic — refine prompt structure.",
        "context_precision": "⚠️  Noisy retrieval — tune the cross-encoder reranker.",
        "context_recall":    "⚠️  Qdrant is missing chunks — increase fetch_k or re-chunk.",
    }

    lines = []
    lines.append("=" * 60)
    lines.append("   Plant Advisor RAG — RAGAS Benchmark Report")
    lines.append("=" * 60)
    lines.append(f"   Model    : {LLM_MODEL}")
    lines.append(f"   Embedder : {EMBED_MODEL}")
    lines.append(f"   Reranker : {RERANKER_MODEL}")
    lines.append(f"   fetch_k  : {FETCH_K}")
    lines.append(f"   final_k  : {FINAL_K}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"{'Metric':<25} {'Score':>8}   {'Status'}")
    lines.append("-" * 60)

    issues = []
    for display_name, key in METRIC_META.items():
        score = scores.get(key)
        if score is None:
            status = "N/A"
            lines.append(f"{display_name:<25} {'N/A':>8}   {status}")
            continue
        status = "✅ PASS" if score >= THRESHOLD else "❌ FAIL"
        lines.append(f"{display_name:<25} {score:>8.4f}   {status}")
        if score < THRESHOLD:
            issues.append((display_name, score, DIAGNOSTICS.get(key, "")))

    lines.append("-" * 60)
    lines.append("")

    if not issues:
        lines.append("🎉 All metrics passed the 0.7 threshold — RAG pipeline is healthy!")
    else:
        lines.append("DIAGNOSTICS (metrics below 0.70):")
        lines.append("")
        for name, score, msg in issues:
            lines.append(f"  [{name}] score={score:.4f}")
            lines.append(f"  → {msg}")
            lines.append("")

    lines.append("=" * 60)
    report_text = "\n".join(lines)

    # print to console
    print("\n" + report_text + "\n")

    # save to file
    with open(RAGAS_REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_text)
    log.info(f"Saved → {RAGAS_REPORT_PATH}")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    if not OPENAI_API_KEY:
        raise EnvironmentError("OPENAI_API_KEY not found. Check your .env file.")

    # ── initialise shared clients ─────────────────────────────
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    qdrant_client, collections = get_qdrant_client()
    collection_name = discover_collection(collections)
    embed_model = load_embedding_model()

    # ── STEP 1: dataset generation ────────────────────────────
    if EVAL_QUESTIONS_PATH.exists():
        log.info(f"Found existing {EVAL_QUESTIONS_PATH} — loading (delete to regenerate).")
        with open(EVAL_QUESTIONS_PATH, encoding="utf-8") as f:
            qa_pairs = json.load(f)
    else:
        qa_pairs = step1_generate_dataset(qdrant_client, collection_name, openai_client)

    # ── STEP 2: RAG pipeline run ──────────────────────────────
    if RAG_RESULTS_PATH.exists():
        log.info(f"Found existing {RAG_RESULTS_PATH} — loading (delete to re-run).")
        with open(RAG_RESULTS_PATH, encoding="utf-8") as f:
            rag_results = json.load(f)
    else:
        rag_results = step2_run_rag(
            qa_pairs, qdrant_client, collection_name, embed_model, openai_client
        )

    # ── STEP 3: RAGAS evaluation ──────────────────────────────
    if RAGAS_SCORES_PATH.exists():
        log.info(f"Found existing {RAGAS_SCORES_PATH} — loading (delete to re-evaluate).")
        with open(RAGAS_SCORES_PATH, encoding="utf-8") as f:
            scores = json.load(f)
    else:
        scores = step3_ragas_evaluate(rag_results)

    # ── STEP 4: report ────────────────────────────────────────
    step4_generate_report(scores)


if __name__ == "__main__":
    main()
