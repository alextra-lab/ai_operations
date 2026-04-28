"""
Retrieval metrics for corpus validation and test suite execution.

Implements standard IR metrics: Hit@K, MRR, nDCG@K, Zero Result Rate.
ADR-034: Use Case Validation & Test Harness
"""

from typing import Any
from uuid import UUID

import numpy as np

from shared.logging_utils.fastapi import get_logger

logger = get_logger(__name__)


def hit_at_k(results: list[dict[str, Any]], expected_ids: list[UUID], k: int) -> float:
    """
    Compute Hit@K metric.

    Returns 1.0 if at least one expected document appears in top-K results, 0.0 otherwise.

    Args:
        results: List of retrieval results with 'doc_id' field
        expected_ids: List of expected document UUIDs
        k: Number of top results to consider

    Returns:
        1.0 if hit, 0.0 if miss

    Example:
        >>> results = [{"doc_id": UUID("...")}, {"doc_id": UUID("...")}]
        >>> expected = [UUID("...")]
        >>> hit_at_k(results, expected, k=5)
        1.0
    """
    if not results or not expected_ids:
        return 0.0

    # Extract top-K doc IDs
    top_k_ids = []
    for result in results[:k]:
        doc_id = result.get("doc_id")
        if doc_id is not None:
            # Handle both UUID objects and strings
            if isinstance(doc_id, str):
                try:
                    doc_id = UUID(doc_id)
                except ValueError:
                    logger.warning(f"Invalid UUID string: {doc_id}")
                    continue
            top_k_ids.append(doc_id)

    # Check if any expected ID is in top-K
    expected_set = set(expected_ids)
    hits = len(set(top_k_ids) & expected_set)

    return 1.0 if hits > 0 else 0.0


def mean_reciprocal_rank(results: list[dict[str, Any]], expected_ids: list[UUID]) -> float:
    """
    Compute Mean Reciprocal Rank (MRR).

    Returns 1/(rank of first relevant document), where rank starts at 1.
    Returns 0.0 if no relevant document found.

    Args:
        results: List of retrieval results with 'doc_id' field
        expected_ids: List of expected document UUIDs

    Returns:
        MRR value between 0.0 and 1.0

    Example:
        >>> # If first relevant doc is at position 3 (0-indexed 2)
        >>> # MRR = 1/3 = 0.333
        >>> mrr = mean_reciprocal_rank(results, expected)
        0.333
    """
    if not results or not expected_ids:
        return 0.0

    expected_set = set(expected_ids)

    for i, result in enumerate(results):
        doc_id = result.get("doc_id")

        if doc_id is not None:
            # Handle both UUID objects and strings
            if isinstance(doc_id, str):
                try:
                    doc_id = UUID(doc_id)
                except ValueError:
                    logger.warning(f"Invalid UUID string: {doc_id}")
                    continue

            if doc_id in expected_set:
                # Rank starts at 1, not 0
                return 1.0 / (i + 1)

    return 0.0


def ndcg_at_k(
    results: list[dict[str, Any]],
    expected_ids: list[UUID],
    relevance_scores: dict[UUID, float],
    k: int,
) -> float:
    """
    Compute Normalized Discounted Cumulative Gain at K (nDCG@K).

    Measures ranking quality considering relevance scores and position discount.

    Args:
        results: List of retrieval results with 'doc_id' field
        expected_ids: List of expected document UUIDs
        relevance_scores: Map of UUID to relevance score (0.0-1.0)
        k: Number of top results to consider

    Returns:
        nDCG@K value between 0.0 and 1.0 (1.0 = perfect ranking)

    Example:
        >>> relevance = {uuid1: 1.0, uuid2: 0.8, uuid3: 0.3}
        >>> ndcg = ndcg_at_k(results, expected, relevance, k=5)
        0.95
    """
    if not results or not expected_ids or not relevance_scores:
        return 0.0

    # Compute DCG (Discounted Cumulative Gain)
    dcg = 0.0
    for i, result in enumerate(results[:k]):
        doc_id = result.get("doc_id")

        if doc_id is not None:
            # Handle both UUID objects and strings
            if isinstance(doc_id, str):
                try:
                    doc_id = UUID(doc_id)
                except ValueError:
                    logger.warning(f"Invalid UUID string: {doc_id}")
                    continue

            # Get relevance score (default 0.0 if not in expected set)
            relevance = relevance_scores.get(doc_id, 0.0)

            # DCG formula: sum(rel_i / log2(i+2))
            # +2 because: index i starts at 0, rank starts at 1, log2(1)=0 so we use i+2
            dcg += relevance / np.log2(i + 2)

    # Compute IDCG (Ideal DCG) - best possible ranking
    ideal_scores = sorted(relevance_scores.values(), reverse=True)
    idcg = sum(score / np.log2(i + 2) for i, score in enumerate(ideal_scores[:k]))

    # Normalize: nDCG = DCG / IDCG
    if idcg > 0:
        return float(dcg / idcg)
    return 0.0


def zero_result_rate(queries: list[str], results: list[list[dict[str, Any]]]) -> float:
    """
    Compute zero-result rate across multiple queries.

    Percentage of queries that returned zero results.

    Args:
        queries: List of query strings
        results: List of result lists (one per query)

    Returns:
        Zero-result rate between 0.0 and 1.0

    Example:
        >>> queries = ["query1", "query2", "query3"]
        >>> results = [[], [{"doc_id": ...}], []]  # 2 out of 3 have zero results
        >>> zero_result_rate(queries, results)
        0.667
    """
    if not queries or not results:
        return 0.0

    if len(queries) != len(results):
        logger.warning(f"Mismatch between queries ({len(queries)}) and results ({len(results)})")
        # Use minimum length to avoid index errors
        length = min(len(queries), len(results))
    else:
        length = len(queries)

    zero_count = sum(1 for result_list in results[:length] if len(result_list) == 0)

    return zero_count / length if length > 0 else 0.0


def compute_aggregate_metrics(
    query_results: list[dict[str, Any]],
) -> dict[str, float]:
    """
    Compute aggregate metrics across multiple query results.

    Args:
        query_results: List of dicts with per-query metrics:
            {
                "query": str,
                "hit_at_k": float,
                "mrr": float,
                "ndcg": float,
                "result_count": int
            }

    Returns:
        Dict with aggregate metrics:
            {
                "avg_hit_at_k": float,
                "avg_mrr": float,
                "avg_ndcg": float,
                "zero_result_rate": float,
                "total_queries": int
            }
    """
    if not query_results:
        return {
            "avg_hit_at_k": 0.0,
            "avg_mrr": 0.0,
            "avg_ndcg": 0.0,
            "zero_result_rate": 0.0,
            "total_queries": 0,
        }

    total_queries = len(query_results)

    # Compute averages
    avg_hit_at_k = sum(r.get("hit_at_k", 0.0) for r in query_results) / total_queries
    avg_mrr = sum(r.get("mrr", 0.0) for r in query_results) / total_queries
    avg_ndcg = sum(r.get("ndcg", 0.0) for r in query_results) / total_queries

    # Compute zero result rate
    zero_count = sum(1 for r in query_results if r.get("result_count", 0) == 0)
    zero_result_rate = zero_count / total_queries

    return {
        "avg_hit_at_k": round(avg_hit_at_k, 3),
        "avg_mrr": round(avg_mrr, 3),
        "avg_ndcg": round(avg_ndcg, 3),
        "zero_result_rate": round(zero_result_rate, 3),
        "total_queries": total_queries,
    }


def evaluate_retrieval_quality(
    query: str,
    results: list[dict[str, Any]],
    expected_ids: list[UUID],
    relevance_scores: dict[UUID, float],
    k: int = 5,
) -> dict[str, Any]:
    """
    Evaluate retrieval quality for a single query with all metrics.

    Convenience function that computes all metrics at once.

    Args:
        query: Query string
        results: Retrieval results with 'doc_id' field
        expected_ids: Expected document UUIDs
        relevance_scores: Map of UUID to relevance score
        k: Number of top results for Hit@K and nDCG@K

    Returns:
        Dict with all metrics:
            {
                "query": str,
                "hit_at_k": float,
                "mrr": float,
                "ndcg": float,
                "result_count": int,
                "k": int
            }
    """
    return {
        "query": query,
        "hit_at_k": hit_at_k(results, expected_ids, k),
        "mrr": mean_reciprocal_rank(results, expected_ids),
        "ndcg": ndcg_at_k(results, expected_ids, relevance_scores, k),
        "result_count": len(results),
        "k": k,
    }
