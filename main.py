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
    
    # Establish a default system prompt in case no report is sent
    system_prompt = "You are E.R.A., a calm, professional AI emergency medical assistant. Keep responses concise and critical."
    
    try:
        while True:
            message = await websocket.receive()
            
            # 1. HANDLE INCOMING JSON
            if "text" in message:
                try:
                    data = json.loads(message["text"])
                    if data.get("type") == "system_context":
                        condition = data.get("condition", "Unknown")
                        inventory_list = data.get("inventory", [])
                        inventory_str = ", ".join(inventory_list) if inventory_list else "Standard Supplies"
                        
                        system_prompt = f"You are E.R.A., an AI emergency medical assistant. The current patient condition is: {condition}. You only have the following inventory available in the ambulance: {inventory_str}. Provide treatment steps using ONLY these items. Keep it concise."
                        
                        # Added flush=True to force Render to show this instantly
                        print("✅ E.R.A. System Prompt Updated with Inventory & Triage!", flush=True)
                except Exception as e:
                    print(f"JSON Parse Error: {e}", flush=True)
            
            # 2. HANDLE INCOMING AUDIO
            elif "bytes" in message:
                audio_bytes = message["bytes"]
                print(f"🎤 Received {len(audio_bytes)} bytes of audio.", flush=True)
                
                try:
                    # Transcribe Audio
                    user_text = await transcribe_audio(audio_bytes)
                    print(f"Paramedic: {user_text}", flush=True)
                    
                    if not user_text:
                        print("⚠️ Transcription was empty.", flush=True)
                        continue
                        
                    if not gemini_client:
                        print("❌ [Error] GEMINI_API_KEY not set.", flush=True)
                        continue
                    
                    full_prompt = f"{system_prompt}\n\nParamedic: {user_text}"
                    
                    # Query LLM
                    print("🧠 Sending to Gemini...", flush=True)
                    response = gemini_client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=full_prompt
                    )
                    era_text = response.text.strip()
                    print(f"E.R.A.: {era_text}", flush=True)
                    
                    # Send back to frontend
                    payload = {
                        "type": "message",
                        "role": "assistant",
                        "text": era_text
                    }
                    await websocket.send_text(json.dumps(payload))
                    print("🚀 Successfully sent AI response to frontend!", flush=True)
                    
                except Exception as process_error:
                    # IF IT CRASHES, WE WILL NOW SEE EXACTLY WHY
                    print(f"🔥 FATAL ERROR during audio processing: {process_error}", flush=True)
                    
    except WebSocketDisconnect:
        print("❌ E.R.A. Client disconnected.", flush=True)
    except Exception as e:
        print(f"[WebSocket Error] {e}", flush=True)

@app.get("/")
def health_check():
    return {"status": "E.R.A. is online and ready."}



if __name__ == "__main__":
    import uvicorn
    # Run headless server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
