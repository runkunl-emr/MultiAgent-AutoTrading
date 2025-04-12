import time
import logging
from typing import Any, Callable, TypeVar, cast
from enum import Enum
from functools import wraps

T = TypeVar('T')
logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "CLOSED"  # Normal operation - requests pass through
    OPEN = "OPEN"      # Circuit is open - requests fail fast
    HALF_OPEN = "HALF_OPEN"  # Testing if service is back


class CircuitBreaker:
    def __init__(self, service_name: str, failure_threshold: int = 5, 
                 reset_timeout: int = 60, half_open_max_calls: int = 1):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED
        self.half_open_count = 0
    
    def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.reset_timeout:
                logger.info(f"Circuit for {self.service_name} transitioning from OPEN to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.half_open_count = 0
            else:
                raise CircuitBreakerError(f"Circuit for {self.service_name} is OPEN")
        
        if self.state == CircuitState.HALF_OPEN and self.half_open_count >= self.half_open_max_calls:
            raise CircuitBreakerError(f"Circuit for {self.service_name} is HALF_OPEN and max calls reached")
        
        try:
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_count += 1
            
            result = func(*args, **kwargs)
            
            # If we get here, the call was successful
            if self.state == CircuitState.HALF_OPEN:
                logger.info(f"Circuit for {self.service_name} transitioning from HALF_OPEN to CLOSED")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.half_open_count = 0
            
            return result
        
        except Exception as e:
            self.record_failure()
            raise e
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if (self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold) or \
           self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit for {self.service_name} transitioning to OPEN due to failures")
            self.state = CircuitState.OPEN
    
    def reset(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.half_open_count = 0
        logger.info(f"Circuit for {self.service_name} has been manually reset")
    
    def get_state(self) -> CircuitState:
        return self.state


class CircuitBreakerError(Exception):
    pass


def circuit_breaker(circuit: CircuitBreaker):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return circuit.execute(func, *args, **kwargs)
        return wrapper
    return decorator 