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

const storyModules = [
  {
    title: "Structured Intake That Starts Clean",
    summary:
      "Turn long intake conversations into clear, chart-ready summaries so clinicians begin each case with the right context and fewer manual rewrites.",
    image: "https://images.pexels.com/photos/4226769/pexels-photo-4226769.jpeg?auto=compress&cs=tinysrgb&w=1800",
    alt: "Clinician reviewing structured digital patient intake on a laptop"
  },
  {
    title: "Evidence-Linked Differential Support",
    summary:
      "Get ranked differentials with traceable rationale and practical follow-up prompts, helping teams move faster while keeping decisions transparent.",
    image: "https://images.pexels.com/photos/7088524/pexels-photo-7088524.jpeg?auto=compress&cs=tinysrgb&w=1800",
    alt: "Healthcare team discussing clinical findings on screens",
    reverse: true
  },
  {
    title: "Action Plans Built For Real Workflows",
    summary:
      "Draft concise plans, next-step checks, and patient-facing guidance in a consistent format that is fast to verify and easy to communicate.",
    image: "https://images.pexels.com/photos/1170979/pexels-photo-1170979.jpeg?auto=compress&cs=tinysrgb&w=1800",
    alt: "Doctor explaining treatment plan to a patient"
  }
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
        : "Move from intake transcript to evidence-backed differential with clear clinical traceability.",
    [isAuthenticated, specialty]
  );

  if (!isAuthenticated) {
    return (
      <div className="marketing-page marketing-page--home fade-up">
        <div className="marketing-page__overlay marketing-page__overlay--one" aria-hidden />
        <div className="marketing-page__overlay marketing-page__overlay--two" aria-hidden />

        <section className="marketing-hero marketing-hero--home">
          <div className="marketing-hero__copy">
            <p className="eyebrow">Clinical Decision Intelligence</p>
            <h1>Production-ready workflow support for modern care teams.</h1>
            <p>{heroSubtitle}</p>
          </div>
        </section>

        <section className="marketing-section fade-up" style={{ animationDelay: "120ms" }}>
          <div className="marketing-section__head">
            <p className="eyebrow">How It Works</p>
            <h2>One workflow, three high-impact modules.</h2>
          </div>
          <div className="marketing-story-list">
            {storyModules.map((module, index) => (
              <article
                key={module.title}
                className={module.reverse ? "marketing-story marketing-story--reverse stagger-card" : "marketing-story stagger-card"}
                style={{ animationDelay: `${150 + index * 80}ms` }}
              >
                <div className="marketing-story__card">
                  <h3>{module.title}</h3>
                  <p>{module.summary}</p>
                  <div className="hero__actions">
                    <Link href="/about" className="button button--ghost">
                      Learn More
                    </Link>
                  </div>
                </div>
                <div className="marketing-story__media">
                  <img src={module.image} alt={module.alt} loading={index === 0 ? "eager" : "lazy"} />
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="app-page dashboard">
      <section className="dashboard-hero card dashboard-hero--modern fade-up">
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
        <article className="card dashboard-panel dashboard-panel--queue fade-up" style={{ animationDelay: "120ms" }}>
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

        <article className="card dashboard-panel dashboard-panel--timeline fade-up" style={{ animationDelay: "200ms" }}>
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
