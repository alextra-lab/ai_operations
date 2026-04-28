-- Compare the last two runs of the demonstrate_enhanced_pipeline_fixed.py script
WITH latest_runs AS (
    SELECT
        metadata->>'run_id' AS run_id,
        MAX(accessed_at) AS run_time
    FROM
        usage_stats
    WHERE
        metadata->>'script_name' = 'demonstrate_enhanced_pipeline_fixed.py'
    GROUP BY
        run_id
    ORDER BY
        run_time DESC
    LIMIT 2
),
latest_run AS (
    SELECT
        run_id
    FROM
        latest_runs
    ORDER BY
        run_time DESC
    LIMIT 1
),
previous_run AS (
    SELECT
        run_id
    FROM
        latest_runs
    ORDER BY
        run_time ASC
    LIMIT 1
)
SELECT
    'Average Search Relevancy' AS metric,
    (SELECT AVG(average_relevancy) FROM usage_stats WHERE metadata->>'run_id' = (SELECT run_id FROM previous_run)) AS before,
    (SELECT AVG(average_relevancy) FROM usage_stats WHERE metadata->>'run_id' = (SELECT run_id FROM latest_run)) AS after
UNION ALL
SELECT
    'Average RAG Confidence' AS metric,
    (SELECT AVG(rag_confidence) FROM usage_stats WHERE metadata->>'run_id' = (SELECT run_id FROM previous_run)) AS before,
    (SELECT AVG(rag_confidence) FROM usage_stats WHERE metadata->>'run_id' = (SELECT run_id FROM latest_run)) AS after
UNION ALL
SELECT
    'Total Search Results Found' AS metric,
    (SELECT SUM(total_results_found) FROM usage_stats WHERE metadata->>'run_id' = (SELECT run_id FROM previous_run)) AS before,
    (SELECT SUM(total_results_found) FROM usage_stats WHERE metadata->>'run_id' = (SELECT run_id FROM latest_run)) AS after
UNION ALL
SELECT
    'Total RAG Source Citations' AS metric,
    (SELECT SUM(source_document_count) FROM usage_stats WHERE metadata->>'run_id' = (SELECT run_id FROM previous_run)) AS before,
    (SELECT SUM(source_document_count) FROM usage_stats WHERE metadata->>'run_id' = (SELECT run_id FROM latest_run)) AS after
UNION ALL
SELECT
    'Low Confidence Queries' AS metric,
    (SELECT COUNT(*) FROM usage_stats WHERE metadata->>'run_id' = (SELECT run_id FROM previous_run) AND rag_confidence < 0.5) AS before,
    (SELECT COUNT(*) FROM usage_stats WHERE metadata->>'run_id' = (SELECT run_id FROM latest_run) AND rag_confidence < 0.5) AS after;
