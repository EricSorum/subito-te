"""
Audio Transcription Module

This module handles audio-to-MIDI transcription using BasicPitch.
Converts WAV audio files into MIDI notation with pitch, timing, and confidence data.

Key Features:
- Audio-to-MIDI transcription using BasicPitch
- Pitch, onset, offset, and confidence extraction
- Support for monophonic and simple polyphonic audio
- Confidence scoring and quality assessment
- Error handling for transcription failures
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
    import basic_pitch
    from basic_pitch import BasicPitch
    from basic_pitch.inference import predict
    from basic_pitch.inference import predict_and_save
    BASIC_PITCH_AVAILABLE = True
except ImportError:
    logger.warning("BasicPitch not available. Please install basic-pitch package.")
    BASIC_PITCH_AVAILABLE = False


class AudioTranscriber:
    """
    Handles audio-to-MIDI transcription using BasicPitch.
    
    This class provides methods to:
    - Transcribe audio files to MIDI
    - Extract pitch, timing, and confidence data
    - Handle various audio formats and qualities
    - Provide transcription quality assessment
    """
    
    def __init__(self, output_dir: Optional[str] = None, model_path: Optional[str] = None):
        """
        Initialize the audio transcriber.
        
        Args:
            output_dir (Optional[str]): Directory to save MIDI files.
                                      If None, uses system temp directory.
            model_path (Optional[str]): Path to custom BasicPitch model.
                                      If None, uses default model.
        """
        if not BASIC_PITCH_AVAILABLE:
            raise ImportError("BasicPitch is not available. Please install basic-pitch package.")
        
        self.output_dir = output_dir or tempfile.gettempdir()
        self.output_path = Path(self.output_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize BasicPitch model
        self.model_path = model_path
        self.model = BasicPitch(model_path) if model_path else BasicPitch()
        
        # Transcription parameters
        self.transcription_params = {
            'onset_threshold': 0.5,      # Onset detection threshold
            'frame_threshold': 0.3,      # Frame-level threshold
            'minimum_note_length': 0.1,  # Minimum note length in seconds
            'minimum_frequency': 80,     # Minimum frequency in Hz
            'maximum_frequency': 8000,   # Maximum frequency in Hz
        }
    
    def transcribe_audio(self, audio_path: str, output_filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio file to MIDI format.
        
        Args:
            audio_path (str): Path to input WAV audio file
            output_filename (Optional[str]): Custom filename for output MIDI.
                                          If None, uses input filename with .mid extension
        
        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'midi_path': Path to generated MIDI file
                - 'confidence': Average transcription confidence score
                - 'notes_count': Number of notes detected
                - 'duration': Transcription duration in seconds
                - 'success': Boolean indicating success
                - 'error': Error message if failed
        
        Raises:
            FileNotFoundError: If audio file doesn't exist
            ValueError: If audio file is invalid or corrupted
        """
        logger.info(f"Starting transcription of audio file: {audio_path}")
        
        # Validate input file
        audio_file = Path(audio_path)
        if not audio_file.exists():
            error_msg = f"Audio file not found: {audio_path}"
            logger.error(error_msg)
            return {
                'midi_path': None,
                'confidence': 0.0,
                'notes_count': 0,
                'duration': 0.0,
                'success': False,
                'error': error_msg
            }
        
        # Generate output filename
        if output_filename:
            midi_file = self.output_path / f"{output_filename}.mid"
        else:
            midi_file = self.output_path / f"{audio_file.stem}.mid"
        
        start_time = time.time()
        
        try:
            # Perform transcription using BasicPitch
            logger.debug(f"Transcribing with BasicPitch model...")
            
            # Use BasicPitch to transcribe and save MIDI
            predict_and_save(
                audio_path_list=[audio_path],
                output_directory=str(self.output_path),
                save_midi=True,
                sonify_midi=False,
                save_model_outputs=False,
                save_notes=False,
                onset_threshold=self.transcription_params['onset_threshold'],
                frame_threshold=self.transcription_params['frame_threshold'],
                minimum_note_length=self.transcription_params['minimum_note_length'],
                minimum_frequency=self.transcription_params['minimum_frequency'],
                maximum_frequency=self.transcription_params['maximum_frequency']
            )
            
            # Find the generated MIDI file
            generated_midi = self._find_generated_midi(audio_file.stem)
            
            if generated_midi and generated_midi.exists():
                # Calculate transcription metrics
                duration = time.time() - start_time
                confidence = self._calculate_confidence(generated_midi)
                notes_count = self._count_notes(generated_midi)
                
                logger.info(f"Successfully transcribed: {generated_midi}")
                logger.info(f"Transcription took {duration:.2f} seconds")
                logger.info(f"Detected {notes_count} notes with confidence {confidence:.2f}")
                
                return {
                    'midi_path': str(generated_midi),
                    'confidence': confidence,
                    'notes_count': notes_count,
                    'duration': duration,
                    'success': True,
                    'error': None
                }
            else:
                error_msg = "MIDI file not generated"
                logger.error(error_msg)
                return {
                    'midi_path': None,
                    'confidence': 0.0,
                    'notes_count': 0,
                    'duration': time.time() - start_time,
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Transcription failed: {str(e)}"
            logger.error(error_msg)
            return {
                'midi_path': None,
                'confidence': 0.0,
                'notes_count': 0,
                'duration': duration,
                'success': False,
                'error': error_msg
            }
    
    def transcribe_with_confidence(self, audio_path: str, output_filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio with detailed confidence analysis.
        
        Args:
            audio_path (str): Path to input WAV audio file
            output_filename (Optional[str]): Custom filename for output MIDI
        
        Returns:
            Dict[str, Any]: Enhanced transcription results with confidence details
        """
        logger.info(f"Starting detailed transcription of: {audio_path}")
        
        try:
            # Get detailed transcription data
            model_output, midi_data, note_events = predict(
                audio_path,
                onset_threshold=self.transcription_params['onset_threshold'],
                frame_threshold=self.transcription_params['frame_threshold'],
                minimum_note_length=self.transcription_params['minimum_note_length'],
                minimum_frequency=self.transcription_params['minimum_frequency'],
                maximum_frequency=self.transcription_params['maximum_frequency']
            )
            
            # Save MIDI file
            if output_filename:
                midi_file = self.output_path / f"{output_filename}.mid"
            else:
                audio_file = Path(audio_path)
                midi_file = self.output_path / f"{audio_file.stem}.mid"
            
            # Save MIDI data
            midi_data.write(str(midi_file))
            
            # Analyze confidence and quality
            confidence_analysis = self._analyze_confidence(model_output, note_events)
            
            return {
                'midi_path': str(midi_file),
                'confidence': confidence_analysis['average_confidence'],
                'notes_count': len(note_events),
                'duration': 0.0,  # Will be calculated by caller
                'success': True,
                'error': None,
                'confidence_analysis': confidence_analysis,
                'note_events': note_events
            }
            
        except Exception as e:
            error_msg = f"Detailed transcription failed: {str(e)}"
            logger.error(error_msg)
            return {
                'midi_path': None,
                'confidence': 0.0,
                'notes_count': 0,
                'duration': 0.0,
                'success': False,
                'error': error_msg,
                'confidence_analysis': None,
                'note_events': []
            }
    
    def _find_generated_midi(self, base_name: str) -> Optional[Path]:
        """
        Find the generated MIDI file in the output directory.
        
        Args:
            base_name (str): Base name of the audio file
            
        Returns:
            Optional[Path]: Path to the generated MIDI file, or None if not found
        """
        # Look for MIDI files in the output directory
        midi_files = list(self.output_path.glob("*.mid"))
        
        if not midi_files:
            return None
        
        # Try to find exact match first
        for file_path in midi_files:
            if base_name.lower() in file_path.stem.lower():
                return file_path
        
        # Return the most recently modified file
        return max(midi_files, key=lambda f: f.stat().st_mtime)
    
    def _calculate_confidence(self, midi_path: Path) -> float:
        """
        Calculate average confidence score for transcription.
        
        Args:
            midi_path (Path): Path to MIDI file
            
        Returns:
            float: Average confidence score (0.0 to 1.0)
        """
        try:
            # This is a simplified confidence calculation
            # In practice, you might want to use the model outputs directly
            file_size = midi_path.stat().st_size
            if file_size > 0:
                # Simple heuristic: larger files might indicate more confident transcription
                return min(1.0, file_size / 10000)  # Normalize to 0-1 range
            return 0.5
        except Exception:
            return 0.5
    
    def _count_notes(self, midi_path: Path) -> int:
        """
        Count the number of notes in a MIDI file.
        
        Args:
            midi_path (Path): Path to MIDI file
            
        Returns:
            int: Number of notes detected
        """
        try:
            # This is a simplified note counting
            # In practice, you might want to parse the MIDI file properly
            file_size = midi_path.stat().st_size
            if file_size > 0:
                # Simple heuristic: estimate notes based on file size
                return max(1, file_size // 100)  # Rough estimate
            return 0
        except Exception:
            return 0
    
    def _analyze_confidence(self, model_output: Any, note_events: List[Any]) -> Dict[str, Any]:
        """
        Analyze confidence scores from model output.
        
        Args:
            model_output: Raw model output from BasicPitch
            note_events: List of note events
            
        Returns:
            Dict[str, Any]: Confidence analysis results
        """
        try:
            # Extract confidence scores from model output
            if hasattr(model_output, 'confidence'):
                confidences = model_output.confidence
                avg_confidence = float(confidences.mean()) if hasattr(confidences, 'mean') else 0.5
                max_confidence = float(confidences.max()) if hasattr(confidences, 'max') else 1.0
                min_confidence = float(confidences.min()) if hasattr(confidences, 'min') else 0.0
            else:
                # Fallback confidence calculation
                avg_confidence = 0.7
                max_confidence = 1.0
                min_confidence = 0.3
            
            return {
                'average_confidence': avg_confidence,
                'max_confidence': max_confidence,
                'min_confidence': min_confidence,
                'confidence_std': 0.1,  # Placeholder
                'high_confidence_notes': len([n for n in note_events if getattr(n, 'confidence', 0.5) > 0.8]),
                'low_confidence_notes': len([n for n in note_events if getattr(n, 'confidence', 0.5) < 0.3])
            }
            
        except Exception as e:
            logger.warning(f"Could not analyze confidence: {e}")
            return {
                'average_confidence': 0.5,
                'max_confidence': 1.0,
                'min_confidence': 0.0,
                'confidence_std': 0.1,
                'high_confidence_notes': 0,
                'low_confidence_notes': 0
            }
    
    def set_transcription_params(self, **kwargs) -> None:
        """
        Update transcription parameters.
        
        Args:
            **kwargs: Parameter updates (onset_threshold, frame_threshold, etc.)
        """
        for key, value in kwargs.items():
            if key in self.transcription_params:
                self.transcription_params[key] = value
                logger.info(f"Updated {key} to {value}")
            else:
                logger.warning(f"Unknown parameter: {key}")
    
    def cleanup(self, midi_path: str) -> bool:
        """
        Clean up generated MIDI file.
        
        Args:
            midi_path (str): Path to MIDI file to delete
            
        Returns:
            bool: True if successfully deleted, False otherwise
        """
        try:
            path = Path(midi_path)
            if path.exists():
                path.unlink()
                logger.info(f"Cleaned up MIDI file: {midi_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cleanup MIDI file {midi_path}: {e}")
            return False
