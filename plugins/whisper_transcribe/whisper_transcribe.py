#!/usr/bin/env python3
"""
Whisper Transcribe Plugin

This plugin integrates with a whisper.cpp server
to automatically generate subtitles (SRT) for video files when a scene is updated.
It follows the same structure as the example RenameFile plugin.
"""

import os
import sys
import traceback
import subprocess
import tempfile
import json
import urllib.request
import urllib.error

# Stash helper classes (same as in the RenameFile example)
try:
    from StashPluginHelper import StashPluginHelper, taskQueue
except Exception:
    # Fallback to local minimal helper if StashPluginHelper isn't available
    from stash_helper_fallback import StashPluginHelper, taskQueue  # type: ignore

# Self-contained transcription logic (no external imports).
def _post_whisper_audio(wav_path: str, server_url: str, translate: bool) -> str:
    try:
        import requests  # type: ignore
    except Exception:
        requests = None

    if requests is not None:
        with open(wav_path, "rb") as audio_file:
            files = {"file": (os.path.basename(wav_path), audio_file, "audio/wav")}
            data = {"response_format": "srt"}
            if translate:
                data["translate"] = "true"
            try:
                resp = requests.post(server_url, files=files, data=data, timeout=3600)
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                raise RuntimeError(f"Error sending request to whisper server at {server_url}. Is it running and reachable? {e}") from e
    else:
        boundary = "----WhisperBoundary7MA4YWxkTrZu0gW"

        def _encode_part(name: str, value: str) -> bytes:
            return (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")

        with open(wav_path, "rb") as f:
            file_content = f.read()

        parts = []
        parts.append(_encode_part("response_format", "srt"))
        if translate:
            parts.append(_encode_part("translate", "true"))
        file_header = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(wav_path)}"\r\n'
            f"Content-Type: audio/wav\r\n\r\n"
        ).encode("utf-8")
        parts.append(file_header)
        parts.append(file_content)
        parts.append(b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode("utf-8"))
        body = b"".join(parts)

        req = urllib.request.Request(
            server_url,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=3600) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else str(e)
            raise RuntimeError(f"HTTP error from whisper server: {e.code} {e.reason}. {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network error contacting whisper server at {server_url}: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error contacting whisper server: {e}") from e


def _check_whisper_server(server_url: str, timeout: float = 5.0) -> None:
    """
    Best-effort connectivity check. We only verify that a TCP connection can be made.
    Any HTTP status code is considered "reachable".
    """
    try:
        import requests  # type: ignore
    except Exception:
        requests = None

    if requests is not None:
        try:
            # OPTIONS is commonly allowed; even a 4xx/5xx means the server is reachable.
            requests.options(server_url, timeout=timeout)
        except Exception as e:
            raise RuntimeError(
                f"Cannot reach whisper server at {server_url}. "
                "Configure the 'Whisper Server URL' plugin setting or set WHISPER_SERVER_URL. "
                f"Underlying error: {e}"
            ) from e
    else:
        req = urllib.request.Request(server_url, method="OPTIONS")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as _:
                return
        except urllib.error.HTTPError:
            # Server reachable (wrong method) – that's sufficient to proceed.
            return
        except Exception as e:
            raise RuntimeError(
                f"Cannot reach whisper server at {server_url}. "
                "Configure the 'Whisper Server URL' plugin setting or set WHISPER_SERVER_URL. "
                f"Underlying error: {e}"
            ) from e


def transcribe_video(video_path: str, translate: bool = False, server_url: str = "http://localhost:9191/inference") -> None:
    """
    Transcribes a video file using a whisper.cpp server. Produces an .srt next to the video.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at '{video_path}'")

    # Verify server reachability before doing any work.
    _check_whisper_server(server_url)

    tmp_wav_path = None
    try:
        # 1. Extract audio to 16kHz mono WAV using ffmpeg
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav_file:
            tmp_wav_path = tmp_wav_file.name

        command = [
            "ffmpeg",
            "-i", video_path,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            "-y",
            "-loglevel", "error",
            tmp_wav_path,
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True, errors="ignore")
        except FileNotFoundError:
            raise RuntimeError("'ffmpeg' not found. Please ensure it is installed and in PATH.")
        except subprocess.CalledProcessError as e:
            stderr = getattr(e, "stderr", "") or ""
            raise RuntimeError(f"ffmpeg failed to extract audio: {stderr}") from e

        # 2. Send audio to whisper.cpp server
        response_text = _post_whisper_audio(tmp_wav_path, server_url, translate)

    finally:
        # Clean up temporary WAV file
        if tmp_wav_path and os.path.exists(tmp_wav_path):
            try:
                os.remove(tmp_wav_path)
            except Exception:
                pass

    # 3. Save response to SRT file
    srt_path = os.path.splitext(video_path)[0] + ".srt"
    try:
        with open(srt_path, "w", encoding="utf-8") as srt_file:
            srt_file.write(response_text)
    except OSError as e:
        raise RuntimeError(f"Failed to write SRT file '{srt_path}': {e}") from e

# ----------------------------------------------------------------------
# Minimal plugin settings – can be extended via a settings file if needed.
# ----------------------------------------------------------------------
settings = {
    "zzdebugTracing": False,
    "zzdryRun": False,
}
# Load optional configuration (currently empty, but kept for parity with RenameFile)
try:
    from whisper_transcribe_settings import config  # type: ignore
except Exception:
    config = {}

stash = StashPluginHelper(
    settings=settings,
    config=config,
    maxbytes=10 * 1024 * 1024,
)

# Read UI settings (with sane defaults)
server_url = stash.Setting("serverUrl", os.getenv("WHISPER_SERVER_URL", "http://127.0.0.1:9191/inference"))
translate_to_english = stash.Setting("translateToEnglish", False)
dry_run = stash.Setting("zzdryRun", False)

# Detect if invoked by a Scene.Update.Post hook and capture scene ID if provided
inputToUpdateScenePost = False
hookSceneID = None
try:
    hook_ctx = stash.JSON_INPUT.get("args", {}).get("hookContext") if stash.JSON_INPUT else None
    if hook_ctx is not None:
        # When input is None, treat as no-op. Otherwise mark as hook trigger.
        if hook_ctx.get("input") is not None:
            inputToUpdateScenePost = True
            if hook_ctx.get("id") is not None:
                hookSceneID = int(hook_ctx.get("id"))
except Exception:
    # best-effort only
    pass

# ----------------------------------------------------------------------
# Helper: transcribe a single scene's primary video file.
# ----------------------------------------------------------------------
def transcribe_scene(scene_id: int):
    """Fetch the scene's video file and run transcription."""
    try:
        # Minimal fragment to get the needed fields.
        fragment = """
            id title files { id path }
        """
        scene = stash.find_scene(scene_id, fragment)
        if not scene:
            stash.Error(f"Scene {scene_id} not found.")
            return

        if not scene.get("files"):
            stash.Warn(f"Scene {scene_id} has no associated files.")
            return

        video_path = scene["files"][0]["path"]
        if not os.path.isfile(video_path):
            stash.Warn(f"Video file does not exist: {video_path}")
            return


        # Call the shared transcription helper.
        # Use configured translate/server_url settings, and support dry-run.
        if dry_run:
            stash.Log(f"Dry-run: would transcribe '{video_path}' (translate={translate_to_english}, server_url={server_url})")
        else:
            transcribe_video(video_path, translate=translate_to_english, server_url=server_url)

        stash.Log(f"Transcription completed for scene {scene_id} (file: {video_path})")
    except Exception as e:
        tb = traceback.format_exc()
        stash.Error(f"Exception in transcribe_scene: {e}\nTraceBack={tb}")

# ----------------------------------------------------------------------
# Task: transcribe the most recently updated scene.
# ----------------------------------------------------------------------
def transcribe_last_scene():
    """Find the latest updated scene and run transcription on it."""
    try:
        all_scenes = stash.get_all_scenes()["allScenes"]
        if not all_scenes:
            stash.Error("No scenes found.")
            return

        latest = max(all_scenes, key=lambda s: s["updated_at"])
        scene_id = latest.get("id")
        if scene_id is None:
            stash.Error("Latest scene has no ID.")
            return

        transcribe_scene(scene_id)
    except Exception as e:
        tb = traceback.format_exc()
        stash.Error(f"Exception in transcribe_last_scene: {e}\nTraceBack={tb}")

def transcribe_scene_task():
    """
    Entry point used by the UI button.
    Expects a `scene_id` argument in the plugin's JSON input.
    """
    try:
        scene_id = stash.JSON_INPUT.get("args", {}).get("scene_id")
        if scene_id is None:
            stash.Error("No scene_id supplied to transcribe_scene_task")
            return
        scene_id = int(scene_id)
        transcribe_scene(scene_id)
    except Exception as e:
        tb = traceback.format_exc()
        stash.Error(f"Exception in transcribe_scene_task: {e}\nTraceBack={tb}")

# ----------------------------------------------------------------------
# Main entry point – mirrors the pattern used by RenameFile.
# ----------------------------------------------------------------------
try:
    if stash.PLUGIN_TASK_NAME == "transcribe_last_scene":
        stash.Trace(f"PLUGIN_TASK_NAME={stash.PLUGIN_TASK_NAME}")
        transcribe_last_scene()
    elif stash.PLUGIN_TASK_NAME == "transcribe_scene_task":
        stash.Trace(f"PLUGIN_TASK_NAME={stash.PLUGIN_TASK_NAME}")
        transcribe_scene_task()
    elif stash.JSON_INPUT and stash.JSON_INPUT.get("args", {}).get("mode") == "transcribe_scene_task":
        stash.Trace("Dispatch via args.mode=transcribe_scene_task")
        transcribe_scene_task()
    elif 'inputToUpdateScenePost' in globals() and inputToUpdateScenePost:
        stash.Trace("Triggered by Scene.Update.Post hook")
        if 'hookSceneID' in globals() and hookSceneID is not None:
            transcribe_scene(hookSceneID)
        else:
            # Fallback to latest scene if no id in hook context
            transcribe_last_scene()
    else:
        stash.Trace(f"No task specified (PLUGIN_TASK_NAME={stash.PLUGIN_TASK_NAME}). Nothing to do.")
except Exception as e:
    tb = traceback.format_exc()
    stash.Error(f"Exception while running plugin: {e}\nTraceBack={tb}")

stash.Trace("\n*********************************\nEXITING   ***********************\n*********************************")
