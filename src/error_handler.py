"""Error handling and retry logic for Google Ads API operations."""

import time
import random
from typing import Any, Callable, Optional, TypeVar, Union, List
from functools import wraps
from datetime import datetime, timedelta

from google.ads.googleads.errors import GoogleAdsException
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import structlog
import httpx

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class GoogleAdsError:
    """Structured representation of a Google Ads API error."""
    
    def __init__(self, error: Any):
        self.error_code = error.error_code
        self.message = error.message
        self.trigger = getattr(error, "trigger", None)
        self.location = getattr(error, "location", None)
        self.details = getattr(error, "details", None)
        
    def is_retryable(self) -> bool:
        """Check if this error is retryable."""
        retryable_codes = {
            "INTERNAL_ERROR",
            "TRANSIENT_ERROR", 
            "DEADLINE_EXCEEDED",
            "RESOURCE_EXHAUSTED",
            "QUOTA_ERROR",
        }
        
        # Check if any error code component is retryable
        for attr in dir(self.error_code):
            if not attr.startswith("_") and getattr(self.error_code, attr) in retryable_codes:
                return True
        return False
        
    def get_error_type(self) -> str:
        """Get the primary error type."""
        # Find the first non-UNSPECIFIED error code
        for attr in dir(self.error_code):
            if not attr.startswith("_"):
                value = getattr(self.error_code, attr)
                if value and value != "UNSPECIFIED":
                    return f"{attr}.{value}"
        return "UNKNOWN_ERROR"
        
    def get_documentation_url(self) -> Optional[str]:
        """Get documentation URL for this error type."""
        error_type = self.get_error_type()
        if "." in error_type:
            category, _ = error_type.split(".", 1)
            category_lower = category.lower().replace("_", "-")
            return f"https://developers.google.com/google-ads/api/reference/rpc/v20/errors#{category_lower}"
        return None
        
    def __str__(self) -> str:
        parts = [f"Error: {self.get_error_type()}"]
        if self.message:
            parts.append(f"Message: {self.message}")
        if self.trigger:
            parts.append(f"Trigger: {self.trigger}")
        if self.location:
            parts.append(f"Location: {self.location}")
        return " | ".join(parts)


class ErrorHandler:
    """Handles Google Ads API errors with retry logic and documentation lookup."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 5.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._error_cache = {}
        
    def parse_exception(self, exception: GoogleAdsException) -> List[GoogleAdsError]:
        """Parse a GoogleAdsException into structured errors."""
        errors = []
        for error in exception.failure.errors:
            errors.append(GoogleAdsError(error))
        return errors
        
    def should_retry(self, exception: Exception) -> bool:
        """Determine if an exception should trigger a retry."""
        if isinstance(exception, GoogleAdsException):
            errors = self.parse_exception(exception)
            return any(error.is_retryable() for error in errors)
        elif isinstance(exception, (httpx.TimeoutException, httpx.ConnectError)):
            return True
        return False
        
    def get_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff and jitter."""
        delay = self.base_delay * (2 ** (attempt - 1))
        jitter = random.uniform(0, delay * 0.1)  # 10% jitter
        return min(delay + jitter, 60.0)  # Cap at 60 seconds
        
    async def lookup_documentation(self, error: GoogleAdsError) -> Optional[str]:
        """Look up documentation for an error."""
        cache_key = error.get_error_type()
        
        # Check cache
        if cache_key in self._error_cache:
            return self._error_cache[cache_key]
            
        doc_url = error.get_documentation_url()
        if not doc_url:
            return None
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(doc_url, timeout=10.0)
                if response.status_code == 200:
                    # Extract relevant section (this is simplified)
                    content = f"Documentation: {doc_url}\n"
                    content += "See the official docs for detailed error explanations."
                    self._error_cache[cache_key] = content
                    return content
        except Exception as e:
            logger.warning(f"Failed to fetch documentation: {e}")
            
        return None
        
    def format_error_response(self, exception: GoogleAdsException, include_docs: bool = True) -> dict:
        """Format an exception into a structured response."""
        errors = self.parse_exception(exception)
        
        response = {
            "success": False,
            "error_count": len(errors),
            "errors": [],
            "is_retryable": any(e.is_retryable() for e in errors),
            "request_id": getattr(exception, "request_id", None),
        }
        
        for error in errors:
            error_info = {
                "type": error.get_error_type(),
                "message": error.message,
                "trigger": error.trigger,
                "location": error.location,
                "is_retryable": error.is_retryable(),
            }
            
            if include_docs and (doc_url := error.get_documentation_url()):
                error_info["documentation_url"] = doc_url
                
            response["errors"].append(error_info)
            
        return response
        
    def with_retry(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to add retry logic to a function."""
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(1, self.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if not self.should_retry(e):
                        logger.error(
                            "Non-retryable error encountered",
                            error=str(e),
                            attempt=attempt,
                        )
                        raise
                        
                    if attempt < self.max_retries:
                        delay = self.get_retry_delay(attempt)
                        logger.warning(
                            f"Retryable error, waiting {delay:.1f}s before retry",
                            error=str(e),
                            attempt=attempt,
                            max_attempts=self.max_retries,
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "Max retries exceeded",
                            error=str(e),
                            attempts=self.max_retries,
                        )
                        
            raise last_exception
            
        return wrapper
        
    def handle_partial_failure(self, response: Any) -> dict:
        """Handle responses with partial failures."""
        result = {
            "success": True,
            "partial_failure": False,
            "results": [],
            "failures": [],
        }
        
        if hasattr(response, "partial_failure_error") and response.partial_failure_error:
            result["partial_failure"] = True
            
            # Parse partial failure details
            for error in response.partial_failure_error.errors:
                failure_info = {
                    "index": getattr(error, "field_path", [None])[0] if hasattr(error, "field_path") else None,
                    "error": str(GoogleAdsError(error)),
                }
                result["failures"].append(failure_info)
                
        # Extract successful results
        if hasattr(response, "results"):
            for i, result_item in enumerate(response.results):
                if not any(f["index"] == i for f in result["failures"]):
                    result["results"].append(result_item)
                    
        return result


class RetryableGoogleAdsClient:
    """Wrapper for GoogleAdsClient that adds automatic retry logic."""
    
    def __init__(self, client: Any, error_handler: Optional[ErrorHandler] = None):
        self._client = client
        self._error_handler = error_handler or ErrorHandler()
        
    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to the underlying client."""
        attr = getattr(self._client, name)
        
        # If it's a service getter, wrap the service
        if name == "get_service":
            def wrapped_get_service(service_name: str, version: str = "v20") -> Any:
                service = attr(service_name, version)
                return RetryableService(service, self._error_handler)
            return wrapped_get_service
            
        return attr


class RetryableService:
    """Wrapper for Google Ads services that adds retry logic to all methods."""
    
    def __init__(self, service: Any, error_handler: ErrorHandler):
        self._service = service
        self._error_handler = error_handler
        
    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to the underlying service."""
        attr = getattr(self._service, name)
        
        # If it's a callable method, wrap it with retry logic
        if callable(attr):
            return self._error_handler.with_retry(attr)
            
        return attr