"""
Output module for sheet music conversion MVP.

This module handles final output generation and export.
Creates PDF files from MusicXML and generates metadata files.

Modules:
- export: Core export functionality for PDF and metadata generation
"""

from .export import MusicExporter

__all__ = ['MusicExporter']
