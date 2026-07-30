import unittest
import time
import httpx
from typing import Optional, Dict, Any
from app.llm.failover_manager import LLMProvider, LLMFailoverManager, is_transient_error

class MockSuccessProvider(LLMProvider):
    def __init__(self, name: str):
        super().__init__(name, "gemini", "mock_key")

    def execute_call(self, prompt, system_instruction=None, json_mode=False, response_schema=None):
        return f"Success from {self.name}"

class MockTransientFailureProvider(LLMProvider):
    def __init__(self, name: str, fail_attempts: int):
        super().__init__(name, "gemini", "mock_key")
        self.fail_attempts = fail_attempts
        self.calls = 0

    def execute_call(self, prompt, system_instruction=None, json_mode=False, response_schema=None):
        self.calls += 1
        if self.calls <= self.fail_attempts:
            # Raise transient error: HTTP 429 Status Error
            resp = httpx.Response(429, request=httpx.Request("POST", "http://test"))
            raise httpx.HTTPStatusError("Rate Limit Exceeded", request=resp.request, response=resp)
        return f"Recovered on call {self.calls} from {self.name}"

class MockNonTransientFailureProvider(LLMProvider):
    def __init__(self, name: str):
        super().__init__(name, "gemini", "mock_key")

    def execute_call(self, prompt, system_instruction=None, json_mode=False, response_schema=None):
        # Raise non-transient error: HTTP 403 Forbidden Error
        resp = httpx.Response(403, request=httpx.Request("POST", "http://test"))
        raise httpx.HTTPStatusError("Invalid API Key", request=resp.request, response=resp)

class TestLLMFailoverSystem(unittest.TestCase):
    def test_transient_error_categorization(self):
        # Timeout error is transient
        self.assertTrue(is_transient_error(httpx.ConnectTimeout("Connect timeout")))
        
        # 429 is transient
        resp_429 = httpx.Response(429, request=httpx.Request("POST", "http://test"))
        self.assertTrue(is_transient_error(httpx.HTTPStatusError("Rate limit", request=resp_429.request, response=resp_429)))
        
        # 503 is transient
        resp_503 = httpx.Response(503, request=httpx.Request("POST", "http://test"))
        self.assertTrue(is_transient_error(httpx.HTTPStatusError("Service Unavailable", request=resp_503.request, response=resp_503)))

        # 403 (Auth/Invalid Key) is NOT transient
        resp_403 = httpx.Response(403, request=httpx.Request("POST", "http://test"))
        self.assertFalse(is_transient_error(httpx.HTTPStatusError("Forbidden", request=resp_403.request, response=resp_403)))

    def test_round_robin_rotation(self):
        manager = LLMFailoverManager()
        # Mock providers list
        p1 = MockSuccessProvider("provider_1")
        p2 = MockSuccessProvider("provider_2")
        manager.providers = [p1, p2]

        # Reset request counter
        manager.request_counter = 0

        # Call 1 -> start_idx = 0 -> provider_1
        res1, provider1 = manager.execute_with_failover("test prompt")
        self.assertEqual(provider1, "provider_1")
        self.assertEqual(res1, "Success from provider_1")

        # Call 2 -> start_idx = 1 -> provider_2
        res2, provider2 = manager.execute_with_failover("test prompt")
        self.assertEqual(provider2, "provider_2")
        self.assertEqual(res2, "Success from provider_2")

        # Call 3 -> start_idx = 0 -> provider_1 (wrapped)
        res3, provider3 = manager.execute_with_failover("test prompt")
        self.assertEqual(provider3, "provider_1")

    def test_transient_retry_success(self):
        manager = LLMFailoverManager()
        # Mock provider that fails once with 429, then succeeds
        p1 = MockTransientFailureProvider("provider_1", fail_attempts=1)
        manager.providers = [p1]
        manager.request_counter = 0

        # Execute should succeed on first retry attempt
        res, provider = manager.execute_with_failover("test prompt")
        self.assertEqual(provider, "provider_1")
        self.assertEqual(res, "Recovered on call 2 from provider_1")
        self.assertEqual(p1.count_retries, 1)

    def test_circuit_breaker_trip_and_cooldown(self):
        manager = LLMFailoverManager()
        # Provider 1 fails continuously (non-transient to trip fast without retry delays)
        p1 = MockNonTransientFailureProvider("provider_1")
        p2 = MockSuccessProvider("provider_2")
        manager.providers = [p1, p2]
        manager.request_counter = 0

        # Failures threshold is 3. We run it three times starting on provider_1.
        for _ in range(3):
            # Run starting on p1. It should fail on p1, trip the error count, and failover to p2.
            manager.request_counter = 0  # Force start at index 0 (provider_1)
            res, provider = manager.execute_with_failover("test prompt")
            # Should failover and succeed via provider_2
            self.assertEqual(provider, "provider_2")

        # After 3 failures, provider_1 circuit state must be OPEN
        self.assertEqual(p1.state, "OPEN")
        self.assertIsNotNone(p1.cooldown_until)

        # A 4th request starting at provider_1 should immediately skip provider_1 and hit provider_2
        manager.request_counter = 0
        res, provider = manager.execute_with_failover("test prompt")
        self.assertEqual(provider, "provider_2")
        # Ensure provider_1 was completely skipped (no new failures/attempts registered)
        self.assertEqual(p1.total_requests, 3)

        # Simulate cooldown expiration
        p1.cooldown_until = time.time() - 1.0 # 1s in the past
        # Now provider_1 should transition to HALF-OPEN on check_circuit, and allow trial request.
        # Since p1 fails again, it should re-trip to OPEN.
        manager.request_counter = 0
        res, provider = manager.execute_with_failover("test prompt")
        self.assertEqual(provider, "provider_2")
        self.assertEqual(p1.state, "OPEN")
        # Requests increased to 4 (representing the trial request)
        self.assertEqual(p1.total_requests, 4)
