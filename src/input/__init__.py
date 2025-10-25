"""
Input module for sheet music conversion MVP.

This module handles audio input from various sources:
- Local audio files (MP3, WAV)
- YouTube URLs (downloads and extracts audio)
- Audio format conversion and normalization

Modules:
- downloader: Handles YouTube audio extraction
- converter: Handles audio format conversion and normalization
"""

from .downloader import YouTubeDownloader
from .converter import AudioConverter

__all__ = ['YouTubeDownloader', 'AudioConverter']
