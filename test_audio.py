import soundcard as sc
import numpy as np
import time

def test_record():
    print("Starting test...")
    try:
        default_speaker = sc.default_speaker()
        print(f"Default Speaker: {default_speaker.name}")
        
        mics = sc.all_microphones(include_loopback=True)
        loopback_mic = None
        for mic in mics:
            if mic.name == default_speaker.name and mic.isloopback:
                loopback_mic = mic
                break
        
        if not loopback_mic:
            for mic in mics:
                if mic.isloopback:
                    loopback_mic = mic
                    break
        
        if not loopback_mic:
            print("No loopback mic found")
            return

        print(f"Recording from: {loopback_mic.name}")
        
        with loopback_mic.recorder(samplerate=16000) as mic:
            print("Recorder opened. Recording 10 chunks...")
            for i in range(10):
                data = mic.record(numframes=1024)
                print(f"Chunk {i}: shape {data.shape}, mean {np.mean(data)}")
                
        print("Test finished successfully.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_record()
