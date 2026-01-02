# Desktop Audio to Text

A real-time desktop audio captioning application that uses OpenAI's Whisper model (via `faster-whisper`) to transcribe system audio and display it in a floating, transparent overlay.

## Features

- **Real-time Transcription**: Captures desktop audio (what you hear) and transcribes it instantly.
- **High Accuracy**: Uses the `large-v3` Whisper model by default for state-of-the-art accuracy.
- **GPU Acceleration**: Supports NVIDIA GPU acceleration (CUDA) for faster processing, with automatic CPU fallback.
- **Overlay UI**: 
  - Frameless, transparent window that stays on top of other applications.
  - Drag-to-move functionality.
  - Minimize support.

## Prerequisites

- **OS**: Windows (due to WASAPI loopback audio capture).
- **Python**: 3.8 or higher.
- **GPU (Optional)**: NVIDIA GPU with CUDA installed is highly recommended for real-time performance.

## Installation

1. Clone the repository:
   ```bash
   git clone YOUR_REPO_URL
   cd desktop-audio-to-text
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   *Note: If you have an NVIDIA GPU, ensure you have the appropriate CUDA and cuDNN libraries installed for `faster-whisper`.*

## Usage

Run the main script to start the application:

```bash
python main.py
```

The application will launch a transparent window. Play any audio on your computer (YouTube, meetings, movies), and the text will appear in the window.

## Configuration

You can modify `main.py` or `transcriber.py` to adjust settings:
- **Model Size**: Change `model_size="large-v3"` in `main.py` to `"medium"`, `"small"`, or `"base"` for lower resource usage.
- **Compute Type**: Change `compute_type="float16"` to `"int8"` if you are running on CPU or have limited VRAM.

## Troubleshooting

- **"WASAPI not found"**: This error occurs if you are not on Windows or if audio drivers are not properly configured. This application relies on Windows WASAPI for loopback recording.
- **Slow Transcription**: If running on CPU, the `large-v3` model may be too slow. Try switching to a smaller model size in `main.py`.
