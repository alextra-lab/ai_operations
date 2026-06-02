#!/usr/bin/env python3
"""
Utility script to pre-stage the models used by the native llm-guard-svc scanners.

Per ADR-073 (D1/D2), the three ONNX classifiers are staged ONNX-only — PyTorch
weights (``*.safetensors``, ``pytorch_model.bin``) and training artifacts are
excluded via ``ignore_patterns`` since they run with ``use_onnx=True``. The GLiNER
PII model (LLG-04) runs eager torch and therefore keeps its PyTorch weights via
``MODEL_IGNORE_OVERRIDES``, and its backbone tokenizer
(``microsoft/mdeberta-v3-base``) is staged into the HF cache
(``<output_dir>/hub``) by ``stage_gliner_backbone_tokenizer`` so GLiNER loads
offline (it ships no tokenizer of its own).

Each model is staged into the flat ``org-model`` directory the native scanners
resolve via ``LLMGuardConfig``; GLiNER keeps an id-only canonical directory
(``gliner_multi_pii-v1``). The cc-by-nc distilbert PII model is no longer staged
(removed in the LLG-04 finale — PII is now Presidio + GLiNER).

Example usage:
    python download_llm_guard_models.py --output-dir ../data/llm-guard-models
"""

import argparse
import importlib
import logging
import os
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

# Map each HuggingFace repo id to the on-disk directory name that
# the native scanners expect (resolved via LLMGuardConfig *_model_dir). The three
# ONNX classifiers use the flat org-model name; GLiNER keeps an id-only name.
# NOTE (LLG-04 finale): the cc-by-nc distilbert PII model was REMOVED — the native
# anonymize engine uses Presidio + GLiNER (Apache-2.0) instead.
DEFAULT_MODELS: dict[str, str] = {
    "madhurjindal/autonlp-Gibberish-Detector-492513457": (
        "madhurjindal-autonlp-Gibberish-Detector-492513457"
    ),
    "protectai/xlm-roberta-base-language-detection-onnx": (
        "protectai-xlm-roberta-base-language-detection-onnx"
    ),
    "protectai/deberta-v3-small-prompt-injection-v2": (
        "protectai-deberta-v3-small-prompt-injection-v2"
    ),
    # GLiNER PII NER (Apache-2.0), used by the native anonymize engine. Unlike the
    # three ONNX classifiers it runs eager torch, so its PyTorch weights must be
    # kept (see MODEL_IGNORE_OVERRIDES); its backbone tokenizer is staged
    # separately (see stage_gliner_backbone_tokenizer). Id-only canonical dir,
    # matching LLMGuardConfig.gliner_model_dir.
    "urchade/gliner_multi_pii-v1": "gliner_multi_pii-v1",
}

# PyTorch weights and training artifacts that are never loaded at runtime.
# ``model_optimized.onnx`` is also excluded per ADR-073 D4 (same size as the full
# model, no benefit without hardware-specific optimizations); the service loads
# ``model_quantized.onnx`` for language detection.
IGNORE_PATTERNS = [
    "*.safetensors",
    "pytorch_model.bin",
    "*.msgpack",
    "flax_model.msgpack",
    "training_args.bin",
    "trainer_state.json",
    "*_results.json",
    "sample_input.pkl",
    "model_optimized.onnx",
]

# GLiNER runs eager torch (no ONNX export — LLG-04 step 3), so it needs its
# PyTorch weights and gliner_config.json kept; only training artifacts are
# dropped. This override replaces the ONNX-only IGNORE_PATTERNS for this repo.
GLINER_IGNORE_PATTERNS = [
    "*.msgpack",
    "flax_model.msgpack",
    "training_args.bin",
    "trainer_state.json",
    "*_results.json",
    "*.onnx",
    "onnx/*",
]

# Per-repo ignore overrides; repos not listed use IGNORE_PATTERNS.
MODEL_IGNORE_OVERRIDES: dict[str, list[str]] = {
    "urchade/gliner_multi_pii-v1": GLINER_IGNORE_PATTERNS,
}

# GLiNER's repo ships NO tokenizer: it loads its backbone's tokenizer at runtime
# from the id in gliner_config.json. Without this staged, the native anonymize
# engine cannot load GLiNER with local_files_only=True (offline). We stage just
# the backbone TOKENIZER (not its ~560MB encoder weights, which GLiNER does not
# need — its own weights carry the encoder) into the HF cache. HF_HOME=/app/models
# in the container, so the cache lives at <models_dir>/hub.
GLINER_BACKBONE_REPO = "microsoft/mdeberta-v3-base"
GLINER_BACKBONE_TOKENIZER_PATTERNS = [
    "config.json",
    "tokenizer_config.json",
    "spm.model",
    "special_tokens_map.json",
    "added_tokens.json",
    "tokenizer.json",
    "vocab.txt",
]


def stage_gliner_backbone_tokenizer(output_dir: str, hf_token: str | None = None) -> None:
    """Stage the GLiNER backbone tokenizer into the HF cache under ``output_dir/hub``."""
    cache_dir = os.path.join(output_dir, "hub")
    logger.info(f"Staging GLiNER backbone tokenizer {GLINER_BACKBONE_REPO} -> {cache_dir}")
    snapshot_download(
        repo_id=GLINER_BACKBONE_REPO,
        cache_dir=cache_dir,
        allow_patterns=GLINER_BACKBONE_TOKENIZER_PATTERNS,
        token=hf_token,
    )


def check_dependencies() -> bool:
    """
    Check that huggingface_hub is importable.

    torch/transformers are not required to download ONNX files; they are reported
    for informational purposes only when present.

    Returns:
        bool: True if huggingface_hub is available, False otherwise.
    """
    try:
        importlib.import_module("huggingface_hub")
    except ImportError as e:
        logger.error(f"Missing required dependency: {e}")
        logger.error("Please install it with: pip install huggingface_hub")
        return False

    for optional in ("transformers", "torch"):
        try:
            module = importlib.import_module(optional)
            logger.info(f"Using {optional} version: {module.__version__}")
        except ImportError:
            logger.debug(f"Optional package {optional} not installed (not needed for download)")

    return True


def download_models(
    output_dir: str,
    models: dict[str, str],
    max_retries: int = 3,
    hf_token: str | None = None,
) -> bool:
    """
    Download and cache the ONNX model files for LLM-Guard.

    Args:
        output_dir: Directory to save models.
        models: Mapping of HuggingFace repo id -> target directory name.
        max_retries: Maximum number of retry attempts per model.
        hf_token: Optional HuggingFace token for gated models.

    Returns:
        bool: True if all models downloaded successfully, False otherwise.
    """
    if not check_dependencies():
        return False

    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Models will be saved to: {output_dir}")

    # Note: we intentionally do NOT set HF_HOME to output_dir. snapshot_download
    # writes the resolved files directly into local_dir; pointing the HF cache at
    # output_dir would additionally litter the mount with a xet/ cache directory.

    success = True

    for repo_id, target_dir in models.items():
        model_success = False
        model_path = os.path.join(output_dir, target_dir)

        ignore_patterns = MODEL_IGNORE_OVERRIDES.get(repo_id, IGNORE_PATTERNS)
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Downloading {repo_id} -> {model_path} "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                os.makedirs(model_path, exist_ok=True)
                snapshot_download(
                    repo_id=repo_id,
                    local_dir=model_path,
                    local_dir_use_symlinks="auto",
                    ignore_patterns=ignore_patterns,
                    token=hf_token,
                )
                logger.info(f"Successfully downloaded {repo_id} to {model_path}")
                model_success = True
                break
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e!s}")
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

        if not model_success:
            logger.error(f"Failed to download {repo_id} after {max_retries} attempts")
            success = False

    # If GLiNER was staged, also stage its backbone tokenizer (offline requirement).
    if success and any("gliner" in target for target in models.values()):
        try:
            stage_gliner_backbone_tokenizer(output_dir, hf_token)
        except Exception as e:
            logger.error(f"Failed to stage GLiNER backbone tokenizer: {e!s}")
            success = False

    if success:
        logger.info("All models downloaded successfully")
    else:
        logger.warning("Some models failed to download")

    return success


def main() -> None:
    """Parse arguments and download the LLM-Guard ONNX models."""
    parser = argparse.ArgumentParser(
        description="Download ONNX models used by LLM-Guard for offline use"
    )
    parser.add_argument(
        "--output-dir",
        default="./models",
        help="Directory to save downloaded models (default: ./models)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help=(
            "HuggingFace repo ids to download. When omitted, the four default "
            "LLM-Guard models are downloaded. Overrides use the flat org-model "
            "directory naming convention."
        ),
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retry attempts per model (default: 3)",
    )
    parser.add_argument("--hf-token", help="Hugging Face API token for downloading gated models")
    args = parser.parse_args()

    if args.models:
        # Derive flat org-model directory names for explicitly requested repos.
        models = {repo_id: repo_id.replace("/", "-") for repo_id in args.models}
    else:
        models = DEFAULT_MODELS

    success = download_models(args.output_dir, models, args.max_retries, args.hf_token)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
