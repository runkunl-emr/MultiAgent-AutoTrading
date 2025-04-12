import logging
import os
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
        }
        
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id
            
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        if hasattr(record, 'data') and record.data:
            log_data['data'] = record.data
            
        return json.dumps(log_data)


def setup_logging(level: str = "INFO", log_file: Optional[str] = None, json_format: bool = True):
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
    
    logger.addHandler(console_handler)
    
    # Add file handler if log_file is specified
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        
        if json_format:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
        
        logger.addHandler(file_handler)
    
    return logger


def log_with_context(logger, level: str, message: str, correlation_id: Optional[str] = None, 
                     data: Optional[Dict[str, Any]] = None):
    record = logging.LogRecord(
        name=logger.name,
        level=getattr(logging, level.upper()),
        pathname='',
        lineno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    
    if correlation_id:
        record.correlation_id = correlation_id
    
    if data:
        record.data = data
    
    logger.handle(record) 