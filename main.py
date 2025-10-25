#!/usr/bin/env python3
"""
Sheet Music Conversion MVP - Main CLI Interface

This is the main entry point for the sheet music conversion pipeline.
It provides a command-line interface for converting audio files to sheet music.

Usage:
    python main.py --input "path/to/audio.mp3" --output "./output" --refine true --pdf true
    python main.py --input "https://youtube.com/watch?v=..." --output "./output" --refine true
    python main.py --input "audio.wav" --output "./output" --style piano
"""

import argparse
import sys
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Import our modules
from src.utils.logging import setup_logging, get_logger, log_pipeline_step, log_pipeline_result
from src.utils.config import load_config
from src.input import YouTubeDownloader, AudioConverter
from src.transcription import AudioTranscriber
from src.conversion import MidiToMusicXmlConverter
from src.refinement import MusicXmlRefiner
from src.output import MusicExporter


def main():
    """
    Main entry point for the sheet music conversion pipeline.
    """
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up logging
    setup_logging(
        log_level=args.log_level,
        log_dir=args.log_dir
    )
    
    logger = get_logger(__name__)
    logger.info("🎼 Sheet Music Conversion MVP - Starting Pipeline")
    logger.info("=" * 60)
    
    # Load configuration
    config = load_config(args.config)
    
    # Validate configuration
    validation = config.validate()
    if not validation['valid']:
        logger.error("Configuration validation failed:")
        for error in validation['errors']:
            logger.error(f"  - {error}")
        sys.exit(1)
    
    if validation['warnings']:
        logger.warning("Configuration warnings:")
        for warning in validation['warnings']:
            logger.warning(f"  - {warning}")
    
    # Generate unique project ID
    project_id = args.project_id or f"project_{uuid.uuid4().hex[:8]}"
    logger.info(f"Project ID: {project_id}")
    
    # Run the conversion pipeline
    try:
        result = run_conversion_pipeline(
            input_path=args.input,
            output_dir=args.output,
            project_id=project_id,
            config=config,
            refine=args.refine,
            pdf=args.pdf,
            style=args.style,
            custom_prompt=args.prompt
        )
        
        if result['success']:
            logger.info("🎉 Pipeline completed successfully!")
            logger.info(f"Output directory: {result['project_dir']}")
            logger.info(f"Files generated:")
            for file_type, file_path in result['files'].items():
                if file_path:
                    logger.info(f"  - {file_type}: {file_path}")
        else:
            logger.error("❌ Pipeline failed!")
            logger.error(f"Error: {result['error']}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)


def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Convert audio files to sheet music using AI transcription",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --input "song.mp3" --output "./output"
  python main.py --input "https://youtube.com/watch?v=..." --output "./output" --refine
  python main.py --input "audio.wav" --output "./output" --style piano --pdf
  python main.py --input "music.mp3" --output "./output" --prompt "Make this suitable for piano"
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input audio file path or YouTube URL'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='./output',
        help='Output directory for generated files (default: ./output)'
    )
    
    # Optional arguments
    parser.add_argument(
        '--project-id',
        help='Custom project ID (default: auto-generated)'
    )
    
    parser.add_argument(
        '--refine',
        action='store_true',
        help='Enable LLM refinement of MusicXML'
    )
    
    parser.add_argument(
        '--pdf',
        action='store_true',
        help='Generate PDF output from MusicXML'
    )
    
    parser.add_argument(
        '--style',
        choices=['piano', 'guitar', 'vocal', 'general'],
        default='general',
        help='Style of refinement (default: general)'
    )
    
    parser.add_argument(
        '--prompt',
        help='Custom refinement prompt'
    )
    
    parser.add_argument(
        '--config', '-c',
        default='config.yaml',
        help='Configuration file path (default: config.yaml)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-dir',
        default='./logs',
        help='Log directory (default: ./logs)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging (equivalent to --log-level DEBUG)'
    )
    
    args = parser.parse_args()
    
    # Handle verbose flag
    if args.verbose:
        args.log_level = 'DEBUG'
    
    return args


def run_conversion_pipeline(input_path: str, output_dir: str, project_id: str, 
                          config, refine: bool = False, pdf: bool = False, 
                          style: str = 'general', custom_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Run the complete conversion pipeline.
    
    Args:
        input_path (str): Path to input audio file or YouTube URL
        output_dir (str): Output directory for generated files
        project_id (str): Unique project identifier
        config: Configuration object
        refine (bool): Whether to enable LLM refinement
        pdf (bool): Whether to generate PDF output
        style (str): Style of refinement
        custom_prompt (Optional[str]): Custom refinement prompt
        
    Returns:
        Dict[str, Any]: Pipeline results
    """
    logger = get_logger(__name__)
    
    # Initialize pipeline state
    pipeline_state = {
        'project_id': project_id,
        'input_path': input_path,
        'output_dir': output_dir,
        'temp_files': [],
        'results': {}
    }
    
    try:
        # Step 1: Input Processing
        log_pipeline_step("Input Processing", __name__)
        start_time = time.time()
        
        input_result = process_input(input_path, config)
        if not input_result['success']:
            return {
                'success': False,
                'error': f"Input processing failed: {input_result['error']}",
                'project_dir': None,
                'files': {}
            }
        
        pipeline_state['results']['input'] = input_result
        pipeline_state['temp_files'].append(input_result['file_path'])
        
        log_pipeline_result(
            "Input Processing", __name__, True, 
            time.time() - start_time, 
            {'audio_file': input_result['file_path'], 'duration': input_result['metadata']['duration']}
        )
        
        # Step 2: Transcription
        log_pipeline_step("Audio Transcription", __name__)
        start_time = time.time()
        
        transcription_result = transcribe_audio(input_result['file_path'], config)
        if not transcription_result['success']:
            return {
                'success': False,
                'error': f"Transcription failed: {transcription_result['error']}",
                'project_dir': None,
                'files': {}
            }
        
        pipeline_state['results']['transcription'] = transcription_result
        pipeline_state['temp_files'].append(transcription_result['midi_path'])
        
        log_pipeline_result(
            "Audio Transcription", __name__, True,
            time.time() - start_time,
            {'midi_file': transcription_result['midi_path'], 'notes': transcription_result['notes_count'], 'confidence': transcription_result['confidence']}
        )
        
        # Step 3: Conversion
        log_pipeline_step("MIDI to MusicXML Conversion", __name__)
        start_time = time.time()
        
        conversion_result = convert_midi_to_musicxml(transcription_result['midi_path'], config)
        if not conversion_result['success']:
            return {
                'success': False,
                'error': f"Conversion failed: {conversion_result['error']}",
                'project_dir': None,
                'files': {}
            }
        
        pipeline_state['results']['conversion'] = conversion_result
        pipeline_state['temp_files'].append(conversion_result['musicxml_path'])
        
        log_pipeline_result(
            "MIDI to MusicXML Conversion", __name__, True,
            time.time() - start_time,
            {'musicxml_file': conversion_result['musicxml_path'], 'quality': conversion_result['quality_score']}
        )
        
        # Step 4: Refinement (optional)
        refinement_result = None
        if refine:
            log_pipeline_step("MusicXML Refinement", __name__)
            start_time = time.time()
            
            refinement_result = refine_musicxml(conversion_result['musicxml_path'], config, style, custom_prompt)
            if refinement_result['success']:
                pipeline_state['results']['refinement'] = refinement_result
                pipeline_state['temp_files'].append(refinement_result['refined_path'])
                # Use refined version for final output
                final_musicxml = refinement_result['refined_path']
            else:
                logger.warning(f"Refinement failed: {refinement_result['error']}, using original MusicXML")
                final_musicxml = conversion_result['musicxml_path']
            
            log_pipeline_result(
                "MusicXML Refinement", __name__, refinement_result['success'],
                time.time() - start_time,
                {'refined_file': refinement_result.get('refined_path'), 'improvements': len(refinement_result.get('improvements', []))}
            )
        else:
            final_musicxml = conversion_result['musicxml_path']
        
        # Step 5: Export
        log_pipeline_step("Final Export", __name__)
        start_time = time.time()
        
        export_result = export_project(
            final_musicxml, project_id, output_dir, 
            pipeline_state['results'], config, pdf
        )
        
        log_pipeline_result(
            "Final Export", __name__, export_result['success'],
            time.time() - start_time,
            {'project_dir': export_result.get('project_dir'), 'files': list(export_result.get('files', {}).keys())}
        )
        
        return export_result
        
    except Exception as e:
        logger.error(f"Pipeline failed with error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'project_dir': None,
            'files': {}
        }
    
    finally:
        # Cleanup temporary files
        cleanup_temp_files(pipeline_state['temp_files'])


def process_input(input_path: str, config) -> Dict[str, Any]:
    """
    Process input audio file or YouTube URL.
    
    Args:
        input_path (str): Path to audio file or YouTube URL
        config: Configuration object
        
    Returns:
        Dict[str, Any]: Input processing results
    """
    logger = get_logger(__name__)
    
    # Check if input is a YouTube URL
    if input_path.startswith(('http://', 'https://')):
        logger.info(f"Processing YouTube URL: {input_path}")
        
        # Download audio from YouTube
        downloader = YouTubeDownloader()
        download_result = downloader.download_audio(input_path)
        
        if not download_result['success']:
            return download_result
        
        # Convert to standardized WAV
        converter = AudioConverter()
        convert_result = converter.convert_to_wav(download_result['file_path'])
        
        if not convert_result['success']:
            return convert_result
        
        return {
            'success': True,
            'file_path': convert_result['file_path'],
            'metadata': convert_result['metadata'],
            'source_type': 'youtube',
            'source_url': input_path,
            'title': download_result['title']
        }
    
    else:
        logger.info(f"Processing local audio file: {input_path}")
        
        # Convert local file to standardized WAV
        converter = AudioConverter()
        convert_result = converter.convert_to_wav(input_path)
        
        if not convert_result['success']:
            return convert_result
        
        return {
            'success': True,
            'file_path': convert_result['file_path'],
            'metadata': convert_result['metadata'],
            'source_type': 'local',
            'source_file': input_path
        }


def transcribe_audio(audio_path: str, config) -> Dict[str, Any]:
    """
    Transcribe audio file to MIDI.
    
    Args:
        audio_path (str): Path to audio file
        config: Configuration object
        
    Returns:
        Dict[str, Any]: Transcription results
    """
    logger = get_logger(__name__)
    
    # Initialize transcriber
    transcriber = AudioTranscriber()
    
    # Set transcription parameters from config
    transcription_config = config.get_module_config('transcription')
    transcriber.set_transcription_params(**transcription_config)
    
    # Perform transcription
    result = transcriber.transcribe_audio(audio_path)
    
    return result


def convert_midi_to_musicxml(midi_path: str, config) -> Dict[str, Any]:
    """
    Convert MIDI file to MusicXML.
    
    Args:
        midi_path (str): Path to MIDI file
        config: Configuration object
        
    Returns:
        Dict[str, Any]: Conversion results
    """
    logger = get_logger(__name__)
    
    # Initialize converter
    converter = MidiToMusicXmlConverter()
    
    # Set conversion parameters from config
    conversion_config = config.get_module_config('conversion')
    converter.set_conversion_params(**conversion_config)
    
    # Perform conversion
    result = converter.convert_midi_to_musicxml(midi_path)
    
    return result


def refine_musicxml(musicxml_path: str, config, style: str, custom_prompt: Optional[str]) -> Dict[str, Any]:
    """
    Refine MusicXML using LLM.
    
    Args:
        musicxml_path (str): Path to MusicXML file
        config: Configuration object
        style (str): Style of refinement
        custom_prompt (Optional[str]): Custom refinement prompt
        
    Returns:
        Dict[str, Any]: Refinement results
    """
    logger = get_logger(__name__)
    
    # Initialize refiner
    api_key = config.get('api', 'openai_api_key')
    model = config.get('refinement', 'model')
    
    refiner = MusicXmlRefiner(api_key=api_key, model=model)
    
    # Set refinement parameters from config
    refinement_config = config.get_module_config('refinement')
    refiner.set_refinement_params(**refinement_config)
    
    # Perform refinement
    result = refiner.refine_musicxml(musicxml_path, style=style, custom_prompt=custom_prompt)
    
    return result


def export_project(musicxml_path: str, project_id: str, output_dir: str, 
                  results: Dict[str, Any], config, pdf: bool) -> Dict[str, Any]:
    """
    Export final project with all files and metadata.
    
    Args:
        musicxml_path (str): Path to final MusicXML file
        project_id (str): Project identifier
        output_dir (str): Output directory
        results (Dict[str, Any]): Pipeline results
        config: Configuration object
        pdf (bool): Whether to generate PDF
        
    Returns:
        Dict[str, Any]: Export results
    """
    logger = get_logger(__name__)
    
    # Initialize exporter
    exporter = MusicExporter(output_dir=output_dir)
    
    # Set export parameters from config
    output_config = config.get_module_config('output')
    exporter.set_export_params(**output_config)
    
    # Prepare source information
    source_info = {
        'type': results['input']['source_type'],
        'filename': results['input'].get('title', 'unknown'),
        'duration': results['input']['metadata']['duration'],
        'sample_rate': results['input']['metadata']['sample_rate'],
        'channels': results['input']['metadata']['channels']
    }
    
    # Export project
    export_result = exporter.export_project(
        musicxml_path=musicxml_path,
        project_id=project_id,
        source_info=source_info,
        transcription_info=results['transcription'],
        conversion_info=results['conversion'],
        refinement_info=results.get('refinement')
    )
    
    return export_result


def cleanup_temp_files(temp_files: list) -> None:
    """
    Clean up temporary files.
    
    Args:
        temp_files (list): List of temporary file paths
    """
    logger = get_logger(__name__)
    
    for file_path in temp_files:
        if file_path and Path(file_path).exists():
            try:
                Path(file_path).unlink()
                logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {file_path}: {e}")


if __name__ == '__main__':
    main()
