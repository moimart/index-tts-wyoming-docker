#!/usr/bin/env python3
"""Wyoming server for IndexTTS voice cloning TTS."""

import argparse
import asyncio
import logging
import signal
from functools import partial
from pathlib import Path

from wyoming.info import Attribution, Info, TtsProgram, TtsVoice
from wyoming.server import AsyncServer, AsyncTcpServer

from . import __version__
from .handler import IndexTTSEventHandler

_LOGGER = logging.getLogger(__name__)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Wyoming IndexTTS Server")
    parser.add_argument(
        "--voice",
        required=True,
        help="Path to reference voice WAV file for cloning",
    )
    parser.add_argument(
        "--checkpoint-dir",
        default="/app/checkpoints",
        help="Path to IndexTTS model checkpoints directory",
    )
    parser.add_argument(
        "--model-version",
        default="v2",
        choices=["v1", "v1.5", "v2"],
        help="IndexTTS model version to use (default: v2)",
    )
    parser.add_argument(
        "--uri",
        default="tcp://0.0.0.0:10300",
        help="Server URI (default: tcp://0.0.0.0:10300)",
    )
    parser.add_argument(
        "--fp16",
        action="store_true",
        help="Use FP16 inference for reduced VRAM usage",
    )
    parser.add_argument("--samples-per-chunk", type=int, default=4096)
    # Generation quality parameters
    parser.add_argument("--top-p", type=float, default=0.8, help="Nucleus sampling top-p (default: 0.8)")
    parser.add_argument("--top-k", type=int, default=30, help="Top-k sampling (default: 30)")
    parser.add_argument("--temperature", type=float, default=0.8, help="Sampling temperature (default: 0.8)")
    parser.add_argument("--num-beams", type=int, default=3, help="Beam search beams (default: 3)")
    parser.add_argument("--repetition-penalty", type=float, default=10.0, help="Repetition penalty (default: 10.0)")
    parser.add_argument("--max-mel-tokens", type=int, default=1500, help="Max mel tokens per segment (default: 1500)")
    parser.add_argument("--debug", action="store_true", help="Log DEBUG messages")
    parser.add_argument(
        "--version", action="version", version=__version__, help="Print version"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    voice_path = Path(args.voice)
    if not voice_path.exists():
        _LOGGER.error("Voice file not found: %s", args.voice)
        raise FileNotFoundError(f"Voice file not found: {args.voice}")

    _LOGGER.info("Using voice file: %s", args.voice)
    _LOGGER.info("Using checkpoint dir: %s", args.checkpoint_dir)
    _LOGGER.info("Model version: %s", args.model_version)

    wyoming_info = Info(
        tts=[
            TtsProgram(
                name="indextts",
                description="IndexTTS zero-shot voice cloning TTS",
                attribution=Attribution(
                    name="IndexTeam",
                    url="https://github.com/index-tts/index-tts",
                ),
                installed=True,
                voices=[
                    TtsVoice(
                        name=voice_path.stem,
                        description=f"Cloned voice from {voice_path.name}",
                        attribution=Attribution(
                            name="custom",
                            url="",
                        ),
                        installed=True,
                        version=__version__,
                        languages=["en", "zh"],
                    )
                ],
                version=__version__,
            )
        ],
    )

    generation_kwargs = {
        "top_p": args.top_p,
        "top_k": args.top_k,
        "temperature": args.temperature,
        "num_beams": args.num_beams,
        "repetition_penalty": args.repetition_penalty,
        "max_mel_tokens": args.max_mel_tokens,
    }
    _LOGGER.info("Generation params: %s", generation_kwargs)

    # Preload model at startup to eliminate cold-start on first request
    from .handler import get_tts_model
    _LOGGER.info("Loading TTS model (this may take a while)...")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        partial(get_tts_model, args.model_version, args.checkpoint_dir, args.fp16),
    )
    _LOGGER.info("TTS model loaded")

    server = AsyncServer.from_uri(args.uri)
    _LOGGER.info("Ready")

    server_task = asyncio.create_task(
        server.run(
            partial(
                IndexTTSEventHandler,
                wyoming_info,
                args.voice,
                args.checkpoint_dir,
                args.model_version,
                args.fp16,
                args.samples_per_chunk,
                generation_kwargs,
            )
        )
    )

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, server_task.cancel)
    loop.add_signal_handler(signal.SIGTERM, server_task.cancel)

    try:
        await server_task
    except asyncio.CancelledError:
        _LOGGER.info("Server stopped")


def run():
    asyncio.run(main())


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        pass
