#!/usr/bin/env python3
"""
End-to-End Document Ingestion Flow Verification

This script traces and verifies every step of the document ingestion process:
1. Client authentication
2. File upload through orchestrator
3. Background processing initiation
4. Status polling
5. Final verification

Author: Cline
Purpose: Complete flow verification and debugging
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

# Configuration
BASE_URL = "http://localhost:8000"
USERNAME = "testuser"
PASSWORD = "password"
TEST_FILE = "corpus_docs/uae-ia-regulation-v11-1.pdf"


class IngestionFlowVerifier:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.document_id = None
        self.verification_results = {}

    def log_step(self, step: str, status: str, details: Any = None):
        """Log verification step results."""
        timestamp = datetime.now().isoformat()
        print(f"\n🔍 [{timestamp}] STEP: {step}")
        print(f"   STATUS: {status}")
        if details:
            if isinstance(details, dict):
                for key, value in details.items():
                    print(f"   {key}: {value}")
            else:
                print(f"   DETAILS: {details}")

        self.verification_results[step] = {
            "status": status,
            "timestamp": timestamp,
            "details": details,
        }

    def verify_authentication(self) -> bool:
        """Step 1: Verify authentication flow."""
        print("\n" + "=" * 80)
        print("🔐 STEP 1: AUTHENTICATION VERIFICATION")
        print("=" * 80)

        try:
            # Test authentication endpoint
            auth_url = f"{BASE_URL}/auth/token"
            auth_data = {"username": USERNAME, "password": PASSWORD}

            print(f"📡 Making auth request to: {auth_url}")
            response = requests.post(auth_url, data=auth_data, timeout=10)

            if response.status_code == 200:
                auth_result = response.json()
                self.auth_token = auth_result.get("access_token")

                self.log_step(
                    "Authentication",
                    "✅ SUCCESS",
                    {
                        "Token Type": auth_result.get("token_type"),
                        "Token Length": len(self.auth_token) if self.auth_token else 0,
                        "User Info": auth_result.get("user", {}),
                    },
                )
                return True
            self.log_step(
                "Authentication",
                "❌ FAILED",
                {"Status Code": response.status_code, "Response": response.text},
            )
            return False

        except Exception as e:
            self.log_step("Authentication", "💥 ERROR", str(e))
            return False

    def verify_file_upload(self) -> bool:
        """Step 2: Verify file upload through orchestrator."""
        print("\n" + "=" * 80)
        print("📄 STEP 2: FILE UPLOAD VERIFICATION")
        print("=" * 80)

        try:
            # Check if test file exists
            file_path = Path(TEST_FILE)
            if not file_path.exists():
                self.log_step("File Upload", "❌ FAILED", f"Test file not found: {TEST_FILE}")
                return False

            file_size = file_path.stat().st_size
            print(f"📂 File: {file_path.name}")
            print(f"📏 Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")

            # Upload through orchestrator API
            upload_url = f"{BASE_URL}/api/v1/documents/"
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, "application/pdf")}
                data = {
                    "title": f"E2E Test - {file_path.name}",
                    "source": "end_to_end_verification",
                    "process_async": "true",
                }

                print(f"📡 Uploading to: {upload_url}")

                response = requests.post(
                    upload_url, files=files, data=data, headers=headers, timeout=30
                )

            if response.status_code == 202:
                upload_result = response.json()
                self.document_id = upload_result.get("document_id")

                self.log_step(
                    "File Upload",
                    "✅ SUCCESS",
                    {
                        "Document ID": self.document_id,
                        "Status": upload_result.get("status"),
                        "Message": upload_result.get("message"),
                    },
                )
                return True
            self.log_step(
                "File Upload",
                "❌ FAILED",
                {"Status Code": response.status_code, "Response": response.text},
            )
            return False

        except Exception as e:
            self.log_step("File Upload", "💥 ERROR", str(e))
            return False

    def verify_database_storage(self) -> bool:
        """Step 3: Verify document stored in database."""
        print("\n" + "=" * 80)
        print("🗄️  STEP 3: DATABASE STORAGE VERIFICATION")
        print("=" * 80)

        try:
            # Check document in database via orchestrator proxy (correct end-to-end path)
            doc_url = f"{BASE_URL}/api/v1/documents/{self.document_id}"
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            print(f"📡 Checking document: {doc_url}")
            response = requests.get(doc_url, headers=headers, timeout=10)

            if response.status_code == 200:
                doc_data = response.json()

                self.log_step(
                    "Database Storage",
                    "✅ SUCCESS",
                    {
                        "Document ID": doc_data.get("id"),
                        "Title": doc_data.get("title"),
                        "Status": doc_data.get("status"),
                        "File Size": doc_data.get("file_size"),
                        "Created At": doc_data.get("created_at"),
                        "Content Compressed": doc_data.get("content_compressed"),
                    },
                )
                return True
            self.log_step(
                "Database Storage",
                "❌ FAILED",
                {"Status Code": response.status_code, "Response": response.text},
            )
            return False

        except Exception as e:
            self.log_step("Database Storage", "💥 ERROR", str(e))
            return False

    def verify_background_processing(self) -> bool:
        """Step 4: Verify background processing through status polling."""
        print("\n" + "=" * 80)
        print("⚙️  STEP 4: BACKGROUND PROCESSING VERIFICATION")
        print("=" * 80)

        try:
            # Use the same approach as demo script - get full document and check status field
            doc_url = f"{BASE_URL}/api/v1/documents/{self.document_id}"
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            start_time = time.time()
            max_wait_time = 120  # 2 minutes max
            poll_interval = 3  # Poll every 3 seconds

            print(f"📡 Document URL: {doc_url}")
            print(f"⏰ Max wait time: {max_wait_time}s")
            print(f"🔄 Poll interval: {poll_interval}s")
            print("\n📊 Status Polling Log:")

            status_history = []

            while (time.time() - start_time) < max_wait_time:
                elapsed = int(time.time() - start_time)

                try:
                    response = requests.get(doc_url, headers=headers, timeout=10)

                    if response.status_code == 200:
                        status_data = response.json()
                        current_status = status_data.get(
                            "status", status_data.get("state", "unknown")
                        )

                        # Log current status
                        chunks_info = ""
                        if "num_chunks" in status_data:
                            chunks_info = f" | Chunks: {status_data['num_chunks']}"
                        elif "chunks_count" in status_data:
                            chunks_info = f" | Chunks: {status_data['chunks_count']}"

                        model_info = ""
                        if "embedding_model" in status_data:
                            model_info = f" | Model: {status_data['embedding_model']}"

                        print(
                            f"   [{elapsed:3d}s] Status: {current_status}{chunks_info}{model_info}"
                        )

                        status_history.append(
                            {"elapsed": elapsed, "status": current_status, "full_data": status_data}
                        )

                        # Check for completion
                        if current_status in ["completed", "processed", "failed"]:
                            final_status = (
                                "✅ SUCCESS"
                                if current_status in ["completed", "processed"]
                                else "❌ FAILED"
                            )

                            self.log_step(
                                "Background Processing",
                                final_status,
                                {
                                    "Final Status": current_status,
                                    "Processing Time": f"{elapsed}s",
                                    "Status History": len(status_history),
                                    "Final Data": status_data,
                                },
                            )
                            return current_status in ["completed", "processed"]

                    else:
                        print(f"   [{elapsed:3d}s] HTTP Error: {response.status_code}")
                        status_history.append(
                            {"elapsed": elapsed, "error": f"HTTP {response.status_code}"}
                        )

                except requests.exceptions.Timeout:
                    print(f"   [{elapsed:3d}s] Request timeout")
                    status_history.append({"elapsed": elapsed, "error": "timeout"})
                except Exception as poll_error:
                    print(f"   [{elapsed:3d}s] Poll error: {poll_error}")
                    status_history.append({"elapsed": elapsed, "error": str(poll_error)})

                time.sleep(poll_interval)

            # Timeout reached
            self.log_step(
                "Background Processing",
                "⏰ TIMEOUT",
                {"Max Wait Time": f"{max_wait_time}s", "Status History": status_history},
            )
            return False

        except Exception as e:
            self.log_step("Background Processing", "💥 ERROR", str(e))
            return False

    def verify_final_state(self) -> bool:
        """Step 5: Verify final processing results."""
        print("\n" + "=" * 80)
        print("🏁 STEP 5: FINAL STATE VERIFICATION")
        print("=" * 80)

        try:
            # Check final document state - same approach as demo script
            doc_url = f"{BASE_URL}/api/v1/documents/{self.document_id}"
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            # Get document details
            print("📡 Fetching final document state...")
            doc_response = requests.get(doc_url, headers=headers, timeout=10)

            results = {}

            if doc_response.status_code == 200:
                doc_data = doc_response.json()
                results["document"] = doc_data

                print("📄 Document Final State:")
                print(f"   ID: {doc_data.get('id')}")
                print(f"   Status: {doc_data.get('status')}")
                print(f"   Chunks: {doc_data.get('num_chunks', 'N/A')}")
                print(f"   Model: {doc_data.get('embedding_model', 'N/A')}")
                print(f"   Size: {doc_data.get('file_size', 'N/A')} bytes")

            # Determine success
            doc_status = doc_data.get("status") if doc_response.status_code == 200 else None
            chunks_count = doc_data.get("num_chunks") if doc_response.status_code == 200 else None

            success = (
                doc_status in ["completed", "processed"]
                and chunks_count is not None
                and chunks_count > 0
            )

            final_status = "✅ SUCCESS" if success else "❌ FAILED"

            self.log_step(
                "Final State",
                final_status,
                {
                    "Document Status": doc_status,
                    "Chunks Created": chunks_count,
                    "Processing Complete": success,
                    "Full Results": results,
                },
            )

            return success

        except Exception as e:
            self.log_step("Final State", "💥 ERROR", str(e))
            return False

    def print_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "=" * 80)
        print("📋 END-TO-END VERIFICATION SUMMARY")
        print("=" * 80)

        total_steps = len(self.verification_results)
        passed_steps = sum(
            1 for result in self.verification_results.values() if result["status"].startswith("✅")
        )

        print(f"📊 Overall Result: {passed_steps}/{total_steps} steps passed")
        print(f"🆔 Document ID: {self.document_id}")

        print("\n📋 Step-by-Step Results:")
        for step, result in self.verification_results.items():
            print(f"   {step}: {result['status']}")

        # Success criteria
        success = passed_steps == total_steps
        overall_status = (
            "🎉 COMPLETE SUCCESS"
            if success
            else "⚠️  PARTIAL SUCCESS" if passed_steps > 0 else "💥 COMPLETE FAILURE"
        )

        print(f"\n🏆 Final Assessment: {overall_status}")

        if not success:
            print("\n🔧 Issues Found:")
            for step, result in self.verification_results.items():
                if not result["status"].startswith("✅"):
                    print(f"   - {step}: {result['status']}")
                    if result.get("details"):
                        print(f"     Details: {result['details']}")


async def main():
    """Run complete end-to-end verification."""
    print("🚀 STARTING END-TO-END DOCUMENT INGESTION VERIFICATION")
    print("=" * 80)

    verifier = IngestionFlowVerifier()

    # Run verification steps
    steps = [
        ("Authentication", verifier.verify_authentication),
        ("File Upload", verifier.verify_file_upload),
        ("Database Storage", verifier.verify_database_storage),
        ("Background Processing", verifier.verify_background_processing),
        ("Final State", verifier.verify_final_state),
    ]

    for step_name, step_func in steps:
        success = step_func()
        if not success:
            print(f"\n💥 STOPPING: {step_name} failed!")
            break

    # Print final summary
    verifier.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
