import json
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

QUEUE_DIR = Path(__file__).parent / "flow_queue"
QUEUE_DIR.mkdir(parents=True, exist_ok=True)

def submit_request(prompt: str, media_type: str = "image") -> str:
    """Submit a request to generate media in Google Flow."""
    task_id = str(uuid.uuid4())
    task_file = QUEUE_DIR / f"{task_id}.json"
    
    task_data = {
        "id": task_id,
        "prompt": prompt,
        "media_type": media_type, # 'image' or 'video'
        "status": "PENDING", # PENDING, PROCESSING, DONE, ERROR
        "created_at": time.time(),
        "result_path": None,
        "error_message": None
    }
    
    task_file.write_text(json.dumps(task_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return task_id

def get_request_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get the current status of a generation request."""
    task_file = QUEUE_DIR / f"{task_id}.json"
    if not task_file.exists():
        return None
        
    try:
        data = json.loads(task_file.read_text(encoding="utf-8"))
        return data
    except json.JSONDecodeError:
        return None

def get_pending_request() -> Optional[Dict[str, Any]]:
    """Worker function to get the oldest PENDING request."""
    files = sorted(QUEUE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("status") == "PENDING":
                return data
        except json.JSONDecodeError:
            continue
    return None

def update_request(task_id: str, updates: Dict[str, Any]):
    """Update a request with new status or data."""
    task_file = QUEUE_DIR / f"{task_id}.json"
    if not task_file.exists():
        return
        
    try:
        data = json.loads(task_file.read_text(encoding="utf-8"))
        data.update(updates)
        task_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except json.JSONDecodeError:
        pass
