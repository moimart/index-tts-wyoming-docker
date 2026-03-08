"""Event handler for Wyoming IndexTTS server."""

import asyncio
import io
import logging
import math
import tempfile
import wave
from functools import partial
from pathlib import Path
from typing import Optional

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Describe, Info
from wyoming.server import AsyncEventHandler
from wyoming.tts import Synthesize

_LOGGER = logging.getLogger(__name__)

_TTS_MODEL = None
_TTS_LOCK = asyncio.Lock()


def get_tts_model(model_version: str, checkpoint_dir: str, use_fp16: bool):
    global _TTS_MODEL
    if _TTS_MODEL is not None:
        return _TTS_MODEL

    if model_version == "v2":
        from indextts.infer_v2 import IndexTTS2
        _TTS_MODEL = IndexTTS2(
            cfg_path=f"{checkpoint_dir}/config.yaml",
            model_dir=checkpoint_dir,
            use_fp16=use_fp16,
        )
    elif model_version == "v1.5":
        from indextts.infer import IndexTTS
        _TTS_MODEL = IndexTTS(
            cfg_path=f"{checkpoint_dir}/config.yaml",
            model_dir=checkpoint_dir,
            use_fp16=use_fp16,
        )
    else:
        from indextts.infer import IndexTTS
        _TTS_MODEL = IndexTTS(
            cfg_path=f"{checkpoint_dir}/config.yaml",
            model_dir=checkpoint_dir,
            use_fp16=use_fp16,
        )

    return _TTS_MODEL


class IndexTTSEventHandler(AsyncEventHandler):
    def __init__(
        self,
        wyoming_info: Info,
        voice_path: str,
        checkpoint_dir: str,
        model_version: str,
        use_fp16: bool,
        samples_per_chunk: int,
        generation_kwargs: dict,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.wyoming_info_event = wyoming_info.event()
        self.voice_path = voice_path
        self.checkpoint_dir = checkpoint_dir
        self.model_version = model_version
        self.use_fp16 = use_fp16
        self.samples_per_chunk = samples_per_chunk
        self.generation_kwargs = generation_kwargs

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(self.wyoming_info_event)
            _LOGGER.debug("Sent info")
            return True

        if not Synthesize.is_type(event.type):
            _LOGGER.debug("Unexpected event: %s", event.type)
            return True

        synthesize = Synthesize.from_event(event)
        _LOGGER.debug("Synthesize request: text='%s'", synthesize.text)

        raw_text = synthesize.text
        text = " ".join(raw_text.strip().splitlines())

        if not text:
            _LOGGER.warning("Empty text, skipping synthesis")
            return True

        loop = asyncio.get_running_loop()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp_wav:
            tmp_path = tmp_wav.name

        async with _TTS_LOCK:
            tts = get_tts_model(self.model_version, self.checkpoint_dir, self.use_fp16)
            await loop.run_in_executor(
                None,
                partial(
                    tts.infer,
                    spk_audio_prompt=self.voice_path,
                    text=text,
                    output_path=tmp_path,
                    **self.generation_kwargs,
                ),
            )

        wav_file: wave.Wave_read = wave.open(tmp_path, "rb")
        with wav_file:
            rate = wav_file.getframerate()
            width = wav_file.getsampwidth()
            channels = wav_file.getnchannels()

            await self.write_event(
                AudioStart(rate=rate, width=width, channels=channels).event()
            )

            audio_bytes = wav_file.readframes(wav_file.getnframes())
            bytes_per_sample = width * channels
            bytes_per_chunk = bytes_per_sample * self.samples_per_chunk
            num_chunks = int(math.ceil(len(audio_bytes) / bytes_per_chunk))

            for i in range(num_chunks):
                offset = i * bytes_per_chunk
                chunk = audio_bytes[offset : offset + bytes_per_chunk]
                await self.write_event(
                    AudioChunk(
                        audio=chunk, rate=rate, width=width, channels=channels
                    ).event()
                )

        await self.write_event(AudioStop().event())

        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)

        _LOGGER.info("Synthesized %d bytes of audio for: %s", len(audio_bytes), text[:50])
        return True
