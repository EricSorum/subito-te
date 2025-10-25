# 🎼 Sheet Music Conversion MVP — Requirements Specification

## 1. Overview
This MVP converts **audio recordings** (MP3, WAV, or YouTube videos) into **notated sheet music**, delivering both **MusicXML** and **PDF** outputs.  
It integrates automatic transcription (AI-based), format conversion, and refinement steps, providing musicians with accurate, editable notation.

---

## 2. Core Pipeline

### 2.1 Input Stage
**Goal:** Accept an audio source (MP3, WAV, or YouTube link) and prepare it for transcription.

#### Requirements
- Accept file uploads (MP3/WAV) via frontend or local CLI.
- Accept YouTube URLs, download and extract audio using `yt-dlp`.
- Normalize and convert all inputs to `.wav` using `ffmpeg`.
- Handle stereo/mono conversion, 44.1 kHz standardization.
- Provide metadata (duration, bitrate, sample rate) for logging.

**Tech stack:** `ffmpeg`, `yt-dlp`, Python `pydub` or `librosa`.

---

### 2.2 Transcription Stage
**Goal:** Transcribe WAV audio into MIDI notation.

#### Requirements
- Use [BasicPitch](https://github.com/spotify/basic-pitch) as the core transcription engine.
- Output a `.mid` file.
- Capture pitch, onset, offset, and confidence metrics.
- Handle monophonic and simple polyphonic input gracefully.
- Log execution time and possible transcription confidence score.

**Tech stack:** `basic-pitch`, Python.

---

### 2.3 Conversion Stage
**Goal:** Convert MIDI into MusicXML for notation editors.

#### Requirements
- Support conversion via `music21` or `MuseScore` CLI.
- Output `.musicxml` file.
- Preserve tempo, key signature, time signature, and basic dynamics.
- Include error handling for malformed MIDI (invalid note lengths, empty tracks).

**Tech stack:** `music21`, `musescore3` or `musescore4` CLI.

---

### 2.4 Refinement Stage (LLM Cleanup)
**Goal:** Use GPT-5 (via API or local agent) to refine and “humanize” the MusicXML.

#### Requirements
- Parse the raw MusicXML text and suggest improvements:
  - Remove redundant rests or overlapping notes.
  - Adjust quantization errors.
  - Infer key/time signature if missing.
  - Add tempo markings or phrasing hints.
- Provide both the **original** and **refined** MusicXML versions.
- Allow prompting for “style refinements” (e.g., “make this readable for piano”).

**Tech stack:** GPT-5 (OpenAI API), Python `openai` SDK.

---

### 2.5 Output Stage
**Goal:** Export final results for musicians.

#### Requirements
- Export:
  - `final.musicxml`
  - `final.pdf` (engraved via MuseScore CLI or LilyPond)
- Include a small `.json` metadata file describing:
  ```json
  {
    "source": "YouTube URL or filename",
    "duration": "mm:ss",
    "transcription_confidence": 0.89,
    "created_at": "ISO8601 timestamp"
  }
