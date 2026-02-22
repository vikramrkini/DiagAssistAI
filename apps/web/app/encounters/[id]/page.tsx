"use client";

import { useEffect, useState } from "react";
import type { Encounter } from "@diagassist/shared";
import { apiFetch } from "@/lib/api";

interface EvidenceItem {
  chunk_id: number;
  title: string;
  source: string;
  specialty_tags: string[];
  chunk_text: string;
}

interface AuditLogItem {
  id: number;
  actor_clinician_id: number | null;
  action: string;
  before_json: Record<string, unknown> | null;
  after_json: Record<string, unknown> | null;
  created_at: string;
}

export default function EncounterDetailPage({ params }: { params: { id: string } }) {
  const id = Number(params.id);
  const [encounter, setEncounter] = useState<Encounter | null>(null);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [audit, setAudit] = useState<AuditLogItem[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([
      apiFetch<Encounter>(`/encounters/${id}`),
      apiFetch<{ evidence: EvidenceItem[] }>(`/encounters/${id}/evidence`),
      apiFetch<{ audit_logs: AuditLogItem[] }>(`/encounters/${id}/audit`)
    ])
      .then(([enc, ev, aud]) => {
        setEncounter(enc);
        setEvidence(ev.evidence);
        setAudit(aud.audit_logs);
      })
      .catch((e) => setErr((e as Error).message));
  }, [id]);

  if (err) return <div className="card">{err}</div>;
  if (!encounter) return <div className="card">Loading...</div>;

  return (
    <div className="app-page">
      <div className="card">
        <h2>Encounter #{encounter.id}</h2>
        <p><strong>Transcript:</strong> {encounter.transcript_text}</p>
        <p><strong>Final diagnosis:</strong> {encounter.final_diagnosis_text || "Pending clinician confirmation"}</p>
      </div>
      <div className="card">
        <h3>Evidence</h3>
        {evidence.length === 0 && <p>No evidence captured yet.</p>}
        <ul className="app-list">
          {evidence.map((item) => (
            <li key={item.chunk_id}>
              <strong>Chunk #{item.chunk_id}</strong> {item.title} ({item.source})
              <div className="app-muted">Tags: {item.specialty_tags.join(", ")}</div>
              <div>{item.chunk_text}</div>
            </li>
          ))}
        </ul>
      </div>
      <div className="card">
        <h3>Audit</h3>
        {audit.length === 0 && <p>No audit events captured yet.</p>}
        <ul className="app-list">
          {audit.map((item) => (
            <li key={item.id}>
              <strong>{item.action}</strong> ({new Date(item.created_at).toLocaleString()})
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
