"""Remember verified AI rewrites so the same code never needs the AI twice."""

import hashlib
import json
from pathlib import Path

CACHE_FILE = Path.home() / ".unloop" / "cache.json"


def cache_key(code):
    """Turn code into a short fingerprint used as its name in the cache."""
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()


def load_cache():
    """Read the cache file, or return an empty cache if it doesn't exist yet."""
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def get_cached(code):
    """Return the saved rewrite for this code, or None."""
    return load_cache().get(cache_key(code))


def save_to_cache(code, new_code):
    """Save a verified rewrite for this code."""
    cache = load_cache()
    cache[cache_key(code)] = new_code
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except OSError:
        pass