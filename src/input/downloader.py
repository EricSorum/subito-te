"""
YouTube Audio Downloader

This module handles downloading and extracting audio from YouTube URLs.
Uses yt-dlp for robust YouTube video processing and audio extraction.

Key Features:
- Downloads audio from YouTube URLs
- Extracts audio in various formats (MP3, WAV, etc.)
- Handles various YouTube URL formats
- Provides metadata about the downloaded content
- Error handling for invalid URLs or network issues
"""

import os
import subprocess
import tempfile
from typing import Optional, Dict, Any
from pathlib import Path
import logging

# Configure logging for this module
logger = logging.getLogger(__name__)


class YouTubeDownloader:
    """
    Handles downloading audio from YouTube URLs using yt-dlp.
    
    This class provides methods to:
    - Download audio from YouTube URLs
    - Extract metadata (title, duration, etc.)
    - Handle various audio formats
    - Manage temporary files
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the YouTube downloader.
        
        Args:
            output_dir (Optional[str]): Directory to save downloaded files.
                                      If None, uses system temp directory.
        """
        self.output_dir = output_dir or tempfile.gettempdir()
        self.output_path = Path(self.output_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # yt-dlp configuration for audio extraction
        self.ytdlp_config = {
            'format': 'bestaudio/best',  # Prefer best audio quality
            'outtmpl': str(self.output_path / '%(title)s.%(ext)s'),
            'extractaudio': True,
            'audioformat': 'wav',  # Extract as WAV for better quality
            'noplaylist': True,    # Don't download playlists
            'quiet': True,         # Suppress yt-dlp output
        }
    
    def download_audio(self, url: str, output_filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Download audio from a YouTube URL.
        
        Args:
            url (str): YouTube URL to download from
            output_filename (Optional[str]): Custom filename for output.
                                           If None, uses video title.
        
        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'file_path': Path to downloaded audio file
                - 'title': Video title
                - 'duration': Video duration in seconds
                - 'success': Boolean indicating success
                - 'error': Error message if failed
        
        Raises:
            ValueError: If URL is invalid or not a YouTube URL
            subprocess.CalledProcessError: If yt-dlp command fails
        """
        logger.info(f"Starting download from URL: {url}")
        
        # Validate URL format
        if not self._is_valid_youtube_url(url):
            error_msg = f"Invalid YouTube URL: {url}"
            logger.error(error_msg)
            return {
                'file_path': None,
                'title': None,
                'duration': None,
                'success': False,
                'error': error_msg
            }
        
        try:
            # Prepare yt-dlp command
            cmd = ['yt-dlp']
            
            # Add format options
            cmd.extend(['-f', 'bestaudio/best'])
            cmd.extend(['-x', '--audio-format', 'wav'])
            cmd.extend(['--no-playlist'])
            cmd.extend(['-q'])  # Quiet mode
            
            # Set output template
            if output_filename:
                output_template = str(self.output_path / f"{output_filename}.%(ext)s")
            else:
                output_template = str(self.output_path / '%(title)s.%(ext)s')
            
            cmd.extend(['-o', output_template])
            
            # Add URL
            cmd.append(url)
            
            logger.debug(f"Executing yt-dlp command: {' '.join(cmd)}")
            
            # Execute yt-dlp command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300  # 5 minute timeout
            )
            
            # Extract metadata from the output
            metadata = self._extract_metadata(url)
            
            # Find the downloaded file
            downloaded_file = self._find_downloaded_file(metadata.get('title', 'unknown'))
            
            if downloaded_file and downloaded_file.exists():
                logger.info(f"Successfully downloaded: {downloaded_file}")
                return {
                    'file_path': str(downloaded_file),
                    'title': metadata.get('title', 'Unknown'),
                    'duration': metadata.get('duration', 0),
                    'success': True,
                    'error': None
                }
            else:
                error_msg = "Downloaded file not found"
                logger.error(error_msg)
                return {
                    'file_path': None,
                    'title': metadata.get('title'),
                    'duration': metadata.get('duration'),
                    'success': False,
                    'error': error_msg
                }
                
        except subprocess.TimeoutExpired:
            error_msg = "Download timed out after 5 minutes"
            logger.error(error_msg)
            return {
                'file_path': None,
                'title': None,
                'duration': None,
                'success': False,
                'error': error_msg
            }
        except subprocess.CalledProcessError as e:
            error_msg = f"yt-dlp failed: {e.stderr}"
            logger.error(error_msg)
            return {
                'file_path': None,
                'title': None,
                'duration': None,
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error during download: {str(e)}"
            logger.error(error_msg)
            return {
                'file_path': None,
                'title': None,
                'duration': None,
                'success': False,
                'error': error_msg
            }
    
    def _is_valid_youtube_url(self, url: str) -> bool:
        """
        Check if the URL is a valid YouTube URL.
        
        Args:
            url (str): URL to validate
            
        Returns:
            bool: True if valid YouTube URL, False otherwise
        """
        youtube_domains = [
            'youtube.com',
            'youtu.be',
            'm.youtube.com',
            'www.youtube.com'
        ]
        
        url_lower = url.lower()
        return any(domain in url_lower for domain in youtube_domains)
    
    def _extract_metadata(self, url: str) -> Dict[str, Any]:
        """
        Extract metadata from YouTube URL without downloading.
        
        Args:
            url (str): YouTube URL
            
        Returns:
            Dict[str, Any]: Metadata dictionary
        """
        try:
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-download',
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            
            import json
            metadata = json.loads(result.stdout)
            
            return {
                'title': metadata.get('title', 'Unknown'),
                'duration': metadata.get('duration', 0),
                'uploader': metadata.get('uploader', 'Unknown'),
                'view_count': metadata.get('view_count', 0)
            }
            
        except Exception as e:
            logger.warning(f"Could not extract metadata: {e}")
            return {
                'title': 'Unknown',
                'duration': 0,
                'uploader': 'Unknown',
                'view_count': 0
            }
    
    def _find_downloaded_file(self, title: str) -> Optional[Path]:
        """
        Find the downloaded file in the output directory.
        
        Args:
            title (str): Expected title of the file
            
        Returns:
            Optional[Path]: Path to the downloaded file, or None if not found
        """
        # Look for WAV files in the output directory
        wav_files = list(self.output_path.glob("*.wav"))
        
        if not wav_files:
            return None
        
        # If we have the title, try to find exact match
        if title and title != 'Unknown':
            for file_path in wav_files:
                if title.lower() in file_path.stem.lower():
                    return file_path
        
        # Return the most recently modified file
        return max(wav_files, key=lambda f: f.stat().st_mtime)
    
    def cleanup(self, file_path: str) -> bool:
        """
        Clean up downloaded file.
        
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
