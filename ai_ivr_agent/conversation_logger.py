# conversation_logger.py
import os
import json
from datetime import datetime
from pathlib import Path


class ConversationLogger:
    """
    Simple JSON logger for IVR calls.
    Each call gets its own file: logs/2025-02-01_12-55-22.json
    """

    def __init__(self, base_dir="logs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.current_file = None
        self.buffer = []

    # -----------------------------------------------------------
    # START NEW LOG
    # -----------------------------------------------------------
    def start_new(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = self.base_dir / f"{timestamp}.json"
        self.current_file = filename
        self.buffer = []
        return filename

    # -----------------------------------------------------------
    # ADD LOG ENTRY
    # -----------------------------------------------------------
    def log(self, role: str, message: str, metadata: dict = None):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "role": role,
            "message": message
        }
        if metadata:
            entry["metadata"] = metadata

        self.buffer.append(entry)
        self._write()

    # -----------------------------------------------------------
    # WRITE TO FILE
    # -----------------------------------------------------------
    def _write(self):
        if not self.current_file:
            return

        with open(self.current_file, "w", encoding="utf-8") as f:
            json.dump(self.buffer, f, indent=2)

    # -----------------------------------------------------------
    # GET ALL LOGS
    # -----------------------------------------------------------
    def get_all_logs(self):
        return sorted(self.base_dir.glob("*.json"))

    # -----------------------------------------------------------
    # READ ONE LOG
    # -----------------------------------------------------------
    def read_log(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None


# -----------------------------------------------------------
# GLOBAL SINGLETON (Optional)
# -----------------------------------------------------------
logger = ConversationLogger()
