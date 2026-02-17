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
  const [message, setMessage] = useState("");
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);

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
      const fd = new FormData();
      if (audioFile) fd.append("audio", audioFile);
      if (!audioFile) fd.append("text_override", transcript);
      const token = localStorage.getItem("diagassist_token");
      const resp = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/transcribe`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        body: fd
      });
      if (!resp.ok) throw new Error(await resp.text());
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
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const file = new File([blob], `encounter-${Date.now()}.webm`, { type: "audio/webm" });
        setAudioFile(file);
        setMessage("Audio recording captured. You can now run Transcribe.");
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

          <label>
            Transcript (paste text in demo mode)
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
