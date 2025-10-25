"""
Refinement module for sheet music conversion MVP.

This module handles MusicXML refinement using LLM (GPT-5).
Improves and "humanizes" the generated MusicXML notation.

Modules:
- refine_musicxml: Core refinement functionality using OpenAI API
"""

from .refine_musicxml import MusicXmlRefiner

__all__ = ['MusicXmlRefiner']
