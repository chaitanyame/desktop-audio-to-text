import sys
import os
import time
import threading
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

# Add NVIDIA library paths for Windows
def setup_nvidia_paths():
    base_path = os.path.dirname(sys.executable)
    site_packages = os.path.join(os.path.dirname(base_path), 'Lib', 'site-packages')
    
    nvidia_paths = [
        os.path.join(site_packages, 'nvidia', 'cudnn', 'bin'),
        os.path.join(site_packages, 'nvidia', 'cublas', 'bin'),
    ]
    
    for path in nvidia_paths:
        if os.path.exists(path):
            os.add_dll_directory(path)
            os.environ['PATH'] = path + os.pathsep + os.environ['PATH']

setup_nvidia_paths()

from ui import CaptionWindow
from audio import AudioCapture
from transcriber import AudioTranscriber

class Worker(QObject):
    text_updated = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.audio_capture = AudioCapture()
        # Using 'cuda' for NVIDIA GPU. If it fails, transcriber handles fallback.
        # Changed model to 'large-v3' for best accuracy
        self.transcriber = AudioTranscriber(model_size="large-v3", device="cuda", compute_type="float16")
        self.running = False

    def start(self):
        self.running = True
        self.transcriber.start(self.handle_transcription)
        self.audio_capture.start()
        
        self.bridge_thread = threading.Thread(target=self._bridge_audio)
        self.bridge_thread.daemon = True
        self.bridge_thread.start()

    def _bridge_audio(self):
        while self.running:
            chunk = self.audio_capture.get_audio_chunk()
            if chunk is not None:
                self.transcriber.add_audio(chunk)
            else:
                time.sleep(0.01)

    def handle_transcription(self, text):
        self.text_updated.emit(text)

    def stop(self):
        self.running = False
        self.audio_capture.stop()
        self.transcriber.stop()

def main():
    app = QApplication(sys.argv)
    
    # UI
    window = CaptionWindow()
    window.show()

    # Logic
    worker = Worker()
    worker.text_updated.connect(window.update_text)
    worker.start()

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        pass
    finally:
        worker.stop()

if __name__ == "__main__":
    main()
