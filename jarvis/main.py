import sys

from jarvis.config import settings, validate_config
from jarvis.core.jarvis import Jarvis


def main() -> None:
    errors = validate_config()
    if errors:
        print("Configuration errors detected:\n")
        for field, message in errors:
            print(f"  [{field}]")
            print(f"  {message}")
            print()
        sys.exit(1)

    input_mode = "DEBUG (text input)" if settings.debug_mode else "VOICE (microphone)"
    conv_mode = settings.conversation_mode.upper()
    sid = settings
    sp = sid.speech_provider.upper()
    if sid.speech_provider == "qwen":
        sm = sid.tts_model
    else:
        sm = sid.minimax_speech_model
    print("=" * 50)
    print("  JARVIS Voice Assistant")
    print(f"  Input Mode:       {input_mode}")
    print(f"  Conversation Mode: {conv_mode}")
    print(f"  Speech Provider:   {sp}")
    print(f"  Speech Model:      {sm}")
    if sid.speech_provider == "minimax":
        print(f"  Speech Mode:       {sid.minimax_speech_mode}")
        print(f"  Voice ID:          {sid.minimax_speech_voice_id}")
        print(f"  Audio Format:      {sid.minimax_speech_audio_format}")
    print(f"  Memory:            {'ON' if sid.memory_enabled else 'OFF'}"
          f" (max {sid.memory_max_turns} turns)")
    print("  Press Ctrl+C to exit")
    print("=" * 50)
    print()

    jarvis = Jarvis()

    try:
        jarvis.run()
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
