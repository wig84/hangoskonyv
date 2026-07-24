"""Hang-szintű segédfüggvények: csend generálása és `AudioSegment`-ek
összefűzése.

Ezekre a `ssml.fallback` szegmentálás eredményének hanggá
"összeépítéséhez" van szükség: minden `SpeechSegment`-hez tartozik
egy önállóan szintetizált `AudioSegment`, amik közé a megfelelő
hosszúságú digitális csendet kell beszúrni, majd az egészet egyetlen,
fejezetnyi `AudioSegment`-té összefűzni.
"""

from __future__ import annotations

import io
import wave

from hangoskonyv.core.exceptions import HangoskonyvError
from hangoskonyv.tts.base import AudioSegment


def generate_silence(
    duration_ms: int, *, sample_rate: int, sample_width: int = 2, channels: int = 1
) -> AudioSegment:
    """A megadott hosszúságú, csendes (nulla amplitúdójú) `AudioSegment`-et
    hoz létre, a megadott hangparaméterekkel."""
    frame_count = int(sample_rate * duration_ms / 1000)
    pcm_data = b"\x00" * (frame_count * sample_width * channels)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)

    return AudioSegment(
        audio_bytes=buffer.getvalue(),
        sample_rate=sample_rate,
        sample_width=sample_width,
        channels=channels,
    )


def concatenate_audio_segments(segments: list[AudioSegment]) -> AudioSegment:
    """Több `AudioSegment`-et egyetlen, folytonos hanggá fűz össze.

    Raises:
        HangoskonyvError: Ha a lista üres, vagy a szegmensek hang-
            paraméterei (mintavételi ráta, mélység, csatornaszám)
            nem egyeznek.
    """
    if not segments:
        raise HangoskonyvError("Nincs mit összefűzni: üres szegmens-lista.")

    first = segments[0]
    for segment in segments[1:]:
        if (
            segment.sample_rate != first.sample_rate
            or segment.sample_width != first.sample_width
            or segment.channels != first.channels
        ):
            raise HangoskonyvError(
                "Az összefűzendő hangrészletek formátuma nem egyezik "
                f"(pl. {first.sample_rate}Hz vs {segment.sample_rate}Hz)."
            )

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output_wav:
        output_wav.setnchannels(first.channels)
        output_wav.setsampwidth(first.sample_width)
        output_wav.setframerate(first.sample_rate)
        for segment in segments:
            with wave.open(io.BytesIO(segment.audio_bytes), "rb") as input_wav:
                output_wav.writeframes(input_wav.readframes(input_wav.getnframes()))

    return AudioSegment(
        audio_bytes=buffer.getvalue(),
        sample_rate=first.sample_rate,
        sample_width=first.sample_width,
        channels=first.channels,
    )
