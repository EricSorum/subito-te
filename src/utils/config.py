"""
Configuration Management Module

This module provides configuration management for the entire pipeline.
Handles loading, saving, and managing configuration settings across all modules.

Key Features:
- YAML-based configuration files
- Environment variable support
- Default configuration values
- Configuration validation
- Module-specific settings
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
import logging

# Configure logging for this module
logger = logging.getLogger(__name__)


class Config:
    """
    Configuration management class for the sheet music conversion pipeline.
    
    This class handles:
    - Loading configuration from YAML files
    - Environment variable overrides
    - Default configuration values
    - Configuration validation
    - Module-specific settings
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file (Optional[str]): Path to configuration file.
                                       If None, uses default config.yaml.
        """
        self.config_file = config_file or 'config.yaml'
        self.config_path = Path(self.config_file)
        
        # Default configuration
        self.default_config = {
            'general': {
                'log_level': 'INFO',
                'log_dir': './logs',
                'output_dir': './output',
                'temp_dir': './temp',
                'cleanup_temp_files': True
            },
            'input': {
                'supported_formats': ['mp3', 'wav', 'm4a', 'flac'],
                'target_sample_rate': 44100,
                'target_channels': 1,
                'target_bit_depth': 16,
                'normalize_audio': True,
                'youtube_download_timeout': 300
            },
            'transcription': {
                'model_path': None,
                'onset_threshold': 0.5,
                'frame_threshold': 0.3,
                'minimum_note_length': 0.1,
                'minimum_frequency': 80,
                'maximum_frequency': 8000,
                'confidence_threshold': 0.3
            },
            'conversion': {
                'quantize': True,
                'quantize_quarter_length': 0.25,
                'remove_redundant_rests': True,
                'infer_key_signature': True,
                'infer_time_signature': True,
                'add_tempo_markings': True,
                'cleanup_overlapping_notes': True
            },
            'refinement': {
                'enabled': True,
                'model': 'gpt-4',
                'temperature': 0.3,
                'max_tokens': 4000,
                'timeout': 60,
                'style': 'general',
                'remove_redundant_rests': True,
                'fix_quantization_errors': True,
                'infer_key_signature': True,
                'infer_time_signature': True,
                'add_tempo_markings': True,
                'add_phrasing_hints': True,
                'cleanup_overlapping_notes': True
            },
            'output': {
                'pdf_quality': 'high',
                'pdf_resolution': 300,
                'include_metadata': True,
                'page_size': 'A4',
                'margins': 'normal',
                'musescore_path': None
            },
            'api': {
                'openai_api_key': None,
                'openai_base_url': None,
                'timeout': 60,
                'retry_attempts': 3
            }
        }
        
        # Load configuration
        self.config = self._load_config()
        
        # Apply environment variable overrides
        self._apply_env_overrides()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file or create default.
        
        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {self.config_path}")
                return self._merge_configs(self.default_config, config)
            except Exception as e:
                logger.warning(f"Failed to load config file {self.config_path}: {e}")
                logger.info("Using default configuration")
                return self.default_config.copy()
        else:
            logger.info(f"Config file {self.config_path} not found, using defaults")
            return self.default_config.copy()
    
    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge user configuration with default configuration.
        
        Args:
            default (Dict[str, Any]): Default configuration
            user (Dict[str, Any]): User configuration
            
        Returns:
            Dict[str, Any]: Merged configuration
        """
        merged = default.copy()
        
        for section, values in user.items():
            if section in merged:
                if isinstance(values, dict) and isinstance(merged[section], dict):
                    merged[section].update(values)
                else:
                    merged[section] = values
            else:
                merged[section] = values
        
        return merged
    
    def _apply_env_overrides(self) -> None:
        """
        Apply environment variable overrides to configuration.
        """
        env_mappings = {
            'LOG_LEVEL': ('general', 'log_level'),
            'OUTPUT_DIR': ('general', 'output_dir'),
            'OPENAI_API_KEY': ('api', 'openai_api_key'),
            'MUSESCORE_PATH': ('output', 'musescore_path'),
            'TRANSCRIPTION_MODEL_PATH': ('transcription', 'model_path'),
            'REFINEMENT_MODEL': ('refinement', 'model'),
            'PDF_QUALITY': ('output', 'pdf_quality')
        }
        
        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if key in ['log_level', 'pdf_quality', 'style', 'model']:
                    self.config[section][key] = value
                elif key in ['target_sample_rate', 'target_channels', 'target_bit_depth', 
                            'pdf_resolution', 'timeout', 'retry_attempts']:
                    self.config[section][key] = int(value)
                elif key in ['onset_threshold', 'frame_threshold', 'minimum_note_length',
                            'confidence_threshold', 'temperature']:
                    self.config[section][key] = float(value)
                elif key in ['normalize_audio', 'quantize', 'remove_redundant_rests',
                            'infer_key_signature', 'infer_time_signature', 'add_tempo_markings',
                            'cleanup_overlapping_notes', 'enabled', 'include_metadata',
                            'cleanup_temp_files']:
                    self.config[section][key] = value.lower() in ('true', '1', 'yes', 'on')
                else:
                    self.config[section][key] = value
                
                logger.info(f"Applied environment override: {env_var} -> {section}.{key} = {value}")
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            section (str): Configuration section
            key (str): Configuration key
            default (Any): Default value if not found
            
        Returns:
            Any: Configuration value
        """
        try:
            return self.config.get(section, {}).get(key, default)
        except KeyError:
            return default
    
    def def set(self, section: str, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            section (str): Configuration section
            key (str): Configuration key
            value (Any): Value to set
        """
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get an entire configuration section.
        
        Args:
            section (str): Configuration section name
            
        Returns:
            Dict[str, Any]: Section configuration
        """
        return self.config.get(section, {})
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate configuration values.
        
        Returns:
            Dict[str, Any]: Validation results
        """
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validate general settings
        log_level = self.get('general', 'log_level')
        if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            validation_results['errors'].append(f"Invalid log_level: {log_level}")
        
        # Validate input settings
        sample_rate = self.get('input', 'target_sample_rate')
        if not isinstance(sample_rate, int) or sample_rate <= 0:
            validation_results['errors'].append(f"Invalid target_sample_rate: {sample_rate}")
        
        # Validate transcription settings
        onset_threshold = self.get('transcription', 'onset_threshold')
        if not isinstance(onset_threshold, (int, float)) or not 0 <= onset_threshold <= 1:
            validation_results['errors'].append(f"Invalid onset_threshold: {onset_threshold}")
        
        # Validate refinement settings
        if self.get('refinement', 'enabled'):
            api_key = self.get('api', 'openai_api_key')
            if not api_key:
                validation_results['warnings'].append("OpenAI API key not set, refinement will fail")
        
        # Validate output settings
        pdf_quality = self.get('output', 'pdf_quality')
        if pdf_quality not in ['low', 'medium', 'high']:
            validation_results['errors'].append(f"Invalid pdf_quality: {pdf_quality}")
        
        validation_results['valid'] = len(validation_results['errors']) == 0
        return validation_results
    
    def save(self, config_file: Optional[str] = None) -> bool:
        """
        Save configuration to file.
        
        Args:
            config_file (Optional[str]): Path to save configuration.
                                       If None, uses current config file.
        
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            save_path = Path(config_file) if config_file else self.config_path
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            
            logger.info(f"Configuration saved to {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def reset_to_defaults(self) -> None:
        """
        Reset configuration to default values.
        """
        self.config = self.default_config.copy()
        logger.info("Configuration reset to defaults")
    
    def get_module_config(self, module_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific module.
        
        Args:
            module_name (str): Name of the module
            
        Returns:
            Dict[str, Any]: Module-specific configuration
        """
        module_configs = {
            'input': ['input', 'general'],
            'transcription': ['transcription', 'general'],
            'conversion': ['conversion', 'general'],
            'refinement': ['refinement', 'api', 'general'],
            'output': ['output', 'general']
        }
        
        config = {}
        for section in module_configs.get(module_name, ['general']):
            config.update(self.get_section(section))
        
        return config


def load_config(config_file: Optional[str] = None) -> Config:
    """
    Load configuration from file.
    
    Args:
        config_file (Optional[str]): Path to configuration file
        
    Returns:
        Config: Configuration object
    """
    return Config(config_file)


def save_config(config: Config, config_file: Optional[str] = None) -> bool:
    """
    Save configuration to file.
    
    Args:
        config (Config): Configuration object to save
        config_file (Optional[str]): Path to save configuration
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    return config.save(config_file)


def create_default_config(config_file: str = 'config.yaml') -> bool:
    """
    Create a default configuration file.
    
    Args:
        config_file (str): Path to configuration file
        
    Returns:
        bool: True if created successfully, False otherwise
    """
    try:
        config = Config()
        config.save(config_file)
        logger.info(f"Default configuration created at {config_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to create default configuration: {e}")
        return False
