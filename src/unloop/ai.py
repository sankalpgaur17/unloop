"""Ask a local Ollama model to rewrite slow code."""

import json
import re
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen2.5-coder:3b"

SYSTEM_PROMPT = (
    "You optimize slow pandas and NumPy code. "
    "Rewrite the user's code so it runs faster using vectorized operations. "
    "Follow these rules strictly:\n"
    "1. The results must be exactly the same, including for rows with missing values (NaN). "
    "Remember that any comparison with NaN is False, so in if/else logic, NaN rows go to the else branch.\n"
    "2. For if/else logic, use np.where or np.select, so that every row gets a value.\n"
    "3. Keep the same variable names and column names.\n"
    "4. Reply with only the rewritten Python code in one code block, and no explanation."
)


def ask_ai(code, model=DEFAULT_MODEL, timeout=120, feedback=None):
    """Send code to the local model and return its rewritten code, or None."""
    prompt = code
    if feedback:
        prompt = f"{code}\n\n{feedback}\nPlease write a corrected version."
    payload = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            answer = json.loads(response.read())["response"]
    except (OSError, ValueError, KeyError):
        return None
    return add_missing_imports(extract_code(answer))


def extract_code(answer):
    """Pull the code out of a reply that may be wrapped in ``` fences."""
    match = re.search(r"```(?:python)?\s*\n(.*?)```", answer, re.DOTALL)
    if match:
        return match.group(1).strip()
    return answer.strip()


def add_missing_imports(code):
    """Add numpy or pandas imports if the code uses them without importing."""
    if "np." in code and "import numpy" not in code:
        code = "import numpy as np\n" + code
    if "pd." in code and "import pandas" not in code:
        code = "import pandas as pd\n" + code
    return code