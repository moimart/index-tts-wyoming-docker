# Wyoming IndexTTS - Voice Cloning TTS for Home Assistant

A Docker service implementing the [Wyoming protocol](https://github.com/OHF-voice/wyoming) for Home Assistant, powered by [IndexTTS-2](https://github.com/index-tts/index-tts) zero-shot voice cloning.

Give it any short WAV clip of a voice, and it will synthesize speech in that voice for your Home Assistant TTS pipeline.

## Project Structure

```
tts-experiment/
├── Dockerfile
├── docker-compose.yml
├── voices/                      # Mount your reference voice WAV here
│   └── reference.wav            # (auto-downloaded if missing)
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
- Model checkpoints are auto-downloaded from HuggingFace on first run and persisted in a Docker volume

## Quick Start

1. **Place your reference voice** in `voices/reference.wav` (any short WAV clip of the voice you want to clone)

2. **Build and run:**
   ```bash
   docker compose up -d
   ```

3. **Add to Home Assistant** via Settings > Devices & Services > Add Integration > Wyoming Protocol, entering your host IP and port `10300`

## Configuration

All configuration is done via environment variables in `docker-compose.yml`:

| Variable | Default | Description |
|---|---|---|
| `VOICE_FILE` | `/app/voices/reference.wav` | Path to reference voice WAV inside container |
| `MODEL_VERSION` | `v2` | IndexTTS version: `v1`, `v1.5`, or `v2` |
| `FP16` | `true` | Use FP16 inference (less VRAM) |
| `DEBUG` | `false` | Verbose logging |

### Changing the Clone Voice

Drop a new WAV file in `voices/` and update `VOICE_FILE` in `docker-compose.yml`:

```yaml
environment:
  - VOICE_FILE=/app/voices/myvoice.wav
```

Then restart:

```bash
docker compose restart
```

## Requirements

- NVIDIA GPU with CUDA 12.8+ support
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed
- If no reference voice is provided, a sample from the LJ Speech dataset is downloaded automatically
