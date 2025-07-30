import threading

from audio_analisys import RealtimeAudioAnalyzer

audio_analyzer = None

def run_audio():
    global audio_analyzer

    if audio_analyzer is None:
        audio_analyzer = RealtimeAudioAnalyzer()
        threading.Thread(target=audio_analyzer.start, daemon=True).start()
        print("Audio analysis started")
    else:
        print("Audio analysis is already running")

def stop_audio():
    global audio_analyzer

    if audio_analyzer is not None:
        audio_analyzer.stop()
        audio_analyzer = None
        print("Audio analysis stopped")
    else:
        print("Audio analysis is not running")

def main():
    print("Type 'start' to start audio analysis, 'stop' to stop, 'exit' to quit.")

    while True:
        cmd = input("> ").strip().lower()

        if cmd == "start":
            run_audio()
        elif cmd == "stop":
            stop_audio()
        elif cmd == "exit":
            if audio_analyzer is not None:
                stop_audio()
            print("Exiting.")
            break
        else:
            print("Unknown command. Use 'start', 'stop', or 'exit'.")

if __name__ == "__main__":
    main()