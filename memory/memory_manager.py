import json
import os
from datetime import datetime
from memory.supabase_client import get_supabase_client

# Instead of local files, E.R.A. will use Supabase for long-term memory.
# For backward compatibility with some existing agent logic during the transition,
# we wrap the calls. Realistically, we'd transition these completely to Supabase queries.

def build_system_context():
    client = get_supabase_client()
    if not client:
        return "== No active DB connection =="
        
    context = "== Active E.R.A. Context ==\n"
    try:
        # Example query: fetch active route details
        response = client.table("active_routes").select("*").eq("status", "active").limit(1).execute()
        if response.data:
            route = response.data[0]
            context += f"- Active Route: {route.get('destination')}\n"
            context += f"- ETA: {route.get('eta_mins')} mins\n"
            
        # Example query: fetch current patient
        patient_resp = client.table("patient_logs").select("*").order("created_at", desc=True).limit(1).execute()
        if patient_resp.data:
            patient = patient_resp.data[0]
            context += f"- Current Patient HR: {patient.get('heart_rate')}, BP: {patient.get('blood_pressure')}\n"
    except Exception as e:
        context += f"[DB Error: {e}]\n"

    return context

def update_memory(memory_update):
    # Map the old memory update format to Supabase records
    client = get_supabase_client()
    if not client:
        return
    try:
        # Simplified for E.R.A: Insert memory facts into an `era_memory` table
        for category, items in memory_update.items():
            for key, value_obj in items.items():
                val = value_obj.get('value') if isinstance(value_obj, dict) else value_obj
                client.table("era_memory").upsert({
                    "category": category,
                    "key": key,
                    "value": val,
                    "updated_at": datetime.utcnow().isoformat()
                }).execute()
    except Exception as e:
        print(f"[Memory DB Error] {e}")

def should_extract_memory(user_text, era_text, api_key):
    # Simpler heuristic for fast emergency routing assistant
    keywords = ["patient", "eta", "traffic", "heart rate", "blood pressure", "accident"]
    combined = (user_text + " " + era_text).lower()
    return any(k in combined for k in keywords)

def extract_memory(user_text, era_text, api_key):
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        prompt = (
            "Extract emergency/paramedic facts from this conversation.\n"
            "Categories: patient_vitals, route_info, hospital_status.\n"
            "Return valid JSON. Example: {\"patient_vitals\": {\"heart_rate\": {\"value\": \"120 bpm\"}}}\n\n"
            f"Paramedic: {user_text}\nE.R.A.: {era_text}\nJSON:"
        )
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        raw = response.text.strip()
        import re
        raw = re.sub(r'```(?:json)?', '', raw).strip().rstrip('`').strip()
        if not raw or raw == '{}':
            return {}
        return json.loads(raw)
    except Exception as e:
        print(f"[Memory Extract Error] {e}")
        return {}

def load_memory():
    client = get_supabase_client()
    memory = {}
    if not client: return memory
    try:
        resp = client.table("era_memory").select("*").execute()
        for row in resp.data:
            cat = row["category"]
            if cat not in memory:
                memory[cat] = {}
            memory[cat][row["key"]] = {"value": row["value"], "updated": row["updated_at"]}
    except Exception as e:
        print(f"[Memory Load Error] {e}")
    return memory

def format_memory_for_prompt(memory):
    if not memory: return ""
    lines = ["== Persistent Memory =="]
    for cat, items in memory.items():
        if not items: continue
        lines.append(f"[{cat.upper()}]")
        for k, v in items.items():
            val = v.get('value', v) if isinstance(v, dict) else v
            lines.append(f"  {k}: {val}")
    return "\n".join(lines) + "\n"
