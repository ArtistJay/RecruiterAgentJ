"""Smart error handling for LLM API calls — retries only when it makes sense."""

import time
import logging

logger = logging.getLogger(__name__)

# Errors where retrying is POINTLESS — fail immediately
FATAL_KEYWORDS = [
    "quota", "exceeded", "billing", "insufficient", "api_key",
    "unauthorized", "authentication", "invalid_api_key",
    "tokens_exhausted", "daily limit", "rpd",
]

# Errors where retrying MIGHT help — wait and try again
TRANSIENT_KEYWORDS = [
    "timeout", "connection", "503", "502", "overloaded",
    "temporarily", "try again", "rate_limit", "too many requests",
]


class GroqQuotaExhausted(Exception):
    """Raised when Groq free tier quota is exhausted. Retrying won't help."""
    pass


class GroqTransientError(Exception):
    """Raised for temporary errors that might resolve on retry."""
    pass


def _classify_error(error: Exception) -> str:
    """Classify an API error as 'fatal', 'transient', or 'unknown'."""
    error_str = str(error).lower()
    
    for keyword in FATAL_KEYWORDS:
        if keyword in error_str:
            return "fatal"
    
    for keyword in TRANSIENT_KEYWORDS:
        if keyword in error_str:
            return "transient"
    
    # Check HTTP status codes if present
    if hasattr(error, 'status_code'):
        code = error.status_code
        if code == 401:
            return "fatal"
        elif code == 429:
            # 429 could be temporary RPM limit OR quota exhaustion
            # Check message to distinguish
            if any(k in error_str for k in ["daily", "quota", "exceeded", "rpd"]):
                return "fatal"
            return "transient"  # Likely just RPM throttle
        elif code in (502, 503, 504):
            return "transient"
    
    return "unknown"


def safe_llm_call(llm, prompt, max_retries: int = 2, base_delay: float = 5.0):
    """
    Invoke an LLM with SMART error handling:
    - Fatal errors (quota gone, bad key): fail IMMEDIATELY with clear message
    - Transient errors (RPM spike, timeout): retry up to max_retries times
    - Unknown errors: retry once, then fail
    """
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            return llm.invoke(prompt)
        
        except Exception as e:
            last_error = e
            error_type = _classify_error(e)
            
            if error_type == "fatal":
                # Don't retry — it will NEVER work until user takes action
                error_msg = str(e)
                logger.error(f"FATAL API Error (not retrying): {error_msg}")
                
                if "unauthorized" in error_msg.lower() or "api_key" in error_msg.lower():
                    raise GroqQuotaExhausted(
                        f"❌ API Authentication Failed. Check your GROQ_API_KEY in .env\n"
                        f"   Original error: {e}"
                    ) from e
                else:
                    raise GroqQuotaExhausted(
                        f"❌ Groq API Quota Exhausted. Free tier limit reached.\n"
                        f"   → Wait for daily reset OR upgrade your Groq plan.\n"
                        f"   → You can also load cached results in the UI.\n"
                        f"   Original error: {e}"
                    ) from e
            
            elif error_type == "transient":
                if attempt < max_retries:
                    delay = base_delay * attempt  # Linear backoff: 5s, 10s
                    logger.warning(
                        f"Transient error (attempt {attempt}/{max_retries}), "
                        f"retrying in {delay}s: {e}"
                    )
                    print(f"\n   ⏳ Temporary API issue, retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Transient error persisted after {max_retries} attempts: {e}")
                    raise
            
            else:  # unknown
                if attempt == 1 and max_retries > 1:
                    logger.warning(f"Unknown error, trying once more: {e}")
                    time.sleep(base_delay)
                    continue
                else:
                    raise
    
    # Should never reach here, but just in case
    raise last_error
