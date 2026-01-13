# Whisper Transcribe Plugin

This Stash plugin automatically generates subtitles for video files using a
whisper.cpp server.

## Features

- Retrieves the video file for the updated scene.
- Transcribes audio and writes an `.srt` file next to the video.
- Adds a UI dropdown button (via `whisper_transcribe.js`) to manually trigger transcription for the current scene.
- Supports optional translation to English (`translateToEnglish` setting) and a dry‑run mode (`zzdryRun`).
- Debug tracing can be enabled with the `zzdebugTracing` setting.

## Installation

1. Place the `whisper_transcribe` directory inside your Stash plugins folder
   (e.g., `~/.stash/plugins/whisper_transcribe`).
2. Ensure the whisper.cpp server is running and reachable.
   - Default URL used by this plugin: `http://127.0.0.1:9191/inference`
   - Override via the "Whisper Server URL" setting or the `WHISPER_SERVER_URL` environment variable.
3. Reload plugins from the Stash UI.

## Configuration

Use the plugin settings in the Stash UI to configure behaviour:

- **serverUrl** – Whisper server inference endpoint (default `http://127.0.0.1:9191/inference`).
- **translateToEnglish** – Translate transcription to English instead of source language.
- **zzdebugTracing** – Enable additional debug logs.
- **zzdryRun** – When enabled, no files are created; actions are only logged.

You can also set the `WHISPER_SERVER_URL` environment variable to override the server URL.
The optional `whisper_transcribe_settings.py` remains for advanced overrides.


## Troubleshooting

- Connection refused to whisper server: Ensure the server is running and that the "Whisper Server URL" points to the correct host/port. You can set it in the plugin settings or export `WHISPER_SERVER_URL` before launching Stash. The plugin checks reachability before doing any work and logs a clear error if unreachable.
- After transcription completes, refresh the scene or navigate away and back to see the new captions appear as an option in the player.

## Development

The core logic lives in `whisper_transcribe.py` and is self-contained.
It does not depend on files outside this plugin directory.

Feel free to extend the plugin with additional settings, UI elements, or
hooks as needed.
