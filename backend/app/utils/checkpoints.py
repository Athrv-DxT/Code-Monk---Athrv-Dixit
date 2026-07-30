import os
import json
import time
from datetime import datetime
from typing import List, Optional, Any
from app.config import settings

class CheckpointLogger:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.jsonl_path = os.path.join(settings.LOG_DIR, f"agent_run_{run_id}.jsonl")
        self.md_path = os.path.join(settings.LOG_DIR, f"agent_run_{run_id}.md")
        self._start_times = {}
        
        # Ensure log dir exists
        try:
            os.makedirs(settings.LOG_DIR, exist_ok=True)
            # Initialize files if they don't exist
            if not os.path.exists(self.md_path):
                with open(self.md_path, "w", encoding="utf-8") as f:
                    f.write(f"# Agent Execution Log - Run ID: `{run_id}`\n")
                    f.write(f"Generated on: {datetime.now().isoformat()}\n\n")
                    f.write("| Timestamp | Stage | Status | Duration (ms) | Model/Provider | Details |\n")
                    f.write("| --- | --- | --- | --- | --- | --- |\n")
        except Exception:
            pass # Gracefully handle non-writeable disks in production

    def start_stage(self, stage: str, input_summary: str = ""):
        self._start_times[stage] = time.time()
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Log to JSONL
        log_entry = {
            "timestamp": timestamp,
            "run_id": self.run_id,
            "stage": stage,
            "status": "started",
            "input_summary": input_summary[:200] if input_summary else "",
            "duration_ms": 0
        }
        self._write_jsonl(log_entry)
        
        # Log to Markdown
        try:
            clean_input = input_summary.replace("\n", " ").replace("|", "\\|")[:100]
            with open(self.md_path, "a", encoding="utf-8") as f:
                f.write(f"| {timestamp} | `{stage}` | **STARTED** | - | - | Input: {clean_input}... |\n")
        except Exception:
            pass

    def complete_stage(
        self, 
        stage: str, 
        output_summary: str = "", 
        gaps_detected: Optional[List[str]] = None, 
        model: str = "", 
        metadata: Optional[Any] = None
    ):
        timestamp = datetime.utcnow().isoformat() + "Z"
        duration_ms = 0.0
        if stage in self._start_times:
            duration_ms = (time.time() - self._start_times[stage]) * 1000
            
        gaps = gaps_detected or []
        
        # Log to JSONL
        log_entry = {
            "timestamp": timestamp,
            "run_id": self.run_id,
            "stage": stage,
            "status": "completed",
            "output_summary": output_summary[:200] if output_summary else "",
            "duration_ms": round(duration_ms, 2),
            "gaps_detected": gaps,
            "model_used": model,
            "metadata": metadata
        }
        self._write_jsonl(log_entry)
        
        # Log to Markdown
        try:
            clean_output = output_summary.replace("\n", " ").replace("|", "\\|")[:100]
            gaps_str = f" Gaps: {len(gaps)}" if gaps else ""
            with open(self.md_path, "a", encoding="utf-8") as f:
                f.write(f"| {timestamp} | `{stage}` | <span style='color:green'>**COMPLETED**</span> | {round(duration_ms, 1)} | {model or '-'} | Output: {clean_output}...{gaps_str} |\n")
        except Exception:
            pass

    def fail_stage(self, stage: str, error_message: str, model: str = ""):
        timestamp = datetime.utcnow().isoformat() + "Z"
        duration_ms = 0.0
        if stage in self._start_times:
            duration_ms = (time.time() - self._start_times[stage]) * 1000
            
        # Log to JSONL
        log_entry = {
            "timestamp": timestamp,
            "run_id": self.run_id,
            "stage": stage,
            "status": "failed",
            "error": error_message,
            "duration_ms": round(duration_ms, 2),
            "model_used": model
        }
        self._write_jsonl(log_entry)
        
        # Log to Markdown
        try:
            with open(self.md_path, "a", encoding="utf-8") as f:
                f.write(f"| {timestamp} | `{stage}` | <span style='color:red'>**FAILED**</span> | {round(duration_ms, 1)} | {model or '-'} | **Error**: {error_message} |\n")
        except Exception:
            pass

    def log_event(self, event_name: str, details: str):
        timestamp = datetime.utcnow().isoformat() + "Z"
        log_entry = {
            "timestamp": timestamp,
            "run_id": self.run_id,
            "event": event_name,
            "details": details
        }
        self._write_jsonl(log_entry)
        
        try:
            with open(self.md_path, "a", encoding="utf-8") as f:
                f.write(f"| {timestamp} | `EVENT:{event_name}` | INFO | - | - | {details} |\n")
        except Exception:
            pass

    def _write_jsonl(self, data: dict):
        # Always output checkpoints to stdout for Render logging console
        print(f"[CHECKPOINT] {json.dumps(data)}", flush=True)
        try:
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
        except Exception:
            pass # Prevent logger from crashing the application if disk error occurs

    def read_logs(self) -> str:
        if os.path.exists(self.md_path):
            try:
                with open(self.md_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
        return "Log file not found."
