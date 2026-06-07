# Jarvis Voice Assistant

A terminal-based AI voice assistant for macOS (Apple Silicon). Press Enter to talk, press Enter again to stop — Jarvis listens, thinks, and speaks back.

## Features

- **Voice I/O** — Microphone recording (16kHz) + macOS `afplay` playback
- **Multi-provider LLM** — MiniMax (OpenAI-compatible), easily extensible
- **Multi-provider Speech** — Qwen3-TTS (local OMLX) or MiniMax T2A v2 (streaming + non-streaming)
- **Conversation Memory** — Short-term (recent turns) + Long-term summary memory, persisted to disk
- **Debug mode** — Text-based I/O, no microphone required

## Prerequisites

- **macOS** (uses `afplay` for audio playback)
- **Python 3.11+**
- **OMLX Server** running locally at `http://127.0.0.1:8000` with:
  - ASR model loaded (Qwen3-ASR-1.7B)
  - TTS model loaded (Qwen3-TTS-12Hz-1.7B-CustomVoice) — optional if using MiniMax Speech
- **MiniMax API key** for LLM and/or Speech (get from [MiniMax platform](https://platform.minimaxi.com))

## Quick Start

```bash
# 1. Install dependencies
pip install -r jarvis/requirements.txt

# 2. Create .env from the template
cd jarvis
cp .env.example .env

# 3. Edit .env — set MINIMAX_API_KEY and OMLX_API_KEY

# 4. Run
python -m jarvis.main
```

### Voice Mode (default)

1. Press **Enter** to start recording
2. Speak your question
3. Press **Enter** to stop
4. Jarvis transcribes → thinks → speaks

### Debug Mode (no microphone)

```bash
DEBUG_MODE=true python -m jarvis.main
```

Type your message at the `You: >` prompt. Press **Ctrl+C** to exit.

## Configuration

All settings via `.env` file or environment variables.

### Required

| Variable | Description |
|---|---|
| `MINIMAX_API_KEY` | MiniMax API key |
| `OMLX_API_KEY` | OMLX local server API key |

### LLM

| Variable | Default | Description |
|---|---|---|
| `MINIMAX_BASE_URL` | `https://api.minimaxi.com/v1` | MiniMax endpoint |
| `MINIMAX_MODEL` | `MiniMax-M3` | LLM model |
| `MINIMAX_MAX_TOKENS` | `1024` | Max response tokens |
| `MINIMAX_TEMPERATURE` | `0.7` | Response creativity |
| `CONVERSATION_MODE` | `llm` | `llm` (MiniMax) or `tts` (Qwen3-TTS bypass) |
| `SYSTEM_PROMPT` | (English prompt) | LLM system personality |

### Speech Provider — Qwen (local OMLX)

| Variable | Default | Description |
|---|---|---|
| `SPEECH_PROVIDER` | `qwen` | Set to `qwen` for local OMLX TTS |
| `TTS_MODEL` | `Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit` | Qwen TTS model |
| `TTS_VOICE` | `Vivian` | Qwen TTS voice |

### Speech Provider — MiniMax (cloud T2A v2)

| Variable | Default | Description |
|---|---|---|
| `SPEECH_PROVIDER` | `qwen` | Set to `minimax` for MiniMax T2A |
| `MINIMAX_SPEECH_URL` | `https://api.minimaxi.com/v1/t2a_v2` | Full T2A endpoint URL |
| `MINIMAX_SPEECH_MODEL` | `speech-2.8-turbo` | speech-2.8-hd/turbo, speech-2.6-hd/turbo, speech-02-hd/turbo, speech-01-hd/turbo |
| `MINIMAX_SPEECH_MODE` | `stream` | `stream` (SSE) or `normal` |
| `MINIMAX_SPEECH_VOICE_ID` | `male-qn-qingse` | Voice ID |
| `MINIMAX_SPEECH_SPEED` | `1.0` | Speech speed |
| `MINIMAX_SPEECH_VOL` | `1.0` | Volume |
| `MINIMAX_SPEECH_PITCH` | `0` | Pitch adjustment |
| `MINIMAX_SPEECH_EMOTION` | `happy` | Emotion preset |
| `MINIMAX_SPEECH_AUDIO_FORMAT` | `mp3` | Output format: `mp3`, `pcm`, `flac` |
| `MINIMAX_SPEECH_SAMPLE_RATE` | `32000` | Audio sample rate |
| `MINIMAX_SPEECH_BITRATE` | `128000` | Audio bitrate |
| `MINIMAX_SPEECH_CHANNEL` | `1` | Audio channels |

### Memory

| Variable | Default | Description |
|---|---|---|
| `MEMORY_ENABLED` | `true` | Enable conversation memory |
| `MEMORY_MAX_TURNS` | `10` | Recent turns to keep in context |
| `MEMORY_AUTO_EXTRACT` | `true` | Auto-extract long-term info each turn |
| `MEMORY_STORAGE_PATH` | `~/.jarvis/memory` | Persistence directory |

### Audio

| Variable | Default | Description |
|---|---|---|
| `SAMPLE_RATE` | `16000` | Mic sample rate |
| `CHANNELS` | `1` | Mic channels |
| `DEBUG_MODE` | `false` | Skip mic, use text input |
| `MAX_RETRIES` | `1` | HTTP retry count |

## Usage Scenarios

### A: MiniMax LLM + Qwen TTS (default)
```env
CONVERSATION_MODE=llm
SPEECH_PROVIDER=qwen
```

### B: MiniMax LLM + MiniMax Speech
```env
CONVERSATION_MODE=llm
SPEECH_PROVIDER=minimax
```

### C: Qwen3-TTS bypass (no LLM)
```env
CONVERSATION_MODE=tts
SPEECH_PROVIDER=qwen
```

All switching via `.env`, no code changes needed.

## Memory System

Jarvis has two layers of memory:

**Short-term memory** — Keeps the last N turns (configurable via `MEMORY_MAX_TURNS`) as conversation context. Lets Jarvis reference things said earlier in the session.

**Long-term memory (Summary)** — Extracts permanent user info (name, occupation, devices, projects, interests, preferences) via LLM extraction. Persisted to `~/.jarvis/memory/user_memory.json`. Survives restarts.

Example:
```
You: 我叫小梁，用 Mac Mini M4 开发 Jarvis
Jarvis: 你好小梁！Jarvis 项目听起来很有趣。

# Restart Jarvis
You: 我叫什么？
Jarvis: 你之前告诉过我，你叫小梁。
```

Disable with `MEMORY_ENABLED=false`.

## Project Structure

```
jarvis/
├── main.py              # CLI entry point
├── config.py             # Centralized config (pydantic-settings)
├── requirements.txt
├── .env                  # Secrets (gitignored)
├── .env.example          # Config template
│
├── audio/
│   ├── recorder.py       # MicrophoneRecorder (sounddevice → input.wav)
│   └── player.py         # AudioPlayer (macOS afplay, supports .wav/.mp3)
│
├── asr/
│   └── qwen_asr.py       # QwenASR (OMLX /v1/audio/transcriptions)
│
├── llm/
│   ├── base.py           # LLMProvider ABC + Message/ChatResponse
│   └── minimax.py        # MiniMaxProvider (OpenAI SDK)
│
├── speech/
│   ├── base.py           # SpeechProvider ABC + SpeechError
│   ├── factory.py        # create_speech_provider() factory
│   ├── qwen_tts_provider.py    # QwenSpeechProvider (wraps QwenTTS)
│   └── minimax_speech_provider.py  # MiniMaxSpeechProvider (T2A v2, SSE stream)
│
├── conversation/
│   ├── base.py           # ConversationProvider ABC + ConversationResult
│   ├── minimax_provider.py    # LLM mode: MiniMax → SpeechProvider
│   └── qwen_tts_provider.py   # TTS bypass: text → SpeechProvider
│
├── memory/
│   ├── models.py         # UserMemory, ConversationTurn dataclasses
│   ├── short_term.py     # ShortTermMemory (ring buffer)
│   ├── summary.py        # SummaryMemory (long-term, persisted)
│   ├── extractor.py      # MemoryExtractor (LLM-based info extraction)
│   ├── manager.py        # MemoryManager (orchestrates short + long)
│   ├── storage.py        # FileStorage (JSON persistence)
│   └── __init__.py
│
├── tts/
│   └── qwen_tts.py       # QwenTTS HTTP client (OMLX /v1/audio/speech)
│
└── core/
    ├── input_strategy.py # InputStrategy (Voice / Text)
    └── jarvis.py         # Pipeline orchestrator
```

## Architecture

```
User Input
    │
    ▼
InputStrategy (Voice → ASR, or Text)
    │
    ▼
ConversationProvider
    ├── Memory: build_context() → system_prompt
    ├── Memory: get_recent_messages() → message history
    ├── LLM → reply text
    ├── Memory: save_turn() + extract_and_update()
    └── SpeechProvider.synthesize(reply_text)
          │
          ▼
    AudioPlayer.play_file()
```

## Troubleshooting

**"Failed to access microphone"** — Grant terminal microphone access in System Preferences > Security & Privacy > Microphone, or use `DEBUG_MODE=true`.

**"MINIMAX_API_KEY is required"** — Copy `.env.example` to `.env` and set your API keys.

**TTS timeout on first request** — OMLX TTS model cold-loads on first use (10-30s). Subsequent requests are fast.

**"Playback failed: AudioFileOpen failed"** — For MiniMax Speech, ensure `MINIMAX_SPEECH_AUDIO_FORMAT=mp3` (not `wav`, which MiniMax doesn't support).

**Memory not loading** — Check `~/.jarvis/memory/user_memory.json` exists and is valid JSON. Delete it to reset.
