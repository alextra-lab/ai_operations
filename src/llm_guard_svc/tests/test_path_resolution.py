"""
Test script to verify model path resolution works correctly.
"""

import os
import sys

# Add the parent directory to the path so we can import from the app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from guard import get_model_path, get_models_base_path, verify_model_path


def test_path_resolution():
    """Test that path resolution finds the correct models."""

    print("🔍 Testing model path resolution...")

    # Test base path resolution
    base_path = get_models_base_path()
    print(f"📁 Base path resolved to: {base_path}")
    print(f"📁 Base path exists: {os.path.exists(base_path)}")

    if os.path.exists(base_path):
        print("📁 Contents of base path:")
        try:
            contents = os.listdir(base_path)
            for item in sorted(contents):
                item_path = os.path.join(base_path, item)
                if os.path.isdir(item_path):
                    print(f"   📂 {item}/")
                else:
                    print(f"   📄 {item}")
        except Exception as e:
            print(f"   ❌ Error listing contents: {e}")

    # Test individual model paths
    models_to_test = [
        "distilbert_finetuned_ai4privacy_v2",
        "madhurjindal-autonlp-Gibberish-Detector-492513457",
        "protectai-xlm-roberta-base-language-detection-onnx",
        "protectai-deberta-v3-small-prompt-injection-v2",
    ]

    print("\n🔍 Testing individual model paths...")
    for model_name in models_to_test:
        model_path = get_model_path(model_name)
        exists = verify_model_path(model_path, model_name)
        status = "✅" if exists else "❌"
        print(f"   {status} {model_name}")
        print(f"      Path: {model_path}")
        print(f"      Exists: {os.path.exists(model_path)}")

        if os.path.exists(model_path):
            try:
                files = os.listdir(model_path)
                config_files = [f for f in files if f.endswith(".json")]
                model_files = [f for f in files if f.endswith((".bin", ".safetensors", ".onnx"))]
                print(f"      Config files: {config_files}")
                print(f"      Model files: {len(model_files)} files")

                # Check for onnx subdirectory
                onnx_path = os.path.join(model_path, "onnx")
                if os.path.exists(onnx_path):
                    print("      ONNX directory: ✅ exists")
                    onnx_files = os.listdir(onnx_path)
                    onnx_model_files = [f for f in onnx_files if f.endswith(".onnx")]
                    print(f"      ONNX model files: {len(onnx_model_files)} files")
                else:
                    print("      ONNX directory: ❌ not found")
            except Exception as e:
                print(f"      ❌ Error examining model: {e}")
        print()


if __name__ == "__main__":
    test_path_resolution()
