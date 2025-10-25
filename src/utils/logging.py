"""
Logging Configuration Module

This module provides centralized logging configuration for the entire pipeline.
Sets up consistent logging across all modules with appropriate levels and formatting.

Key Features:
- Centralized logging configuration
- Module-specific loggers
- Log level management
- File and console output
- Timestamped log messages
- Error tracking and debugging
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


def setup_logging(log_level: str = 'INFO', log_file: Optional[str] = None, 
                 log_dir: str = './logs') -> None:
    """
    Set up centralized logging configuration for the entire pipeline.
    
    Args:
        log_level (str): Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        log_file (Optional[str]): Path to log file. If None, uses timestamped filename.
        log_dir (str): Directory for log files
    """
    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Generate log filename if not provided
    if log_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_path / f'sheet_music_conversion_{timestamp}.log'
    else:
        log_file = Path(log_file)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Error file handler (separate file for errors)
    error_file = log_path / f'errors_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    error_handler = logging.FileHandler(error_file, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # Log the setup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, File: {log_file}")
    logger.info(f"Error logging to: {error_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        name (str): Logger name (usually __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


def log_function_call(func):
    """
    Decorator to log function calls with parameters and results.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed with error: {str(e)}")
            raise
    
    return wrapper


def log_execution_time(func):
    """
    Decorator to log function execution time.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    import time
    
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.2f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f} seconds: {str(e)}")
            raise
    
    return wrapper


def log_pipeline_step(step_name: str, module_name: str):
    """
    Log a pipeline step with consistent formatting.
    
    Args:
        step_name (str): Name of the pipeline step
        module_name (str): Name of the module performing the step
    """
    logger = logging.getLogger(module_name)
    logger.info(f"🎵 Starting {step_name}")
    logger.info("=" * 50)


def log_pipeline_result(step_name: str, module_name: str, success: bool, 
                       duration: float, details: Optional[Dict[str, Any]] = None):
    """
    Log a pipeline step result with consistent formatting.
    
    Args:
        step_name (str): Name of the pipeline step
        module_name (str): Name of the module performing the step
        success (bool): Whether the step was successful
        duration (float): Duration of the step in seconds
        details (Optional[Dict[str, Any]]): Additional details to log
    """
    logger = logging.getLogger(module_name)
    
    if success:
        logger.info(f"✅ {step_name} completed successfully in {duration:.2f} seconds")
        if details:
            for key, value in details.items():
                logger.info(f"   {key}: {value}")
    else:
        logger.error(f"❌ {step_name} failed after {duration:.2f} seconds")
        if details:
            for key, value in details.items():
                logger.error(f"   {key}: {value}")
    
    logger.info("=" * 50)


def log_error(error: Exception, context: str = "", module_name: str = ""):
    """
    Log an error with context information.
    
    Args:
        error (Exception): The error that occurred
        context (str): Additional context about where the error occurred
        module_name (str): Name of the module where the error occurred
    """
    logger = logging.getLogger(module_name)
    
    error_msg = f"Error in {context}: {type(error).__name__}: {str(error)}"
    logger.error(error_msg)
    
    # Log stack trace for debugging
    import traceback
    logger.debug(f"Stack trace: {traceback.format_exc()}")


def log_performance_metrics(operation: str, duration: float, 
                           input_size: Optional[int] = None, 
                           output_size: Optional[int] = None,
                           module_name: str = ""):
    """
    Log performance metrics for an operation.
    
    Args:
        operation (str): Name of the operation
        duration (float): Duration in seconds
        input_size (Optional[int]): Size of input data
        output_size (Optional[int]): Size of output data
        module_name (str): Name of the module
    """
    logger = logging.getLogger(module_name)
    
    metrics = {
        'operation': operation,
        'duration': f"{duration:.2f}s",
        'input_size': input_size,
        'output_size': output_size
    }
    
    if input_size and output_size:
        efficiency = output_size / input_size if input_size > 0 else 0
        metrics['efficiency'] = f"{efficiency:.2f}"
    
    logger.info(f"Performance metrics: {metrics}")


def setup_module_logging(module_name: str, log_level: str = 'INFO') -> logging.Logger:
    """
    Set up logging for a specific module.
    
    Args:
        module_name (str): Name of the module
        log_level (str): Logging level for the module
        
    Returns:
        logging.Logger: Configured logger for the module
    """
    logger = logging.getLogger(module_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Add module-specific handler if needed
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            f'%(asctime)s - {module_name} - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def log_system_info():
    """
    Log system information for debugging purposes.
    """
    logger = logging.getLogger(__name__)
    
    import platform
    import sys
    
    system_info = {
        'platform': platform.platform(),
        'python_version': sys.version,
        'architecture': platform.architecture(),
        'processor': platform.processor()
    }
    
    logger.info("System Information:")
    for key, value in system_info.items():
        logger.info(f"  {key}: {value}")


def log_dependencies():
    """
    Log information about required dependencies.
    """
    logger = logging.getLogger(__name__)
    
    dependencies = [
        'basic-pitch',
        'music21',
        'yt-dlp',
        'openai',
        'ffmpeg-python'
    ]
    
    logger.info("Checking dependencies:")
    for dep in dependencies:
        try:
            __import__(dep.replace('-', '_'))
            logger.info(f"  ✅ {dep}")
        except ImportError:
            logger.warning(f"  ❌ {dep} - Not installed")
        except Exception as e:
            logger.warning(f"  ❓ {dep} - Unknown status: {e}")
