from services.runpod_client import transcribe_file
import os

if __name__ == "__main__":
    fn = "test_audio.mp3"
    if not os.path.exists(fn):
        print("Please put a small MP3 file named test_audio.mp3 in the root folder to test.")
        exit(1)
    result = transcribe_file(fn, language="en")
    print("Extracted text:", result["text"])
    print("Full response:", result["raw"])
