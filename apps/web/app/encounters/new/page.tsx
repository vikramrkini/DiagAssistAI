"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import type { DecisionSupportOutput, Encounter, Patient, StructuredIntake } from "@diagassist/shared";
import { apiFetch } from "@/lib/api";

const emptyIntake: StructuredIntake = {
  chief_complaint: "",
  hpi: {},
  relevant_negatives: [],
  timeline: "",
  symptoms: []
};

export default function NewEncounterPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [patientId, setPatientId] = useState<number | null>(null);
  const [specialty, setSpecialty] = useState("general");
  const [transcript, setTranscript] = useState("");
  const [intake, setIntake] = useState<StructuredIntake>(emptyIntake);
  const [decision, setDecision] = useState<DecisionSupportOutput | null>(null);
  const [encounter, setEncounter] = useState<Encounter | null>(null);
  const [diagnosis, setDiagnosis] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isAutoProcessing, setIsAutoProcessing] = useState(false);
  const [meterLevel, setMeterLevel] = useState(0);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [message, setMessage] = useState("");
  const [toast, setToast] = useState<{ type: "error" | "success"; text: string } | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const meterFrameRef = useRef<number | null>(null);
  const timerRef = useRef<number | null>(null);
  const recordStartedAtRef = useRef<number>(0);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);

  function formatDuration(seconds: number): string {
    const minutes = Math.floor(seconds / 60)
      .toString()
      .padStart(2, "0");
    const rest = (seconds % 60).toString().padStart(2, "0");
    return `${minutes}:${rest}`;
  }

  function stopMetering() {
    if (meterFrameRef.current !== null) {
      cancelAnimationFrame(meterFrameRef.current);
      meterFrameRef.current = null;
    }
    if (audioContextRef.current) {
      void audioContextRef.current.close();
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    setMeterLevel(0);
  }

  function stopTimer() {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  function stopStreamTracks() {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  }

  useEffect(() => {
    return () => {
      stopMetering();
      stopTimer();
      stopStreamTracks();
    };
  }, []);

  useEffect(() => {
    apiFetch<Patient[]>("/patients")
      .then((rows) => {
        setPatients(rows);
        if (rows.length > 0) setPatientId(rows[0].id);
      })
      .catch((e) => handleError(e));
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => setToast(null), 4800);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  function toFriendlyErrorMessage(err: unknown): string {
    const raw = err instanceof Error ? err.message : "Unable to complete this action.";
    try {
      const parsed = JSON.parse(raw) as {
        detail?: string | Array<{ msg?: string; type?: string; loc?: Array<string | number> } | string>;
      };
      if (typeof parsed.detail === "string") return parsed.detail;
      if (Array.isArray(parsed.detail)) {
        const shortTranscript = parsed.detail.find((item) => {
          if (typeof item === "string") return false;
          if (!item) return false;
          const loc = Array.isArray(item.loc) ? item.loc.map(String) : [];
          return item.type === "string_too_short" && loc.includes("transcript");
        });
        if (shortTranscript) {
          return "Please record a longer statement so we can generate a useful transcript.";
        }
        const joined = parsed.detail
          .map((item) => (typeof item === "string" ? item : item.msg || ""))
          .filter(Boolean)
          .join(" | ");
        if (joined) return joined;
      }
      return raw;
    } catch {
      return raw;
    }
  }

  function handleError(err: unknown) {
    const friendly = toFriendlyErrorMessage(err);
    setMessage(friendly);
    setToast({ type: "error", text: friendly });
  }

  async function transcribeRecordedAudio(recordedFile: File): Promise<string> {
    if (recordedFile.size === 0) {
      throw new Error("Recorded audio is empty. Please record again.");
    }
    const fd = new FormData();
    fd.append("audio", recordedFile);
    const token = localStorage.getItem("diagassist_token");
    const resp = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/transcribe`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      body: fd
    });
    if (!resp.ok) {
      const raw = await resp.text();
      let detail = raw || `Request failed (${resp.status})`;
      try {
        const parsed = JSON.parse(raw) as { detail?: string | Array<{ msg?: string } | string> };
        if (typeof parsed.detail === "string") {
          detail = parsed.detail;
        } else if (Array.isArray(parsed.detail)) {
          const joined = parsed.detail
            .map((item) => (typeof item === "string" ? item : item.msg || ""))
            .filter(Boolean)
            .join(" | ");
          if (joined) detail = joined;
        }
      } catch {
        // Keep raw text fallback.
      }
      throw new Error(detail);
    }
    const data = (await resp.json()) as { transcript: string };
    return data.transcript;
  }

  async function startRecording() {
    if (isAutoProcessing) return;
    try {
      setDecision(null);
      setEncounter(null);
      setIntake(emptyIntake);
      setTranscript("");
      setMessage("Recording in progress...");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const preferredType = "audio/webm;codecs=opus";
      const recorder = MediaRecorder.isTypeSupported(preferredType)
        ? new MediaRecorder(stream, { mimeType: preferredType })
        : new MediaRecorder(stream);
      chunksRef.current = [];

      const audioContext = new AudioContext();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);
      analyser.fftSize = 128;
      source.connect(analyser);
      audioContextRef.current = audioContext;
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const animateMeter = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        const overallAverage = dataArray.reduce((sum, value) => sum + value, 0) / Math.max(1, dataArray.length);
        const nextLevel = Math.min(1, overallAverage / 255);
        setMeterLevel((previous) => previous * 0.6 + nextLevel * 0.4);
        meterFrameRef.current = requestAnimationFrame(animateMeter);
      };
      meterFrameRef.current = requestAnimationFrame(animateMeter);

      setRecordSeconds(0);
      recordStartedAtRef.current = Date.now();
      timerRef.current = window.setInterval(() => {
        const elapsed = Math.floor((Date.now() - recordStartedAtRef.current) / 1000);
        setRecordSeconds(elapsed);
      }, 250);

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = async () => {
        const mimeType = recorder.mimeType || "audio/webm";
        const extension = mimeType.includes("wav")
          ? "wav"
          : mimeType.includes("mp3") || mimeType.includes("mpeg")
            ? "mp3"
            : mimeType.includes("ogg") || mimeType.includes("oga")
              ? "ogg"
              : "webm";
        const blob = new Blob(chunksRef.current, { type: mimeType });

        if (blob.size === 0) {
          setMessage("Recording was empty. Please record again.");
          setToast({ type: "error", text: "Recording was empty. Please record again." });
        } else {
          const file = new File([blob], `encounter-${Date.now()}.${extension}`, { type: mimeType });
          stopMetering();
          stopTimer();
          stopStreamTracks();
          await runAutoPipeline(file);
          return;
        }

        stopMetering();
        stopTimer();
        stopStreamTracks();
      };

      recorder.start();
      recorderRef.current = recorder;
      setIsRecording(true);
    } catch (e) {
      handleError(e);
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
    recorderRef.current = null;
    setIsRecording(false);
  }

  async function runExtract(transcriptText: string) {
    const data = await apiFetch<StructuredIntake>("/extract-intake", {
      method: "POST",
      body: JSON.stringify({ transcript: transcriptText, specialty })
    });
    setIntake(data);
    return data;
  }

  async function runDecisionSupport(transcriptText: string, structuredIntake: StructuredIntake) {
    const data = await apiFetch<DecisionSupportOutput>("/decision-support", {
      method: "POST",
      body: JSON.stringify({
        transcript: transcriptText,
        structured_intake: structuredIntake,
        specialty,
        encounter_id: encounter?.id ?? null
      })
    });
    setDecision(data);
    return data;
  }

  async function runAutoPipeline(recordedFile: File) {
    setIsAutoProcessing(true);
    try {
      setMessage("Generating transcript...");
      const nextTranscript = await transcribeRecordedAudio(recordedFile);
      if (nextTranscript.trim().length < 5) {
        throw new Error("Please record a longer statement so we can generate a useful transcript.");
      }
      setTranscript(nextTranscript);

      setMessage("Extracting structured intake from transcript...");
      const nextIntake = await runExtract(nextTranscript);

      setMessage("Generating decision support...");
      await runDecisionSupport(nextTranscript, nextIntake);
      setMessage("Decision support generated automatically.");
      setToast({ type: "success", text: "Decision support generated." });
    } catch (e) {
      handleError(e);
    } finally {
      setIsAutoProcessing(false);
    }
  }

  async function saveEncounter(e: FormEvent) {
    e.preventDefault();
    if (!patientId) {
      setMessage("Choose a patient first.");
      return;
    }
    try {
      const data = await apiFetch<Encounter>("/encounters", {
        method: "POST",
        body: JSON.stringify({ patient_id: patientId, transcript_text: transcript, structured_intake_json: intake })
      });
      setEncounter(data);
      setMessage(`Encounter #${data.id} saved.`);
      setToast({ type: "success", text: `Encounter #${data.id} saved.` });
    } catch (e) {
      handleError(e);
    }
  }

  async function confirmDiagnosis() {
    if (!encounter) {
      setMessage("Save encounter before confirming final diagnosis.");
      return;
    }
    try {
      const data = await apiFetch<Encounter>(`/encounters/${encounter.id}/confirm-diagnosis`, {
        method: "POST",
        body: JSON.stringify({ final_diagnosis_text: diagnosis })
      });
      setEncounter(data);
      setMessage("Final diagnosis confirmed and saved.");
      setToast({ type: "success", text: "Final diagnosis confirmed and saved." });
    } catch (e) {
      handleError(e);
    }
  }

  return (
    <div className="app-page">
      {toast && (
        <div className={`app-toast app-toast--${toast.type}`} role="alert" aria-live="assertive">
          <span>{toast.text}</span>
          <button type="button" className="app-toast__close" onClick={() => setToast(null)} aria-label="Dismiss alert">
            Dismiss
          </button>
        </div>
      )}
      <div className="card">
        <h2>Encounter workspace</h2>
        <p>Record an encounter and the system will auto-generate transcript, structured intake, and decision support.</p>
        <form onSubmit={saveEncounter} className="app-stack">
          <label>
            Patient
            <select value={patientId ?? ""} onChange={(e) => setPatientId(Number(e.target.value))}>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </label>

          <label>
            Specialty context
            <select value={specialty} onChange={(e) => setSpecialty(e.target.value)}>
              <option value="general">General</option>
              <option value="pediatrics">Pediatrics</option>
              <option value="physiotherapy">Physiotherapy</option>
              <option value="dermatology">Dermatology</option>
            </select>
          </label>

          <div className="encounter-recorder">
            <button
              type="button"
              className={isRecording ? "mic-button mic-button--recording" : "mic-button"}
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isAutoProcessing}
              aria-label={isRecording ? "Stop recording" : "Start recording"}
            >
              <span className="mic-button__fill" style={{ height: `${Math.max(8, meterLevel * 100)}%` }} aria-hidden="true" />
              <svg className="mic-button__icon" viewBox="0 0 24 24" aria-hidden="true">
                <path
                  d="M12 15a3 3 0 0 0 3-3V7a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Zm5-3a1 1 0 1 1 2 0 7 7 0 0 1-6 6.93V21h2a1 1 0 1 1 0 2H9a1 1 0 1 1 0-2h2v-2.07A7 7 0 0 1 5 12a1 1 0 1 1 2 0 5 5 0 1 0 10 0Z"
                  fill="currentColor"
                />
              </svg>
            </button>
            <p className="recording-label">
              {isAutoProcessing
                ? "Processing recording..."
                : isRecording
                  ? "Tap to stop recording"
                  : "Tap the microphone to start recording"}
            </p>
            <p className="recording-time">{formatDuration(recordSeconds)}</p>
          </div>

          <label>
            Transcript
            <textarea rows={6} value={transcript} onChange={(e) => setTranscript(e.target.value)} />
          </label>

          <div className="app-row">
            <button type="submit" disabled={isAutoProcessing || !transcript}>Save encounter</button>
          </div>
        </form>
        <p>{message}</p>
      </div>

      <div className="card">
        <h3>Decision support</h3>
        {!decision && <p>No output yet.</p>}
        {decision && (
          <div className="app-stack">
            <div><strong>Confidence:</strong> {decision.confidence.toFixed(2)}</div>
            <div><strong>Needs human review:</strong> {String(decision.needs_human_review)}</div>
            <div><strong>Uncertainty:</strong> {decision.uncertainty_notes}</div>

            <section>
              <h4>Differential</h4>
              <ul>
                {decision.differential.map((d, idx) => (
                  <li key={idx}>{d.name} ({d.likelihood_bucket}) - citations: {d.citations.join(", ") || "none"}</li>
                ))}
              </ul>
            </section>

            <section>
              <h4>Red flags</h4>
              <ul>
                {decision.red_flags.map((r, idx) => (
                  <li key={idx}>{r.flag} - {r.action}</li>
                ))}
              </ul>
            </section>

            <section>
              <h4>Follow-up questions</h4>
              <ul>
                {decision.followups.map((f, idx) => (
                  <li key={idx}>{f.question}</li>
                ))}
              </ul>
            </section>

            <section>
              <h4>Suggested tests</h4>
              <ul>
                {decision.tests.map((t, idx) => (
                  <li key={idx}>{t.test}</li>
                ))}
              </ul>
            </section>
          </div>
        )}
      </div>

      <div className="card">
        <h3>Confirm final diagnosis</h3>
        <input value={diagnosis} onChange={(e) => setDiagnosis(e.target.value)} placeholder="Clinician-confirmed final diagnosis" />
        <div className="app-mt-sm">
          <button onClick={confirmDiagnosis}>Confirm final diagnosis</button>
        </div>
        {encounter && <p>Encounter ID: {encounter.id}. Final diagnosis: {encounter.final_diagnosis_text || "pending"}</p>}
      </div>
    </div>
  );
}
