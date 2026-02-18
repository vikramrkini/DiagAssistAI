"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
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
  const defaultMeterBars = [10, 12, 14, 11, 9, 13, 15, 12, 10, 13, 11, 9];
  const [patients, setPatients] = useState<Patient[]>([]);
  const [patientId, setPatientId] = useState<number | null>(null);
  const [specialty, setSpecialty] = useState("general");
  const [transcript, setTranscript] = useState("");
  const [intake, setIntake] = useState<StructuredIntake>(emptyIntake);
  const [decision, setDecision] = useState<DecisionSupportOutput | null>(null);
  const [encounter, setEncounter] = useState<Encounter | null>(null);
  const [diagnosis, setDiagnosis] = useState("");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [meterBars, setMeterBars] = useState(defaultMeterBars);
  const [meterLevel, setMeterLevel] = useState(0);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [message, setMessage] = useState("");
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
    setMeterBars(defaultMeterBars);
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
      .catch((e) => setMessage((e as Error).message));
  }, []);

  const intakeJson = useMemo(() => JSON.stringify(intake, null, 2), [intake]);

  async function runTranscribe() {
    try {
      if (audioFile && audioFile.size === 0) {
        setMessage("Selected audio file is empty. Please record again.");
        return;
      }
      const fd = new FormData();
      if (audioFile) fd.append("audio", audioFile);
      if (!audioFile) fd.append("text_override", transcript);
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
      const data = (await resp.json()) as { transcript: string; mode: string };
      setTranscript(data.transcript);
      setMessage(`Transcript ready (${data.mode}).`);
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  async function startRecording() {
    try {
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
      const barCount = defaultMeterBars.length;
      const animateMeter = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        const overallAverage = dataArray.reduce((sum, value) => sum + value, 0) / Math.max(1, dataArray.length);
        const nextBars = Array.from({ length: barCount }, (_, idx) => {
          const start = Math.floor((idx * dataArray.length) / barCount);
          const end = Math.floor(((idx + 1) * dataArray.length) / barCount);
          let total = 0;
          for (let i = start; i < end; i++) total += dataArray[i];
          const average = total / Math.max(1, end - start);
          return 8 + Math.round((average / 255) * 34);
        });
        setMeterBars(nextBars);
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
      recorder.onstop = () => {
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
          setAudioFile(null);
          setMessage("Recording was empty. Please record again.");
        } else {
          const file = new File([blob], `encounter-${Date.now()}.${extension}`, { type: mimeType });
          setAudioFile(file);
          setMessage("Audio recording captured. You can now run Transcribe.");
        }

        stopMetering();
        stopTimer();
        stopStreamTracks();
      };

      recorder.start();
      recorderRef.current = recorder;
      setIsRecording(true);
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
    recorderRef.current = null;
    setIsRecording(false);
  }

  async function runExtract() {
    try {
      const data = await apiFetch<StructuredIntake>("/extract-intake", {
        method: "POST",
        body: JSON.stringify({ transcript, specialty })
      });
      setIntake(data);
      setMessage("Structured intake extracted.");
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  async function runDecisionSupport() {
    try {
      const data = await apiFetch<DecisionSupportOutput>("/decision-support", {
        method: "POST",
        body: JSON.stringify({ transcript, structured_intake: intake, specialty, encounter_id: encounter?.id ?? null })
      });
      setDecision(data);
      setMessage("Decision support generated.");
    } catch (e) {
      setMessage((e as Error).message);
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
    } catch (e) {
      setMessage((e as Error).message);
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
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  return (
    <div style={{ display: "grid", gap: "1rem" }}>
      <div className="card">
        <h2>Encounter workspace</h2>
        <p>Needs human review is always true for decision-support outputs.</p>
        <form onSubmit={saveEncounter} style={{ display: "grid", gap: "0.7rem" }}>
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

          <label>
            Audio input (optional)
            <input type="file" accept="audio/*" onChange={(e) => setAudioFile(e.target.files?.[0] ?? null)} />
          </label>
          <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
            {!isRecording ? (
              <button type="button" className="secondary" onClick={startRecording}>Start recording</button>
            ) : (
              <button type="button" className="secondary" onClick={stopRecording}>Stop recording</button>
            )}
            <span style={{ color: "#4c6674" }}>{audioFile ? `Selected audio: ${audioFile.name}` : "No audio selected"}</span>
          </div>
          {isRecording && (
            <div
              className="recording-visualizer"
              style={{ ["--meter-level" as string]: meterLevel.toFixed(3) }}
              aria-live="polite"
            >
              <div className="recording-orb-stack" aria-hidden="true">
                <span className="recording-ripple recording-ripple--one" />
                <span className="recording-ripple recording-ripple--two" />
                <span className="recording-ripple recording-ripple--three" />
                <div className="recording-orb">
                  <span className="recording-orb__core" />
                </div>
              </div>
              <div className="recording-bars-wrap">
                <div className="recording-bars" aria-hidden="true">
                  {meterBars.map((value, idx) => (
                    <span key={idx} style={{ height: `${value}px`, animationDelay: `${idx * 26}ms` }} />
                  ))}
                </div>
                <div className="recording-meta">
                  <p className="recording-label">Listening...</p>
                  <p className="recording-time">{formatDuration(recordSeconds)}</p>
                </div>
              </div>
              <p className="recording-hint">Speak naturally. Tap stop when done.</p>
            </div>
          )}
          {!isRecording && audioFile && (
            <div className="recording-visualizer recording-visualizer--idle" aria-live="polite">
              <div className="recording-orb recording-orb--idle" aria-hidden="true">
                <span className="recording-orb__core" />
              </div>
              <div className="recording-bars recording-bars--idle" aria-hidden="true">
                {meterBars.map((value, idx) => (
                  <span key={idx} style={{ height: `${Math.max(8, value - 2)}px` }} />
                ))}
              </div>
              <p className="recording-label">Ready to transcribe</p>
            </div>
          )}

          <label>
            Transcript (or provide text override)
            <textarea rows={6} value={transcript} onChange={(e) => setTranscript(e.target.value)} />
          </label>

          <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
            <button type="button" className="secondary" onClick={runTranscribe}>Transcribe</button>
            <button type="button" className="secondary" onClick={runExtract}>Extract intake</button>
            <button type="button" className="secondary" onClick={runDecisionSupport}>Generate decision support</button>
            <button type="submit">Save encounter</button>
          </div>
        </form>
        <p>{message}</p>
      </div>

      <div className="card">
        <h3>Structured intake (editable JSON)</h3>
        <textarea
          rows={14}
          value={intakeJson}
          onChange={(e) => {
            try {
              setIntake(JSON.parse(e.target.value));
            } catch {
              setMessage("Intake JSON is invalid.");
            }
          }}
        />
      </div>

      <div className="card">
        <h3>Decision support</h3>
        {!decision && <p>No output yet.</p>}
        {decision && (
          <div style={{ display: "grid", gap: "0.8rem" }}>
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
        <div style={{ marginTop: "0.6rem" }}>
          <button onClick={confirmDiagnosis}>Confirm final diagnosis</button>
        </div>
        {encounter && <p>Encounter ID: {encounter.id}. Final diagnosis: {encounter.final_diagnosis_text || "pending"}</p>}
      </div>
    </div>
  );
}
