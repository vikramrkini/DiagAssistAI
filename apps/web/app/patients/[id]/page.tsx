"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { Encounter, Patient } from "@diagassist/shared";
import { apiFetch } from "@/lib/api";

export default function PatientDetailPage({ params }: { params: { id: string } }) {
  const id = Number(params.id);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([
      apiFetch<Patient>(`/patients/${id}`),
      apiFetch<Encounter[]>(`/patients/${id}/encounters`)
    ])
      .then(([p, e]) => {
        setPatient(p);
        setEncounters(e);
      })
      .catch((e) => setErr((e as Error).message));
  }, [id]);

  if (err) return <div className="card">{err}</div>;
  if (!patient) return <div className="card">Loading...</div>;

  return (
    <div style={{ display: "grid", gap: "1rem" }}>
      <div className="card">
        <h2>{patient.name}</h2>
        <p>DOB: {patient.dob || "Not set"}</p>
        <p>Sex: {patient.sex || "Not set"}</p>
        <Link href="/encounters/new">Create encounter</Link>
      </div>

      <div className="card">
        <h3>Encounter history</h3>
        {encounters.length === 0 && <p>No encounters yet.</p>}
        <ul style={{ display: "grid", gap: "0.8rem", paddingLeft: "1rem" }}>
          {encounters.map((enc) => (
            <li key={enc.id}>
              <Link href={`/encounters/${enc.id}`}>Encounter #{enc.id}</Link>
              <div><strong>Transcript:</strong> {enc.transcript_text}</div>
              <div><strong>Final diagnosis:</strong> {enc.final_diagnosis_text || "Pending clinician confirmation"}</div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
