import time
import logging
import random
from functools import wraps
from typing import Type, List, Callable, TypeVar, Any, Optional

T = TypeVar('T')
logger = logging.getLogger(__name__)


def retry_with_backoff(max_retries: int = 3, 
                       backoff_factor: float = 2.0, 
                       jitter: bool = True,
                       initial_delay: float = 0.1,
                       max_delay: float = 10.0,
                       exception_types: List[Type[Exception]] = None):
    
    if exception_types is None:
        exception_types = [Exception]
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            retries = 0
            delay = initial_delay
            
            while True:
                try:
                    return func(*args, **kwargs)
                except tuple(exception_types) as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Failed after {max_retries} retries: {e}")
                        raise
                    
                    # Calculate delay with optional jitter
                    current_delay = min(delay * (backoff_factor ** (retries - 1)), max_delay)
                    if jitter:
                        current_delay = current_delay * (0.5 + random.random())
                    
                    logger.warning(f"Retry {retries}/{max_retries} after error: {e}. "
                                  f"Waiting {current_delay:.2f}s...")
                    
                    time.sleep(current_delay)
                except Exception as e:
                    # Don't retry unexpected exceptions
                    logger.error(f"Unexpected error (not retrying): {e}")
                    raise
        
        return wrapper
    
    return decorator


def retry_on_specific_errors(func: Optional[Callable] = None, 
                             retries: int = 3, 
                             error_types: List[Type[Exception]] = None):
    
    if error_types is None:
        error_types = [Exception]
    
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < retries:
                try:
                    return f(*args, **kwargs)
                except tuple(error_types) as e:
                    attempt += 1
                    if attempt == retries:
                        logger.error(f"Failed after {retries} attempts: {e}")
                        raise
                    logger.warning(f"Retry attempt {attempt}/{retries} after error: {e}")
                except Exception as e:
                    # Don't retry other exceptions
                    logger.error(f"Unexpected error (not retrying): {e}")
                    raise
        return wrapper
    
    # Allow use as either @retry_on_specific_errors or @retry_on_specific_errors()
    if func is not None:
        return decorator(func)
    return decorator 