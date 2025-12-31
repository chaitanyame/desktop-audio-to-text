from faster_whisper import WhisperModel
import numpy as np
import threading
import queue
import time
import inspect

class AudioTranscriber:
    def __init__(
        self,
        model_size="small",
        device="cuda",
        compute_type="float16",
        *,
        warmup_seconds=10.0,
        transcribe_interval=3.0,
        min_detect_seconds=8.0,
        language_lock_threshold=0.80,
        language_detection_segments=2,
        language_detection_threshold=0.80,
        language_redetect_interval=180.0,
        beam_size=3,
        temperature=0.0,
        best_of=1,
    ):
        print(f"Loading Whisper model: {model_size} on {device}...")
        try:
            self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        except Exception as e:
            print(f"Error loading model on {device}: {e}")
            print("Falling back to CPU...")
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

        # Cache supported transcribe() kwargs for compatibility across faster-whisper versions.
        try:
            self._transcribe_supported_kwargs = set(inspect.signature(self.model.transcribe).parameters.keys())
        except Exception:
            self._transcribe_supported_kwargs = None

        self.audio_queue = queue.Queue()
        self.running = False
        self.thread = None
        self.callback = None
        
        # Buffer for accumulating audio
        self.buffer = np.array([], dtype=np.float32)
        self.sample_rate = 16000

        # Chunking / cadence
        self.warmup_seconds = float(warmup_seconds)
        self.transcribe_interval = float(transcribe_interval)
        self.min_detect_seconds = float(min_detect_seconds)

        # Multi-language strategy: detect once during warm-up, then lock language.
        self.language_lock_threshold = float(language_lock_threshold)
        self.language_detection_segments = int(language_detection_segments)
        self.language_detection_threshold = float(language_detection_threshold)
        self.language_redetect_interval = float(language_redetect_interval)
        self.locked_language = None
        self.locked_language_probability = 0.0
        self.last_language_check_ts = 0.0
        self._pending_language = None
        self._pending_language_count = 0

        # Decoding (speed/quality)
        self.beam_size = int(beam_size)
        self.temperature = float(temperature)
        self.best_of = int(best_of)

        self._has_emitted_text = False

    def start(self, callback):
        self.callback = callback
        self.running = True
        self.thread = threading.Thread(target=self._process_loop)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def add_audio(self, audio_chunk):
        self.audio_queue.put(audio_chunk)

    def _process_loop(self):
        while self.running:
            try:
                # Get audio from queue
                chunk = self.audio_queue.get(timeout=0.1)
                self.buffer = np.concatenate((self.buffer, chunk))
                
                # Check if we have enough audio or time passed
                current_time = time.time()
                duration = len(self.buffer) / self.sample_rate

                target_seconds = self.transcribe_interval
                if not self._has_emitted_text and self.warmup_seconds > 0:
                    # Initial delay is acceptable: use a bigger warm-up chunk so language detection is reliable.
                    target_seconds = max(target_seconds, self.warmup_seconds)

                if duration >= target_seconds:
                    self._transcribe()
                    # Clear buffer after transcription for this simple version
                    # In a more advanced version, we would use a rolling window or VAD
                    self.buffer = np.array([], dtype=np.float32) 
                    # current_time kept for potential future cadence logic
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in processing: {e}")

    def _transcribe(self):
        if len(self.buffer) == 0:
            return

        now = time.time()
        duration = len(self.buffer) / self.sample_rate

        should_redetect = (
            self.locked_language is None
            or (
                self.language_redetect_interval > 0
                and (now - self.last_language_check_ts) >= self.language_redetect_interval
                and duration >= self.min_detect_seconds
            )
        )

        # If locked, pass explicit language to avoid repeated detection overhead.
        language_arg = None if should_redetect else self.locked_language
        multilingual_arg = True if language_arg is None else False

        # Run inference
        # vad_filter=True helps ignore silence
        # condition_on_previous_text=False helps prevent hallucination loops
        transcribe_kwargs = dict(
            beam_size=self.beam_size,
            best_of=self.best_of,
            temperature=self.temperature,
            language=language_arg,
            multilingual=multilingual_arg,
            task="translate",
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            condition_on_previous_text=False,
            language_detection_segments=self.language_detection_segments,
            language_detection_threshold=self.language_detection_threshold,
        )

        if self._transcribe_supported_kwargs is not None:
            transcribe_kwargs = {
                k: v for k, v in transcribe_kwargs.items() if k in self._transcribe_supported_kwargs
            }

        segments, info = self.model.transcribe(self.buffer, **transcribe_kwargs)

        segments_list = list(segments)
        text = " ".join([segment.text for segment in segments_list]).strip()

        # Update language lock when we did detection.
        if language_arg is None and hasattr(info, "language") and hasattr(info, "language_probability"):
            self.last_language_check_ts = now
            detected_language = info.language
            detected_prob = float(info.language_probability or 0.0)

            if detected_prob >= self.language_lock_threshold and detected_language:
                if self.locked_language == detected_language:
                    self.locked_language_probability = detected_prob
                    self._pending_language = None
                    self._pending_language_count = 0
                else:
                    # Require two consecutive detections before switching to avoid transient flips.
                    if self._pending_language == detected_language:
                        self._pending_language_count += 1
                    else:
                        self._pending_language = detected_language
                        self._pending_language_count = 1

                    if self._pending_language_count >= 2:
                        self.locked_language = detected_language
                        self.locked_language_probability = detected_prob
                        self._pending_language = None
                        self._pending_language_count = 0
        
        # Filter common Whisper hallucinations
        hallucinations = [
            "Thank you", "Thanks for watching", "Thank you for watching", 
            "Subscribe", "Amara.org", "MBC", "Copyright", "silence"
        ]
        
        # If the text is short and contains a hallucination phrase, ignore it
        if any(h.lower() in text.lower() for h in hallucinations):
            if len(text) < 50: # Only filter if it's a short phrase (likely just the hallucination)
                return

        if text and self.callback:
            # print(f"Detected language: {info.language} with probability {info.language_probability}")
            self.callback(text)
            self._has_emitted_text = True
