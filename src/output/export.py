"""
Music Export Module

This module handles final output generation and export.
Creates PDF files from MusicXML and generates metadata files.

Key Features:
- PDF generation from MusicXML using MuseScore CLI
- Metadata file generation with process information
- Project organization and file management
- Quality assessment and validation
- Error handling for export failures
"""

import os
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging
import time
import json
from datetime import datetime

# Configure logging for this module
logger = logging.getLogger(__name__)


class MusicExporter:
    """
    Handles final output generation and export.
    
    This class provides methods to:
    - Generate PDF files from MusicXML
    - Create metadata files with process information
    - Organize output files in project directories
    - Validate and assess output quality
    """
    
    def __init__(self, output_dir: Optional[str] = None, musescore_path: Optional[str] = None):
        """
        Initialize the music exporter.
        
        Args:
            output_dir (Optional[str]): Base directory for output files.
                                      If None, uses './output' directory.
            musescore_path (Optional[str]): Path to MuseScore executable.
                                          If None, tries to find it in PATH.
        """
        self.output_dir = output_dir or './output'
        self.output_path = Path(self.output_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Find MuseScore executable
        self.musescore_path = musescore_path or self._find_musescore()
        if not self.musescore_path:
            logger.warning("MuseScore not found. PDF generation may not work.")
        
        # Export parameters
        self.export_params = {
            'pdf_quality': 'high',      # PDF quality: 'low', 'medium', 'high'
            'pdf_resolution': 300,      # PDF resolution in DPI
            'include_metadata': True,    # Include metadata in PDF
            'page_size': 'A4',          # Page size for PDF
            'margins': 'normal',       # Page margins: 'narrow', 'normal', 'wide'
        }
    
    def export_project(self, musicxml_path: str, project_id: str, 
                      source_info: Dict[str, Any], transcription_info: Dict[str, Any],
                      conversion_info: Dict[str, Any], refinement_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Export a complete project with all files and metadata.
        
        Args:
            musicxml_path (str): Path to final MusicXML file
            project_id (str): Unique project identifier
            source_info (Dict[str, Any]): Source audio information
            transcription_info (Dict[str, Any]): Transcription process information
            conversion_info (Dict[str, Any]): Conversion process information
            refinement_info (Optional[Dict[str, Any]]): Refinement process information
        
        Returns:
            Dict[str, Any]: Export results with file paths and metadata
        """
        logger.info(f"Exporting project: {project_id}")
        
        # Create project directory
        project_dir = self.output_path / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Copy MusicXML to project directory
            musicxml_file = Path(musicxml_path)
            project_musicxml = project_dir / f"{project_id}.musicxml"
            
            if musicxml_file.exists():
                import shutil
                shutil.copy2(musicxml_file, project_musicxml)
                logger.info(f"Copied MusicXML to: {project_musicxml}")
            else:
                error_msg = f"MusicXML file not found: {musicxml_path}"
                logger.error(error_msg)
                return {
                    'project_dir': str(project_dir),
                    'musicxml_path': None,
                    'pdf_path': None,
                    'metadata_path': None,
                    'success': False,
                    'error': error_msg
                }
            
            # Generate PDF from MusicXML
            pdf_result = self.generate_pdf(str(project_musicxml), str(project_dir / f"{project_id}.pdf"))
            
            # Generate metadata file
            metadata_result = self.generate_metadata(
                project_id, source_info, transcription_info, 
                conversion_info, refinement_info, str(project_dir / f"{project_id}_metadata.json")
            )
            
            # Create project summary
            summary = {
                'project_id': project_id,
                'created_at': datetime.now().isoformat(),
                'project_dir': str(project_dir),
                'files': {
                    'musicxml': str(project_musicxml),
                    'pdf': pdf_result.get('pdf_path'),
                    'metadata': metadata_result.get('metadata_path')
                },
                'success': pdf_result.get('success', False) and metadata_result.get('success', False),
                'errors': []
            }
            
            if not pdf_result.get('success', False):
                summary['errors'].append(f"PDF generation failed: {pdf_result.get('error', 'Unknown error')}")
            
            if not metadata_result.get('success', False):
                summary['errors'].append(f"Metadata generation failed: {metadata_result.get('error', 'Unknown error')}")
            
            logger.info(f"Project export completed: {project_id}")
            return summary
            
        except Exception as e:
            error_msg = f"Project export failed: {str(e)}"
            logger.error(error_msg)
            return {
                'project_dir': str(project_dir),
                'musicxml_path': None,
                'pdf_path': None,
                'metadata_path': None,
                'success': False,
                'error': error_msg
            }
    
    def generate_pdf(self, musicxml_path: str, output_path: str) -> Dict[str, Any]:
        """
        Generate PDF file from MusicXML using MuseScore CLI.
        
        Args:
            musicxml_path (str): Path to input MusicXML file
            output_path (str): Path for output PDF file
        
        Returns:
            Dict[str, Any]: PDF generation results
        """
        logger.info(f"Generating PDF from: {musicxml_path}")
        
        if not self.musescore_path:
            error_msg = "MuseScore not available for PDF generation"
            logger.error(error_msg)
            return {
                'pdf_path': None,
                'success': False,
                'error': error_msg
            }
        
        try:
            # Build MuseScore command
            cmd = [
                self.musescore_path,
                musicxml_path,
                '-o', output_path,
                '--export-to', 'pdf'
            ]
            
            # Add quality parameters
            if self.export_params['pdf_quality'] == 'high':
                cmd.extend(['--export-high-quality'])
            elif self.export_params['pdf_quality'] == 'low':
                cmd.extend(['--export-low-quality'])
            
            logger.debug(f"Executing MuseScore command: {' '.join(cmd)}")
            
            # Execute MuseScore command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300  # 5 minute timeout
            )
            
            # Verify PDF was created
            pdf_file = Path(output_path)
            if pdf_file.exists() and pdf_file.stat().st_size > 0:
                logger.info(f"Successfully generated PDF: {output_path}")
                return {
                    'pdf_path': str(pdf_file),
                    'success': True,
                    'error': None
                }
            else:
                error_msg = "PDF file not created or empty"
                logger.error(error_msg)
                return {
                    'pdf_path': None,
                    'success': False,
                    'error': error_msg
                }
                
        except subprocess.TimeoutExpired:
            error_msg = "PDF generation timed out after 5 minutes"
            logger.error(error_msg)
            return {
                'pdf_path': None,
                'success': False,
                'error': error_msg
            }
        except subprocess.CalledProcessError as e:
            error_msg = f"MuseScore failed: {e.stderr}"
            logger.error(error_msg)
            return {
                'pdf_path': None,
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"PDF generation failed: {str(e)}"
            logger.error(error_msg)
            return {
                'pdf_path': None,
                'success': False,
                'error': error_msg
            }
    
    def generate_metadata(self, project_id: str, source_info: Dict[str, Any], 
                         transcription_info: Dict[str, Any], conversion_info: Dict[str, Any],
                         refinement_info: Optional[Dict[str, Any]], output_path: str) -> Dict[str, Any]:
        """
        Generate metadata file with process information.
        
        Args:
            project_id (str): Project identifier
            source_info (Dict[str, Any]): Source audio information
            transcription_info (Dict[str, Any]): Transcription information
            conversion_info (Dict[str, Any]): Conversion information
            refinement_info (Optional[Dict[str, Any]]): Refinement information
            output_path (str): Path for output metadata file
        
        Returns:
            Dict[str, Any]: Metadata generation results
        """
        logger.info(f"Generating metadata for project: {project_id}")
        
        try:
            # Create metadata structure
            metadata = {
                'project_id': project_id,
                'created_at': datetime.now().isoformat(),
                'source': {
                    'type': source_info.get('type', 'unknown'),
                    'filename': source_info.get('filename', 'unknown'),
                    'duration': source_info.get('duration', 0),
                    'sample_rate': source_info.get('sample_rate', 0),
                    'channels': source_info.get('channels', 0)
                },
                'transcription': {
                    'confidence': transcription_info.get('confidence', 0.0),
                    'notes_count': transcription_info.get('notes_count', 0),
                    'duration': transcription_info.get('duration', 0.0),
                    'success': transcription_info.get('success', False)
                },
                'conversion': {
                    'quality_score': conversion_info.get('quality_score', 0.0),
                    'notes_count': conversion_info.get('notes_count', 0),
                    'duration': conversion_info.get('duration', 0.0),
                    'success': conversion_info.get('success', False)
                },
                'refinement': {
                    'confidence': refinement_info.get('confidence', 0.0) if refinement_info else 0.0,
                    'improvements': refinement_info.get('improvements', []) if refinement_info else [],
                    'success': refinement_info.get('success', False) if refinement_info else False
                },
                'output': {
                    'musicxml_path': source_info.get('musicxml_path', ''),
                    'pdf_path': source_info.get('pdf_path', ''),
                    'total_processing_time': (
                        transcription_info.get('duration', 0) +
                        conversion_info.get('duration', 0) +
                        (refinement_info.get('duration', 0) if refinement_info else 0)
                    )
                }
            }
            
            # Write metadata to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully generated metadata: {output_path}")
            return {
                'metadata_path': output_path,
                'success': True,
                'error': None
            }
            
        except Exception as e:
            error_msg = f"Metadata generation failed: {str(e)}"
            logger.error(error_msg)
            return {
                'metadata_path': None,
                'success': False,
                'error': error_msg
            }
    
    def _find_musescore(self) -> Optional[str]:
        """
        Find MuseScore executable in the system PATH.
        
        Returns:
            Optional[str]: Path to MuseScore executable, or None if not found
        """
        musescore_names = ['musescore', 'MuseScore', 'musescore3', 'musescore4']
        
        for name in musescore_names:
            try:
                result = subprocess.run(['which', name], capture_output=True, text=True, check=True)
                if result.returncode == 0:
                    musescore_path = result.stdout.strip()
                    logger.info(f"Found MuseScore at: {musescore_path}")
                    return musescore_path
            except subprocess.CalledProcessError:
                continue
        
        # Try common installation paths
        common_paths = [
            '/Applications/MuseScore 3.app/Contents/MacOS/mscore',
            '/Applications/MuseScore 4.app/Contents/MacOS/mscore',
            '/usr/bin/musescore',
            '/usr/local/bin/musescore',
            'C:\\Program Files\\MuseScore 3\\bin\\MuseScore3.exe',
            'C:\\Program Files\\MuseScore 4\\bin\\MuseScore4.exe'
        ]
        
        for path in common_paths:
            if Path(path).exists():
                logger.info(f"Found MuseScore at: {path}")
                return path
        
        logger.warning("MuseScore not found in PATH or common locations")
        return None
    
    def validate_output(self, project_dir: str) -> Dict[str, Any]:
        """
        Validate output files in a project directory.
        
        Args:
            project_dir (str): Path to project directory
        
        Returns:
            Dict[str, Any]: Validation results
        """
        project_path = Path(project_dir)
        
        if not project_path.exists():
            return {
                'valid': False,
                'error': 'Project directory not found',
                'files': {}
            }
        
        validation_results = {
            'valid': True,
            'error': None,
            'files': {}
        }
        
        # Check for required files
        required_files = ['*.musicxml', '*.pdf', '*_metadata.json']
        
        for pattern in required_files:
            files = list(project_path.glob(pattern))
            if files:
                validation_results['files'][pattern] = {
                    'found': True,
                    'path': str(files[0]),
                    'size': files[0].stat().st_size
                }
            else:
                validation_results['files'][pattern] = {
                    'found': False,
                    'path': None,
                    'size': 0
                }
                validation_results['valid'] = False
        
        return validation_results
    
    def cleanup_project(self, project_dir: str) -> bool:
        """
        Clean up project directory and files.
        
        Args:
            project_dir (str): Path to project directory to clean up
        
        Returns:
            bool: True if successfully cleaned up, False otherwise
        """
        try:
            import shutil
            path = Path(project_dir)
            if path.exists():
                shutil.rmtree(path)
                logger.info(f"Cleaned up project directory: {project_dir}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cleanup project directory {project_dir}: {e}")
            return False
    
    def set_export_params(self, **kwargs) -> None:
        """
        Update export parameters.
        
        Args:
            **kwargs: Parameter updates (pdf_quality, pdf_resolution, etc.)
        """
        for key, value in kwargs.items():
            if key in self.export_params:
                self.export_params[key] = value
                logger.info(f"Updated {key} to {value}")
            else:
                logger.warning(f"Unknown parameter: {key}")
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """
        List all projects in the output directory.
        
        Returns:
            List[Dict[str, Any]]: List of project information
        """
        projects = []
        
        for project_dir in self.output_path.iterdir():
            if project_dir.is_dir():
                validation = self.validate_output(str(project_dir))
                projects.append({
                    'project_id': project_dir.name,
                    'path': str(project_dir),
                    'valid': validation['valid'],
                    'files': validation['files']
                })
        
        return projects
