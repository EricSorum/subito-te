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
Store outputs in /output/[project-id]/ folders.

Tech stack: MuseScore CLI, Python reportlab or subprocess.

3. Project Structure
/project-root
├── src/
│   ├── input/
│   │   ├── downloader.py
│   │   ├── converter.py
│   │   └── __init__.py
│   ├── transcription/
│   │   └── transcribe.py
│   ├── conversion/
│   │   ├── midi_to_musicxml.py
│   │   └── __init__.py
│   ├── refinement/
│   │   └── refine_musicxml.py
│   ├── output/
│   │   └── export.py
│   └── utils/
│       ├── logging.py
│       └── config.py
├── requirements.txt
├── config.yaml
├── main.py
└── README.md

4. Functional Requirements
ID	Description	Priority	Owner
F1	Accept audio file or YouTube link input	High	Input module
F2	Convert any input to standardized WAV	High	Input module
F3	Generate MIDI from WAV using BasicPitch	High	Transcription module
F4	Convert MIDI to MusicXML	High	Conversion module
F5	Refine MusicXML using GPT-5	Medium	Refinement module
F6	Generate PDF from MusicXML	Medium	Output module
F7	Log process metadata to JSON	Medium	Utils
F8	CLI interface for local runs	Medium	Main app
F9	Basic frontend upload (optional for later MVP)	Low	TBD
5. Non-Functional Requirements

Runtime: < 2 minutes for 3-minute audio on modern hardware.

Portability: macOS + Linux (local) compatibility.

Extensibility: Modular design; future modules can replace BasicPitch or MuseScore.

Error Handling: Graceful fallback with logging (e.g., skip to next step even if LLM fails).

Observability: Timestamped logs for each stage.

Privacy: All local processing; optional cloud-based LLM step.

6. Future Enhancements (Post-MVP)

Instrument detection & multi-track separation.

GUI or web dashboard.

User presets for “instrument type” (piano, guitar, vocal).

Fine-tuned quantization or tempo correction.

Integration with MuseScore Plugin API.

Cloud processing queue with async jobs.

7. Example CLI Usage
python3 main.py \
  --input "/path/to/file.mp3" \
  --output "./output" \
  --refine true \
  --pdf true


Expected output:

✅ Downloaded and converted input.mp3 → temp.wav
✅ Transcribed to output.mid
✅ Converted to output.musicxml
✅ Refined and cleaned MusicXML (GPT-5)
✅ Exported to output/final.pdf

8. Dependencies (Python)
basic-pitch
music21
yt-dlp
pydub
openai
ffmpeg-python
reportlab
pyyaml

9. Milestones
Milestone	Deliverable	Target
M1	Input + Transcription end-to-end (WAV → MIDI)	Week 1
M2	Conversion + Output (MIDI → MusicXML → PDF)	Week 2
M3	LLM refinement loop	Week 3
M4	CLI + Docs polish	Week 4
10. Acceptance Criteria

✅ Audio → MusicXML + PDF output fully automated.

✅ BasicPitch integration stable for ≥ 80% of tested files.

✅ Generated MusicXML opens cleanly in MuseScore.

✅ Logs and metadata created per run.

✅ Optional GPT-5 refinement demonstrably improves legibility.

11. License & Attribution

BasicPitch © Spotify under MIT License.

MuseScore CLI and MusicXML © MuseScore BVBA.

This MVP will be open-sourced under MIT or Apache 2.0 license.