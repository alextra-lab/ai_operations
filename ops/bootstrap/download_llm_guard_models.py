#!/usr/bin/env python3
"""
Utility script to pre-download models used by LLM-Guard.

This script downloads and caches Hugging Face models to a local directory,
making them available for offline use within containers.

Example usage:
    python download_models.py --output-dir ./models
"""

import argparse
import importlib  # Added import
import logging
import os
import shutil  # Added import
import sys
import time

from huggingface_hub import snapshot_download

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("model-downloader")


def check_dependencies():
    """
    Check if required dependencies are installed.

    Returns:
        bool: True if dependencies are installed, False otherwise
    """
    try:
        torch_module = importlib.import_module("torch")
        transformers_module = importlib.import_module("transformers")

        logger.info(f"Using transformers version: {transformers_module.__version__}")
        logger.info(f"Using torch version: {torch_module.__version__}")
        return True
    except ImportError as e:
        logger.error(f"Missing dependencies: {e}")
        logger.error("Please install required packages:")
        logger.error("pip install transformers[torch] or torch")  # Updated message slightly
        return False


def download_models(
    output_dir: str, models: list, max_retries: int = 3, hf_token: str | None = None
):
    """
    Download and cache Hugging Face models.

    Args:
        output_dir: Directory to save models
        models: List of model identifiers to download
        max_retries: Maximum number of retry attempts

    Returns:
        bool: True if successful, False otherwise
    """
    # Check dependencies first
    if not check_dependencies():
        return False

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Models will be saved to: {output_dir}")

    # Set environment variables to use our cache location
    os.environ["TRANSFORMERS_CACHE"] = output_dir
    os.environ["HF_HOME"] = output_dir

    success = True

    # Download each model
    for model_name in models:
        model_success = False

        # Try with multiple retries
        for attempt in range(max_retries):
            try:
                logger.info(f"Downloading model: {model_name} (Attempt {attempt+1}/{max_retries})")

                # Create model-specific directories
                model_dir_flat = os.path.join(output_dir, model_name.replace("/", "-"))
                os.makedirs(model_dir_flat, exist_ok=True)

                logger.info(f"Downloading all files for {model_name} to {model_dir_flat}")
                snapshot_download(
                    repo_id=model_name,
                    local_dir=model_dir_flat,
                    local_dir_use_symlinks=False,
                    token=hf_token,
                    # Using HF_HOME for cache, which is set to output_dir
                )
                logger.info(f"Successfully downloaded {model_name} to {model_dir_flat}")

                # Also ensure the model is available at the path structure LLM-Guard expects.
                # LLM-Guard typically expects /app/models/MODEL_ID_PART/
                # So, if model_name is "Org/ModelId", we target "output_dir/ModelId/"
                if "/" in model_name:
                    _, model_id_part = model_name.split("/", 1)
                else:
                    model_id_part = (
                        model_name  # Should ideally not happen for HF models if org is standard
                    )

                llm_guard_expected_path = os.path.join(output_dir, model_id_part)

                # snapshot_download creates the directory, ensure parent output_dir exists (already done)
                logger.info(
                    f"Ensuring model {model_name} is also available at LLM-Guard expected path: {llm_guard_expected_path}"
                )
                snapshot_download(
                    repo_id=model_name,
                    local_dir=llm_guard_expected_path,
                    local_dir_use_symlinks=False,  # Using False for better cross-system/Docker compatibility
                    token=hf_token,
                    # Using HF_HOME (set to output_dir) for caching, so this effectively creates another "view"
                )
                logger.info(
                    f"Successfully ensured {model_name} is available at {llm_guard_expected_path}"
                )

                # Post-processing for specific ONNX models to make their 'onnx' subfolder self-contained
                onnx_models_to_postprocess = [
                    "protectai/deberta-v3-small-prompt-injection-v2",
                    "madhurjindal/autonlp-Gibberish-Detector-492513457",  # Added for ONNX processing
                    "protectai/xlm-roberta-base-language-detection-onnx",
                ]

                if model_name in onnx_models_to_postprocess:
                    logger.info(f"Post-processing ONNX config for {model_name}...")
                    # model_dir_flat is where the full model including config.json was downloaded
                    # e.g., output_dir/protectai-deberta-v3-small-prompt-injection-v2
                    source_config_path = model_dir_flat  # This is the root of the downloaded model
                    target_onnx_config_path = os.path.join(model_dir_flat, "onnx")

                    if os.path.isdir(target_onnx_config_path):  # Ensure the onnx subdir exists
                        config_files_to_copy = [
                            "config.json",
                            "tokenizer.json",
                            "special_tokens_map.json",
                            "tokenizer_config.json",
                            # Add other files if optimum needs them e.g. vocab.txt, merges.txt for some tokenizers
                            "vocab.txt",
                            "merges.txt",
                            "spm.model",
                        ]
                        for config_file in config_files_to_copy:
                            source_file = os.path.join(source_config_path, config_file)
                            target_file = os.path.join(target_onnx_config_path, config_file)
                            if os.path.exists(source_file):
                                try:
                                    shutil.copy2(source_file, target_file)
                                    logger.info(
                                        f"Copied {config_file} to {target_onnx_config_path}"
                                    )
                                except Exception as copy_e:
                                    logger.error(
                                        f"Failed to copy {config_file} for {model_name} to {target_onnx_config_path}: {copy_e}"
                                    )
                            # else:
                            # It's okay if some optional files like vocab.txt don't exist for all models
                            # logger.warning(f"Config file {config_file} not found at {source_file} for {model_name}, skipping.")
                    else:
                        logger.warning(
                            f"ONNX subdirectory not found at {target_onnx_config_path} for {model_name}, skipping config copy. This might be okay if the model is not ONNX or ONNX files are at root."
                        )

                logger.info(f"Successfully processed model: {model_name}")
                model_success = True
                break

            except Exception as e:
                logger.error(f"Attempt {attempt+1} failed: {e!s}")
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

        if not model_success:
            logger.error(f"Failed to download model {model_name} after {max_retries} attempts")
            success = False

    if success:
        logger.info("All models downloaded successfully")
    else:
        logger.warning("Some models failed to download")

    return success


def main():
    """Main function to parse arguments and download models."""
    parser = argparse.ArgumentParser(description="Download Hugging Face models for offline use")
    parser.add_argument(
        "--output-dir",
        default="./models",
        help="Directory to save downloaded models (default: ./models)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=[
            "Isotonic/distilbert_finetuned_ai4privacy_v2",  # PII (non-ONNX, downloaded)
            "madhurjindal/autonlp-Gibberish-Detector-492513457",  # Using this for Gibberish (ONNX)
            # "Emilio407/autonlp-Gibberish-Detector-492513457-8bit", # Removed 8-bit version
            "protectai/xlm-roberta-base-language-detection-onnx",  # Language (ONNX, downloaded)
            "protectai/deberta-v3-small-prompt-injection-v2",  # Prompt Injection (ONNX, downloaded)
        ],
        help="Model names to download. Default list contains successfully downloaded smaller/faster models.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retry attempts per model (default: 3)",
    )
    parser.add_argument("--hf-token", help="Hugging Face API token for downloading gated models")
    args = parser.parse_args()

    success = download_models(args.output_dir, args.models, args.max_retries, args.hf_token)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
