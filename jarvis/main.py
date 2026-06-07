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

    print("=" * 50)
    print("  JARVIS Voice Assistant")
    print(f"  Input:     {input_mode}")
    if not settings.debug_mode:
        words = ", ".join(f"'{w}'" for w in settings.wake_words)
        print(f"  Wake Words: {words}")
    print(f"  Mode:      {conv_mode}")
    print(f"  Speech:    {settings.speech_provider.upper()}")
    print("  Press Ctrl+C to exit")
    print("=" * 50)

    jarvis = Jarvis()

    try:
        jarvis.run()
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
