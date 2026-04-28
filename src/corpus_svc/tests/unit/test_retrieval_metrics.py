"""
Unit tests for retrieval metrics functions.

Tests Hit@K, MRR, nDCG@K, and zero result rate calculations.
"""

from uuid import uuid4

from src.corpus_svc.app.services.retrieval_metrics import (
    compute_aggregate_metrics,
    evaluate_retrieval_quality,
    hit_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    zero_result_rate,
)


class TestHitAtK:
    """Tests for hit_at_k metric."""

    def test_hit_at_k_with_hit(self):
        """Test hit@k returns 1.0 when expected doc is in top-k."""
        expected_id = uuid4()
        results = [
            {"doc_id": uuid4()},
            {"doc_id": expected_id},
            {"doc_id": uuid4()},
        ]
        expected_ids = [expected_id]

        score = hit_at_k(results, expected_ids, k=5)
        assert score == 1.0

    def test_hit_at_k_no_hit(self):
        """Test hit@k returns 0.0 when expected doc is not in top-k."""
        results = [
            {"doc_id": uuid4()},
            {"doc_id": uuid4()},
        ]
        expected_ids = [uuid4()]  # Different ID

        score = hit_at_k(results, expected_ids, k=5)
        assert score == 0.0

    def test_hit_at_k_empty_results(self):
        """Test hit@k returns 0.0 for empty results."""
        score = hit_at_k([], [uuid4()], k=5)
        assert score == 0.0

    def test_hit_at_k_respects_k_limit(self):
        """Test hit@k only considers top-k results."""
        expected_id = uuid4()
        results = [
            {"doc_id": uuid4()},
            {"doc_id": uuid4()},
            {"doc_id": uuid4()},
            {"doc_id": expected_id},  # At position 4
        ]
        expected_ids = [expected_id]

        # Should miss with k=3
        score = hit_at_k(results, expected_ids, k=3)
        assert score == 0.0

        # Should hit with k=5
        score = hit_at_k(results, expected_ids, k=5)
        assert score == 1.0


class TestMeanReciprocalRank:
    """Tests for mean_reciprocal_rank metric."""

    def test_mrr_first_position(self):
        """Test MRR returns 1.0 when relevant doc is first."""
        expected_id = uuid4()
        results = [
            {"doc_id": expected_id},
            {"doc_id": uuid4()},
        ]
        expected_ids = [expected_id]

        score = mean_reciprocal_rank(results, expected_ids)
        assert score == 1.0

    def test_mrr_second_position(self):
        """Test MRR returns 0.5 when relevant doc is second."""
        expected_id = uuid4()
        results = [
            {"doc_id": uuid4()},
            {"doc_id": expected_id},
        ]
        expected_ids = [expected_id]

        score = mean_reciprocal_rank(results, expected_ids)
        assert score == 0.5

    def test_mrr_third_position(self):
        """Test MRR returns 0.333 when relevant doc is third."""
        expected_id = uuid4()
        results = [
            {"doc_id": uuid4()},
            {"doc_id": uuid4()},
            {"doc_id": expected_id},
        ]
        expected_ids = [expected_id]

        score = mean_reciprocal_rank(results, expected_ids)
        assert abs(score - 0.333) < 0.001

    def test_mrr_no_relevant_doc(self):
        """Test MRR returns 0.0 when no relevant doc found."""
        results = [
            {"doc_id": uuid4()},
            {"doc_id": uuid4()},
        ]
        expected_ids = [uuid4()]

        score = mean_reciprocal_rank(results, expected_ids)
        assert score == 0.0


class TestNDCGAtK:
    """Tests for ndcg_at_k metric."""

    def test_ndcg_perfect_ranking(self):
        """Test nDCG returns 1.0 for perfect ranking."""
        doc1 = uuid4()
        doc2 = uuid4()
        doc3 = uuid4()

        results = [
            {"doc_id": doc1},
            {"doc_id": doc2},
            {"doc_id": doc3},
        ]

        relevance_scores = {
            doc1: 1.0,
            doc2: 0.8,
            doc3: 0.5,
        }

        score = ndcg_at_k(results, [doc1, doc2, doc3], relevance_scores, k=3)
        assert abs(score - 1.0) < 0.001

    def test_ndcg_reversed_ranking(self):
        """Test nDCG < 1.0 for imperfect ranking."""
        doc1 = uuid4()
        doc2 = uuid4()
        doc3 = uuid4()

        # Reversed order (worst to best)
        results = [
            {"doc_id": doc3},
            {"doc_id": doc2},
            {"doc_id": doc1},
        ]

        relevance_scores = {
            doc1: 1.0,  # Best
            doc2: 0.8,
            doc3: 0.5,  # Worst
        }

        score = ndcg_at_k(results, [doc1, doc2, doc3], relevance_scores, k=3)
        assert score < 1.0
        assert score > 0.0

    def test_ndcg_empty_results(self):
        """Test nDCG returns 0.0 for empty results."""
        score = ndcg_at_k([], [uuid4()], {uuid4(): 1.0}, k=5)
        assert score == 0.0


class TestZeroResultRate:
    """Tests for zero_result_rate metric."""

    def test_zero_result_rate_all_results(self):
        """Test ZRR returns 0.0 when all queries have results."""
        queries = ["query1", "query2", "query3"]
        results = [
            [{"doc_id": uuid4()}],
            [{"doc_id": uuid4()}],
            [{"doc_id": uuid4()}],
        ]

        rate = zero_result_rate(queries, results)
        assert rate == 0.0

    def test_zero_result_rate_no_results(self):
        """Test ZRR returns 1.0 when no queries have results."""
        queries = ["query1", "query2", "query3"]
        results = [[], [], []]

        rate = zero_result_rate(queries, results)
        assert rate == 1.0

    def test_zero_result_rate_partial(self):
        """Test ZRR returns correct fraction for partial results."""
        queries = ["query1", "query2", "query3"]
        results = [
            [{"doc_id": uuid4()}],  # Has results
            [],  # No results
            [{"doc_id": uuid4()}],  # Has results
        ]

        rate = zero_result_rate(queries, results)
        assert abs(rate - 0.333) < 0.001

    def test_zero_result_rate_empty_input(self):
        """Test ZRR returns 0.0 for empty input."""
        rate = zero_result_rate([], [])
        assert rate == 0.0


class TestComputeAggregateMetrics:
    """Tests for compute_aggregate_metrics function."""

    def test_aggregate_metrics_calculation(self):
        """Test aggregate metrics are calculated correctly."""
        query_results = [
            {"hit_at_k": 1.0, "mrr": 1.0, "ndcg": 0.9, "result_count": 5},
            {"hit_at_k": 1.0, "mrr": 0.5, "ndcg": 0.8, "result_count": 3},
            {"hit_at_k": 0.0, "mrr": 0.0, "ndcg": 0.0, "result_count": 0},
        ]

        metrics = compute_aggregate_metrics(query_results)

        assert metrics["total_queries"] == 3
        assert abs(metrics["avg_hit_at_k"] - 0.667) < 0.001
        assert abs(metrics["avg_mrr"] - 0.5) < 0.001
        assert abs(metrics["avg_ndcg"] - 0.567) < 0.001
        assert abs(metrics["zero_result_rate"] - 0.333) < 0.001

    def test_aggregate_metrics_empty_input(self):
        """Test aggregate metrics for empty input."""
        metrics = compute_aggregate_metrics([])

        assert metrics["total_queries"] == 0
        assert metrics["avg_hit_at_k"] == 0.0
        assert metrics["avg_mrr"] == 0.0
        assert metrics["avg_ndcg"] == 0.0
        assert metrics["zero_result_rate"] == 0.0


class TestEvaluateRetrievalQuality:
    """Tests for evaluate_retrieval_quality convenience function."""

    def test_evaluate_retrieval_quality(self):
        """Test evaluate_retrieval_quality computes all metrics."""
        expected_id = uuid4()
        results = [
            {"doc_id": expected_id},
            {"doc_id": uuid4()},
        ]
        expected_ids = [expected_id]
        relevance_scores = {expected_id: 1.0}

        metrics = evaluate_retrieval_quality(
            query="test query",
            results=results,
            expected_ids=expected_ids,
            relevance_scores=relevance_scores,
            k=5,
        )

        assert metrics["query"] == "test query"
        assert metrics["hit_at_k"] == 1.0
        assert metrics["mrr"] == 1.0
        assert metrics["ndcg"] > 0.0
        assert metrics["result_count"] == 2
        assert metrics["k"] == 5
