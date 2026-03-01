import hashlib
import json
import logging
import os

logger = logging.getLogger(__name__)


def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def load_email_meta(path: str) -> dict:
    meta_path = path + ".meta.json"
    if not os.path.exists(meta_path):
        return {}
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Failed to read metadata %s: %s", meta_path, exc)
        return {}


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)
