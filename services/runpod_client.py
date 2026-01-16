import os
import base64
import requests
from typing import Optional, Dict, Any

RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID", "bfarkaz0uwuhcn")
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_URL = os.getenv(
    "RUNPOD_ENDPOINT_URL",
    f"https://api.runpod.ai/v1/{RUNPOD_ENDPOINT_ID}/sync-invoke"
)

def _extract_text_from_response(resp_json: Dict[str, Any]) -> Optional[str]:
    if resp_json is None:
        return None
    if isinstance(resp_json, dict):
        if "output" in resp_json and isinstance(resp_json["output"], str):
            return resp_json["output"]
        if "output" in resp_json and isinstance(resp_json["output"], dict):
            out = resp_json["output"]
            for k in ("text", "transcript", "transcription"):
                if k in out and isinstance(out[k], str):
                    return out[k]
        for k in ("text", "transcript", "transcription"):
            if k in resp_json and isinstance(resp_json[k], str):
                return resp_json[k]
    return None

def transcribe_file(file_path: str, language: str = "en", timeout: int = 600) -> Dict[str, Any]:
    """
    Send audio file to Runpod sync-invoke and return the parsed response.
    Returns a dict: {"raw": <full-json>, "text": <extracted-text-or-none>}
    Raises requests.HTTPError on non-2xx response.
    """
    if not RUNPOD_API_KEY:
        raise RuntimeError("RUNPOD_API_KEY environment variable is not set")

    with open(file_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "input": {
            "audio_base64": audio_b64,
            "language": language,
            "task": "transcribe"
        }
    }

    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }

    resp = requests.post(RUNPOD_ENDPOINT_URL, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    json_resp = resp.json()
    text = _extract_text_from_response(json_resp)
    return {"raw": json_resp, "text": text}
