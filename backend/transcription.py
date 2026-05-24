import os
import sys

# Dynamic FFmpeg path loading
FFMPEG_BIN_PATH = r"C:\Users\royan\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"
if os.path.exists(FFMPEG_BIN_PATH) and FFMPEG_BIN_PATH not in os.environ["PATH"]:
    os.environ["PATH"] = FFMPEG_BIN_PATH + os.path.pathsep + os.environ["PATH"]

# Flags for faster-whisper availability
HAS_FASTER_WHISPER = False
try:
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    print("faster-whisper not installed or failed to import. Falling back to Gemini Multimodal Audio API.")

_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if not HAS_FASTER_WHISPER:
        return None
    if _whisper_model is None:
        try:
            # Using the "tiny" model on CPU with float32 for maximum compatibility
            _whisper_model = WhisperModel("tiny", device="cpu", compute_type="float32")
        except Exception as e:
            print(f"Failed to load faster-whisper model: {e}")
            _whisper_model = None
    return _whisper_model

def transcribe_audio_gemini(audio_file_path: str, gemini_client) -> str:
    """Fallback transcription using Gemini File API."""
    if not gemini_client:
        raise ValueError("Gemini client is required for fallback transcription.")
    
    print(f"Using Gemini File API to transcribe: {audio_file_path}")
    audio_file = None
    try:
        # Upload the audio file to the Gemini File API
        audio_file = gemini_client.files.upload(file=audio_file_path)
        
        # Ask Gemini to transcribe the audio content
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                audio_file,
                "Transcribe this audio clip exactly. If it is silent or unintelligible, return an empty string. Output only the transcription, do not add introductory comments."
            ]
        )
        return response.text.strip() if response.text else ""
    except Exception as e:
        print(f"Gemini transcription fallback failed: {e}")
        raise e
    finally:
        if audio_file:
            try:
                # Clean up uploaded file
                gemini_client.files.delete(name=audio_file.name)
            except Exception as e:
                print(f"Failed to delete Gemini temp file: {e}")

def transcribe_audio(audio_file_path: str, gemini_client=None) -> str:
    """
    Main transcription entrypoint.
    First attempts faster-whisper, and falls back to Gemini Audio API if whisper fails or is missing.
    """
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
    model = get_whisper_model()
    if model:
        try:
            print(f"Transcribing {audio_file_path} using local faster-whisper...")
            segments, info = model.transcribe(audio_file_path, beam_size=1)
            text = " ".join([seg.text for seg in segments]).strip()
            print(f"Local Whisper Transcription: {text}")
            return text
        except Exception as e:
            print(f"Local Whisper transcription failed, trying Gemini API: {e}")
            
    # Fallback to Gemini Multimodal API if whisper is disabled or errored
    if gemini_client:
        return transcribe_audio_gemini(audio_file_path, gemini_client)
        
    raise RuntimeError("No transcription method succeeded (Whisper failed, and no Gemini Client was provided).")
