#!/usr/bin/env python3
"""
Minimal fallback for StashPluginHelper so the plugin can run without the external helper.

This implements:
- Reading JSON input from stdin.
- Accessing settings via Setting().
- Basic logging to stderr with level prefixes understood by Stash.
- Minimal GraphQL client for find_scene() and get_all_scenes().
"""

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


def _read_stdin_json(maxbytes: Optional[int]) -> Dict[str, Any]:
    try:
        data = sys.stdin.buffer.read() if maxbytes is None else sys.stdin.buffer.read(maxbytes)
        if not data:
            return {}
        return json.loads(data.decode("utf-8", errors="ignore"))
    except Exception:
        return {}


class StashPluginHelper:
    def __init__(self, settings: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None, maxbytes: Optional[int] = None):
        self.settings = settings or {}
        self.config = config or {}
        self.maxbytes = maxbytes
        self.JSON_INPUT: Dict[str, Any] = _read_stdin_json(maxbytes)

        # Try to detect a task name similarly to the real helper
        args = self.JSON_INPUT.get("args", {}) if isinstance(self.JSON_INPUT.get("args"), dict) else {}
        task = self.JSON_INPUT.get("task", {}) if isinstance(self.JSON_INPUT.get("task"), dict) else {}
        self.PLUGIN_TASK_NAME = task.get("name") or args.get("mode") or ""

    # Settings come from JSON_INPUT.settings (preferred), falling back to ctor settings and args
    def Setting(self, name: str, default: Any = None) -> Any:
        src = self.JSON_INPUT.get("settings", {})
        if isinstance(src, dict) and name in src:
            return src.get(name, default)
        args = self.JSON_INPUT.get("args", {})
        if isinstance(args, dict) and name in args:
            return args.get(name, default)
        return self.settings.get(name, default)

    # ---- Logging (stderr) using Stash plugin log level prefixes ----
    def _log(self, level_char: str, *args: Any) -> None:
        try:
            msg = " ".join(str(a) for a in args)
            sys.stderr.write(f"[{level_char}] {msg}\n")
            sys.stderr.flush()
        except Exception:
            pass

    def Trace(self, *args: Any) -> None:
        self._log("T", *args)

    def Log(self, *args: Any) -> None:
        self._log("I", *args)

    def Warn(self, *args: Any) -> None:
        self._log("W", *args)

    def Error(self, *args: Any) -> None:
        self._log("E", *args)

    # ---- GraphQL helpers ----
    def _api_key(self) -> Optional[str]:
        sc = self.JSON_INPUT.get("server_connection") or self.JSON_INPUT.get("serverConnection") or {}
        if isinstance(sc, dict):
            return sc.get("api_key") or sc.get("apiKey") or sc.get("ApiKey")
        return os.getenv("STASH_API_KEY")

    def _graphql_url(self) -> str:
        # Prefer explicit GraphQL URL if present
        sc = self.JSON_INPUT.get("server_connection") or self.JSON_INPUT.get("serverConnection") or {}
        url = None
        if isinstance(sc, dict):
            url = sc.get("graphql_endpoint") or sc.get("graphqlUrl") or sc.get("url")
            if not url:
                scheme = sc.get("scheme") or sc.get("Scheme") or "http"
                endpoint = sc.get("endpoint") or sc.get("Endpoint") or sc.get("host")
                if endpoint:
                    url = f"{scheme}://{endpoint}/graphql"
        if not url:
            url = os.getenv("STASH_GRAPHQL_URL")
        if not url:
            base = os.getenv("STASH_URL")
            if base:
                url = base.rstrip("/") + "/graphql"
        if not url:
            url = "http://localhost:9999/graphql"
        return url

    def _graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        url = self._graphql_url()
        headers = {"Content-Type": "application/json"}
        api_key = self._api_key()
        if api_key:
            headers["ApiKey"] = api_key
            headers["Authorization"] = f"apikey {api_key}"

        payload = {"query": query, "variables": variables or {}}
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read()
                if not body:
                    self.Warn("Empty GraphQL response")
                    return None
                j = json.loads(body.decode("utf-8", errors="ignore"))
                if isinstance(j, dict) and j.get("errors"):
                    self.Error("GraphQL errors:", j.get("errors"))
                    return None
                return j
        except urllib.error.HTTPError as e:
            self.Error("HTTP error calling GraphQL:", e, "body=", getattr(e, "read", lambda: b"")().decode("utf-8", errors="ignore"))
        except urllib.error.URLError as e:
            self.Error("URL error calling GraphQL:", e)
        except Exception as e:
            self.Error("Unexpected error calling GraphQL:", e)
        return None

    def find_scene(self, scene_id: int, fragment: str) -> Optional[Dict[str, Any]]:
        # Allow fragments without braces
        frag = fragment.strip()
        if frag.startswith("{") and frag.endswith("}"):
            frag = frag[1:-1]
        query = f"query($id: ID!) {{ findScene(id: $id) {{ {frag} }} }}"
        resp = self._graphql(query, {"id": str(scene_id)})
        if not resp:
            return None
        data = resp.get("data", {})
        return data.get("findScene") if isinstance(data, dict) else None

    def get_all_scenes(self) -> Dict[str, Any]:
        # Minimal fields needed by the plugin
        query = "query { allScenes { id updated_at } }"
        resp = self._graphql(query)
        if not resp:
            return {"allScenes": []}
        data = resp.get("data", {})
        scenes = data.get("allScenes") if isinstance(data, dict) else []
        return {"allScenes": scenes if isinstance(scenes, list) else []}


# Simple placeholder to satisfy imports where present
taskQueue = None
