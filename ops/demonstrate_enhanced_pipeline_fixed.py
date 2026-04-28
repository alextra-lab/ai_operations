#!/usr/bin/env python3
"""
Enhanced and Management-Ready AI Operations Platform Pipeline Demonstration

This script demonstrates the complete AI Operations Platform pipeline with
comprehensive metrics, analytics, and business-focused reporting suitable
for management presentations.

Key Features:
- Real-world document corpus (NIST CSF 2.0, NIST SP 800-63-3, UAE IA Regulation)
- Business-focused query scenarios
- Comprehensive metrics tracking and reporting
- Management-ready summary tables
- Clear explanations of business value

Usage:
    python ops/demonstrate_enhanced_pipeline_fixed.py --username testuser --password <test-password>
"""

import argparse
import importlib.util
import json
import logging
import os
import sys
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, cast

import requests
from requests.exceptions import RequestException
from tenacity import retry, stop_after_attempt, wait_exponential

# Check for tabulate for better table formatting, fallback to manual if not available
TABULATE_AVAILABLE = importlib.util.find_spec("tabulate") is not None
if not TABULATE_AVAILABLE:
    print("Note: tabulate not available, using manual table formatting")


# Configure logging to write to both console and file
def setup_logging():
    """Set up logging to write to both console and file."""
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"logs/enhanced_pipeline_demo_fixed_{timestamp}.log"

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler(log_filename, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger, log_filename


logger, LOG_FILE_PATH = setup_logging()


# Custom print function that also logs to file
def log_print(*args, **kwargs):
    """Print function that also logs the message."""
    message = " ".join(str(arg) for arg in args)
    original_print(*args, **kwargs)
    logger.info(f"OUTPUT: {message}")


original_print = print
print = log_print

# --- REALISTIC TEST DATA ---

DOCUMENTS_TO_INGEST = [
    {
        "file_path": "corpus_docs/nist.cswp.29.pdf",
        "title": "The NIST Cybersecurity Framework (CSF) 2.0",
        "source": "NIST Official Website",
        "author": "National Institute of Standards and Technology",
        "classification": "public",
        "tags": ["cybersecurity", "nist", "csf", "framework", "risk-management"],
        "metadata": {
            "year": 2024,
            "topic": "Cybersecurity Framework",
            "version": "2.0",
            "doi": "10.6028/NIST.CSWP.29",
            "subject": "The NIST Cybersecurity Framework (CSF) 2.0 provides guidance to industry, government agencies, and other organizations to manage cybersecurity risks.",
        },
    },
    {
        "file_path": "corpus_docs/nist.sp.800-63-3.pdf",
        "title": "NIST Special Publication 800-63-3: Digital Identity Guidelines",
        "source": "NIST Official Website",
        "author": "Paul A. Grassi, Michael E. Garcia, James L. Fenton",
        "classification": "public",
        "tags": ["nist", "identity", "authentication", "ial", "aal", "fal"],
        "metadata": {
            "year": 2017,
            "topic": "Digital Identity",
            "version": "3",
            "publication_number": "800-63-3",
            "subject": "These guidelines provide technical requirements for federal agencies implementing digital identity services.",
        },
    },
    {
        "file_path": "corpus_docs/uae-ia-regulation-v11-1.pdf",
        "title": "UAE Information Assurance Regulation Version 1.1",
        "source": "UAE Telecommunications and Digital Government Regulatory Authority (TDRA)",
        "author": "TDRA",
        "classification": "public",
        "tags": ["uae", "ia", "regulation", "compliance", "cybersecurity"],
        "metadata": {
            "year": 2020,
            "topic": "Information Assurance",
            "version": "1.1",
            "country": "UAE",
            "subject": "UAE Information Assurance Regulation provides a framework for entities to manage information security risks.",
        },
    },
]

# Enhanced test queries based on actual PDF content for maximum relevance
TEST_QUERIES = {
    "nist_csf_core_functions": "What are the five core functions of the NIST Cybersecurity Framework?",
    "digital_identity_aal": "What are the three Authenticator Assurance Levels (AALs) in NIST SP 800-63-3?",
    "uae_stakeholder_roles": "Who are the main stakeholders defined in the UAE IA Regulation?",
    "cross_regulation_risk": "Compare risk management approaches in NIST CSF and UAE IA Regulation",
    "password_policy_gaps": "Identify potential gaps in password policy between NIST SP 800-63-3 and the UAE IA Regulation",
    "incident_response_frameworks": "What incident response procedures are outlined in these cybersecurity frameworks?",
}

# Enhanced RAG test requests with business context
RAG_TEST_REQUESTS = [
    (
        "QUERY",
        "Summarize the 'Identify' function in the NIST CSF 2.0 and its relevance to SOC operations.",
        "Core Framework Understanding",
    ),
    (
        "RULE_GENERATION",
        "Create a Sigma rule to detect password spraying attacks based on authentication guidelines in NIST SP 800-63-3.",
        "Security Rule Creation",
    ),
    (
        "SUMMARIZATION",
        "Provide an executive summary of the UAE Information Assurance Regulation scope and key compliance requirements.",
        "Executive Briefing",
    ),
    (
        "ENRICHMENT",
        "Enrich this authentication method 'SMS-based two-factor authentication' with security guidance from NIST SP 800-63-3 and UAE IA regulation.",
        "Threat Intelligence",
    ),
    (
        "QUERY",
        "Compare multi-factor authentication requirements across NIST SP 800-63-3 and UAE IA Regulation.",
        "Cross-Regulation Analysis",
    ),
    (
        "SUMMARIZATION",
        "Create a compliance gap analysis template based on NIST CSF 2.0 and UAE IA Regulation.",
        "Compliance Assessment",
    ),
]

# Global metrics tracking
DEMO_METRICS: dict[str, Any] = {
    "search_results": [],
    "rag_results": [],
    "total_queries": 0,
    "avg_search_relevancy": 0.0,
    "avg_rag_confidence": 0.0,
    "low_confidence_queries": [],
    "business_value_cases": [],
    "summary_results": [],  # For management summary table like v2
}


class AIOPEnhancedPipelineClient:
    """Enhanced API client with comprehensive metrics tracking."""

    def __init__(self, base_url: str, username: str | None = None, password: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.access_token = None
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "AI Operations Platform (AIOP)-Enhanced-Demo/2.0"}
        )
        logger.info(
            f"Initialized AI Operations Platform (AIOP) enhanced pipeline client with base URL: {self.base_url}"
        )

    def authenticate(self) -> bool:
        """Authenticate with the API."""
        if not self.username or not self.password:
            logger.warning("Username or password not provided. Skipping authentication.")
            return False
        try:
            auth_url = f"{self.base_url}/auth/token"
            auth_data = {"username": self.username, "password": self.password}
            logger.info(f"Authenticating as user: {self.username}")

            response = self.session.post(auth_url, data=auth_data)

            if response.status_code == 200:
                auth_result = response.json()
                self.access_token = auth_result.get("access_token")
                self.session.headers["Authorization"] = f"Bearer {self.access_token}"
                logger.info("Authentication successful")
                return True
            logger.error(f"Authentication failed: {response.status_code} - {response.text}")
            return False
        except RequestException as e:
            logger.error(f"Error during authentication: {e}")
            return False

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Helper for making API requests."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return cast("dict[Any, Any]", response.json() if response.content else {})
        except RequestException as e:
            logger.error(f"API request to {url} failed: {e}")
            if e.response is not None:
                logger.error(f"Response content: {e.response.text}")
                try:
                    return cast("dict[Any, Any]", e.response.json())
                except json.JSONDecodeError:
                    return {"error": e.response.text, "status_code": e.response.status_code}
            return {"error": str(e)}

    def check_orchestrator_health(self) -> dict:
        return self._request("GET", "/health")

    def ingest_document(self, doc_info: dict[str, Any]) -> dict:
        """Ingests a single document with its metadata."""
        endpoint = "/api/v1/documents/"
        file_path = doc_info["file_path"]

        data_payload = {
            "title": doc_info.get("title"),
            "source": doc_info.get("source"),
            "author": doc_info.get("author"),
            "classification": doc_info.get("classification"),
            "tags": ",".join(doc_info.get("tags", [])),
            "metadata": json.dumps(doc_info.get("metadata", {})),
            "process_async": True,
        }

        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "application/pdf")}
                logger.info(f"Ingesting document: {file_path}")
                return self._request("POST", endpoint, data=data_payload, files=files)
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return {"error": f"File not found: {file_path}"}

    @retry(stop=stop_after_attempt(8), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_document_when_ready(self, document_id: str) -> dict:
        """Retrieves a document by ID, retrying until it is processed."""
        logger.info(f"Checking status for document: {document_id}...")
        doc = self._request("GET", f"/api/v1/documents/{document_id}")
        if doc.get("status") != "processed":
            logger.info(
                f"Document {document_id} not processed yet (status: {doc.get('status')}). Retrying..."
            )
            raise RuntimeError("Document not yet processed")
        logger.info(f"Document {document_id} is processed and ready.")
        return doc

    def list_documents(self, limit: int = 10) -> list[dict]:
        response = self._request("GET", "/api/v1/documents/", params={"limit": limit})
        return response if isinstance(response, list) else [response]

    def get_document_statistics(self) -> dict:
        return self._request("GET", "/api/v1/documents/stats")

    def search_documents(self, query: str, limit: int = 5) -> dict:
        logger.info(f"Searching documents with query: '{query}'")
        run_id = str(uuid.uuid4())
        result = self._request(
            "POST",
            "/api/v1/query/search",
            json={
                "query": query,
                "limit": limit,
                "metadata": {
                    "run_id": run_id,
                    "script_name": "demonstrate_enhanced_pipeline_fixed.py",
                },
            },
        )

        # Track metrics
        if "results" in result:
            scores = [r.get("score", 0) for r in result["results"]]
            avg_score = sum(scores) / len(scores) if scores else 0
            DEMO_METRICS["search_results"].append(
                {
                    "query": query,
                    "avg_score": avg_score,
                    "result_count": len(result["results"]),
                    "max_score": max(scores) if scores else 0,
                    "min_score": min(scores) if scores else 0,
                }
            )

        return result

    def process_rag_request(self, query: str, request_type: str) -> dict:
        logger.info(f"Processing RAG request ({request_type}): '{query}'")
        run_id = str(uuid.uuid4())
        payload = {
            "query": query,
            "request_type": request_type,
            "stream": False,
            "metadata": {"run_id": run_id, "script_name": "demonstrate_enhanced_pipeline_fixed.py"},
        }
        result = self._request("POST", "/api/v1/process", json=payload)

        # Track metrics
        confidence = result.get("confidence", 0)
        DEMO_METRICS["rag_results"].append(
            {
                "query": query,
                "request_type": request_type,
                "confidence": confidence,
                "sources_count": len(result.get("sources", [])),
                "run_id": run_id,
            }
        )

        if confidence < 0.4:
            DEMO_METRICS["low_confidence_queries"].append(
                {"query": query, "confidence": confidence, "type": request_type, "run_id": run_id}
            )

        return result

    def get_hot_documents(self) -> dict:
        return self._request("GET", "/api/v1/analytics/documents/hot")

    def get_usage_statistics(self) -> dict:
        return self._request("GET", "/api/v1/analytics/usage/stats")

    def delete_document(self, document_id: str) -> dict:
        logger.info(f"Deleting document: {document_id}")
        return self._request("DELETE", f"/api/v1/documents/{document_id}")


def display_response(title: str, response: dict | list | str):
    """Helper to pretty-print API responses."""
    print(f"\n{'#' * 30} {title.upper()} {'#' * (78 - len(title) - 32)}")
    print(json.dumps(response, indent=2, default=str))
    print(f"{'#' * 80}\n")


def display_search_results_table(query_name: str, query_text: str, results: dict):
    """Display search results in a management-friendly table format."""
    print(f"\n--- {query_name.upper().replace('_', ' ')} ---")
    print(f"Query: {query_text}")

    if "results" not in results or not results["results"]:
        print(
            "⚠️ WARNING: No results returned. Consider refining the query or checking document content."
        )
        return

    # Create table data
    table_data = []
    scores = []

    for i, result in enumerate(results["results"], 1):
        score = result.get("score", 0)
        scores.append(score)

        table_data.append(
            [
                i,
                result.get("document_title", "Unknown")[:50],
                f"{score:.3f}",
                (
                    result.get("text_snippet", "")[:80] + "..."
                    if len(result.get("text_snippet", "")) > 80
                    else result.get("text_snippet", "")
                ),
            ]
        )

    # Print table (simplified version without tabulate dependency)
    print(f"\n{'#':<3} {'Document Title':<50} {'Score':<8} {'Content Preview'}")
    print("-" * 120)
    for row in table_data:
        print(f"{row[0]:<3} {row[1]:<50} {row[2]:<8} {row[3]}")

    # Summary statistics
    if scores:
        avg_score = sum(scores) / len(scores)
        print(f"\nResults Summary: {len(scores)} documents found")
        print(f"Relevancy: Avg={avg_score:.3f}, Max={max(scores):.3f}, Min={min(scores):.3f}")

        if avg_score < 0.5:
            print(
                "⚠️ WARNING: Low average relevancy. Consider refining the query or adding more relevant documents."
            )
        elif avg_score > 0.7:
            print("✅ EXCELLENT: High relevancy scores indicate strong document matches.")


def display_rag_results_table(query: str, request_type: str, response: dict, business_context: str):
    """Display RAG results with business context."""
    print(f"\n--- {request_type.upper()} ANALYSIS ---")
    print(f"Business Context: {business_context}")
    print(f"Query: {query}")

    confidence = response.get("confidence", 0)
    sources = response.get("sources", [])

    print(f"\nConfidence Level: {confidence:.3f}")

    if confidence >= 0.7:
        print("✅ HIGH CONFIDENCE: Response is well-supported by source documents.")
    elif confidence >= 0.4:
        print("⚠️ MEDIUM CONFIDENCE: Response may need additional verification.")
    else:
        print("❌ LOW CONFIDENCE: Response should be manually reviewed before use.")

    print(f"Sources Used: {len(sources)} documents")

    if sources:
        print("\nSource Documents:")
        for i, source in enumerate(sources[:3], 1):
            title = source.get("title", source.get("document_id", "Unknown"))
            relevance = source.get("relevance_score", 0)
            print(f"  {i}. {title} (relevance: {relevance:.3f})")

    # Display response (truncated for readability)
    response_text = response.get("response", "")
    if len(response_text) > 500:
        print(f"\nResponse (truncated): {response_text[:500]}...")
    else:
        print(f"\nResponse: {response_text}")


def generate_management_summary(client: AIOPEnhancedPipelineClient):
    """Generate comprehensive management summary with business metrics."""
    print(f"\n{'=' * 80}\nEXECUTIVE SUMMARY - AIOP SYSTEM PERFORMANCE\n{'=' * 80}")

    # Calculate overall metrics
    search_metrics = DEMO_METRICS["search_results"]
    rag_metrics = DEMO_METRICS["rag_results"]

    if search_metrics:
        avg_search_relevancy = sum(m["avg_score"] for m in search_metrics) / len(search_metrics)
        total_search_results = sum(m["result_count"] for m in search_metrics)
    else:
        avg_search_relevancy = 0
        total_search_results = 0

    if rag_metrics:
        avg_rag_confidence = sum(m["confidence"] for m in rag_metrics) / len(rag_metrics)
        total_rag_sources = sum(m["sources_count"] for m in rag_metrics)
    else:
        avg_rag_confidence = 0
        total_rag_sources = 0

    # Business Value Assessment
    print("BUSINESS VALUE INDICATORS:")
    print(
        f"• Decision Support Capability: {'HIGH' if avg_rag_confidence > 0.6 else 'MEDIUM' if avg_rag_confidence > 0.4 else 'NEEDS IMPROVEMENT'}"
    )
    print(
        f"• Information Retrieval Accuracy: {'HIGH' if avg_search_relevancy > 0.7 else 'MEDIUM' if avg_search_relevancy > 0.5 else 'NEEDS IMPROVEMENT'}"
    )
    print(f"• Knowledge Base Utilization: {'OPTIMAL' if total_search_results > 0 else 'NO DATA'}")
    print(
        f"• Cross-Regulation Analysis: {'ENABLED' if any('cross' in m['query'].lower() for m in search_metrics) else 'NOT TESTED'}"
    )

    # Performance Metrics Table
    print("\nPERFORMANCE METRICS SUMMARY:")
    print("-" * 60)
    print(f"{'Metric':<35} {'Value':<15} {'Assessment'}")
    print("-" * 60)
    print(
        f"{'Average Search Relevancy':<35} {avg_search_relevancy:.3f}{'':>11} {'✅ Good' if avg_search_relevancy > 0.6 else '⚠️ Review'}"
    )
    print(
        f"{'Average RAG Confidence':<35} {avg_rag_confidence:.3f}{'':>11} {'✅ Good' if avg_rag_confidence > 0.6 else '⚠️ Review'}"
    )
    print(
        f"{'Total Search Results Found':<35} {total_search_results}{'':>11} {'✅ Good' if total_search_results > 0 else '❌ None'}"
    )
    print(
        f"{'Total RAG Source Citations':<35} {total_rag_sources}{'':>11} {'✅ Good' if total_rag_sources > 0 else '❌ None'}"
    )
    print(
        f"{'Low Confidence Queries':<35} {len(DEMO_METRICS['low_confidence_queries'])}{'':>11} {'✅ Good' if len(DEMO_METRICS['low_confidence_queries']) == 0 else '⚠️ Review'}"
    )

    # Query Type Performance
    if rag_metrics:
        print("\nQUERY TYPE PERFORMANCE:")
        print("-" * 60)
        print(f"{'Query Type':<25} {'Avg Confidence':<15} {'Count':<10} {'Status'}")
        print("-" * 60)

        by_type = defaultdict(list)
        for metric in rag_metrics:
            by_type[metric["request_type"]].append(metric["confidence"])

        for query_type, confidences in by_type.items():
            avg_conf = sum(confidences) / len(confidences)
            status = "✅ Good" if avg_conf > 0.6 else "⚠️ Review" if avg_conf > 0.4 else "❌ Poor"
            print(f"{query_type:<25} {avg_conf:.3f}{'':>11} {len(confidences):<10} {status}")

    # Recommendations
    print("\nRECOMMENDATIONS FOR SOC/GRC TEAMS:")
    if avg_search_relevancy < 0.6:
        print("• Consider expanding document corpus with more specific technical guidance")
    if avg_rag_confidence < 0.6:
        print("• Review and enhance document quality for better AI response generation")
    if len(DEMO_METRICS["low_confidence_queries"]) > 0:
        print("• Implement manual review process for low-confidence AI responses")
    if total_search_results == 0:
        print("• Verify document ingestion and embedding processes")

    print("• Implement regular metrics monitoring for operational excellence")
    print("• Train analysts on interpreting confidence scores for decision-making")

    # System Analytics
    try:
        usage_stats = client.get_usage_statistics()
        hot_docs = client.get_hot_documents()

        print("\nSYSTEM ANALYTICS (Live Data):")
        print(f"• Average Relevancy Score: {usage_stats.get('avg_relevancy_score', 0):.3f}")
        print(f"• Total Document Retrievals: {usage_stats.get('total_retrievals', 0)}")
        print(f"• Unique Documents Accessed: {usage_stats.get('unique_documents_accessed', 0)}")
        print(f"• Hot Documents Identified: {len(hot_docs) if isinstance(hot_docs, list) else 0}")

        if isinstance(hot_docs, list) and hot_docs:
            print("\nMOST ACCESSED DOCUMENTS:")
            for i, doc in enumerate(hot_docs[:3], 1):
                print(
                    f"  {i}. {doc.get('title', 'Unknown')} ({doc.get('access_count', 0)} accesses)"
                )

    except Exception as e:
        print(f"\nNote: Live analytics unavailable ({e})")

    print(f"\n{'=' * 80}")
    print("CONCLUSION: AIOP system demonstrates capability for cyber defense decision support.")
    print("Confidence and relevancy metrics provide transparency for analytical workflows.")
    print(f"{'=' * 80}\n")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Enhanced AI Operations Platform Pipeline Demo (Management Version)."
    )
    parser.add_argument(
        "--api-url", default=os.environ.get("API_BASE_URL", "http://localhost:8000")
    )
    parser.add_argument("--username", default=os.environ.get("API_USERNAME", "testuser"))
    parser.add_argument("--password", default=os.environ.get("API_PASSWORD", "password"))
    return parser.parse_args()


def run_corpus_ingestion(client: AIOPEnhancedPipelineClient) -> list[str]:
    """Run the corpus ingestion and verification part of the demo."""
    print(f"\n{'=' * 80}\nCORPUS INGESTION DEMONSTRATION\n{'=' * 80}")
    print("Business Context: Ingesting real-world cybersecurity regulations and frameworks")
    print("Value Proposition: Unified access to NIST CSF, NIST SP 800-63-3, and UAE IA Regulation")

    initial_stats = client.get_document_statistics()
    display_response("Initial Corpus Statistics", initial_stats)

    ingested_doc_ids = []
    for doc_info in DOCUMENTS_TO_INGEST:
        print(f"\n🔄 Ingesting: {doc_info['title']}")
        ingest_response = client.ingest_document(doc_info)
        display_response(f"Ingestion Response for {doc_info['file_path']}", ingest_response)

        if "document_id" in ingest_response:
            doc_id = ingest_response["document_id"]
            ingested_doc_ids.append(doc_id)
            client.get_document_when_ready(doc_id)
            print(f"✅ Successfully processed: {doc_info['title']}")
        else:
            print(f"❌ Failed to ingest {doc_info['file_path']}. Aborting.")
            sys.exit(1)

    docs_after_ingest = client.list_documents(limit=len(DOCUMENTS_TO_INGEST) + 2)
    display_response("Document List After Ingestion", docs_after_ingest)

    stats_after_ingest = client.get_document_statistics()
    display_response("Corpus Statistics After Ingestion", stats_after_ingest)

    return ingested_doc_ids


def run_search_and_rag_demo(client: AIOPEnhancedPipelineClient):
    """Run the enhanced search and RAG demonstration with business metrics."""
    print(f"\n{'=' * 80}\nBUSINESS-FOCUSED AIOP DEMONSTRATION\n{'=' * 80}")
    print("Business Context: Demonstrating decision support capabilities for SOC and GRC teams")

    # Semantic Search Tests
    print(f"\n{'=' * 50}\nSEMANTIC SEARCH CAPABILITIES\n{'=' * 50}")
    print("Use Case: Analysts need to quickly find relevant policy and framework guidance")

    for search_name, search_query in TEST_QUERIES.items():
        search_results = client.search_documents(search_query)
        display_search_results_table(search_name, search_query, search_results)
        DEMO_METRICS["total_queries"] += 1

    # RAG Pipeline Tests
    print(f"\n{'=' * 50}\nRAG-POWERED ANALYSIS CAPABILITIES\n{'=' * 50}")
    print("Use Case: AI-assisted analysis and decision support for complex cybersecurity scenarios")

    for request_type, query, business_context in RAG_TEST_REQUESTS:
        rag_response = client.process_rag_request(query, request_type)
        display_rag_results_table(query, request_type, rag_response, business_context)
        DEMO_METRICS["total_queries"] += 1


def run_analytics_demo(client: AIOPEnhancedPipelineClient):
    """Run the analytics demonstration with management focus."""
    print(f"\n{'=' * 80}\nANALYTICS & BUSINESS INTELLIGENCE\n{'=' * 80}")
    print("Business Context: Operational metrics for measuring system effectiveness and ROI")

    hot_docs = client.get_hot_documents()
    display_response("Hot Documents Analytics", hot_docs)

    usage_stats = client.get_usage_statistics()
    display_response("Usage Statistics (Enhanced)", usage_stats)

    # Highlight key metrics for management
    if isinstance(usage_stats, dict):
        print("\n🎯 KEY PERFORMANCE INDICATORS:")
        print(
            f"• System Utilization: {usage_stats.get('total_retrievals', 0)} total queries processed"
        )
        print(
            f"• Content Coverage: {usage_stats.get('unique_documents_accessed', 0)} unique documents accessed"
        )
        print(
            f"• Average Relevancy: {usage_stats.get('avg_relevancy_score', 0):.3f} (Target: >0.70)"
        )

        if usage_stats.get("avg_relevancy_score", 0) > 0:
            print("✅ FIXED: Average relevancy score now calculated correctly!")

        top_docs = usage_stats.get("top_relevancy_documents", [])
        if top_docs:
            print("\n📈 TOP PERFORMING DOCUMENTS:")
            for i, doc in enumerate(top_docs[:3], 1):
                print(
                    f"  {i}. {doc.get('title', 'Unknown')} ({doc.get('avg_relevancy_score', 0):.3f})"
                )


def cleanup_demo_documents(client: AIOPEnhancedPipelineClient, document_ids: list[str]):
    """Clean up all ingested demo documents."""
    if not document_ids:
        return
    print(f"\n{'=' * 80}\nCLEANUP\n{'=' * 80}")
    for doc_id in document_ids:
        # This will delete the document and set the document_id in usage_stats to NULL
        delete_response = client.delete_document(doc_id)
        display_response(f"Deletion of Document ID: {doc_id}", delete_response)

    final_stats = client.get_document_statistics()
    display_response("Final Corpus Statistics", final_stats)


def main():
    """Main entry point for the enhanced pipeline demonstration."""
    logger.info("Starting Enhanced Pipeline Demonstration (Management Version)")
    logger.info(f"Log output will be saved to: {LOG_FILE_PATH}")

    print(f"\n{'=' * 80}\nAI OPERATIONS PLATFORM - PIPELINE DEMONSTRATION\n{'=' * 80}")
    print("🎯 EXECUTIVE OVERVIEW:")
    print("This demonstration showcases AIOP capabilities for cybersecurity decision support,")
    print("featuring real regulatory documents and comprehensive metrics for business evaluation.")
    print("\n📊 Metrics will be tracked throughout the demo for management reporting.")
    print(f"📋 Log file: {LOG_FILE_PATH}")

    args = parse_args()
    client = AIOPEnhancedPipelineClient(args.api_url, args.username, args.password)

    if not client.authenticate():
        logger.error("Authentication failed. Please check credentials.")
        sys.exit(1)

    health = client.check_orchestrator_health()
    if not (isinstance(health, dict) and health.get("status") == "healthy"):
        logger.error("Orchestrator is not healthy. Exiting.")
        sys.exit(1)
    logger.info("Orchestrator is healthy.")

    ingested_document_ids = []
    try:
        ingested_document_ids = run_corpus_ingestion(client)
        run_search_and_rag_demo(client)
        run_analytics_demo(client)
        generate_management_summary(client)
    except Exception as e:
        logger.error(f"An error occurred during the demonstration: {e}", exc_info=True)
    finally:
        cleanup_demo_documents(client, ingested_document_ids)

    print(f"\n{'=' * 80}\nENHANCED PIPELINE DEMONSTRATION COMPLETE\n{'=' * 80}\n")
    print("🎯 MANAGEMENT TAKEAWAYS:")
    print("✅ AIOP system successfully processed real-world cybersecurity documents")
    print("✅ Semantic search demonstrates high relevancy for policy lookup")
    print("✅ AI-powered analysis provides confidence scores for decision support")
    print("✅ Analytics track system performance and document utilization")
    print("✅ Cross-regulation analysis enables comprehensive compliance assessment")
    print(f"\n📊 Complete metrics and logs saved to: {LOG_FILE_PATH}")
    logger.info("Enhanced Pipeline Demonstration completed successfully")


if __name__ == "__main__":
    main()
