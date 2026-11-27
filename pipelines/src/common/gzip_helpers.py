import os
import gzip
import json
from pathlib import Path

def write_gzip_json(local_path: str, data: dict | list, verbose: bool = False):
    """Write data to gzipped JSON file

    Args:
        local_path: Local file path (should end with .json.gz)
        data: Dict or list to serialize
        verbose: Print write progress
    """
    # Create parent directory if needed
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"Writing {local_path}")

    json_str = json.dumps(data, separators=(',', ':'))
    with gzip.open(local_path, 'wt', encoding='utf-8') as f:
        f.write(json_str)


def read_gzip_json(local_path: str, verbose: bool = False) -> dict | list | None:
    """Read gzipped JSON file from local disk

    Args:
        local_path: Local file path
        verbose: Print read progress

    Returns:
        Parsed JSON, or None if file doesn't exist
    """
    if not os.path.exists(local_path):
        if verbose:
            print(f"Local file not found: {local_path}")
        return None

    if verbose:
        print(f"Reading {local_path}")

    with gzip.open(local_path, 'rt', encoding='utf-8') as f:
        return json.load(f)
