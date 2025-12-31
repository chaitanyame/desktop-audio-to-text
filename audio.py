import pyaudiowpatch as pyaudio
import numpy as np
import threading
import queue

class AudioCapture:
    def __init__(self, sample_rate=16000, block_size=1024):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.audio_queue = queue.Queue()
        self.running = False
        self.thread = None
        self.p = None
        self.stream = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._record_loop)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _record_loop(self):
        try:
            self.p = pyaudio.PyAudio()
            
            # Get default WASAPI info
            try:
                wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
            except OSError:
                print("WASAPI not found")
                return

            # Get default output device
            default_speakers = self.p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            print(f"Default Output Device: {default_speakers['name']}")
            
            # Find loopback device
            loopback_device = None
            if not default_speakers["isLoopbackDevice"]:
                for loopback in self.p.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        loopback_device = loopback
                        break
                
                # Fallback: use first loopback device if exact match not found
                if not loopback_device:
                    for loopback in self.p.get_loopback_device_info_generator():
                        loopback_device = loopback
                        break
            else:
                loopback_device = default_speakers

            if not loopback_device:
                print("No loopback device found.")
                return

            print(f"Recording from: {loopback_device['name']}")
            
            def callback(in_data, frame_count, time_info, status):
                if not self.running:
                    return (None, pyaudio.paComplete)
                
                # Convert to numpy array
                audio_data = np.frombuffer(in_data, dtype=np.int16)
                audio_data = audio_data.astype(np.float32) / 32768.0
                channels = loopback_device["maxInputChannels"]
                audio_data = audio_data.reshape(-1, channels)
                mono_data = np.mean(audio_data, axis=1)
                
                # Resample if necessary
                device_rate = int(loopback_device["defaultSampleRate"])
                if device_rate == 48000:
                    mono_data = mono_data[::3]
                elif device_rate == 44100:
                    step = device_rate / 16000
                    indices = np.arange(0, len(mono_data), step).astype(int)
                    indices = indices[indices < len(mono_data)]
                    mono_data = mono_data[indices]

                self.audio_queue.put(mono_data)
                return (None, pyaudio.paContinue)

            # Open stream
            self.stream = self.p.open(
                format=pyaudio.paInt16,
                channels=loopback_device["maxInputChannels"],
                rate=int(loopback_device["defaultSampleRate"]),
                input=True,
                input_device_index=loopback_device["index"],
                frames_per_buffer=self.block_size,
                stream_callback=callback
            )
            
            self.stream.start_stream()
            
            while self.running:
                self.stream.is_active()
                import time
                time.sleep(0.1)

        except Exception as e:
            print(f"Error in audio capture: {e}")
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.p:
                self.p.terminate()

    def get_audio_chunk(self):
        try:
            return self.audio_queue.get_nowait()
        except queue.Empty:
            return None
