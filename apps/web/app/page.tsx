"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { Patient } from "@diagassist/shared";
import { apiFetch, getToken, subscribeToAuthChanges } from "@/lib/api";

type MeResponse = {
  id: number;
  email: string;
  name: string;
  specialty: string;
};

const queueItems = [
  { title: "Pending confirmations", value: "06", note: "Diagnoses awaiting clinician sign-off." },
  { title: "High-priority red flags", value: "02", note: "Escalations surfaced in last 24h." },
  { title: "Documentation drift", value: "01", note: "Encounter missing final rationale." }
];

const timelineItems = [
  { time: "09:24", label: "Intake extraction completed for pediatric visit.", state: "success" },
  { time: "10:02", label: "Decision support generated with 4 citations.", state: "neutral" },
  { time: "10:31", label: "Red-flag action prompt acknowledged.", state: "warning" }
] as const;

export default function HomePage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [clinicianName, setClinicianName] = useState("Clinician");
  const [specialty, setSpecialty] = useState("General");
  const [patientCount, setPatientCount] = useState<number | null>(null);

  useEffect(() => {
    const syncAuthState = () => setIsAuthenticated(Boolean(getToken()));
    syncAuthState();
    return subscribeToAuthChanges(syncAuthState);
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      setPatientCount(null);
      return;
    }

    apiFetch<MeResponse>("/auth/me")
      .then((me) => {
        setClinicianName(me.name);
        setSpecialty(me.specialty);
      })
      .catch(() => undefined);

    apiFetch<Patient[]>("/patients")
      .then((patients) => setPatientCount(patients.length))
      .catch(() => setPatientCount(null));
  }, [isAuthenticated]);

  const heroSubtitle = useMemo(
    () =>
      isAuthenticated
        ? `Live workspace tuned for ${specialty.toLowerCase()} workflows.`
        : "Move from intake transcript to evidence-backed differential with transparent auditability.",
    [isAuthenticated, specialty]
  );

  if (!isAuthenticated) {
    return (
      <section className="hero card fade-up">
        <div className="hero__content">
          <p className="eyebrow">Clinical Decision Support</p>
          <h1>Production-ready intake intelligence for modern care teams.</h1>
          <p>{heroSubtitle}</p>
          <div className="hero__actions">
            <Link href="/auth/signin" className="button">
              Sign in
            </Link>
            <Link href="/auth/signup" className="button button--ghost">
              Create account
            </Link>
          </div>
        </div>
        <div className="hero__metrics">
          <div className="metric-card">
            <strong>94%</strong>
            <span>Structured intake completeness across eval fixtures</span>
          </div>
          <div className="metric-card">
            <strong>&lt; 3s</strong>
            <span>Median decision-support generation latency</span>
          </div>
          <div className="metric-card">
            <strong>100%</strong>
            <span>Synthetic-data-only training and evaluation flow</span>
          </div>
        </div>
      </section>
    );
  }

  return (
    <div className="dashboard">
      <section className="dashboard-hero card fade-up">
        <div>
          <p className="eyebrow">Operations Dashboard</p>
          <h1>Welcome back, {clinicianName}.</h1>
          <p>{heroSubtitle}</p>
          <div className="hero__actions">
            <Link href="/encounters/new" className="button">
              Start New Encounter
            </Link>
            <Link href="/patients" className="button button--ghost">
              Review Patients
            </Link>
          </div>
        </div>
        <div className="dashboard-hero__stats">
          <div className="stat-tile">
            <span>Active Patients</span>
            <strong>{patientCount === null ? "--" : patientCount}</strong>
          </div>
          <div className="stat-tile">
            <span>Clinical Specialty</span>
            <strong>{specialty}</strong>
          </div>
          <div className="stat-tile">
            <span>Human Review Mode</span>
            <strong>Enabled</strong>
          </div>
        </div>
      </section>

      <section className="dashboard-grid">
        <article className="card fade-up" style={{ animationDelay: "120ms" }}>
          <h2>Priority Queue</h2>
          <ul className="queue-list">
            {queueItems.map((item) => (
              <li key={item.title}>
                <div>
                  <p>{item.title}</p>
                  <span>{item.note}</span>
                </div>
                <strong>{item.value}</strong>
              </li>
            ))}
          </ul>
        </article>

        <article className="card fade-up" style={{ animationDelay: "200ms" }}>
          <h2>System Timeline</h2>
          <ul className="timeline-list">
            {timelineItems.map((item) => (
              <li key={`${item.time}-${item.label}`}>
                <span className={`timeline-dot timeline-dot--${item.state}`} />
                <div>
                  <p>{item.label}</p>
                  <span>{item.time}</span>
                </div>
              </li>
            ))}
          </ul>
        </article>
      </section>
    </div>
  );
}
