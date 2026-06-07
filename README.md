# Jarvis Voice Assistant

A terminal-based AI voice assistant for macOS (Apple Silicon). Press Enter to talk, press Enter again to stop -- Jarvis listens, thinks, and speaks back.

## Prerequisites

- **macOS** (uses `afplay` for audio playback)
- **Python 3.11+**
- **OMLX Server** running locally at `http://127.0.0.1:8000` with:
  - ASR model loaded (Qwen3-ASR-1.7B)
  - TTS model loaded (Qwen3-TTS-12Hz-1.7B-CustomVoice, voice: Vivian)
- **MiniMax API key** (or another OpenAI-compatible LLM provider)

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env from the template
cp .env.example .env

# 3. Edit .env and set your MiniMax API key
# MINIMAX_API_KEY=your_api_key_here
```

## Usage

```bash
python -m jarvis.main
```

**Voice mode (default):**
1. Press **Enter** to start recording
2. Speak your question
3. Press **Enter** to stop recording
4. Jarvis transcribes, thinks, and speaks the reply

**Debug mode (no microphone needed):**
```bash
DEBUG_MODE=true python -m jarvis.main
```
Type your message at the `You: >` prompt instead of speaking.

Press **Ctrl+C** to exit.

## Configuration

All settings are managed in `config.py`. Override via environment variables or a `.env` file.

| Variable | Default | Required | Description |
|---|---|---|---|
| `MINIMAX_API_KEY` | -- | **Yes** | MiniMax API key |
| `MINIMAX_BASE_URL` | `https://api.minimax.io/v1` | No | MiniMax endpoint |
| `MINIMAX_MODEL` | `abab7-chat` | No | Model name |
| `OMLX_API_KEY` | -- | **Yes** | OMLX server API key |
| `OMLX_BASE_URL` | `http://127.0.0.1:8000` | No | Local OMLX server |
| `TTS_VOICE` | `Vivian` | No | TTS voice name |
| `DEBUG_MODE` | `false` | No | Skip mic, use text input |

## Project Structure

```
jarvis/
├── main.py              # CLI entry point
├── config.py             # Centralized configuration
├── audio/
│   ├── recorder.py       # Microphone recording (sounddevice)
│   └── player.py         # WAV playback (afplay)
├── asr/
│   └── qwen_asr.py       # Speech-to-text (OMLX)
├── llm/
│   ├── base.py           # Abstract LLM interface
│   └── minimax.py        # MiniMax provider
├── tts/
│   └── qwen_tts.py       # Text-to-speech (OMLX)
├── core/
│   ├── input_strategy.py # Input strategy pattern (voice/text)
│   └── jarvis.py         # Pipeline orchestrator
└── requirements.txt
```

## Troubleshooting

**"Failed to access microphone"**
Grant terminal (Terminal.app / iTerm2) microphone access in System Preferences > Security & Privacy > Microphone. Or use debug mode: `DEBUG_MODE=true python -m jarvis.main`.

**"MINIMAX_API_KEY is required"**
Copy `.env.example` to `.env` and set your API key.

**TTS timeout on first request**
The OMLX TTS model cold-loads on first use, which can take 10-30 seconds. Subsequent requests are fast.
