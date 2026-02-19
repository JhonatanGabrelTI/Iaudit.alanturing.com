import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any
from app.models import CommunicationLog, CommunicationChannel, CommunicationStatus

LOG_FILE = "backend/data/comm_logs.json"

class CommunicationService:
    def __init__(self):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)

    def _read_logs(self) -> List[Dict[str, Any]]:
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _write_logs(self, logs: List[Dict[str, Any]]):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, default=str)

    async def log_message(
        self, 
        channel: CommunicationChannel, 
        recipient: str, 
        content: str, 
        status: CommunicationStatus, 
        subject: str = None,
        error_message: str = None,
        metadata: dict = None
    ) -> str:
        logs = self._read_logs()
        log_id = str(uuid.uuid4())
        
        new_log = {
            "id": log_id,
            "timestamp": datetime.now().isoformat(),
            "channel": channel,
            "recipient": recipient,
            "subject": subject,
            "content": content,
            "status": status,
            "error_message": error_message,
            "metadata": metadata or {}
        }
        
        logs.insert(0, new_log)  # Newest first
        self._write_logs(logs[:500])  # Keep last 500 logs
        return log_id

    async def get_logs(self, channel: str = None, status: str = None) -> List[Dict[str, Any]]:
        logs = self._read_logs()
        if channel:
            logs = [l for l in logs if l["channel"] == channel]
        if status:
            logs = [l for l in logs if l["status"] == status]
        return logs

    async def get_stats(self) -> Dict[str, Any]:
        logs = self._read_logs()
        total = len(logs)
        if total == 0:
            return {"total": 0, "sent": 0, "failed": 0, "success_rate": 0}
            
        sent = len([l for l in logs if l["status"] == CommunicationStatus.sent])
        failed = len([l for l in logs if l["status"] == CommunicationStatus.failed])
        
        return {
            "total": total,
            "sent": sent,
            "failed": failed,
            "success_rate": (sent / (sent + failed) * 100) if (sent + failed) > 0 else 0
        }

    async def clear_logs(self):
        self._write_logs([])

comm_service = CommunicationService()
