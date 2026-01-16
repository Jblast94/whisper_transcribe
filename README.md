## Runpod Serverless Whisper Integration

To use a Runpod serverless endpoint for transcription:

1. Obtain your Runpod API key and set in your local `.env` or environment:
    ```
    RUNPOD_ENDPOINT_ID=bfarkaz0uwuhcn
    RUNPOD_API_KEY=your_runpod_api_key_here
    ```

2. Use the helper in your backend wherever you want to transcribe:
    ```python
    from services.runpod_client import transcribe_file
    result = transcribe_file("audio.mp3", language="en")
    print(result["text"])
    ```

3. To test locally, put a short audio file named `test_audio.mp3` in the root of your repo and run:
    ```
    python scripts/test_runpod_transcribe.py
    ```

4. The backend call will raise an error if `RUNPOD_API_KEY` is not set, or if the network call fails.