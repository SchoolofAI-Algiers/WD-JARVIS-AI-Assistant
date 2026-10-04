"""Unit tests for the voice TTS"""
import asyncio
from pathlib import Path

import pytest

from app.voice.models import SpeechResult, TTSError, VoiceConfig, VoiceErrorCode, VoiceProfile
from app.voice.tts import (
    EdgeTTS,
    FallbackTTS,
    Pyttsx3TTS,
    TTSProvider,
    build_tts,
    detect_language,
    prepare_spoken_text,
    sniff_audio_mime,
)

PROFILE = VoiceProfile()


def run(coro):
    return asyncio.run(coro)


# prepare_spoken_text 
def test_plain_text_is_unchanged():
    assert prepare_spoken_text("The demo is on Friday.") == ("The demo is on Friday.", False)


def test_empty_text():
    assert prepare_spoken_text("   ") == ("", False)


def test_markdown_is_stripped_for_speech():
    text = "## Summary\n**Three** projects:\n- Voice\n- RAG\n- *Memory*\nSee [the docs](https://example.com/x) now."
    spoken, truncated = prepare_spoken_text(text)
    assert spoken == "Summary. Three projects: Voice. RAG. Memory. See the docs now."
    assert truncated is False


def test_urls_inline_code_and_emoji_are_removed():
    spoken, _ = prepare_spoken_text("Run `pip install pydantic` 🚀 then visit https://example.com today")
    assert spoken == "Run pip install pydantic then visit today"


def test_code_blocks_are_replaced_by_a_spoken_note():
    spoken, _ = prepare_spoken_text("Here you go:\n```python\nprint('hi')\n```\nEnjoy.")
    assert "print" not in spoken
    assert spoken.endswith("The code is on your screen.")


def test_code_only_reply_keeps_nothing_to_say():
    assert prepare_spoken_text("```python\nprint('hi')\n```") == ("", False)


def test_markdown_table_rows_become_sentences():
    spoken, _ = prepare_spoken_text("| Tool | Use |\n|---|---|\n| Calculator | Maths |")
    assert spoken == "Tool, Use. Calculator, Maths."


def test_snake_case_and_math_survive():
    spoken, _ = prepare_spoken_text("Set my_var_name to 15*20 please.")
    assert spoken == "Set my_var_name to 15*20 please."


def test_long_text_is_cut_at_a_sentence_boundary():
    text = "First sentence is here. Second sentence follows. Third sentence is quite a bit longer than the others."
    spoken, truncated = prepare_spoken_text(text, max_chars=50)
    assert truncated is True
    assert spoken == "First sentence is here. Second sentence follows. The full answer is on your screen."


def test_single_very_long_sentence_is_cut_at_a_word():
    spoken, truncated = prepare_spoken_text("word " * 100, max_chars=40)
    assert truncated is True
    assert spoken.startswith("word word") and "\u2026" in spoken
    assert spoken.endswith("The full answer is on your screen.")


def test_truncation_note_follows_the_reply_language():
    spoken, _ = prepare_spoken_text("Une phrase. " * 30, max_chars=30, language="fr")
    assert spoken.endswith("La réponse complète est affichée à l'écran.")


# detect_language / voices 
def test_arabic_text_selects_arabic():
    assert detect_language("مرحبا، كيف حالك اليوم؟", hint="en") == "ar"


def test_latin_text_follows_the_stt_hint():
    assert detect_language("Bonjour, quelle heure est-il ?", hint="fr") == "fr"
    assert detect_language("What time is it?", hint="en-GB") == "en"


def test_unsupported_or_arabic_hint_on_latin_text_falls_back_to_default():
    assert detect_language("Hello there", hint="de") == "en"
    assert detect_language("Hello there", hint="ar") == "en"  # English text must not get an Arabic voice
    assert detect_language("Hello there") == "en"


def test_voice_profile_maps_languages_with_fallback():
    assert PROFILE.voice_for("fr-FR") == PROFILE.voices["fr"]
    assert PROFILE.voice_for("AR") == PROFILE.voices["ar"]
    assert PROFILE.voice_for("xx") == PROFILE.voices["en"]
    assert PROFILE.voice_for(None) == PROFILE.voices["en"]


def test_sniff_audio_mime():
    assert sniff_audio_mime(b"RIFF\x00\x00\x00\x00WAVEfmt ") == "audio/wav"
    assert sniff_audio_mime(b"FORM\x00\x00\x00\x00AIFF") == "audio/aiff"
    assert sniff_audio_mime(b"ID3\x04\x00") == "audio/mpeg"
    assert sniff_audio_mime(b"\xff\xfb\x90\x00") == "audio/mpeg"
    assert sniff_audio_mime(b"OggS\x00") == "audio/ogg"
    assert sniff_audio_mime(b"????") == "application/octet-stream"


# EdgeTTS
class FakeCommunicate:
    def __init__(self, chunks=None, error=None):
        self.chunks, self.error = chunks, error

    async def stream(self):
        for chunk in self.chunks or []:
            yield chunk
        if self.error:
            raise self.error


def edge(chunks=None, error=None, record=None):
    def factory(text, voice, **kwargs):
        if record is not None:
            record.update(text=text, voice=voice, **kwargs)
        return FakeCommunicate(chunks, error)

    return EdgeTTS(communicate_factory=factory)


def test_edge_concatenates_audio_chunks_only():
    record = {}
    provider = edge(
        [{"type": "audio", "data": b"AB"}, {"type": "WordBoundary", "offset": 1}, {"type": "audio", "data": b"CD"}],
        record=record,
    )
    result = run(provider.synthesize("Good evening.", language="en", profile=PROFILE))
    assert isinstance(result, SpeechResult)
    assert result.audio == b"ABCD" and result.mime_type == "audio/mpeg"
    assert result.provider == "edge-tts" and result.spoken_text == "Good evening."
    # the J.A.R.V.I.S. voice identity is applied
    assert record["voice"] == PROFILE.voices["en"]
    assert (record["rate"], record["pitch"], record["volume"]) == (PROFILE.rate, PROFILE.pitch, PROFILE.volume)


def test_edge_picks_voice_from_language():
    record = {}
    run(edge([{"type": "audio", "data": b"x"}], record=record).synthesize("Bonjour", language="fr", profile=PROFILE))
    assert record["voice"] == PROFILE.voices["fr"]


def test_edge_network_failure_becomes_tts_unavailable():
    provider = edge(error=ConnectionError("getaddrinfo failed"))
    with pytest.raises(TTSError) as exc:
        run(provider.synthesize("Hello", language="en", profile=PROFILE))
    assert exc.value.code == VoiceErrorCode.TTS_UNAVAILABLE
    assert "ConnectionError" in exc.value.detail


def test_edge_empty_audio_is_an_error():
    with pytest.raises(TTSError) as exc:
        run(edge([{"type": "WordBoundary"}]).synthesize("Hello", language="en", profile=PROFILE))
    assert exc.value.code == VoiceErrorCode.TTS_UNAVAILABLE


def test_edge_is_available_reflects_installed_package(monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)
    assert EdgeTTS().is_available() is False
    assert edge().is_available() is True


# Pyttsx3TTS
class FakeEngine:
    def __init__(self, payload=b"RIFF\x00\x00\x00\x00WAVEdata", fail=False):
        self.payload, self.fail, self.props, self.path = payload, fail, {}, None

    def setProperty(self, key, value):
        self.props[key] = value

    def save_to_file(self, text, path):
        self.path = path
        Path(path).write_bytes(self.payload)

    def runAndWait(self):
        if self.fail:
            raise RuntimeError("driver crashed")


def test_pyttsx3_returns_wav_and_cleans_up_temp_file():
    engine = FakeEngine()
    result = run(Pyttsx3TTS(engine_factory=lambda: engine).synthesize("Hi", language="en", profile=PROFILE))
    assert result.audio.startswith(b"RIFF") and result.mime_type == "audio/wav"
    assert engine.props["rate"] == PROFILE.offline_rate_wpm
    assert not Path(engine.path).exists()


def test_pyttsx3_driver_failure_and_empty_output():
    with pytest.raises(TTSError):
        run(Pyttsx3TTS(engine_factory=lambda: FakeEngine(fail=True)).synthesize("Hi", language="en", profile=PROFILE))
    with pytest.raises(TTSError):
        run(Pyttsx3TTS(engine_factory=lambda: FakeEngine(payload=b"")).synthesize("Hi", language="en", profile=PROFILE))


# FallbackTTS 
class StubTTS(TTSProvider):
    def __init__(self, name, audio=b"ok", error=None, delay=0.0):
        self.name, self.audio, self.error, self.delay, self.calls = name, audio, error, delay, 0

    async def synthesize(self, text, *, language, profile):
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return SpeechResult(audio=self.audio, mime_type="audio/mpeg", provider=self.name, spoken_text=text)


def boom():
    return TTSError(VoiceErrorCode.TTS_UNAVAILABLE, "offline")


def test_fallback_uses_second_provider_when_first_fails():
    primary, backup = StubTTS("edge", error=boom()), StubTTS("offline", audio=b"wav")
    result = run(FallbackTTS([primary, backup]).synthesize("Hi", language="en", profile=PROFILE))
    assert result.provider == "offline" and result.audio == b"wav"


def test_fallback_times_out_a_hanging_provider():
    primary, backup = StubTTS("edge", delay=1.0), StubTTS("offline")
    chain = FallbackTTS([primary, backup], per_provider_timeout_s=0.05)
    assert run(chain.synthesize("Hi", language="en", profile=PROFILE)).provider == "offline"


def test_fallback_skips_a_recently_failed_provider_then_retries_after_cooldown():
    now = [0.0]
    primary, backup = StubTTS("edge", error=boom()), StubTTS("offline")
    chain = FallbackTTS([primary, backup], cooldown_s=30, clock=lambda: now[0])
    run(chain.synthesize("one", language="en", profile=PROFILE))
    run(chain.synthesize("two", language="en", profile=PROFILE))
    assert primary.calls == 1  # second request went straight to the backup
    now[0] = 31
    primary.error = None
    assert run(chain.synthesize("three", language="en", profile=PROFILE)).provider == "edge"
    assert primary.calls == 2


def test_fallback_raises_when_every_provider_fails():
    chain = FallbackTTS([StubTTS("a", error=boom()), StubTTS("b", error=RuntimeError("driver"))])
    with pytest.raises(TTSError) as exc:
        run(chain.synthesize("Hi", language="en", profile=PROFILE))
    assert exc.value.code == VoiceErrorCode.TTS_UNAVAILABLE
    assert "a: offline" in exc.value.detail and "b: RuntimeError" in exc.value.detail


def test_fallback_never_skips_the_last_provider():
    now = [0.0]
    only = StubTTS("only", error=boom())
    chain = FallbackTTS([StubTTS("edge", error=boom()), only], cooldown_s=30, clock=lambda: now[0])
    for _ in range(2):
        with pytest.raises(TTSError):
            run(chain.synthesize("Hi", language="en", profile=PROFILE))
    assert only.calls == 2


# build_tts
def test_build_tts_default_chain_and_single_provider():
    assert build_tts(VoiceConfig()).name == "fallback(edge-tts>pyttsx3)"
    assert build_tts(VoiceConfig(tts_providers=["pyttsx3"])).name == "pyttsx3"


def test_build_tts_rejects_unknown_provider():
    with pytest.raises(ValueError):
        build_tts(VoiceConfig(tts_providers=["nope"]))
