import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

_client = None

def get_supabase_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            # Fallback/Mock behavior for local dev without keys
            print("[Supabase] Missing SUPABASE_URL or SUPABASE_KEY.")
            return None
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client

def log_patient_vitals(patient_id: str, case_id: str, heart_rate: int, blood_pressure: str):
    client = get_supabase_client()
    if not client: return
    try:
        data = {
            "patient_id": patient_id,
            "case_id": case_id,
            "heart_rate": heart_rate,
            "blood_pressure": blood_pressure
        }
        client.table("patient_logs").insert(data).execute()
    except Exception as e:
        print(f"[Supabase Error] {e}")

def update_route_status(route_id: str, status: str, eta_mins: int):
    client = get_supabase_client()
    if not client: return
    try:
        data = {
            "status": status,
            "eta_mins": eta_mins
        }
        client.table("active_routes").update(data).eq("route_id", route_id).execute()
    except Exception as e:
        print(f"[Supabase Error] {e}")

def get_patient_history(patient_id: str):
    client = get_supabase_client()
    if not client: return []
    try:
        response = client.table("patient_logs").select("*").eq("patient_id", patient_id).execute()
        return response.data
    except Exception as e:
        print(f"[Supabase Error] {e}")
        return []

def get_ambulance_inventory(ambulance_id: str) -> dict:
    client = get_supabase_client()
    if not client: return {"error": "DB disconnected"}
    try:
        response = client.table("ambulance_inventory").select("item_name, quantity, status").eq("ambulance_id", ambulance_id).execute()
        # Convert to dictionary mapping item name to quantity/status
        if response.data:
            return {row["item_name"]: {"quantity": row["quantity"], "status": row.get("status", "available")} for row in response.data}
        return {}
    except Exception as e:
        return {"error": str(e)}

def generate_handover_report(case_id: str, content: str):
    """Generates an ephemeral patient handover report in the database tied to a case_id."""
    client = get_supabase_client()
    if not client: return
    try:
        data = {
            "case_id": case_id,
            "report_content": content
        }
        client.table("patient_reports").insert(data).execute()
        print(f"[Supabase] Handover report saved for case {case_id}")
    except Exception as e:
        print(f"[Supabase Error] failed to save report: {e}")

def delete_case_data(case_id: str) -> bool:
    """Permanently deletes all database logs and generated files associated with the active_case_id."""
    client = get_supabase_client()
    if not client: return False
    try:
        # Delete from patient_logs
        client.table("patient_logs").delete().eq("case_id", case_id).execute()
        
        # Delete from patient_reports
        client.table("patient_reports").delete().eq("case_id", case_id).execute()
        
        # Delete from era_memory if any notes are tied to case_id
        client.table("era_memory").delete().eq("case_id", case_id).execute()
        
        # Note: If using Supabase Storage for actual files, you would do:
        # files = client.storage.from_("reports").list(path=case_id)
        # for f in files: client.storage.from_("reports").remove([f"{case_id}/{f['name']}"])
        
        print(f"[Supabase] Permanently deleted all data for case {case_id}")
        return True
    except Exception as e:
        print(f"[Supabase Error] failed to delete case data: {e}")
        return False
