"""
Preflight Analysis Service for intelligent chunking strategy recommendation.

Analyzes document structure and recommends optimal chunking strategies
based on document characteristics and optional test suite metrics.

Part of Layer 3: Corpus Management Backend (P4-F10)
ADR-034: Use Case Validation & Test Harness
"""

import statistics
import time
from uuid import UUID

from shared.logging_utils.fastapi import get_logger

from ..schemas.chunking_enums import ChunkingConfig, ChunkingStrategy
from ..schemas.preflight import (
    PreflightRecommendation,
    PreflightReport,
    StrategyBenchmarkResult,
    StructureSignals,
)
from .chunking_service import ChunkingService

logger = get_logger(__name__)


class PreflightAnalyzer:
    """
    Analyze documents and recommend chunking strategies.

    Features:
    - Structure analysis (headings, tables, lists, paragraphs)
    - Strategy benchmarking (5 core strategies)
    - Retrieval metrics (if test suite provided)
    - Confidence-based recommendations
    """

    def __init__(self, chunking_service: ChunkingService):
        """
        Initialize preflight analyzer.

        Args:
            chunking_service: ChunkingService instance for strategy execution
        """
        self.chunking_service = chunking_service

    async def analyze(
        self,
        text: str,
        document_name: str,
        document_type: str,
        document_size_bytes: int,
        test_suite_id: UUID | None = None,
        strategies_to_test: list[ChunkingStrategy] | None = None,
        max_sample_tokens: int = 10000,
    ) -> PreflightReport:
        """
        Run preflight analysis on document.

        Args:
            text: Document text content
            document_name: Document filename
            document_type: MIME type
            document_size_bytes: Document size in bytes
            test_suite_id: Optional test suite for retrieval metrics
            strategies_to_test: Optional specific strategies (defaults to core 5)
            max_sample_tokens: Maximum sample size for analysis

        Returns:
            PreflightReport with analysis results and recommendation
        """
        start_time = time.time()

        # Extract sample for analysis
        sample_text = self._extract_sample(text, max_sample_tokens)
        sample_tokens = len(sample_text.split())

        logger.info(
            f"Starting preflight analysis for {document_name}",
            extra={
                "document_name": document_name,
                "document_size_bytes": document_size_bytes,
                "sample_tokens": sample_tokens,
            },
        )

        # Analyze document structure
        structure_signals = self._analyze_structure(sample_text)

        # Determine strategies to test
        if strategies_to_test is None:
            strategies_to_test = self._get_default_strategies()

        # Benchmark each strategy
        strategy_results = []
        for strategy in strategies_to_test:
            result = await self._benchmark_strategy(
                strategy=strategy,
                text=sample_text,
                structure_signals=structure_signals,
                test_suite_id=test_suite_id,
            )
            strategy_results.append(result)

        # Rank strategies by score
        strategy_results.sort(key=lambda r: r.score, reverse=True)
        for rank, result in enumerate(strategy_results, start=1):
            result.rank = rank

        # Generate recommendation
        recommendation = self._select_best_strategy(
            strategy_results=strategy_results,
            structure_signals=structure_signals,
        )

        analysis_time_ms = int((time.time() - start_time) * 1000)

        return PreflightReport(
            document_id=None,
            document_name=document_name,
            document_type=document_type,
            document_size_bytes=document_size_bytes,
            sample_size_tokens=sample_tokens,
            structure_signals=structure_signals,
            strategy_results=strategy_results,
            recommendation=recommendation,
            test_suite_id=test_suite_id,
            analysis_time_ms=analysis_time_ms,
            metadata=None,
        )

    def _extract_sample(self, text: str, max_tokens: int) -> str:
        """
        Extract sample from document for analysis.

        Takes first max_tokens words (approximate tokenization).

        Args:
            text: Full document text
            max_tokens: Maximum tokens to extract

        Returns:
            Sample text
        """
        words = text.split()
        if len(words) <= max_tokens:
            return text

        # Take first max_tokens words
        sample_words = words[:max_tokens]
        return " ".join(sample_words)

    def _analyze_structure(self, text: str) -> StructureSignals:
        """
        Analyze document structure signals.

        Computes:
        - heading_density: Ratio of heading lines to total lines
        - table_ratio: Ratio of table content to total content
        - list_ratio: Ratio of list items to total lines
        - avg_paragraph_length: Average paragraph length in tokens
        - sentence_count: Total sentences
        - token_count: Total tokens
        - has_code_blocks: Whether doc contains code
        - has_equations: Whether doc contains equations

        Args:
            text: Document text

        Returns:
            StructureSignals with computed metrics
        """
        lines = text.split("\n")
        total_lines = len(lines)

        # Count headings (Markdown style: # heading, ## heading, etc.)
        heading_lines = sum(1 for line in lines if line.strip().startswith("#"))
        heading_density = heading_lines / total_lines if total_lines > 0 else 0.0

        # Detect tables (Markdown style: | col1 | col2 |)
        table_lines = sum(1 for line in lines if "|" in line and line.count("|") >= 2)
        table_ratio = table_lines / total_lines if total_lines > 0 else 0.0

        # Detect lists (Markdown/plain text: -, *, 1., etc.)
        list_lines = sum(1 for line in lines if any(c in line[:5] for c in ["-", "*", "+"]))
        list_ratio = list_lines / total_lines if total_lines > 0 else 0.0

        # Calculate average paragraph length
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        if paragraphs:
            paragraph_lengths = [len(p.split()) for p in paragraphs]
            avg_paragraph_length = sum(paragraph_lengths) / len(paragraph_lengths)
        else:
            avg_paragraph_length = 0.0

        # Count sentences (approximate: split by . ! ?)
        sentences = [
            s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()
        ]
        sentence_count = len(sentences)

        # Count tokens (approximate: split by whitespace)
        token_count = len(text.split())

        # Detect code blocks (Markdown style: ```code```)
        has_code_blocks = "```" in text or "    " in text[:100]  # Indented code

        # Detect equations (LaTeX style: $equation$ or $$equation$$)
        has_equations = "$" in text or "\\(" in text or "\\[" in text

        return StructureSignals(
            heading_density=min(heading_density, 1.0),
            table_ratio=min(table_ratio, 1.0),
            list_ratio=min(list_ratio, 1.0),
            avg_paragraph_length=avg_paragraph_length,
            sentence_count=sentence_count,
            token_count=token_count,
            has_code_blocks=has_code_blocks,
            has_equations=has_equations,
            ocr_confidence=None,
        )

    def _get_default_strategies(self) -> list[ChunkingStrategy]:
        """Get default strategies to test (5 core strategies)."""
        return [
            ChunkingStrategy.FIXED_TOKEN,
            ChunkingStrategy.SLIDING_TOKEN,
            ChunkingStrategy.HEADING_AWARE,
            ChunkingStrategy.SENTENCE_PARAGRAPH,
            ChunkingStrategy.TABLE_AWARE,
        ]

    async def _benchmark_strategy(
        self,
        strategy: ChunkingStrategy,
        text: str,
        structure_signals: StructureSignals,
        test_suite_id: UUID | None = None,  # noqa: ARG002
    ) -> StrategyBenchmarkResult:
        """
        Benchmark a single chunking strategy.

        Args:
            strategy: Chunking strategy to test
            text: Document text
            structure_signals: Document structure analysis
            test_suite_id: Optional test suite for retrieval metrics

        Returns:
            StrategyBenchmarkResult with metrics and score
        """
        start_time = time.time()

        # Create chunking config (other params use defaults)
        config = ChunkingConfig(  # type: ignore[call-arg]
            strategy=strategy,
            chunk_size=1024,  # Standard chunk size
        )

        try:
            # Execute chunking
            result = await self.chunking_service.chunk_document(text, config)

            # Calculate chunk size statistics
            chunk_sizes = [len(chunk.split()) for chunk in result.chunks]
            if chunk_sizes:
                avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes)
                std_chunk_size = statistics.stdev(chunk_sizes) if len(chunk_sizes) > 1 else 0.0
            else:
                avg_chunk_size = 0.0
                std_chunk_size = 0.0

            processing_time_ms = int((time.time() - start_time) * 1000)

            # TODO: Compute retrieval metrics if test_suite_id provided
            # For now, set to None (requires integration with test suite execution)
            hit_at_k = None
            mrr = None
            ndcg = None
            zero_result_rate = None

            # Calculate overall score
            score = self._calculate_strategy_score(
                strategy=strategy,
                structure_signals=structure_signals,
                chunk_count=result.chunk_count,
                avg_chunk_size=avg_chunk_size,
                std_chunk_size=std_chunk_size,
                hit_at_k=hit_at_k,
                mrr=mrr,
            )

            return StrategyBenchmarkResult(
                strategy=strategy,
                chunk_count=result.chunk_count,
                avg_chunk_size=avg_chunk_size,
                std_chunk_size=std_chunk_size,
                processing_time_ms=processing_time_ms,
                hit_at_k=hit_at_k,
                mrr=mrr,
                ndcg=ndcg,
                zero_result_rate=zero_result_rate,
                score=score,
                rank=None,
            )

        except Exception as e:
            logger.error(f"Failed to benchmark strategy {strategy}: {e}")
            # Return low-score result on failure
            return StrategyBenchmarkResult(
                strategy=strategy,
                chunk_count=0,
                avg_chunk_size=0.0,
                std_chunk_size=0.0,
                processing_time_ms=int((time.time() - start_time) * 1000),
                hit_at_k=None,
                mrr=None,
                ndcg=None,
                zero_result_rate=None,
                score=0.0,
                rank=None,
            )

    def _calculate_strategy_score(
        self,
        strategy: ChunkingStrategy,
        structure_signals: StructureSignals,
        chunk_count: int,  # noqa: ARG002
        avg_chunk_size: float,
        std_chunk_size: float,
        hit_at_k: float | None,
        mrr: float | None,
    ) -> float:
        """
        Calculate overall score for a strategy.

        Scoring factors:
        - Structure match (40%): How well strategy matches document structure
        - Chunk quality (30%): Consistency of chunk sizes
        - Retrieval metrics (30%): Hit@K, MRR if available

        Args:
            strategy: Chunking strategy
            structure_signals: Document structure
            chunk_count: Number of chunks produced
            avg_chunk_size: Average chunk size
            std_chunk_size: Standard deviation of chunk sizes
            hit_at_k: Optional hit@k metric
            mrr: Optional MRR metric

        Returns:
            Score between 0.0 and 1.0
        """
        score = 0.0

        # Structure match score (40%)
        structure_match = 0.0

        if strategy == ChunkingStrategy.HEADING_AWARE:
            # Prefer for documents with high heading density
            structure_match = structure_signals.heading_density
        elif strategy == ChunkingStrategy.TABLE_AWARE:
            # Prefer for documents with tables
            structure_match = structure_signals.table_ratio
        elif strategy == ChunkingStrategy.SENTENCE_PARAGRAPH:
            # Prefer for narrative documents (low heading/table density, long paragraphs)
            narrative_score = (
                (1.0 - structure_signals.heading_density) * 0.4
                + (1.0 - structure_signals.table_ratio) * 0.4
                + min(structure_signals.avg_paragraph_length / 100.0, 1.0) * 0.2
            )
            structure_match = narrative_score
        elif strategy in (ChunkingStrategy.FIXED_TOKEN, ChunkingStrategy.SLIDING_TOKEN):
            # General-purpose strategies - moderate score
            structure_match = 0.5

        score += structure_match * 0.4

        # Chunk quality score (30%)
        # Prefer consistent chunk sizes (low std deviation)
        consistency = 1.0 - min(std_chunk_size / avg_chunk_size, 1.0) if avg_chunk_size > 0 else 0.0

        score += consistency * 0.3

        # Retrieval metrics score (30%)
        if hit_at_k is not None and mrr is not None:
            retrieval_score = hit_at_k * 0.5 + mrr * 0.5
            score += retrieval_score * 0.3
        else:
            # No retrieval metrics available, boost structure score
            score += structure_match * 0.3

        return min(score, 1.0)

    def _select_best_strategy(
        self,
        strategy_results: list[StrategyBenchmarkResult],
        structure_signals: StructureSignals,
    ) -> PreflightRecommendation:
        """
        Select best strategy and generate recommendation.

        Args:
            strategy_results: Benchmarked strategy results (sorted by score)
            structure_signals: Document structure signals

        Returns:
            PreflightRecommendation with strategy and reasoning
        """
        if not strategy_results:
            raise ValueError("No strategy results to select from")

        # Best strategy is first (already sorted)
        best = strategy_results[0]

        # Generate reasoning
        reasoning = []

        # Add structure-based reasoning
        if structure_signals.heading_density > 0.3:
            reasoning.append(
                f"Document has high heading density ({structure_signals.heading_density:.1%}), "
                "suggesting structured content."
            )

        if structure_signals.table_ratio > 0.2:
            reasoning.append(
                f"Document contains significant tabular content ({structure_signals.table_ratio:.1%})."
            )

        if structure_signals.avg_paragraph_length > 100:
            reasoning.append(
                f"Document has long paragraphs (avg {structure_signals.avg_paragraph_length:.0f} tokens), "
                "suggesting narrative content."
            )

        # Add strategy-specific reasoning
        if best.strategy == ChunkingStrategy.HEADING_AWARE:
            reasoning.append("Heading-aware chunking will preserve document structure.")
        elif best.strategy == ChunkingStrategy.TABLE_AWARE:
            reasoning.append("Table-aware chunking will handle tabular data effectively.")
        elif best.strategy == ChunkingStrategy.SENTENCE_PARAGRAPH:
            reasoning.append("Sentence-paragraph chunking will maintain narrative flow.")
        elif best.strategy == ChunkingStrategy.SLIDING_TOKEN:
            reasoning.append("Sliding token chunking provides consistent overlap for context.")
        else:
            reasoning.append(
                f"{best.strategy.value} chunking is recommended for this document type."
            )

        # Add confidence reasoning
        if best.score > 0.8:
            reasoning.append(f"High confidence recommendation (score: {best.score:.2f}).")
        elif best.score > 0.6:
            reasoning.append(f"Moderate confidence recommendation (score: {best.score:.2f}).")
        else:
            reasoning.append(
                f"Low confidence recommendation (score: {best.score:.2f}). Consider testing multiple strategies."
            )

        # Calculate confidence (based on score gap between best and second-best)
        if len(strategy_results) > 1:
            score_gap = best.score - strategy_results[1].score
            confidence = min(best.score + score_gap * 0.5, 1.0)
        else:
            confidence = best.score

        # Get alternative strategies (2nd and 3rd ranked)
        alternatives = [r.strategy for r in strategy_results[1:3]]

        return PreflightRecommendation(
            strategy=best.strategy,
            confidence=confidence,
            reasoning=reasoning,
            alternative_strategies=alternatives,
        )
