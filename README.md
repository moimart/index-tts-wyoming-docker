# Wyoming IndexTTS - Voice Cloning TTS for Home Assistant

A Docker service implementing the [Wyoming protocol](https://github.com/OHF-voice/wyoming) for Home Assistant, powered by [IndexTTS-2](https://github.com/index-tts/index-tts) zero-shot voice cloning.

Drop any number of voice WAV clips into a directory and they each become a selectable voice in Home Assistant's TTS dropdown.

## Project Structure

```
tts-experiment/
├── Dockerfile
├── docker-compose.yml
├── voices/                      # Drop your .wav files here
│   ├── morgan.wav               # Each file = a selectable voice
│   └── sarah.wav
├── scripts/
│   └── run.sh                   # Container entrypoint
└── wyoming_indextts/
    ├── __init__.py
    ├── __main__.py              # Wyoming server setup
    └── handler.py               # TTS synthesis handler
```

## How It Works

- Implements the **Wyoming protocol** (TCP on port 10300) so Home Assistant discovers it as a TTS provider
- Uses **IndexTTS-2** for zero-shot voice cloning — give it any reference WAV and it synthesizes speech in that voice
- All `.wav` files in the voices directory are automatically registered as selectable voices
- The TTS model is preloaded at startup so the first request is fast (no cold start)
- Model checkpoints are auto-downloaded from HuggingFace on first run and persisted in a Docker volume

## Quick Start

1. **Add your voice files** to the `voices/` directory (any short WAV clips of voices you want to clone):
   ```
   voices/
   ├── morgan.wav
   └── sarah.wav
   ```

2. **Build and run:**
   ```bash
   docker compose up -d
   ```

3. **Add to Home Assistant** via Settings > Devices & Services > Add Integration > Wyoming Protocol, entering your host IP and port `10300`

4. **Select a voice** in Settings > Voice Assistants > pick your pipeline > TTS voice dropdown

## Configuration

All configuration is done via environment variables in `docker-compose.yml`:

| Variable | Default | Description |
|---|---|---|
| `VOICES_DIR` | `/app/voices` | Directory containing reference voice WAV files |
| `DEFAULT_VOICE` | *(first found)* | Default voice name (filename without `.wav`) |
| `MODEL_VERSION` | `v2` | IndexTTS version: `v1`, `v1.5`, or `v2` |
| `FP16` | `true` | Use FP16 inference (less VRAM) |
| `TOP_P` | `0.8` | Nucleus sampling top-p |
| `TOP_K` | `30` | Top-k sampling |
| `TEMPERATURE` | `0.8` | Sampling temperature |
| `NUM_BEAMS` | `3` | Beam search width |
| `REPETITION_PENALTY` | `10.0` | Repetition penalty |
| `MAX_MEL_TOKENS` | `1500` | Max mel tokens per segment |
| `DEBUG` | `false` | Verbose logging |

### Adding or Changing Voices

Drop new `.wav` files into `voices/` and restart:

```bash
docker compose restart
```

The filename (without `.wav`) becomes the voice name in Home Assistant. For example, `voices/morgan.wav` appears as "morgan" in the voice dropdown.

To set a specific default voice:

```yaml
environment:
  - DEFAULT_VOICE=morgan
```

## Requirements

- NVIDIA GPU with CUDA 12.8+ support
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed
