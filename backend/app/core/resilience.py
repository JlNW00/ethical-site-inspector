from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

import structlog

logger = structlog.get_logger("core.resilience")

T = TypeVar("T")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2**attempt), max_delay)
                        logger.warning(
                            "retry_attempt",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=delay,
                            error=str(e),
                        )
                        time.sleep(delay)
            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        name: str = "default",
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._state = "closed"

    @property
    def state(self) -> str:
        if self._state == "open" and time.time() - self._last_failure_time >= self.recovery_timeout:
            self._state = "half-open"
        return self._state

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        if self.state == "open":
            logger.error("circuit_breaker_open", name=self.name, failure_count=self._failure_count)
            raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self) -> None:
        self._failure_count = 0
        self._state = "closed"

    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.error(
                "circuit_breaker_tripped",
                name=self.name,
                failure_count=self._failure_count,
            )


class CircuitBreakerOpenError(Exception):
    pass
