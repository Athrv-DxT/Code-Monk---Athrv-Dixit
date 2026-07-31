import time
import random
import logging
import threading
import httpx
from typing import Optional, List, Dict, Any, Tuple
from app.config import settings
from app.llm.gemini_client import call_gemini
from app.llm.groq_client import call_groq

logger = logging.getLogger("intellix.failover")

def is_transient_error(e: Exception) -> bool:
    """
    Categorizes errors to determine if they should be retried (429, 5xx, timeouts, network issues).
    """
    if isinstance(e, httpx.TimeoutException):
        return True
    if isinstance(e, httpx.NetworkError) or isinstance(e, httpx.RequestError):
        return True
    if isinstance(e, httpx.HTTPStatusError):
        status_code = e.response.status_code
        if status_code == 429 or (status_code >= 500 and status_code < 600):
            return True
    
    # Text-based checks for exceptions wrapped by other libraries
    err_str = str(e).lower()
    transient_indicators = ["429", "too many requests", "timeout", "500", "503", "connection", "rate limit"]
    if any(ind in err_str for ind in transient_indicators):
        # Ensure we don't treat auth/validation errors (401, 403, 400) as transient
        if not any(auth_ind in err_str for auth_ind in ["401", "403", "unauthorized", "invalid key"]):
            return True
            
    return False

class LLMProvider:
    def __init__(self, name: str, provider_type: str, api_key: str):
        self.name = name
        self.provider_type = provider_type
        self.api_key = api_key
        
        # Circuit Breaker state: CLOSED, OPEN, HALF-OPEN
        self.state = "CLOSED"
        self.consecutive_failures = 0
        self.cooldown_until: Optional[float] = None
        self.failure_threshold = 3
        self.cooldown_duration = 30.0  # seconds
        
        # Runtime Metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.count_429 = 0
        self.count_timeout = 0
        self.count_retries = 0
        self.total_latency = 0.0
        self.last_success_time: Optional[float] = None
        self.last_failure_reason: Optional[str] = None
        
        self.lock = threading.Lock()

    def check_circuit(self) -> bool:
        """
        Checks circuit status. Returns True if requests can be processed.
        If OPEN but cooldown has expired, transitions to HALF-OPEN.
        """
        with self.lock:
            if self.state == "OPEN":
                if self.cooldown_until and time.time() > self.cooldown_until:
                    self.state = "HALF-OPEN"
                    logger.info(f"Circuit Breaker state change: Provider {self.name} changed from OPEN to HALF-OPEN (cooldown expired).")
                    return True
                return False
            return True

    def record_success(self, latency: float):
        """
        Records a successful request and closes the circuit if it was HALF-OPEN.
        """
        with self.lock:
            self.total_requests += 1
            self.successful_requests += 1
            self.consecutive_failures = 0
            self.total_latency += latency
            self.last_success_time = time.time()
            if self.state == "HALF-OPEN":
                self.state = "CLOSED"
                logger.info(f"Circuit Breaker state change: Provider {self.name} trial succeeded. Changed state from HALF-OPEN to CLOSED.")

    def record_failure(self, error: Exception):
        """
        Records a failed request and opens the circuit if threshold is exceeded.
        """
        with self.lock:
            self.total_requests += 1
            self.failed_requests += 1
            self.consecutive_failures += 1
            
            err_str = str(error)
            self.last_failure_reason = err_str
            
            err_lower = err_str.lower()
            if "429" in err_lower or "rate limit" in err_lower:
                self.count_429 += 1
            elif "timeout" in err_lower:
                self.count_timeout += 1

            if self.consecutive_failures >= self.failure_threshold:
                self.state = "OPEN"
                self.cooldown_until = time.time() + self.cooldown_duration
                logger.warning(
                    f"Circuit Breaker state change: Provider {self.name} reached failure threshold ({self.consecutive_failures}). "
                    f"State changed to OPEN. Cooldown active for {self.cooldown_duration}s."
                )

    def execute_call(
        self, 
        prompt: str, 
        system_instruction: Optional[str] = None, 
        json_mode: bool = False,
        response_schema: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Executes actual client API calls.
        """
        if self.provider_type == "gemini":
            return call_gemini(
                prompt=prompt,
                system_instruction=system_instruction,
                json_mode=json_mode,
                response_schema=response_schema,
                api_key=self.api_key
            )
        elif self.provider_type == "groq":
            return call_groq(
                prompt=prompt,
                system_instruction=system_instruction,
                json_mode=json_mode,
                api_key=self.api_key
            )
        else:
            raise ValueError(f"Unknown provider type: {self.provider_type}")

    def execute_call_stream(
        self, 
        prompt: str, 
        system_instruction: Optional[str] = None
    ):
        """
        Executes streaming client API calls.
        """
        if self.provider_type == "gemini":
            from app.llm.gemini_client import call_gemini_stream
            return call_gemini_stream(
                prompt=prompt,
                system_instruction=system_instruction,
                api_key=self.api_key
            )
        elif self.provider_type == "groq":
            from app.llm.groq_client import call_groq_stream
            return call_groq_stream(
                prompt=prompt,
                system_instruction=system_instruction,
                api_key=self.api_key
            )
        else:
            raise ValueError(f"Unknown provider type: {self.provider_type}")


class LLMFailoverManager:
    """
    Manages LLM provider failover with Gemini-first round-robin and Groq as last resort.
    
    Strategy:
    - Gemini keys are rotated in round-robin order first.
    - Groq is only attempted if ALL Gemini providers are unavailable/failed.
    - Prints a startup banner listing loaded providers and active provider.
    - Logs provider selection reasons and failover/fallback details for every request.
    """
    def __init__(self):
        self.gemini_providers: List[LLMProvider] = []
        self.groq_providers: List[LLMProvider] = []
        self.gemini_counter = 0
        self.groq_counter = 0
        self.counter_lock = threading.Lock()
        self.initialize_providers()

    @property
    def providers(self) -> List[LLMProvider]:
        """Combined view of all providers for health reporting."""
        return self.gemini_providers + self.groq_providers

    def initialize_providers(self):
        """
        Dynamically scans environment variables and loads active providers.
        Separates Gemini keys from Groq keys. Prints a startup banner.
        """
        self.gemini_providers = []
        self.groq_providers = []
        
        # 1. Load Gemini Keys
        gemini_keys = settings.get_gemini_keys()
        for idx, key in enumerate(gemini_keys):
            self.gemini_providers.append(
                LLMProvider(name=f"gemini_key_{idx+1}", provider_type="gemini", api_key=key)
            )
            
        # 2. Load Groq Keys
        groq_keys = settings.get_groq_keys()
        for idx, key in enumerate(groq_keys):
            self.groq_providers.append(
                LLMProvider(name=f"groq_key_{idx+1}", provider_type="groq", api_key=key)
            )
        
        # Print startup banner
        banner_lines = [
            "",
            "=" * 60,
            "  INTELLIX — LLM Provider Startup Banner",
            "=" * 60,
        ]
        if self.gemini_providers:
            banner_lines.append(f"  Gemini Providers ({len(self.gemini_providers)} loaded):")
            for p in self.gemini_providers:
                masked_key = p.api_key[:8] + "..." if len(p.api_key) > 8 else "***"
                banner_lines.append(f"    [{p.name}]  key={masked_key}  state={p.state}")
        else:
            banner_lines.append("  Gemini Providers: NONE CONFIGURED")
        
        if self.groq_providers:
            banner_lines.append(f"  Groq Providers ({len(self.groq_providers)} loaded — fallback only):")
            for p in self.groq_providers:
                masked_key = p.api_key[:8] + "..." if len(p.api_key) > 8 else "***"
                banner_lines.append(f"    [{p.name}]  key={masked_key}  state={p.state}")
        else:
            banner_lines.append("  Groq Providers: NONE CONFIGURED")

        if self.gemini_providers:
            first = self.gemini_providers[0]
            banner_lines.append(f"  Active Provider (Initial): {first.name}")
        elif self.groq_providers:
            banner_lines.append(f"  Active Provider (Initial): {self.groq_providers[0].name}")
        else:
            banner_lines.append("  Active Provider (Initial): NONE — service will fail!")

        banner_lines.append("=" * 60)
        banner_lines.append("")
        logger.info("\n".join(banner_lines))

    def _try_provider(
        self,
        provider: LLMProvider,
        prompt: str,
        system_instruction: Optional[str],
        json_mode: bool,
        response_schema: Optional[Dict[str, Any]],
        errors: List[str]
    ) -> Optional[Tuple[str, str]]:
        """
        Attempts a single provider with exponential backoff retries.
        Returns (result, provider_name) on success, or None on complete failure.
        Appends error messages to `errors` list.
        """
        if not provider.check_circuit():
            logger.info(f"Skipping provider {provider.name}: circuit is OPEN (cooling down).")
            return None

        max_attempts = 4
        base_delay = 1.0
        max_delay = 8.0

        for attempt in range(1, max_attempts + 1):
            start_time = time.time()
            try:
                res = provider.execute_call(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    json_mode=json_mode,
                    response_schema=response_schema
                )
                latency = time.time() - start_time
                provider.record_success(latency)
                logger.info(f"[LLM Router] Provider {provider.name} succeeded in {latency:.2f}s (attempt {attempt})")
                return res, provider.name
            except Exception as e:
                latency = time.time() - start_time
                err_msg = str(e)
                if is_transient_error(e) and attempt < max_attempts:
                    provider.count_retries += 1
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    jitter = random.uniform(0.1, 0.5)
                    total_delay = delay + jitter
                    logger.warning(
                        f"[LLM Router] Provider {provider.name} transient error (attempt {attempt}/{max_attempts}): {err_msg}. "
                        f"Retrying in {total_delay:.2f}s..."
                    )
                    time.sleep(total_delay)
                else:
                    provider.record_failure(e)
                    errors.append(f"{provider.name}: {err_msg}")
                    logger.warning(
                        f"[LLM Router] Provider {provider.name} failed permanently after {attempt} attempt(s): {err_msg}"
                    )
                    break
        return None

    def execute_with_failover(
        self, 
        prompt: str, 
        system_instruction: Optional[str] = None, 
        json_mode: bool = False,
        response_schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        Executes LLM call with Gemini-first Round-Robin, Circuit Breakers, and Jittered Exponential Backoff.
        Falls back to Groq only if ALL Gemini providers are exhausted or unavailable.
        """
        if not self.gemini_providers and not self.groq_providers:
            self.initialize_providers()
            if not self.gemini_providers and not self.groq_providers:
                raise RuntimeError("No LLM providers configured.")

        errors: List[str] = []

        # --- Phase 1: Try Gemini providers (round-robin) ---
        if self.gemini_providers:
            with self.counter_lock:
                start_idx = self.gemini_counter % len(self.gemini_providers)
                self.gemini_counter += 1

            for i in range(len(self.gemini_providers)):
                provider_idx = (start_idx + i) % len(self.gemini_providers)
                provider = self.gemini_providers[provider_idx]
                logger.info(
                    f"[LLM Router] Selecting Gemini provider: {provider.name} "
                    f"(round-robin slot {provider_idx}, reason=primary_gemini_pool)"
                )
                result = self._try_provider(provider, prompt, system_instruction, json_mode, response_schema, errors)
                if result is not None:
                    return result
        
        # --- Phase 2: All Gemini failed — fall back to Groq ---
        if self.groq_providers:
            logger.warning(
                f"[LLM Router] All Gemini providers exhausted/unavailable. "
                f"Falling back to Groq (reason=gemini_pool_exhausted). "
                f"Gemini errors: {' | '.join(errors)}"
            )
            with self.counter_lock:
                start_idx = self.groq_counter % len(self.groq_providers)
                self.groq_counter += 1

            for i in range(len(self.groq_providers)):
                provider_idx = (start_idx + i) % len(self.groq_providers)
                provider = self.groq_providers[provider_idx]
                logger.info(
                    f"[LLM Router] Selecting Groq provider: {provider.name} "
                    f"(round-robin slot {provider_idx}, reason=groq_fallback)"
                )
                result = self._try_provider(provider, prompt, system_instruction, json_mode, response_schema, errors)
                if result is not None:
                    return result

        # All providers failed
        all_errs = " | ".join(errors)
        logger.critical(f"[LLM Router] Failover Event: All configured LLM providers failed. Details: {all_errs}")
        raise RuntimeError(f"All configured LLM providers failed. Details: {all_errs}")

    def _try_provider_stream(
        self,
        provider: LLMProvider,
        prompt: str,
        system_instruction: Optional[str],
        errors: List[str]
    ):
        """
        Attempts a single provider for streaming. Yields (chunk, provider_name) on success.
        Returns False if the provider failed completely.
        """
        if not provider.check_circuit():
            logger.info(f"[LLM Router Stream] Skipping {provider.name}: circuit OPEN.")
            return False

        max_attempts = 4
        base_delay = 1.0
        max_delay = 8.0

        for attempt in range(1, max_attempts + 1):
            start_time = time.time()
            try:
                stream_gen = provider.execute_call_stream(prompt=prompt, system_instruction=system_instruction)
                iterator = iter(stream_gen)
                try:
                    first_chunk = next(iterator)
                except StopIteration:
                    first_chunk = ""
                    
                yield (first_chunk, provider.name)
                for chunk in iterator:
                    yield (chunk, provider.name)
                    
                latency = time.time() - start_time
                provider.record_success(latency)
                return True
                
            except Exception as e:
                err_msg = str(e)
                errors.append(f"{provider.name} (attempt {attempt}): {err_msg}")
                logger.warning(f"[LLM Router Stream] Provider {provider.name} attempt {attempt} failed: {err_msg}")
                provider.record_failure(e)
                
                if attempt < max_attempts:
                    delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                    jitter = random.uniform(0, 0.1 * delay)
                    sleep_time = delay + jitter
                    logger.info(f"[LLM Router Stream] Retrying {provider.name} in {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"[LLM Router Stream] Provider {provider.name} exhausted after {max_attempts} attempts.")
                    break
        return False

    def execute_with_failover_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None
    ):
        """
        Executes a streaming LLM call with Gemini-first Round-Robin, Circuit Breakers, and failover.
        Yields Tuple[chunk, provider_name]. Falls back to Groq only if all Gemini fail.
        """
        if not self.gemini_providers and not self.groq_providers:
            self.initialize_providers()
            
        if not self.gemini_providers and not self.groq_providers:
            raise RuntimeError("No LLM providers are configured.")
            
        errors: List[str] = []

        # --- Phase 1: Try Gemini providers (round-robin) ---
        if self.gemini_providers:
            with self.counter_lock:
                start_idx = self.gemini_counter % len(self.gemini_providers)
                self.gemini_counter += 1

            for i in range(len(self.gemini_providers)):
                provider_idx = (start_idx + i) % len(self.gemini_providers)
                provider = self.gemini_providers[provider_idx]
                logger.info(
                    f"[LLM Router Stream] Selecting Gemini provider: {provider.name} "
                    f"(round-robin slot {provider_idx}, reason=primary_gemini_pool)"
                )
                succeeded = False
                for item in self._try_provider_stream(provider, prompt, system_instruction, errors):
                    if item is True or item is False:
                        succeeded = item
                    else:
                        yield item
                if succeeded:
                    return

        # --- Phase 2: Groq fallback ---
        if self.groq_providers:
            logger.warning(
                f"[LLM Router Stream] All Gemini providers exhausted/unavailable. "
                f"Falling back to Groq stream (reason=gemini_pool_exhausted). "
                f"Errors: {' | '.join(errors)}"
            )
            with self.counter_lock:
                start_idx = self.groq_counter % len(self.groq_providers)
                self.groq_counter += 1

            for i in range(len(self.groq_providers)):
                provider_idx = (start_idx + i) % len(self.groq_providers)
                provider = self.groq_providers[provider_idx]
                logger.info(
                    f"[LLM Router Stream] Selecting Groq provider: {provider.name} "
                    f"(round-robin slot {provider_idx}, reason=groq_fallback)"
                )
                succeeded = False
                for item in self._try_provider_stream(provider, prompt, system_instruction, errors):
                    if item is True or item is False:
                        succeeded = item
                    else:
                        yield item
                if succeeded:
                    return
                    
        all_errs = " | ".join(errors)
        logger.critical(f"[LLM Router Stream] Failover Event: All providers failed. Details: {all_errs}")
        raise RuntimeError(f"All configured LLM providers failed (stream). Details: {all_errs}")

    def get_providers_status(self) -> List[Dict[str, Any]]:
        """
        Returns structured metrics for all configured providers (without exposing keys).
        """
        status_list = []
        for provider in self.providers:
            cooldown_rem = 0.0
            if provider.state == "OPEN" and provider.cooldown_until:
                cooldown_rem = max(0.0, provider.cooldown_until - time.time())
                
            avg_lat = 0.0
            if provider.successful_requests > 0:
                avg_lat = provider.total_latency / provider.successful_requests
                
            status_list.append({
                "provider_name": provider.name,
                "provider_type": provider.provider_type,
                "healthy": provider.state != "OPEN",
                "state": provider.state,
                "consecutive_failures": provider.consecutive_failures,
                "cooldown_remaining_sec": round(cooldown_rem, 2),
                "total_requests": provider.total_requests,
                "successful_requests": provider.successful_requests,
                "failed_requests": provider.failed_requests,
                "retry_count": provider.count_retries,
                "429_count": provider.count_429,
                "timeout_count": provider.count_timeout,
                "average_latency_sec": round(avg_lat, 3),
                "last_success_timestamp": provider.last_success_time,
                "last_failure_reason": provider.last_failure_reason
            })
        return status_list

# Instantiate singleton failover manager
failover_manager = LLMFailoverManager()
