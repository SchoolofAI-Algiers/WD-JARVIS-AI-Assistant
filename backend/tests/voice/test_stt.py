"""Unit tests for the voice STT"""
from types import SimpleNamespace

import pytest

from app.voice.models import STTError, TranscriptionResult, VoiceErrorCode
from app.voice.stt import (
    FallbackSTT,
    FasterWhisperSTT,
    STTProvider,
    segment_confidence,
    summarize_segments,
    validate_audio,
)

AUDIO = b"x" * 5_000


def seg(text, avg_logprob=-0.2, no_speech_prob=0.01, start=0.0, end=1.0):
    return SimpleNamespace(text=text, avg_logprob=avg_logprob, no_speech_prob=no_speech_prob, start=start, end=end)


class FakeModel:
    def __init__(self, segments=(), language="en", raises=None):
        self.segments, self.language, self.raises = list(segments), language, raises
        self.calls = []

    def transcribe(self, audio, **kwargs):
        self.calls.append(kwargs)
        if self.raises:
            raise self.raises
        info = SimpleNamespace(language=self.language, duration=2.5)
        return iter(self.segments), info


def make_stt(model=None, **kwargs):
    model = model or FakeModel([seg("hello jarvis")])
    return FasterWhisperSTT(model_factory=lambda: model, **kwargs), model


# validate_audio
def test_validate_audio_accepts_normal_recording():
    validate_audio(AUDIO, min_bytes=1_000, max_bytes=10_000)


@pytest.mark.parametrize("audio", [b"", None, b"tiny"])
def test_validate_audio_rejects_empty_or_accidental_tap(audio):
    with pytest.raises(STTError) as exc:
        validate_audio(audio, min_bytes=1_000, max_bytes=10_000)
    assert exc.value.code == VoiceErrorCode.EMPTY_AUDIO


def test_validate_audio_rejects_oversized_recording():
    with pytest.raises(STTError) as exc:
        validate_audio(b"x" * 20_000, min_bytes=1_000, max_bytes=10_000)
    assert exc.value.code == VoiceErrorCode.AUDIO_TOO_LARGE


# confidence / segment handling
def test_segment_confidence_is_bounded():
    assert segment_confidence(0.0) == 1.0
    assert segment_confidence(0.5) == 1.0  # clipped
    assert 0.0 < segment_confidence(-1.0) < 0.4
    assert segment_confidence(-50.0) == pytest.approx(0.0, abs=1e-9)


def test_summarize_joins_text_and_weights_confidence_by_duration():
    segments = [seg("what time", avg_logprob=0.0, start=0, end=1), seg("is it", avg_logprob=-1.0, start=1, end=4)]
    text, confidence = summarize_segments(segments, no_speech_threshold=0.6)
    assert text == "what time is it"
    # (1*1.0 + 3*exp(-1)) / 4
    assert confidence == pytest.approx((1.0 + 3 * 0.36788) / 4, abs=1e-3)


def test_summarize_drops_non_speech_but_keeps_quiet_real_speech():
    noise = seg("thanks for watching", avg_logprob=-1.4, no_speech_prob=0.9)
    quiet_speech = seg("open the report", avg_logprob=-0.3, no_speech_prob=0.9)  # unsure it is speech, sure of words
    text, _ = summarize_segments([noise, quiet_speech], no_speech_threshold=0.6)
    assert text == "open the report"


def test_summarize_with_no_segments():
    assert summarize_segments([], 0.6) == ("", None)


# FasterWhisperSTT 
def test_transcribe_returns_text_language_and_confidence():
    stt, model = make_stt(FakeModel([seg("What is SOAI?", avg_logprob=-0.1)], language="en"))
    result = stt.transcribe(AUDIO, "audio/webm")
    assert isinstance(result, TranscriptionResult)
    assert result.text == "What is SOAI?"
    assert result.language == "en"
    assert result.provider == "faster-whisper"
    assert result.duration_s == 2.5
    assert result.confidence == pytest.approx(0.905, abs=1e-3)
    assert model.calls[0]["vad_filter"] is True


def test_language_argument_overrides_default_language():
    stt, model = make_stt(language="fr")
    stt.transcribe(AUDIO)
    stt.transcribe(AUDIO, language="ar")
    assert [c["language"] for c in model.calls] == ["fr", "ar"]


def test_silence_gives_empty_text_not_an_exception():
    stt, _ = make_stt(FakeModel([]))
    result = stt.transcribe(AUDIO)
    assert result.text == "" and result.confidence is None


def test_model_loads_once_and_is_reused():
    loads = []
    model = FakeModel([seg("hi")])
    stt = FasterWhisperSTT(model_factory=lambda: loads.append(1) or model)
    stt.transcribe(AUDIO)
    stt.transcribe(AUDIO)
    stt.warmup()
    assert loads == [1]


def test_corrupt_audio_is_reported_as_unreadable():
    class DecodeError(Exception):
        pass

    DecodeError.__module__ = "av.error"  # PyAV raises its own exception types
    stt, _ = make_stt(FakeModel(raises=DecodeError("Invalid data found")))
    with pytest.raises(STTError) as exc:
        stt.transcribe(AUDIO)
    assert exc.value.code == VoiceErrorCode.AUDIO_UNREADABLE


def test_engine_crash_is_reported_as_service_unavailable():
    stt, _ = make_stt(FakeModel(raises=RuntimeError("CUDA out of memory")))
    with pytest.raises(STTError) as exc:
        stt.transcribe(AUDIO)
    assert exc.value.code == VoiceErrorCode.STT_UNAVAILABLE


def test_missing_package_is_permanent_until_restart():
    attempts = []

    def factory():
        attempts.append(1)
        raise ImportError("No module named 'faster_whisper'")

    stt = FasterWhisperSTT(model_factory=factory)
    for _ in range(3):
        with pytest.raises(STTError) as exc:
            stt.transcribe(AUDIO)
        assert exc.value.code == VoiceErrorCode.STT_UNAVAILABLE
    assert len(attempts) == 1
    assert stt.is_available() is False


def test_failed_model_load_is_retried_only_after_cooldown():
    now = [0.0]
    attempts = []

    def factory():
        attempts.append(1)
        if len(attempts) == 1:
            raise OSError("cannot download model (offline)")
        return FakeModel([seg("back online")])

    stt = FasterWhisperSTT(model_factory=factory, retry_after_s=60, clock=lambda: now[0])
    assert stt.health() == {"available": True, "ready": False, "status": "not_loaded"}
    with pytest.raises(STTError):
        stt.transcribe(AUDIO)  # 1st attempt fails
    assert stt.health() == {"available": True, "ready": False, "status": "load_failed"}
    now[0] = 10
    with pytest.raises(STTError):
        stt.transcribe(AUDIO)  # still cooling down: no new attempt
    assert len(attempts) == 1
    now[0] = 61
    assert stt.transcribe(AUDIO).text == "back online"
    assert len(attempts) == 2
    assert stt.health() == {"available": True, "ready": True, "status": "ready"}


def test_is_available_checks_package_without_loading(monkeypatch):
    stt = FasterWhisperSTT()
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)
    assert stt.is_available() is False
    monkeypatch.setattr("importlib.util.find_spec", lambda name: object())
    assert stt.is_available() is True


# FallbackSTT 
class StubSTT(STTProvider):
    def __init__(self, name, result=None, error=None, available=True):
        self.name, self._result, self._error, self._available = name, result, error, available
        self.calls = 0

    def transcribe(self, audio, mime_type="audio/webm", language=None):
        self.calls += 1
        if self._error:
            raise self._error
        return self._result

    def is_available(self):
        return self._available


OK = TranscriptionResult(text="from backup", provider="backup")


def test_fallback_uses_next_provider_when_first_is_unavailable():
    primary = StubSTT("primary", error=STTError(VoiceErrorCode.STT_UNAVAILABLE, "down"))
    backup = StubSTT("backup", result=OK)
    chain = FallbackSTT([primary, backup])
    assert chain.transcribe(AUDIO).text == "from backup"
    assert (primary.calls, backup.calls) == (1, 1)
    assert chain.name == "fallback(primary>backup)"


def test_fallback_does_not_retry_bad_audio_on_other_providers():
    primary = StubSTT("primary", error=STTError(VoiceErrorCode.AUDIO_UNREADABLE, "corrupt"))
    backup = StubSTT("backup", result=OK)
    with pytest.raises(STTError) as exc:
        FallbackSTT([primary, backup]).transcribe(AUDIO)
    assert exc.value.code == VoiceErrorCode.AUDIO_UNREADABLE
    assert backup.calls == 0


def test_fallback_raises_unavailable_when_everything_fails():
    a = StubSTT("a", error=STTError(VoiceErrorCode.STT_UNAVAILABLE, "a down"))
    b = StubSTT("b", error=STTError(VoiceErrorCode.STT_TIMEOUT, "b slow"))
    with pytest.raises(STTError) as exc:
        FallbackSTT([a, b]).transcribe(AUDIO)
    assert exc.value.code == VoiceErrorCode.STT_UNAVAILABLE
    assert "b slow" in exc.value.detail


def test_fallback_availability_and_warmup_never_raise():
    class Boom(StubSTT):
        def warmup(self):
            raise RuntimeError("no model")

    chain = FallbackSTT([Boom("a", available=False), StubSTT("b", result=OK)])
    assert chain.is_available() is True
    chain.warmup()  # must swallow the failure
    assert FallbackSTT([StubSTT("a", available=False)]).is_available() is False


def test_fallback_requires_a_provider():
    with pytest.raises(ValueError):
        FallbackSTT([])
