import os
from groq import Groq

# Ensure you have GROQ_API_KEY in your environment variables
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """
    Transcribes audio bytes using Groq's whisper-large-v3-turbo model.
    """
    try:
        # The Groq API expects a tuple for the file: (filename, file_bytes)
        completion = client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model="whisper-large-v3-turbo",
            response_format="text", # or "json", "verbose_json"
            language="en" # Adjust or remove to auto-detect
        )
        # response_format="text" returns the transcribed text directly
        return completion.strip()
    except Exception as e:
        print(f"[STT Error] {e}")
        return ""
