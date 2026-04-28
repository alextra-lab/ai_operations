"""
Script to download and save sentence-transformer models for the Embedding Service.

This script should be run from the project root directory.
It ensures that the models are downloaded to the correct location (`data/models`)
which is then volume-mounted into the embedding-service container at `/opt/models`.

Requirements:
  - sentence-transformers library installed in the Python environment where this script is run.
    (pip install sentence-transformers)
"""

import argparse
import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Determine project root assuming this script is in project_root/scripts/bootstrap/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MODELS_DIR = PROJECT_ROOT / "data" / "models"

DEFAULT_MODEL_LIST = {
    "all-minilm-l6-v2": "sentence-transformers/all-MiniLM-L6-v2",
    # Add other models here if needed, e.g.:
    # "multi-qa-mpnet-base-dot-v1": "sentence-transformers/multi-qa-mpnet-base-dot-v1",
}


def download_model(model_name_or_path: str, models_dir: Path, local_model_name: str) -> None:
    """
    Downloads a sentence-transformer model to the specified directory.

    Args:
        model_name_or_path (str): The Hugging Face model name (e.g., "sentence-transformers/all-MiniLM-L6-v2")
                                  or path to a local model.
        models_dir (Path): The base directory where models should be saved.
                           A subdirectory with `local_model_name` will be created here.
        local_model_name (str): The name of the subdirectory to save the model in (e.g., "all-minilm-l6-v2").
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.error(
            "SentenceTransformers library not found. Please install it: pip install sentence-transformers"
        )
        return

    save_path = models_dir / local_model_name

    if save_path.exists() and any(save_path.iterdir()):
        logger.info(f"Model '{local_model_name}' already exists at {save_path}. Skipping download.")
        return

    logger.info(f"Downloading model '{model_name_or_path}' to '{save_path}'...")
    try:
        # Create the target directory if it doesn't exist
        save_path.mkdir(parents=True, exist_ok=True)

        # Load the model (this will download it if not cached by sentence-transformers)
        model = SentenceTransformer(model_name_or_path)

        # Save the model to the specified path
        model.save(str(save_path))
        logger.info(
            f"Successfully downloaded and saved model '{model_name_or_path}' to '{save_path}'."
        )
    except Exception as e:
        logger.error(f"Failed to download or save model '{model_name_or_path}': {e}")
        # Clean up partially created directory if download failed
        if save_path.exists() and not any(save_path.iterdir()):
            try:
                os.rmdir(save_path)  # Try to remove if empty
            except OSError:
                logger.warning(
                    f"Could not remove empty directory {save_path} after failed download."
                )
        elif save_path.exists():
            logger.warning(
                f"Directory {save_path} may contain partial download. Please check manually."
            )


def main():
    parser = argparse.ArgumentParser(description="Download sentence-transformer models.")
    parser.add_argument(
        "--model_name",
        type=str,
        help="Specific model to download (e.g., 'all-minilm-l6-v2'). "
        "If not provided, downloads all models in DEFAULT_MODEL_LIST.",
    )
    parser.add_argument(
        "--models_dir",
        type=Path,
        default=DEFAULT_MODELS_DIR,
        help=f"Base directory to save models. Default: {DEFAULT_MODELS_DIR}",
    )

    args = parser.parse_args()

    logger.info(f"Ensuring models directory exists: {args.models_dir}")
    args.models_dir.mkdir(parents=True, exist_ok=True)

    if args.model_name:
        if args.model_name in DEFAULT_MODEL_LIST:
            hf_model_name = DEFAULT_MODEL_LIST[args.model_name]
            download_model(hf_model_name, args.models_dir, args.model_name)
        else:
            logger.warning(
                f"Model name '{args.model_name}' not in predefined list. "
                f"Attempting to download directly. Ensure it's a valid Hugging Face model name."
            )
            # Assuming the user provides a direct Hugging Face name if not in our list
            # The local_model_name will be derived from the full HF path for simplicity here
            local_subdir_name = (
                args.model_name.split("/")[-1] if "/" in args.model_name else args.model_name
            )
            download_model(args.model_name, args.models_dir, local_subdir_name)
    else:
        logger.info("Downloading all predefined models...")
        for local_name, hf_name in DEFAULT_MODEL_LIST.items():
            download_model(hf_name, args.models_dir, local_name)

    logger.info("Model download process finished.")


if __name__ == "__main__":
    main()
