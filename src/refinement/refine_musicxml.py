"""
MusicXML Refinement Module

This module handles MusicXML refinement using LLM (GPT-5).
Improves and "humanizes" the generated MusicXML notation by removing
redundant elements, adjusting quantization, and adding musical context.

Key Features:
- LLM-based MusicXML refinement using OpenAI API
- Removes redundant rests and overlapping notes
- Adjusts quantization errors
- Infers key and time signatures
- Adds tempo markings and phrasing hints
- Style-specific refinements (piano, guitar, etc.)
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging
import time
import json

# Configure logging for this module
logger = logging.getLogger(__name__)

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    logger.warning("OpenAI package not available. Please install openai package.")
    OPENAI_AVAILABLE = False


class MusicXmlRefiner:
    """
    Handles MusicXML refinement using OpenAI's GPT models.
    
    This class provides methods to:
    - Refine MusicXML using LLM analysis
    - Remove redundant elements and fix quantization
    - Add musical context and phrasing
    - Apply style-specific refinements
    - Provide both original and refined versions
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4", output_dir: Optional[str] = None):
        """
        Initialize the MusicXML refiner.
        
        Args:
            api_key (Optional[str]): OpenAI API key. If None, uses environment variable.
            model (str): OpenAI model to use for refinement.
            output_dir (Optional[str]): Directory to save refined files.
                                      If None, uses system temp directory.
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package is not available. Please install openai package.")
        
        self.output_dir = output_dir or tempfile.gettempdir()
        self.output_path = Path(self.output_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize OpenAI client
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = model
        
        # Refinement parameters
        self.refinement_params = {
            'remove_redundant_rests': True,
            'fix_quantization_errors': True,
            'infer_key_signature': True,
            'infer_time_signature': True,
            'add_tempo_markings': True,
            'add_phrasing_hints': True,
            'cleanup_overlapping_notes': True,
            'style_refinement': 'general',  # 'piano', 'guitar', 'vocal', 'general'
        }
    
    def refine_musicxml(self, musicxml_path: str, output_filename: Optional[str] = None, 
                       style: str = 'general', custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Refine MusicXML file using LLM analysis.
        
        Args:
            musicxml_path (str): Path to input MusicXML file
            output_filename (Optional[str]): Custom filename for output.
                                          If None, uses input filename with _refined suffix
            style (str): Style of refinement ('piano', 'guitar', 'vocal', 'general')
            custom_prompt (Optional[str]): Custom refinement prompt
        
        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'refined_path': Path to refined MusicXML file
                - 'original_path': Path to original MusicXML file
                - 'improvements': List of improvements made
                - 'confidence': Refinement confidence score
                - 'duration': Refinement duration in seconds
                - 'success': Boolean indicating success
                - 'error': Error message if failed
        """
        logger.info(f"Refining MusicXML file: {musicxml_path}")
        
        # Validate input file
        musicxml_file = Path(musicxml_path)
        if not musicxml_file.exists():
            error_msg = f"MusicXML file not found: {musicxml_path}"
            logger.error(error_msg)
            return {
                'refined_path': None,
                'original_path': musicxml_path,
                'improvements': [],
                'confidence': 0.0,
                'duration': 0.0,
                'success': False,
                'error': error_msg
            }
        
        # Generate output filename
        if output_filename:
            refined_file = self.output_path / f"{output_filename}.musicxml"
        else:
            refined_file = self.output_path / f"{musicxml_file.stem}_refined.musicxml"
        
        start_time = time.time()
        
        try:
            # Read the original MusicXML content
            with open(musicxml_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Generate refinement prompt
            prompt = self._generate_refinement_prompt(original_content, style, custom_prompt)
            
            # Call OpenAI API for refinement
            logger.debug(f"Calling OpenAI API with model: {self.model}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent results
                max_tokens=4000,  # Adjust based on expected MusicXML size
                timeout=60  # 60 second timeout
            )
            
            # Extract refined content from response
            refined_content = response.choices[0].message.content
            
            # Parse the response to extract MusicXML and metadata
            parsed_response = self._parse_refinement_response(refined_content)
            
            # Save refined MusicXML
            with open(refined_file, 'w', encoding='utf-8') as f:
                f.write(parsed_response['musicxml'])
            
            # Calculate refinement metrics
            duration = time.time() - start_time
            confidence = self._calculate_refinement_confidence(original_content, parsed_response['musicxml'])
            improvements = parsed_response.get('improvements', [])
            
            logger.info(f"Successfully refined: {refined_file}")
            logger.info(f"Refinement took {duration:.2f} seconds")
            logger.info(f"Confidence: {confidence:.2f}, Improvements: {len(improvements)}")
            
            return {
                'refined_path': str(refined_file),
                'original_path': musicxml_path,
                'improvements': improvements,
                'confidence': confidence,
                'duration': duration,
                'success': True,
                'error': None
            }
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Refinement failed: {str(e)}"
            logger.error(error_msg)
            return {
                'refined_path': None,
                'original_path': musicxml_path,
                'improvements': [],
                'confidence': 0.0,
                'duration': duration,
                'success': False,
                'error': error_msg
            }
    
    def _generate_refinement_prompt(self, musicxml_content: str, style: str, custom_prompt: Optional[str]) -> str:
        """
        Generate refinement prompt for the LLM.
        
        Args:
            musicxml_content (str): Original MusicXML content
            style (str): Style of refinement
            custom_prompt (Optional[str]): Custom prompt text
        
        Returns:
            str: Complete refinement prompt
        """
        if custom_prompt:
            base_prompt = custom_prompt
        else:
            base_prompt = self._get_style_prompt(style)
        
        prompt = f"""
{base_prompt}

Please analyze and refine the following MusicXML content:

{musicxml_content}

Please provide:
1. The refined MusicXML content
2. A list of improvements made
3. Any notes about the refinement process

Format your response as JSON with the following structure:
{{
    "musicxml": "<refined MusicXML content>",
    "improvements": ["improvement 1", "improvement 2", ...],
    "notes": "Additional notes about the refinement"
}}
"""
        return prompt
    
    def _get_system_prompt(self) -> str:
        """
        Get the system prompt for the LLM.
        
        Returns:
            str: System prompt text
        """
        return """You are an expert music notation specialist and MusicXML editor. Your task is to refine and improve MusicXML notation to make it more readable, accurate, and musically appropriate.

Key areas to focus on:
1. Remove redundant rests and overlapping notes
2. Fix quantization errors and timing issues
3. Infer and add appropriate key signatures and time signatures
4. Add tempo markings and phrasing hints
5. Clean up notation for better readability
6. Ensure proper musical structure and flow

Always provide your response in the requested JSON format with the refined MusicXML content and a list of improvements made."""
    
    def _get_style_prompt(self, style: str) -> str:
        """
        Get style-specific refinement prompt.
        
        Args:
            style (str): Style of refinement
        
        Returns:
            str: Style-specific prompt text
        """
        style_prompts = {
            'piano': """
Refine this MusicXML for piano performance. Focus on:
- Clear hand separation and voice leading
- Appropriate fingerings and phrasing
- Piano-specific notation conventions
- Dynamic markings and articulation
- Pedal markings where appropriate
""",
            'guitar': """
Refine this MusicXML for guitar performance. Focus on:
- Tablature-friendly notation
- Chord symbols and fingerings
- Guitar-specific techniques (hammer-ons, pull-offs, etc.)
- Capo markings if needed
- Strumming patterns and rhythm
""",
            'vocal': """
Refine this MusicXML for vocal performance. Focus on:
- Clear melodic line
- Appropriate vocal range
- Lyric placement and phrasing
- Breath marks and articulation
- Dynamic markings for expression
""",
            'general': """
Refine this MusicXML for general use. Focus on:
- Clean, readable notation
- Proper musical structure
- Appropriate tempo and dynamics
- Clear phrasing and articulation
- Standard notation conventions
"""
        }
        
        return style_prompts.get(style, style_prompts['general'])
    
    def _parse_refinement_response(self, response_content: str) -> Dict[str, Any]:
        """
        Parse the LLM response to extract MusicXML and metadata.
        
        Args:
            response_content (str): Raw response from LLM
        
        Returns:
            Dict[str, Any]: Parsed response data
        """
        try:
            # Try to parse as JSON first
            if response_content.strip().startswith('{'):
                return json.loads(response_content)
            
            # If not JSON, try to extract MusicXML and improvements manually
            lines = response_content.split('\n')
            musicxml_lines = []
            improvements = []
            in_musicxml = False
            
            for line in lines:
                if '<musicxml' in line.lower() or '<score-partwise' in line.lower():
                    in_musicxml = True
                elif in_musicxml and ('</score-partwise>' in line.lower() or '</musicxml>' in line.lower()):
                    musicxml_lines.append(line)
                    break
                elif in_musicxml:
                    musicxml_lines.append(line)
                elif line.strip().startswith('-') or line.strip().startswith('•'):
                    improvements.append(line.strip())
            
            return {
                'musicxml': '\n'.join(musicxml_lines),
                'improvements': improvements,
                'notes': 'Parsed from non-JSON response'
            }
            
        except json.JSONDecodeError:
            logger.warning("Could not parse JSON response, using fallback parsing")
            return {
                'musicxml': response_content,
                'improvements': ['Response parsing failed'],
                'notes': 'Fallback parsing used'
            }
    
    def _calculate_refinement_confidence(self, original: str, refined: str) -> float:
        """
        Calculate confidence score for the refinement.
        
        Args:
            original (str): Original MusicXML content
            refined (str): Refined MusicXML content
        
        Returns:
            float: Confidence score (0.0 to 1.0)
        """
        try:
            # Simple confidence calculation based on content changes
            original_length = len(original)
            refined_length = len(refined)
            
            if original_length == 0:
                return 0.0
            
            # Calculate similarity ratio
            similarity = min(original_length, refined_length) / max(original_length, refined_length)
            
            # Confidence based on similarity (not too similar, not too different)
            if 0.7 <= similarity <= 0.95:
                return 0.8
            elif 0.5 <= similarity < 0.7:
                return 0.6
            elif 0.95 < similarity <= 1.0:
                return 0.4  # Too similar, might not have been refined
            else:
                return 0.3  # Too different, might be corrupted
            
        except Exception:
            return 0.5  # Default confidence score
    
    def batch_refine(self, musicxml_paths: List[str], style: str = 'general') -> Dict[str, Any]:
        """
        Refine multiple MusicXML files in batch.
        
        Args:
            musicxml_paths (List[str]): List of MusicXML file paths
            style (str): Style of refinement
        
        Returns:
            Dict[str, Any]: Batch refinement results
        """
        logger.info(f"Starting batch refinement of {len(musicxml_paths)} files")
        
        results = {
            'successful': [],
            'failed': [],
            'total_duration': 0.0,
            'total_improvements': 0
        }
        
        for i, path in enumerate(musicxml_paths):
            logger.info(f"Refining file {i+1}/{len(musicxml_paths)}: {path}")
            
            result = self.refine_musicxml(path, style=style)
            
            if result['success']:
                results['successful'].append(result)
                results['total_improvements'] += len(result['improvements'])
            else:
                results['failed'].append(result)
            
            results['total_duration'] += result['duration']
        
        logger.info(f"Batch refinement completed: {len(results['successful'])} successful, {len(results['failed'])} failed")
        return results
    
    def set_refinement_params(self, **kwargs) -> None:
        """
        Update refinement parameters.
        
        Args:
            **kwargs: Parameter updates (remove_redundant_rests, style_refinement, etc.)
        """
        for key, value in kwargs.items():
            if key in self.refinement_params:
                self.refinement_params[key] = value
                logger.info(f"Updated {key} to {value}")
            else:
                logger.warning(f"Unknown parameter: {key}")
    
    def cleanup(self, refined_path: str) -> bool:
        """
        Clean up refined MusicXML file.
        
        Args:
            refined_path (str): Path to refined file to delete
            
        Returns:
            bool: True if successfully deleted, False otherwise
        """
        try:
            path = Path(refined_path)
            if path.exists():
                path.unlink()
                logger.info(f"Cleaned up refined file: {refined_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cleanup refined file {refined_path}: {e}")
            return False
