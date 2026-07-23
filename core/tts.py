import edge_tts
import io

async def generate_speech(text: str, voice: str = "en-US-AriaNeural") -> bytes:
    """
    Generates speech from text using Microsoft Edge TTS and returns the audio bytes (mp3).
    """
    try:
        communicate = edge_tts.Communicate(text, voice)
        audio_stream = io.BytesIO()
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.write(chunk["data"])
                
        return audio_stream.getvalue()
    except Exception as e:
        print(f"[TTS Error] {e}")
        return b""
