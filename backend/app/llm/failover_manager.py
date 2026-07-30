import time
import random
import logging
import threading
import httpx
from typing import Optional, List, Dict, Any, Tuple
from app.config import settings
from app.llm.gemini_client import call_gemini
from app.llm.groq_client import call_groq

logger = logging.getLogger("meridian.failover")

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
    def __init__(self):
        self.providers: List[LLMProvider] = []
        self.request_counter = 0
        self.counter_lock = threading.Lock()
        self.initialize_providers()

    def initialize_providers(self):
        """
        Dyanmically scans environment variables and loads active providers.
        """
        self.providers = []
        
        # 1. Load Gemini Keys
        gemini_keys = settings.get_gemini_keys()
        for idx, key in enumerate(gemini_keys):
            self.providers.append(
                LLMProvider(name=f"gemini_key_{idx+1}", provider_type="gemini", api_key=key)
            )
            
        # 2. Load Groq Keys
        groq_keys = settings.get_groq_keys()
        for idx, key in enumerate(groq_keys):
            self.providers.append(
                LLMProvider(name=f"groq_key_{idx+1}", provider_type="groq", api_key=key)
            )
            
        logger.info(f"LLM Failover Manager initialized with {len(self.providers)} total providers.")

    def execute_with_failover(
        self, 
        prompt: str, 
        system_instruction: Optional[str] = None, 
        json_mode: bool = False,
        response_schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        Executes LLM call with Round-Robin, Circuit Breakers, and Jittered Exponential Backoff.
        """
        if not self.providers:
            # Re-initialize in case keys were added at runtime
            self.initialize_providers()
            if not self.providers:
                raise RuntimeError("No LLM providers configured.")

        # Determine round-robin start index
        with self.counter_lock:
            start_idx = self.request_counter % len(self.providers)
            self.request_counter += 1

        errors = []
        
        # Loop through all providers starting from the Round-Robin index
        for i in range(len(self.providers)):
            provider_idx = (start_idx + i) % len(self.providers)
            provider = self.providers[provider_idx]
            
            # Check Circuit Breaker status
            if not provider.check_circuit():
                # Skip provider if circuit is OPEN and cooldown has not expired
                continue
                
            # Log current active provider
            logger.info(f"Active provider selected: {provider.name} (Round-robin index: {provider_idx})")
            
            # Attempt execution with Exponential Backoff + Jitter retries
            max_attempts = 4  # 1 original + 3 retries (Base: 1s, 2s, 4s, 8s max)
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
                    
                    # Record success metrics
                    latency = time.time() - start_time
                    provider.record_success(latency)
                    
                    logger.info(f"Successful response from provider {provider.name} in {latency:.2f}s")
                    return res, provider.name
                    
                except Exception as e:
                    latency = time.time() - start_time
                    err_msg = str(e)
                    
                    # Check if error is transient
                    if is_transient_error(e) and attempt < max_attempts:
                        provider.count_retries += 1
                        
                        # Calculate Jittered Exponential Backoff delay
                        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                        jitter = random.uniform(0.1, 0.5)
                        total_delay = delay + jitter
                        
                        logger.warning(
                            f"Failover Event: Provider {provider.name} failed with transient error: {err_msg}. "
                            f"Attempting retry {attempt} of {max_attempts-1} after {total_delay:.2f}s delay..."
                        )
                        time.sleep(total_delay)
                    else:
                        # Non-transient error or exhausted all retries
                        provider.record_failure(e)
                        errors.append(f"{provider.name}: {err_msg}")
                        logger.warning(f"Provider {provider.name} attempt failed completely: {err_msg}")
                        # Break retry loop and failover to next provider
                        break

        # If all providers failed
        all_errs = " | ".join(errors)
        logger.critical(f"Failover Event: All configured LLM providers failed. Details: {all_errs}")
        raise RuntimeError(f"All configured LLM providers failed. Details: {all_errs}")

    def execute_with_failover_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None
    ):
        """
        Executes a streaming LLM call with Round-Robin, Circuit Breakers, and failover if connection fails.
        Yields Tuple[chunk, provider_name].
        """
        import random
        if not self.providers:
            self.initialize_providers()
            
        if not self.providers:
            raise RuntimeError("No LLM providers are configured.")
            
        num_providers = len(self.providers)
        errors = []
        
        start_idx = self.round_robin_index
        
        for p_offset in range(num_providers):
            provider_idx = (start_idx + p_offset) % num_providers
            provider = self.providers[provider_idx]
            
            if not provider.check_circuit():
                continue
                
            self.round_robin_index = (provider_idx + 1) % num_providers
            logger.info(f"Active streaming provider selected: {provider.name} (Round-robin index: {provider_idx})")
            
            max_attempts = 4
            base_delay = 1.0
            max_delay = 8.0
            
            for attempt in range(1, max_attempts + 1):
                start_time = time.time()
                try:
                    stream_gen = provider.execute_call_stream(
                        prompt=prompt,
                        system_instruction=system_instruction
                    )
                    
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
                    return
                    
                except Exception as e:
                    err_msg = str(e)
                    errors.append(f"{provider.name} (attempt {attempt}): {err_msg}")
                    logger.warning(f"Streaming attempt {attempt} failed for provider {provider.name}: {err_msg}")
                    
                    provider.record_failure(err_msg)
                    
                    if attempt < max_attempts:
                        delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                        jitter = random.uniform(0, 0.1 * delay)
                        sleep_time = delay + jitter
                        logger.info(f"Retrying streaming call in {sleep_time:.2f} seconds...")
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"Provider {provider.name} streaming attempt failed completely after {max_attempts} attempts.")
                        break
                        
        all_errs = " | ".join(errors)
        logger.critical(f"Failover Event (Stream): All configured LLM providers failed. Details: {all_errs}")
        raise RuntimeError(f"All configured LLM providers failed. Details: {all_errs}")

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
