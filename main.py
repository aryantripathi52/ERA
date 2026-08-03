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
            # Use receive() to catch BOTH text (JSON) and bytes (Audio)
            message = await websocket.receive()
            
            # 1. HANDLE INCOMING JSON (INVENTORY & TRIAGE REPORT)
            if "text" in message:
                try:
                    data = json.loads(message["text"])
                    if data.get("type") == "system_context":
                        condition = data.get("condition", "Unknown")
                        inventory_list = data.get("inventory", [])
                        inventory_str = ", ".join(inventory_list) if inventory_list else "Standard Supplies"
                        
                        # Dynamically update the AI's brain with the live ambulance data
                        system_prompt = f"You are E.R.A., an AI emergency medical assistant. The current patient condition is: {condition}. You only have the following inventory available in the ambulance: {inventory_str}. Provide treatment steps using ONLY these items. Keep it concise."
                        print("✅ E.R.A. System Prompt Updated with Inventory & Triage!")
                except Exception as e:
                    print(f"JSON Parse Error: {e}")
            
            # 2. HANDLE INCOMING AUDIO (MICROPHONE)
            elif "bytes" in message:
                audio_bytes = message["bytes"]
                print(f"🎤 Received {len(audio_bytes)} bytes of audio.")
                
                # Transcribe Audio
                user_text = await transcribe_audio(audio_bytes)
                
                if not user_text:
                    continue
                    
                print(f"Paramedic: {user_text}")
                
                if not gemini_client:
                    print("[Error] GEMINI_API_KEY not set.")
                    await websocket.send_text(json.dumps({"error": "LLM not configured"}))
                    continue
                
                full_prompt = (
                    f"{system_prompt}\n\n"
                    f"Paramedic: {user_text}"
                )
                
                try:
                    # Query LLM (Gemini)
                    response = gemini_client.models.generate_content(
                        model='gemini-2.5-flash', # You can also use 'gemini-1.5-flash' if 2.5 throws an error
                        contents=full_prompt
                    )
                    era_text = response.text.strip()
                    print(f"E.R.A.: {era_text}")
                    
                    # Stream JSON payload back over WebSocket (NO BACKEND AUDIO NEEDED)
                    payload = {
                        "type": "message",
                        "role": "assistant",
                        "text": era_text
                    }
                    await websocket.send_text(json.dumps(payload))
                    
                except Exception as llm_error:
                    print(f"❌ AI Generation Error: {llm_error}")
                    
    except WebSocketDisconnect:
        print("❌ E.R.A. Client disconnected.")
    except Exception as e:
        print(f"[WebSocket Error] {e}")

@app.get("/")
def health_check():
    return {"status": "E.R.A. is online and ready."}



if __name__ == "__main__":
    import uvicorn
    # Run headless server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
