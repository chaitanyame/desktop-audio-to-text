# Copilot Instructions

## Project shape
- Desktop live-caption app on Windows: PyQt6 overlay window, loopback audio capture, faster-whisper transcription.
- Entry point: main.py wires UI + Worker that bridges audio capture to transcription callbacks.
- GPU-first: attempts CUDA float16; auto falls back to CPU int8 if model load fails.

## Components & flows
- Audio capture: audio.AudioCapture uses PyAudioWPatch WASAPI loopback of default speakers; converts int16 -> float32, averages to mono, downsamples 48k/44.1k to 16k, enqueues numpy chunks sized by block_size (default 1024). No explicit stop of PyAudio until thread ends.
- Transcription: transcriber.AudioTranscriber wraps faster-whisper WhisperModel.
  - Buffering: collects chunks at 16k; transcribe when buffer duration >= transcribe_interval (default 3s); first pass uses warmup_seconds (default 10s) to stabilize language detection.
  - Language handling: detects language during warmup; locks when probability >= language_lock_threshold (0.8) with two consecutive matches; optional re-detect every language_redetect_interval (default 180s) if enough audio; passes language to transcribe() to skip detection once locked.
  - Decoding defaults: task="translate" (forces English output), beam_size=3, temperature=0, best_of=1, vad_filter=True with min_silence_duration_ms=500, condition_on_previous_text=False to avoid hallucination loops.
  - Hallucination filter: drops short (<50 chars) outputs containing phrases like "Thank you", "Thanks for watching", etc.
- UI: ui.CaptionWindow is frameless, always-on-top, draggable; custom title bar with minimize and exit; label shows latest text only (no history); positioned near bottom center of primary screen.
- Worker: main.Worker spins AudioCapture + AudioTranscriber threads, forwards transcription text via Qt signal to UI; uses thread-based bridge polling audio_queue every 10ms.

## Running & environment
- Use a venv for all runs; do not install libraries globally. Example: `python -m venv .venv && .venv/Scripts/activate` then `pip install -r requirements.txt`.
- Run app: `python main.py` (expects Windows with WASAPI loopback). main.py injects NVIDIA DLL paths from site-packages (cudnn/cublas) before importing PyQt; Whisper load may still fall back to CPU.
- Models: AudioTranscriber defaults to model_size="small" but main.py constructs with model_size="large-v3", device="cuda", compute_type="float16".
- Requirements: faster-whisper, PyAudioWPatch, PyQt6, numpy. PyAudioWPatch supplies WASAPI loopback; soundcard is only used in test_audio.py.

## Testing & diagnostics
- Loopback sanity check: run `python test_audio.py` to record 10 chunks from loopback mic using soundcard; prints shapes/means.
- Audio capture prints chosen device names and errors (e.g., missing WASAPI); transcription prints model load failures.

## Conventions & cautions
- Sample rate is assumed 16k across pipeline; capture downsampling is manual—ensure new capture paths match this.
- Transcription buffer resets after each emit; no rolling context; condition_on_previous_text=False by design.
- UI shows only latest text, not a log; any history feature must manage layout constraints and transparency.
- Keep instructions Windows-focused (WASAPI + PyAudioWPatch); alternative platforms need new capture path.
