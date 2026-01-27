#!/usr/bin/env python3
"""
Quick test script for Eleven Labs TTS integration.

Usage:
    python test_voice.py

Make sure you have set the environment variables:
    ELEVEN_LABS_API_KEY=sk_xxx
    ELEVEN_LABS_VOICE_ID=xPnmQf6Ow3GGYWWURFPi
"""
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()


def test_sdk_import():
    """Test if elevenlabs SDK is installed."""
    print("1. Testing SDK import...")
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import VoiceSettings
        print("   ✓ elevenlabs SDK imported successfully")
        return True
    except ImportError as e:
        print(f"   ✗ Failed to import: {e}")
        print("   Run: pip install elevenlabs")
        return False


def test_api_key():
    """Test if API key is configured."""
    print("\n2. Testing API key configuration...")
    api_key = os.getenv("ELEVEN_LABS_API_KEY")
    if api_key:
        print(f"   ✓ API key found: {api_key[:10]}...")
        return True
    else:
        print("   ✗ ELEVEN_LABS_API_KEY not set")
        return False


def test_voice_id():
    """Test if voice ID is configured."""
    print("\n3. Testing voice ID configuration...")
    voice_id = os.getenv("ELEVEN_LABS_VOICE_ID")
    if voice_id:
        print(f"   ✓ Voice ID found: {voice_id}")
        return True
    else:
        print("   ✗ ELEVEN_LABS_VOICE_ID not set")
        return False


def test_tts_generation():
    """Test text-to-speech generation."""
    print("\n4. Testing TTS generation...")

    api_key = os.getenv("ELEVEN_LABS_API_KEY")
    voice_id = os.getenv("ELEVEN_LABS_VOICE_ID")

    if not api_key or not voice_id:
        print("   ✗ Missing API key or voice ID")
        return False

    try:
        from elevenlabs.client import ElevenLabs

        client = ElevenLabs(api_key=api_key)

        # Generate short test audio
        audio = client.text_to_speech.convert(
            text="Olá! Este é um teste do serviço de voz.",
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )

        # Collect audio bytes
        audio_bytes = b"".join(chunk for chunk in audio)

        print(f"   ✓ Generated {len(audio_bytes)} bytes of audio")

        # Save to file for manual testing
        with open("test_output.mp3", "wb") as f:
            f.write(audio_bytes)
        print("   ✓ Saved to test_output.mp3")

        return True

    except Exception as e:
        print(f"   ✗ TTS failed: {e}")
        return False


def test_ffmpeg():
    """Test if FFmpeg is available."""
    print("\n5. Testing FFmpeg...")
    import subprocess

    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.decode().split('\n')[0]
            print(f"   ✓ FFmpeg available: {version[:50]}...")
            return True
        else:
            print("   ✗ FFmpeg returned non-zero")
            return False
    except FileNotFoundError:
        print("   ✗ FFmpeg not found. Install: brew install ffmpeg")
        return False
    except Exception as e:
        print(f"   ✗ FFmpeg error: {e}")
        return False


def test_ogg_conversion():
    """Test MP3 to OGG OPUS conversion."""
    print("\n6. Testing OGG OPUS conversion...")

    if not os.path.exists("test_output.mp3"):
        print("   ✗ test_output.mp3 not found (run TTS test first)")
        return False

    import subprocess

    try:
        # Read MP3
        with open("test_output.mp3", "rb") as f:
            mp3_data = f.read()

        # Convert with FFmpeg
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "mp3",
            "-i", "pipe:0",
            "-c:a", "libopus",
            "-b:a", "32k",
            "-ar", "48000",
            "-ac", "1",
            "-application", "voip",
            "-f", "ogg",
            "pipe:1"
        ]

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        ogg_data, error = process.communicate(input=mp3_data, timeout=30)

        if process.returncode != 0:
            print(f"   ✗ FFmpeg error: {error.decode()[:100]}")
            return False

        # Save OGG
        with open("test_output.ogg", "wb") as f:
            f.write(ogg_data)

        print(f"   ✓ Converted {len(mp3_data)} bytes MP3 → {len(ogg_data)} bytes OGG")
        print("   ✓ Saved to test_output.ogg")

        return True

    except Exception as e:
        print(f"   ✗ Conversion failed: {e}")
        return False


def test_voices_list():
    """Test listing available voices."""
    print("\n7. Testing voices list...")

    api_key = os.getenv("ELEVEN_LABS_API_KEY")
    if not api_key:
        print("   ✗ Missing API key")
        return False

    try:
        from elevenlabs.client import ElevenLabs

        client = ElevenLabs(api_key=api_key)
        response = client.voices.get_all()

        print(f"   ✓ Found {len(response.voices)} voices:")
        for v in response.voices[:5]:  # Show first 5
            print(f"      - {v.name} ({v.voice_id})")

        if len(response.voices) > 5:
            print(f"      ... and {len(response.voices) - 5} more")

        return True

    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 50)
    print("ELEVEN LABS TTS INTEGRATION TEST")
    print("=" * 50)

    results = {
        "SDK Import": test_sdk_import(),
        "API Key": test_api_key(),
        "Voice ID": test_voice_id(),
        "TTS Generation": test_tts_generation(),
        "FFmpeg": test_ffmpeg(),
        "OGG Conversion": test_ogg_conversion(),
        "Voices List": test_voices_list(),
    }

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test, result in results.items():
        status = "✓" if result else "✗"
        print(f"  {status} {test}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All tests passed! Voice service is ready.")
    else:
        print("\n⚠️  Some tests failed. Check configuration.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
