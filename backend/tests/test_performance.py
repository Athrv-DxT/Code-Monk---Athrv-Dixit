import unittest
import asyncio
import time
from app.agents.orchestrator import run_pipeline, run_pipeline_stream, translate_text
from app.utils.translation_cache import translation_cache
from app.core.models import AudienceProfile

class TestPerformanceOptimizations(unittest.TestCase):
    def setUp(self):
        from app.config import settings
        self.old_offline = settings.DEMO_OFFLINE_MODE
        settings.DEMO_OFFLINE_MODE = True
        translation_cache.clear()

    def tearDown(self):
        from app.config import settings
        settings.DEMO_OFFLINE_MODE = self.old_offline

    def test_translation_cache(self):
        """
        Verify that translation caching stores text and returns it immediately.
        """
        text = "Hello, this is a test notice for citizens."
        target_lang = "hi"
        
        # First translation (calls mock/actual generator and caches it)
        t1 = translate_text(text, target_lang)
        self.assertIsNotNone(t1)
        
        # Second translation must hit cache
        start = time.time()
        t2 = translate_text(text, target_lang)
        duration = time.time() - start
        
        self.assertEqual(t1, t2)
        # Cache hit should be sub-millisecond, definitely under 5ms
        self.assertLess(duration, 0.005)

    def test_pipeline_timing_metrics(self):
        """
        Verify that run_pipeline returns a structured metrics payload tracking stage latency.
        """
        content = "NOTICE OF VIOLATION. Please respond within 30 days."
        
        # Run asynchronously
        result = asyncio.run(run_pipeline(
            content=content,
            audience_profile_dict={
                "role": "general_adult",
                "domain_familiarity": "intermediate",
                "cognitive_access_needs": "standard",
                "preferred_language": "en",
                "modality": "text"
            },
            options={
                "include_fidelity_note": False,
                "language": "en",
                "tts_output": False
            }
        ))
        
        self.assertIn("metrics", result)
        metrics = result["metrics"]
        self.assertIn("classification_sec", metrics)
        self.assertIn("extraction_sec", metrics)
        self.assertIn("planning_sec", metrics)
        self.assertIn("rewrite_sec", metrics)
        self.assertIn("translation_sec", metrics)
        self.assertIn("total_sec", metrics)
        
        self.assertGreater(metrics["total_sec"], 0.0)

    def test_streaming_pipeline(self):
        """
        Verify that run_pipeline_stream yields metadata, updates, and completes sequentially.
        """
        content = "NOTICE OF DECISION. Case No 9182. Approved with conditions."
        
        async def consume_stream():
            events = []
            async for chunk in run_pipeline_stream(
                content=content,
                audience_profile_dict={
                    "role": "general_adult",
                    "domain_familiarity": "intermediate",
                    "cognitive_access_needs": "standard",
                    "preferred_language": "en",
                    "modality": "text"
                },
                options={"language": "en"}
            ):
                events.append(chunk)
            return events

        events = asyncio.run(consume_stream())
        
        self.assertGreater(len(events), 0)
        # First event should be metadata
        self.assertEqual(events[0]["status"], "metadata")
        # Final event should be completed
        self.assertEqual(events[-1]["status"], "completed")
        
        # Verify that we received section updates
        has_updates = any(e["status"] == "section_update" for e in events)
        self.assertTrue(has_updates)
