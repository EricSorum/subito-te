"""
Transcription module for sheet music conversion MVP.

This module handles audio-to-MIDI transcription using BasicPitch.
Converts WAV audio files into MIDI notation with pitch, timing, and confidence data.

Modules:
- transcribe: Core transcription functionality using BasicPitch
"""

from .transcribe import AudioTranscriber

__all__ = ['AudioTranscriber']
