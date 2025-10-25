"""
Conversion module for sheet music conversion MVP.

This module handles MIDI to MusicXML conversion.
Converts MIDI files into MusicXML format suitable for notation editors.

Modules:
- midi_to_musicxml: Core conversion functionality using music21
"""

from .midi_to_musicxml import MidiToMusicXmlConverter

__all__ = ['MidiToMusicXmlConverter']
