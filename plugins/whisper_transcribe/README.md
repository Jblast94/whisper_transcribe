# Whisper Transcribe Plugin

This Stash plugin automatically generates subtitles for video files using a
whisper.cpp server.

## Features

- Listens for `Scene.Update.Post` events.
- Retrieves the video file for the updated scene.
- Transcribes audio and writes an `.srt` file next to the video.
- Provides a task to manually transcribe the most recently updated scene.

## Installation

1. Place the `whisper_transcribe` directory inside your Stash plugins folder
   (e.g., `~/.stash/plugins/whisper_transcribe`).
2. Ensure the whisper.cpp server is running and reachable.
   - Default URL used by this plugin: `http://127.0.0.1:9191/inference`
   - Override via the "Whisper Server URL" setting or the `WHISPER_SERVER_URL` environment variable.
3. Reload plugins from the Stash UI.

## Configuration

Use the plugin settings in the Stash UI to configure behaviour (e.g., server URL, translation).
You can also set the `WHISPER_SERVER_URL` environment variable to override the server URL.
The optional `whisper_transcribe_settings.py` remains for advanced overrides.

## Tasks

- **Transcribe Last Scene** – runs the transcription on the most recently
  updated scene.  Can be triggered from the Stash UI under *Plugins → Tasks*.

## Troubleshooting

- Connection refused to whisper server: Ensure the server is running and that the "Whisper Server URL" points to the correct host/port. You can set it in the plugin settings or export `WHISPER_SERVER_URL` before launching Stash. The plugin checks reachability before doing any work and logs a clear error if unreachable.

## Development

The core logic lives in `whisper_transcribe.py` and is self-contained.
It does not depend on files outside this plugin directory.

Feel free to extend the plugin with additional settings, UI elements, or
hooks as needed.
