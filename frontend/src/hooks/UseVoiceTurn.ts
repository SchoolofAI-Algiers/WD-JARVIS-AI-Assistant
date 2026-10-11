import { useCallback, useEffect, useRef, useState } from "react";

import type { AssistantStatusType } from "../components/status/AssistantStatus";
import {
  sendVoiceTurn,
  speakText,
  type SpeechResult,
  type VoiceTurnResponse,
} from "../services/api/voice";

interface Options {
  /** The conversation shared with text chat. Read at the moment recording stops. */
  conversationId: string;
  onStatus: (status: AssistantStatusType) => void;
  /** A voice turn reached the backend and came back (ok or friendly failure). */
  onTurn: (result: VoiceTurnResponse) => void;
  /** The turn could not happen at all (microphone, network, server error). */
  onProblem: (message: string) => void;
}

const PREFERRED_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/ogg;codecs=opus",
  "audio/mp4",
];

function pickMimeType(): string | undefined {
  return PREFERRED_TYPES.find((type) => MediaRecorder.isTypeSupported(type));
}

/** "interrupted" = stopped on purpose (new recording, new message, new conversation). */
type PlaybackOutcome = "ended" | "failed" | "interrupted";

interface Playback {
  audio: HTMLAudioElement;
  finish: (outcome: PlaybackOutcome) => void;
}

export function useVoiceTurn({
  conversationId,
  onStatus,
  onTurn,
  onProblem,
}: Options) {
  const [listening, setListening] = useState(false);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const playbackRef = useRef<Playback | null>(null);
  const busyRef = useRef(false);

  // Always the id of the conversation currently on screen, so a reply that
  // arrives after "New conversation" is dropped instead of leaking into it.
  const conversationIdRef = useRef(conversationId);
  useEffect(() => {
    conversationIdRef.current = conversationId;
  }, [conversationId]);

  // Keep the latest callbacks without re-creating the handlers below.
  const callbacksRef = useRef({ onStatus, onTurn, onProblem });
  useEffect(() => {
    callbacksRef.current = { onStatus, onTurn, onProblem };
  }, [onStatus, onTurn, onProblem]);

  const releaseMicrophone = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    recorderRef.current = null;
  }, []);

  const stopPlayback = useCallback(() => {
    const playback = playbackRef.current;
    if (!playback) return;
    playback.audio.pause();
    playback.finish("interrupted");
  }, []);

  const play = useCallback(
    (speech: SpeechResult) =>
      new Promise<PlaybackOutcome>((resolve) => {
        const audio = new Audio(
          `data:${speech.mime_type};base64,${speech.audio}`
        );
        const finish = (outcome: PlaybackOutcome) => {
          if (playbackRef.current?.audio === audio) {
            playbackRef.current = null;
          }
          resolve(outcome);
        };
        playbackRef.current = { audio, finish };
        audio.onended = () => finish("ended");
        audio.onerror = () => finish("failed");
        // Autoplay can be refused by the browser; the text reply is still shown.
        audio.play().catch(() => finish("failed"));
      }),
    []
  );

  const submit = useCallback(
    async (recording: Blob) => {
      const sentFor = conversationIdRef.current;
      busyRef.current = true;
      callbacksRef.current.onStatus("thinking");

      try {
        const result = await sendVoiceTurn(recording, sentFor);

        if (sentFor !== conversationIdRef.current) {
          return; // the user started a new conversation meanwhile
        }

        callbacksRef.current.onTurn(result);

        let outcome: PlaybackOutcome = "ended";
        if (result.speech) {
          callbacksRef.current.onStatus("speaking");
          outcome = await play(result.speech);
        }
        if (outcome !== "interrupted" && sentFor === conversationIdRef.current) {
          callbacksRef.current.onStatus("idle");
        }
      } catch (error) {
        console.error(error);
        if (sentFor === conversationIdRef.current) {
          callbacksRef.current.onStatus("error");
          callbacksRef.current.onProblem(
            "I couldn't reach my voice service. Please try again, or type your request."
          );
        }
      } finally {
        busyRef.current = false;
      }
    },
    [play]
  );

  const start = useCallback(async () => {
    if (
      !navigator.mediaDevices?.getUserMedia ||
      typeof MediaRecorder === "undefined"
    ) {
      callbacksRef.current.onStatus("error");
      callbacksRef.current.onProblem(
        "Voice input isn't supported by this browser. Please type your request."
      );
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = pickMimeType();
      const recorder = new MediaRecorder(
        stream,
        mimeType ? { mimeType } : undefined
      );
      const chunks: Blob[] = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.push(event.data);
      };
      recorder.onstop = () => {
        const cancelled = recorderRef.current !== recorder;
        releaseMicrophone();
        if (cancelled) return;
        void submit(new Blob(chunks, { type: recorder.mimeType || mimeType }));
      };

      streamRef.current = stream;
      recorderRef.current = recorder;
      recorder.start();
      setListening(true);
      callbacksRef.current.onStatus("listening");
    } catch (error) {
      console.error(error);
      releaseMicrophone();
      callbacksRef.current.onStatus("error");
      callbacksRef.current.onProblem(
        "I can't access the microphone. Check the browser permission, or type your request."
      );
    }
  }, [releaseMicrophone, submit]);

  /** Push-to-talk: first click starts recording, second click sends it. */
  const toggle = useCallback(async () => {
    if (listening) {
      setListening(false);
      recorderRef.current?.stop();
      return;
    }
    if (busyRef.current) return; // a turn is already being processed
    stopPlayback(); // speaking over J.A.R.V.I.S. interrupts it
    await start();
  }, [listening, start, stopPlayback]);

  /**
   * Speak the reply to a TYPED message. Failures are silent: the text reply is already on screen.
   * Does nothing while a recording or a voice turn is in progress.
   */
  const speak = useCallback(
    async (text: string, language?: string) => {
      if (busyRef.current || recorderRef.current) return;

      const sentFor = conversationIdRef.current;
      try {
        const result = await speakText(text, sentFor, language);
        if (!result.speech && result.error) {
          console.warn("Spoken reply unavailable:", result.error.code);
        }
        if (
          !result.speech ||
          sentFor !== conversationIdRef.current ||
          busyRef.current ||
          recorderRef.current
        ) {
          return;
        }
        stopPlayback(); // never let two replies talk over each other
        callbacksRef.current.onStatus("speaking");
        const outcome = await play(result.speech);
        if (outcome !== "interrupted" && sentFor === conversationIdRef.current) {
          callbacksRef.current.onStatus("idle");
        }
      } catch (error) {
        console.error(error);
      }
    },
    [play, stopPlayback]
  );

  /** Drop any recording or playback without sending (e.g. new conversation). */
  const cancel = useCallback(() => {
    const recorder = recorderRef.current;
    recorderRef.current = null; // marks the pending onstop as cancelled
    if (recorder && recorder.state !== "inactive") recorder.stop();
    releaseMicrophone();
    setListening(false);
    stopPlayback();
  }, [releaseMicrophone, stopPlayback]);

  useEffect(() => cancel, [cancel]);

  return { listening, toggle, cancel, stopPlayback, speak };
}