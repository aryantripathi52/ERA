import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv

from core.stt import transcribe_audio
from core.tts import generate_speech
from memory.supabase_client import get_ambulance_inventory

# For LLM
from google import genai

load_dotenv()

app = FastAPI(title="E.R.A. (Emergency Routing Assistant) WebSocket API")

# Initialize Gemini Client
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

def load_prompt():
    try:
        with open(os.path.join(os.path.dirname(__file__), "core", "prompt.txt"), "r") as f:
            return f.read()
    except Exception:
        return "You are E.R.A. (Emergency Routing Assistant)."

@app.websocket("/ws/audio")
async def websocket_audio_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WebSocket] Client connected.")
    
    # Normally, the ambulance_id would be passed via JWT or headers, using a default for now.
    ambulance_id = "AMB-101"

    try:
        while True:
            # 1. Receive PCM/WAV chunks or text from the ambulance dashboard
            message = await websocket.receive()
            
            user_text = ""
            if "text" in message:
                # Allows the Next.js UI to send simple text strings
                user_text = message["text"]
                print(f"[WebSocket] Received text: {user_text}")
            elif "bytes" in message:
                audio_bytes = message["bytes"]
                print(f"[WebSocket] Received {len(audio_bytes)} bytes of audio.")
                # Transcribe Audio (Groq API: <100ms)
                user_text = await transcribe_audio(audio_bytes)
                
            if not user_text:
                continue
                
            print(f"Paramedic: {user_text}")
            
            # 2. Setup Context & Inventory
            if not gemini_client:
                print("[Error] GEMINI_API_KEY not set.")
                await websocket.send_text(json.dumps({"error": "LLM not configured"}))
                continue
                
            system_prompt = load_prompt()
            
            # Fetch Dynamic AMBULANCE_INVENTORY from Supabase
            inventory = get_ambulance_inventory(ambulance_id)
            inventory_json = json.dumps(inventory, indent=2)
            
            full_prompt = (
                f"{system_prompt}\n\n"
                f"=== AMBULANCE_INVENTORY (Ambulance ID: {ambulance_id}) ===\n"
                f"{inventory_json}\n\n"
                f"Paramedic: {user_text}"
            )
            
            # 3. Query LLM (Gemini 2.5 Flash / 1.5 Flash)
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=full_prompt
            )
            era_text = response.text.strip()
            print(f"E.R.A.: {era_text}")
            
            import base64
            # 5. Text-to-Speech (Edge-TTS Microsoft Neural Voices)
            audio_response = await generate_speech(era_text)
            
            # 6. Stream JSON payload back over WebSocket
            audio_b64 = base64.b64encode(audio_response).decode('utf-8') if audio_response else ""
            
            payload = {
                "type": "message",
                "role": "assistant",
                "text": era_text,
                "audio": audio_b64
            }
            await websocket.send_text(json.dumps(payload))
                
    except WebSocketDisconnect:
        print("[WebSocket] Client disconnected.")
    except Exception as e:
        print(f"[WebSocket Error] {e}")

@app.get("/")
def health_check():
    return {"status": "E.R.A. is online and ready."}



if __name__ == "__main__":
    import uvicorn
    # Run headless server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
