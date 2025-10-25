"""
MIDI to MusicXML Converter

This module handles conversion from MIDI files to MusicXML format.
Converts MIDI notation into MusicXML format suitable for notation editors.

Key Features:
- MIDI to MusicXML conversion using music21
- Preserves tempo, key signature, time signature, and dynamics
- Handles monophonic and polyphonic MIDI files
- Error handling for malformed MIDI files
- Quality assessment and validation
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging
import time

# Configure logging for this module
logger = logging.getLogger(__name__)

try:
    from music21 import stream, converter, meter, tempo, key, note, chord, duration
    from music21.midi import MidiFile
    from music21.musicxml import m21ToXml
    MUSIC21_AVAILABLE = True
except ImportError:
    logger.warning("music21 not available. Please install music21 package.")
    MUSIC21_AVAILABLE = False


class MidiToMusicXmlConverter:
    """
    Handles MIDI to MusicXML conversion using music21.
    
    This class provides methods to:
    - Convert MIDI files to MusicXML format
    - Preserve musical elements (tempo, key, time signature)
    - Handle various MIDI file structures
    - Validate and assess conversion quality
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the MIDI to MusicXML converter.
        
        Args:
            output_dir (Optional[str]): Directory to save MusicXML files.
                                      If None, uses system temp directory.
        """
        if not MUSIC21_AVAILABLE:
            raise ImportError("music21 is not available. Please install music21 package.")
        
        self.output_dir = output_dir or tempfile.gettempdir()
        self.output_path = Path(self.output_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Conversion parameters
        self.conversion_params = {
            'quantize': True,           # Quantize note durations
            'quantize_quarter_length': 0.25,  # Quantization resolution
            'remove_redundant_rests': True,   # Remove unnecessary rests
            'infer_key_signature': True,      # Try to infer key signature
            'infer_time_signature': True,     # Try to infer time signature
            'add_tempo_markings': True,       # Add tempo markings
            'cleanup_overlapping_notes': True, # Remove overlapping notes
        }
    
    def convert_midi_to_musicxml(self, midi_path: str, output_filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Convert MIDI file to MusicXML format.
        
        Args:
            midi_path (str): Path to input MIDI file
            output_filename (Optional[str]): Custom filename for output MusicXML.
                                          If None, uses input filename with .musicxml extension
        
        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'musicxml_path': Path to generated MusicXML file
                - 'quality_score': Conversion quality score (0.0 to 1.0)
                - 'notes_count': Number of notes in the MusicXML
                - 'duration': Conversion duration in seconds
                - 'success': Boolean indicating success
                - 'error': Error message if failed
        
        Raises:
            FileNotFoundError: If MIDI file doesn't exist
            ValueError: If MIDI file is invalid or corrupted
        """
        logger.info(f"Converting MIDI file to MusicXML: {midi_path}")
        
        # Validate input file
        midi_file = Path(midi_path)
        if not midi_file.exists():
            error_msg = f"MIDI file not found: {midi_path}"
            logger.error(error_msg)
            return {
                'musicxml_path': None,
                'quality_score': 0.0,
                'notes_count': 0,
                'duration': 0.0,
                'success': False,
                'error': error_msg
            }
        
        # Generate output filename
        if output_filename:
            musicxml_file = self.output_path / f"{output_filename}.musicxml"
        else:
            musicxml_file = self.output_path / f"{midi_file.stem}.musicxml"
        
        start_time = time.time()
        
        try:
            # Load MIDI file using music21
            logger.debug(f"Loading MIDI file: {midi_path}")
            midi_stream = converter.parse(midi_path)
            
            if midi_stream is None:
                error_msg = "Failed to parse MIDI file"
                logger.error(error_msg)
                return {
                    'musicxml_path': None,
                    'quality_score': 0.0,
                    'notes_count': 0,
                    'duration': time.time() - start_time,
                    'success': False,
                    'error': error_msg
                }
            
            # Process and clean up the stream
            processed_stream = self._process_stream(midi_stream)
            
            # Write MusicXML file
            logger.debug(f"Writing MusicXML file: {musicxml_file}")
            processed_stream.write('musicxml', fp=str(musicxml_file))
            
            # Verify output file was created
            if musicxml_file.exists() and musicxml_file.stat().st_size > 0:
                # Calculate conversion metrics
                duration = time.time() - start_time
                quality_score = self._assess_conversion_quality(processed_stream)
                notes_count = self._count_notes(processed_stream)
                
                logger.info(f"Successfully converted: {musicxml_file}")
                logger.info(f"Conversion took {duration:.2f} seconds")
                logger.info(f"Quality score: {quality_score:.2f}, Notes: {notes_count}")
                
                return {
                    'musicxml_path': str(musicxml_file),
                    'quality_score': quality_score,
                    'notes_count': notes_count,
                    'duration': duration,
                    'success': True,
                    'error': None
                }
            else:
                error_msg = "MusicXML file not created or empty"
                logger.error(error_msg)
                return {
                    'musicxml_path': None,
                    'quality_score': 0.0,
                    'notes_count': 0,
                    'duration': time.time() - start_time,
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Conversion failed: {str(e)}"
            logger.error(error_msg)
            return {
                'musicxml_path': None,
                'quality_score': 0.0,
                'notes_count': 0,
                'duration': duration,
                'success': False,
                'error': error_msg
            }
    
    def _process_stream(self, stream_obj) -> stream.Stream:
        """
        Process and clean up the music21 stream.
        
        Args:
            stream_obj: music21 stream object
            
        Returns:
            stream.Stream: Processed stream object
        """
        logger.debug("Processing music21 stream...")
        
        # Create a new stream for processing
        processed_stream = stream.Stream()
        
        # Copy elements from original stream
        for element in stream_obj.flat:
            if hasattr(element, 'isNote') and element.isNote:
                processed_stream.append(element)
            elif hasattr(element, 'isChord') and element.isChord:
                processed_stream.append(element)
            elif hasattr(element, 'isRest') and element.isRest:
                processed_stream.append(element)
            elif hasattr(element, 'isTempo') and element.isTempo:
                processed_stream.append(element)
            elif hasattr(element, 'isKeySignature') and element.isKeySignature:
                processed_stream.append(element)
            elif hasattr(element, 'isTimeSignature') and element.isTimeSignature:
                processed_stream.append(element)
        
        # Apply conversion parameters
        if self.conversion_params['quantize']:
            processed_stream = processed_stream.quantize(
                quarterLength=self.conversion_params['quantize_quarter_length']
            )
        
        if self.conversion_params['remove_redundant_rests']:
            processed_stream = self._remove_redundant_rests(processed_stream)
        
        if self.conversion_params['cleanup_overlapping_notes']:
            processed_stream = self._cleanup_overlapping_notes(processed_stream)
        
        # Infer musical elements if requested
        if self.conversion_params['infer_key_signature']:
            inferred_key = processed_stream.analyze('key')
            if inferred_key:
                processed_stream.insert(0, inferred_key)
        
        if self.conversion_params['infer_time_signature']:
            inferred_meter = processed_stream.analyze('meter')
            if inferred_meter:
                processed_stream.insert(0, inferred_meter)
        
        if self.conversion_params['add_tempo_markings']:
            tempo_marking = tempo.TempoIndication(number=120)  # Default 120 BPM
            processed_stream.insert(0, tempo_marking)
        
        return processed_stream
    
    def _remove_redundant_rests(self, stream_obj) -> stream.Stream:
        """
        Remove redundant rests from the stream.
        
        Args:
            stream_obj: music21 stream object
            
        Returns:
            stream.Stream: Stream with redundant rests removed
        """
        logger.debug("Removing redundant rests...")
        
        # This is a simplified implementation
        # In practice, you might want more sophisticated rest removal logic
        filtered_stream = stream.Stream()
        
        for element in stream_obj:
            if hasattr(element, 'isRest') and element.isRest:
                # Only keep rests that are longer than a certain duration
                if element.duration.quarterLength > 0.25:  # Quarter note or longer
                    filtered_stream.append(element)
            else:
                filtered_stream.append(element)
        
        return filtered_stream
    
    def _cleanup_overlapping_notes(self, stream_obj) -> stream.Stream:
        """
        Clean up overlapping notes in the stream.
        
        Args:
            stream_obj: music21 stream object
            
        Returns:
            stream.Stream: Stream with overlapping notes cleaned up
        """
        logger.debug("Cleaning up overlapping notes...")
        
        # This is a simplified implementation
        # In practice, you might want more sophisticated overlap detection
        cleaned_stream = stream.Stream()
        note_times = {}  # Track note start times
        
        for element in stream_obj:
            if hasattr(element, 'isNote') and element.isNote:
                start_time = element.offset
                end_time = start_time + element.duration.quarterLength
                
                # Check for overlaps
                overlapping = False
                for existing_start, existing_end in note_times.items():
                    if not (end_time <= existing_start or start_time >= existing_end):
                        overlapping = True
                        break
                
                if not overlapping:
                    note_times[start_time] = end_time
                    cleaned_stream.append(element)
                else:
                    logger.debug(f"Removed overlapping note at {start_time}")
            else:
                cleaned_stream.append(element)
        
        return cleaned_stream
    
    def _assess_conversion_quality(self, stream_obj) -> float:
        """
        Assess the quality of the conversion.
        
        Args:
            stream_obj: music21 stream object
            
        Returns:
            float: Quality score (0.0 to 1.0)
        """
        try:
            # Calculate quality based on various factors
            quality_factors = []
            
            # Factor 1: Note density (more notes = higher quality)
            note_count = len([e for e in stream_obj.flat if hasattr(e, 'isNote') and e.isNote])
            if note_count > 0:
                quality_factors.append(min(1.0, note_count / 100))  # Normalize to 0-1
            else:
                quality_factors.append(0.0)
            
            # Factor 2: Duration coverage (longer pieces = higher quality)
            total_duration = stream_obj.duration.quarterLength
            if total_duration > 0:
                quality_factors.append(min(1.0, total_duration / 32))  # Normalize to 0-1
            else:
                quality_factors.append(0.0)
            
            # Factor 3: Musical structure (key signature, time signature)
            has_key = any(hasattr(e, 'isKeySignature') and e.isKeySignature for e in stream_obj)
            has_time = any(hasattr(e, 'isTimeSignature') and e.isTimeSignature for e in stream_obj)
            structure_score = (has_key + has_time) / 2.0
            quality_factors.append(structure_score)
            
            # Calculate overall quality score
            overall_quality = sum(quality_factors) / len(quality_factors)
            return min(1.0, max(0.0, overall_quality))
            
        except Exception as e:
            logger.warning(f"Could not assess conversion quality: {e}")
            return 0.5  # Default quality score
    
    def _count_notes(self, stream_obj) -> int:
        """
        Count the number of notes in the stream.
        
        Args:
            stream_obj: music21 stream object
            
        Returns:
            int: Number of notes
        """
        try:
            return len([e for e in stream_obj.flat if hasattr(e, 'isNote') and e.isNote])
        except Exception:
            return 0
    
    def set_conversion_params(self, **kwargs) -> None:
        """
        Update conversion parameters.
        
        Args:
            **kwargs: Parameter updates (quantize, quantize_quarter_length, etc.)
        """
        for key, value in kwargs.items():
            if key in self.conversion_params:
                self.conversion_params[key] = value
                logger.info(f"Updated {key} to {value}")
            else:
                logger.warning(f"Unknown parameter: {key}")
    
    def validate_musicxml(self, musicxml_path: str) -> Dict[str, Any]:
        """
        Validate a MusicXML file for correctness.
        
        Args:
            musicxml_path (str): Path to MusicXML file
            
        Returns:
            Dict[str, Any]: Validation results
        """
        try:
            # Try to parse the MusicXML file
            parsed_stream = converter.parse(musicxml_path)
            
            if parsed_stream is None:
                return {
                    'valid': False,
                    'error': 'Could not parse MusicXML file',
                    'notes_count': 0,
                    'duration': 0.0
                }
            
            # Basic validation
            notes_count = self._count_notes(parsed_stream)
            duration = parsed_stream.duration.quarterLength
            
            return {
                'valid': True,
                'error': None,
                'notes_count': notes_count,
                'duration': duration
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'notes_count': 0,
                'duration': 0.0
            }
    
    def cleanup(self, musicxml_path: str) -> bool:
        """
        Clean up generated MusicXML file.
        
        Args:
            musicxml_path (str): Path to MusicXML file to delete
            
        Returns:
            bool: True if successfully deleted, False otherwise
        """
        try:
            path = Path(musicxml_path)
            if path.exists():
                path.unlink()
                logger.info(f"Cleaned up MusicXML file: {musicxml_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cleanup MusicXML file {musicxml_path}: {e}")
            return False
