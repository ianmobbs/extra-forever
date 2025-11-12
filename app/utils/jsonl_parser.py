"""
Utility functions for parsing JSONL files.
"""

import base64
import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path


def parse_jsonl[T](file_path: Path, parser: Callable[[dict], T]) -> list[T]:
    """
    Parse a JSONL file and convert each line using the provided parser.

    Args:
        file_path: Path to the JSONL file
        parser: Function to convert a dict to the desired type

    Returns:
        List of parsed objects
    """
    results = []
    with open(file_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            results.append(parser(data))
    return results


def decode_base64_body(encoded: str) -> str:
    """
    Decode a base64-encoded message body.

    Args:
        encoded: Base64-encoded string

    Returns:
        Decoded UTF-8 string
    """
    return base64.b64decode(encoded).decode("utf-8", errors="replace")


def parse_iso_date(date_str: str) -> datetime:
    """
    Parse an ISO-8601 date string, handling the 'Z' timezone suffix.

    Args:
        date_str: ISO-8601 formatted date string

    Returns:
        datetime object
    """
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
