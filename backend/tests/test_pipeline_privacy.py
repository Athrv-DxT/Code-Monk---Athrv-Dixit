import unittest
import os
import json
from app.agents.orchestrator import run_pipeline
from app.config import settings

class TestPipelinePrivacyIntegration(unittest.TestCase):
    def test_pipeline_pii_redaction(self):
        # Force PII masking to True
        settings.ENABLE_PII_MASKING = True
        
        pii_content = (
            "NOTICE OF ADMINISTRATIVE RECOVERY\n\n"
            "This is to notify that Mr. Rahul Sharma (Aadhaar: 3668-0275-3381), residing at Plot 42, "
            "Sector 12, PIN 400703, has outstanding dues of Rs. 15,000 on Loan Account 918273645019.\n\n"
            "Please pay immediately to avoid legal actions under case number WP/4820/2026."
        )
        
        result = run_pipeline(
            content=pii_content,
            audience_profile_dict={
                "role": "general_adult",
                "domain_familiarity": "intermediate",
                "cognitive_access_needs": "standard",
                "preferred_language": "en",
                "modality": "text"
            },
            options={
                "include_fidelity_note": True,
                "language": "en",
                "tts_output": False
            }
        )
        
        # Verify run succeeded
        self.assertIn("run_id", result)
        run_id = result["run_id"]
        
        # Verify final adapted content returned to user has original PII reinserted
        adapted_text = result["versions"][0]["adapted_content"]
        self.assertIn("Rahul Sharma", adapted_text)
        self.assertIn("3668-0275-3381", adapted_text)
        
        # Check logs to ensure PII did not leak into logging
        log_file_path = os.path.join(settings.LOG_DIR, f"agent_run_{run_id}.md")
        self.assertTrue(os.path.exists(log_file_path))
        
        with open(log_file_path, "r", encoding="utf-8") as f:
            log_content = f.read()
            # Log file must NOT contain raw Aadhaar or Name, only masked tokens
            self.assertNotIn("3668-0275-3381", log_content)
            self.assertNotIn("Rahul Sharma", log_content)
            self.assertIn("Main document masked", log_content)
            self.assertIn("Aadhaar", log_content)

        # Check raw jsonl log to be 100% sure PII is not leaked there
        jsonl_path = os.path.join(settings.LOG_DIR, f"agent_run_{run_id}.jsonl")
        self.assertTrue(os.path.exists(jsonl_path))
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                event = json.loads(line)
                # Check message fields
                msg = str(event)
                self.assertNotIn("3668-0275-3381", msg)
                self.assertNotIn("Rahul Sharma", msg)

        print("\n[+] Pipeline Privacy Integration Test Passed! PII is fully masked in logs and unmasked in output.")

if __name__ == "__main__":
    unittest.main()
