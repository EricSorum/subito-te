"""
Audio Converter

This module handles audio format conversion and normalization.
Converts various audio formats (MP3, WAV, etc.) to standardized WAV format
suitable for transcription.

Key Features:
- Converts audio files to standardized WAV format
- Normalizes audio levels and sample rates
- Handles stereo/mono conversion
- Provides audio metadata extraction
- Error handling for corrupted or unsupported files
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import logging
import tempfile

# Configure logging for this module
logger = logging.getLogger(__name__)


class AudioConverter:
    """
    Handles audio format conversion and normalization using ffmpeg.
    
    This class provides methods to:
    - Convert audio files to standardized WAV format
    - Normalize audio levels and sample rates
    - Extract audio metadata
    - Handle various input formats
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the audio converter.
        
        Args:
            output_dir (Optional[str]): Directory to save converted files.
                                      If None, uses system temp directory.
        """
        self.output_dir = output_dir or tempfile.gettempdir()
        self.output_path = Path(self.output_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Standardized audio format settings
        self.target_format = {
            'sample_rate': 44100,    # 44.1 kHz standard
            'channels': 1,           # Mono for better transcription
            'bit_depth': 16,         # 16-bit depth
            'format': 'wav'          # WAV format
        }
    
    def convert_to_wav(self, input_path: str, output_filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Convert audio file to standardized WAV format.
        
        Args:
            input_path (str): Path to input audio file
            output_filename (Optional[str]): Custom filename for output.
                                           If None, uses input filename with .wav extension
        
        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'file_path': Path to converted WAV file
                - 'metadata': Audio metadata (duration, sample_rate, etc.)
                - 'success': Boolean indicating success
                - 'error': Error message if failed
        
        Raises:
            FileNotFoundError: If input file doesn't exist
            subprocess.CalledProcessError: If ffmpeg command fails
        """
        logger.info(f"Converting audio file: {input_path}")
        
        # Validate input file
        input_file = Path(input_path)
        if not input_file.exists():
            error_msg = f"Input file not found: {input_path}"
            logger.error(error_msg)
            return {
                'file_path': None,
                'metadata': None,
                'success': False,
                'error': error_msg
            }
        
        # Generate output filename
        if output_filename:
            output_file = self.output_path / f"{output_filename}.wav"
        else:
            output_file = self.output_path / f"{input_file.stem}.wav"
        
        try:
            # Build ffmpeg command for conversion
            cmd = self._build_ffmpeg_command(input_path, str(output_file))
            
            logger.debug(f"Executing ffmpeg command: {' '.join(cmd)}")
            
            # Execute ffmpeg command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300  # 5 minute timeout
            )
            
            # Verify output file was created
            if output_file.exists() and output_file.stat().st_size > 0:
                # Extract metadata from converted file
                metadata = self._extract_metadata(str(output_file))
                
                logger.info(f"Successfully converted: {output_file}")
                return {
                    'file_path': str(output_file),
                    'metadata': metadata,
                    'success': True,
                    'error': None
                }
            else:
                error_msg = "Conversion failed - output file not created or empty"
                logger.error(error_msg)
                return {
                    'file_path': None,
                    'metadata': None,
                    'success': False,
                    'error': error_msg
                }
                
        except subprocess.TimeoutExpired:
            error_msg = "Conversion timed out after 5 minutes"
            logger.error(error_msg)
            return {
                'file_path': None,
                'metadata': None,
                'success': False,
                'error': error_msg
            }
        except subprocess.CalledProcessError as e:
            error_msg = f"ffmpeg failed: {e.stderr}"
            logger.error(error_msg)
            return {
                'file_path': None,
                'metadata': None,
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error during conversion: {str(e)}"
            logger.error(error_msg)
            return {
                'file_path': None,
                'metadata': None,
                'success': False,
                'error': error_msg
            }
    
    def _build_ffmpeg_command(self, input_path: str, output_path: str) -> list:
        """
        Build ffmpeg command for audio conversion.
        
        Args:
            input_path (str): Path to input file
            output_path (str): Path to output file
            
        Returns:
            list: ffmpeg command as list of strings
        """
        cmd = [
            'ffmpeg',
            '-i', input_path,                    # Input file
            '-ar', str(self.target_format['sample_rate']),  # Sample rate
            '-ac', str(self.target_format['channels']),     # Number of channels (mono)
            '-sample_fmt', 's16',                # 16-bit sample format
            '-acodec', 'pcm_s16le',             # PCM 16-bit little-endian codec
            '-y',                               # Overwrite output file
            output_path                          # Output file
        ]
        
        return cmd
    
    def _extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract audio metadata using ffprobe.
        
        Args:
            file_path (str): Path to audio file
            
        Returns:
            Dict[str, Any]: Audio metadata dictionary
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            
            import json
            probe_data = json.loads(result.stdout)
            
            # Extract relevant metadata
            format_info = probe_data.get('format', {})
            stream_info = probe_data.get('streams', [{}])[0]
            
            metadata = {
                'duration': float(format_info.get('duration', 0)),
                'sample_rate': int(stream_info.get('sample_rate', 0)),
                'channels': int(stream_info.get('channels', 0)),
                'bit_rate': int(format_info.get('bit_rate', 0)),
                'format_name': format_info.get('format_name', 'unknown'),
                'file_size': int(format_info.get('size', 0))
            }
            
            return metadata
            
        except Exception as e:
            logger.warning(f"Could not extract metadata: {e}")
            return {
                'duration': 0,
                'sample_rate': 0,
                'channels': 0,
                'bit_rate': 0,
                'format_name': 'unknown',
                'file_size': 0
            }
    
    def normalize_audio(self, input_path: str, output_path: str) -> bool:
        """
        Normalize audio levels using ffmpeg.
        
        Args:
            input_path (str): Path to input audio file
            output_path (str): Path to output normalized file
            
        Returns:
            bool: True if normalization successful, False otherwise
        """
        try:
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-af', 'loudnorm',  # Loudness normalization filter
                '-y',
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300
            )
            
            return Path(output_path).exists()
            
        except Exception as e:
            logger.error(f"Audio normalization failed: {e}")
            return False
    
    def get_audio_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get detailed audio information without conversion.
        
        Args:
            file_path (str): Path to audio file
            
        Returns:
            Dict[str, Any]: Audio information dictionary
        """
        return self._extract_metadata(file_path)
    
    def cleanup(self, file_path: str) -> bool:
        """
        Clean up converted file.
        
        Args:
            file_path (str): Path to file to delete
            
        Returns:
            bool: True if successfully deleted, False otherwise
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"Cleaned up file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cleanup file {file_path}: {e}")
            return False
