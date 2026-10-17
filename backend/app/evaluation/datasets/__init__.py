"""
R5 Operational Intelligence Platform - Phase 20: Controlled Synthetic Benchmark Datasets
All datasets in this package are explicitly labeled as synthetic evaluation data.
Used exclusively for reproducible regression testing and algorithmic verification.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List

DATASET_DIR = Path(__file__).parent


def load_dataset(filename: str) -> Dict[str, Any]:
    """Load and parse a synthetic dataset by filename."""
    path = DATASET_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Synthetic dataset '{filename}' not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def list_available_datasets() -> List[Dict[str, Any]]:
    """Enumerate all available synthetic datasets with their metadata."""
    manifest = []
    for f in sorted(os.listdir(DATASET_DIR)):
        if f.endswith(".json") and f.startswith("synthetic_"):
            try:
                data = load_dataset(f)
                meta = data.get("_metadata", {})
                cases = data.get("cases", [])
                manifest.append({
                    "filename": f,
                    "datasetName": meta.get("datasetName", f),
                    "dimension": meta.get("dimension", "UNKNOWN"),
                    "sampleCount": len(cases),
                    "synthetic": meta.get("synthetic", True),
                    "label": meta.get("label", "CONTROLLED_SYNTHETIC_EVALUATION_DATA"),
                    "disclaimer": meta.get("disclaimer", "SYNTHETIC BENCHMARK DATA")
                })
            except Exception:
                pass
    return manifest
