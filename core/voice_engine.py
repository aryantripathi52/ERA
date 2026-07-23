import pyttsx3
import speech_recognition as sr
import threading
import time
import io
import os
import tempfile

# Attempt to import whisper
try:
    import whisper
    import numpy as np
    _HAS_WHISPER = True
except ImportError:
    _HAS_WHISPER = False

class VoiceEngine:
    def __init__(self, voice_name="Lester", model_size="base"):
        # Initialize TTS
        self.tts = pyttsx3.init()
        self.tts.setProperty('rate', 175)  # Speed of speech
        self.tts.setProperty('volume', 0.9) # Volume (0.0 to 1.0)
        
        # Set a male, sharp voice if possible (similar to Jarvis/Lester)
        voices = self.tts.getProperty('voices')
        for v in voices:
            if "david" in v.name.lower() or "zira" not in v.name.lower():
                self.tts.setProperty('voice', v.id)
                break
        
        # Initialize STT
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Whisper model
        self.stt_model = None
        if _HAS_WHISPER:
            print(f"[Voice] 🧠 Loading Whisper model ({model_size})...")
            self.stt_model = whisper.load_model(model_size)
            print("[Voice] ✅ Whisper ready.")
        else:
            print("[Voice] ⚠️ Whisper not found. Using Google fallback.")
        
        self.is_listening = False
        self.is_speaking = False
        self._stop_listening = False

    def speak(self, text):
        """Turn text to speech synchronously."""
        if not text: return
        self.is_speaking = True
        print(f"[Voice] 🗣️ {text}")
        self.tts.say(text)
        self.tts.runAndWait()
        self.is_speaking = False

    def speak_async(self, text):
        """Speak in a separate thread to avoid blocking."""
        threading.Thread(target=self.speak, args=(text,), daemon=True).start()

    def _transcribe(self, audio_data):
        """Internal transcription helper using Whisper or Google."""
        if self.stt_model:
            # Whisper Transcription
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data.get_wav_data())
                tmp_path = f.name
            
            try:
                # Direct array transcription to avoid ffmpeg dependency
                import wave
                import numpy as np
                
                with wave.open(tmp_path, "rb") as wf:
                    # Whisper expects 16kHz mono PCM
                    frames = wf.readframes(wf.getnframes())
                    audio_np = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                
                result = self.stt_model.transcribe(audio_np, fp16=False)
                text = result.get("text", "").strip()
                return text if text else None
            except Exception as e:
                print(f"[Voice] ❌ Whisper error: {e}")
                # Fallback to google if whisper fails
                try:
                    return self.recognizer.recognize_google(audio_data)
                except:
                    return None
            finally:
                if os.path.exists(tmp_path):
                    try: os.remove(tmp_path)
                    except: pass
        else:
            # Google Fallback
            try:
                return self.recognizer.recognize_google(audio_data)
            except:
                return None

    def listen(self, timeout=5, phrase_time_limit=10):
        """Listen for a single phrase and return text."""
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("[Voice] 🎤 Listening...")
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                text = self._transcribe(audio)
                if text:
                    print(f"[Voice] 👂 You said: {text}")
                return text
            except sr.WaitTimeoutError:
                return None
            except Exception as e:
                print(f"[Voice] ❌ Listen error: {e}")
                return None

    def start_background_listening(self, callback):
        """Continuously listen for wake word or input."""
        def background_thread():
            with self.microphone as source:
                while not self._stop_listening:
                    if self.is_speaking:
                        time.sleep(0.5)
                        continue
                    
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    try:
                        audio = self.recognizer.listen(source, timeout=2)
                        text = self._transcribe(audio)
                        if text:
                            callback(text)
                    except:
                        continue
        
        self._stop_listening = False
        threading.Thread(target=background_thread, daemon=True).start()

    def stop_listening(self):
        self._stop_listening = True
