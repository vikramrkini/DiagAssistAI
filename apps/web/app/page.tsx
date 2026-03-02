"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { DashboardSummary } from "@diagassist/shared";
import { apiFetch, getToken, subscribeToAuthChanges } from "@/lib/api";

type MeResponse = {
  id: number;
  email: string;
  name: string;
  specialty: string;
};

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
  const [dashboardData, setDashboardData] = useState<DashboardSummary | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  useEffect(() => {
    const syncAuthState = () => setIsAuthenticated(Boolean(getToken()));
    syncAuthState();
    return subscribeToAuthChanges(syncAuthState);
  }, []);

  function toFriendlyErrorMessage(err: unknown): string {
    const raw = err instanceof Error ? err.message : "Unable to load dashboard data.";
    try {
      const parsed = JSON.parse(raw) as { detail?: string | Array<{ msg?: string } | string> | { msg?: string } };
      if (typeof parsed.detail === "string") return parsed.detail;
      if (Array.isArray(parsed.detail)) {
        const joined = parsed.detail
          .map((item) => (typeof item === "string" ? item : item.msg || ""))
          .filter(Boolean)
          .join(" | ");
        if (joined) return joined;
      }
      if (parsed.detail && typeof parsed.detail === "object" && "msg" in parsed.detail) {
        return parsed.detail.msg || raw;
      }
    } catch {
      return raw;
    }
    return raw;
  }

  const loadDashboard = useCallback(
    async (opts?: { silent?: boolean }) => {
      if (!isAuthenticated) return;
      const silent = opts?.silent ?? false;
      if (!silent) setDashboardLoading(true);
      setDashboardError(null);
      try {
        const data = await apiFetch<DashboardSummary>("/dashboard/summary");
        setDashboardData(data);
      } catch (err) {
        setDashboardError(toFriendlyErrorMessage(err));
      } finally {
        if (!silent) setDashboardLoading(false);
      }
    },
    [isAuthenticated]
  );

  useEffect(() => {
    if (!isAuthenticated) {
      setDashboardData(null);
      setDashboardError(null);
      return;
    }

    apiFetch<MeResponse>("/auth/me")
      .then((me) => {
        setClinicianName(me.name);
        setSpecialty(me.specialty);
      })
      .catch(() => undefined);

    void loadDashboard();
  }, [isAuthenticated, loadDashboard]);

  const heroSubtitle = useMemo(
    () =>
      isAuthenticated
        ? `Live workspace tuned for ${specialty.toLowerCase()} workflows.`
        : "Move from intake transcript to evidence-backed differential with clear clinical traceability.",
    [isAuthenticated, specialty]
  );

  function formatRelativeTime(value: string): string {
    const input = new Date(value).getTime();
    if (Number.isNaN(input)) return "just now";
    const diffMs = input - Date.now();
    const absMs = Math.abs(diffMs);
    const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
    if (absMs < 60_000) return rtf.format(Math.round(diffMs / 1000), "seconds");
    if (absMs < 3_600_000) return rtf.format(Math.round(diffMs / 60_000), "minutes");
    if (absMs < 86_400_000) return rtf.format(Math.round(diffMs / 3_600_000), "hours");
    return rtf.format(Math.round(diffMs / 86_400_000), "days");
  }

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
                className={"reverse" in module && module.reverse ? "marketing-story marketing-story--reverse stagger-card" : "marketing-story stagger-card"}
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
            <button
              type="button"
              className="button button--ghost dashboard-refresh"
              onClick={() => void loadDashboard()}
              disabled={dashboardLoading}
            >
              {dashboardLoading ? "Refreshing..." : "Refresh"}
            </button>
          </div>
          {dashboardError && (
            <div className="dashboard-error-banner">
              <span>{dashboardError}</span>
              <button type="button" onClick={() => void loadDashboard()}>
                Retry
              </button>
            </div>
          )}
        </div>
        <div className="dashboard-hero__stats">
          <div className="stat-tile">
            <span>Active Patients</span>
            {dashboardLoading && !dashboardData ? (
              <span className="dashboard-kpi-skeleton" aria-hidden />
            ) : (
              <strong>{dashboardData ? dashboardData.kpis.active_patients : "--"}</strong>
            )}
          </div>
          <div className="stat-tile">
            <span>Pending Confirmations</span>
            {dashboardLoading && !dashboardData ? (
              <span className="dashboard-kpi-skeleton" aria-hidden />
            ) : (
              <strong>{dashboardData ? dashboardData.kpis.pending_confirmations : "--"}</strong>
            )}
          </div>
          <div className="stat-tile">
            <span>High-Priority Red Flags (24h)</span>
            {dashboardLoading && !dashboardData ? (
              <span className="dashboard-kpi-skeleton" aria-hidden />
            ) : (
              <strong>{dashboardData ? dashboardData.kpis.high_priority_red_flags_24h : "--"}</strong>
            )}
          </div>
        </div>
      </section>

      <section className="dashboard-grid dashboard-grid--triple">
        <article className="card dashboard-panel dashboard-panel--queue fade-up" style={{ animationDelay: "120ms" }}>
          <h2>Urgent Queue</h2>
          {dashboardLoading && !dashboardData ? (
            <ul className="dashboard-queue-list">
              {Array.from({ length: 4 }).map((_, idx) => (
                <li key={idx} className="dashboard-skeleton-row" />
              ))}
            </ul>
          ) : dashboardData && dashboardData.urgent_queue.length > 0 ? (
            <ul className="dashboard-queue-list">
              {dashboardData.urgent_queue.map((item) => (
                <li key={item.encounter_id}>
                  <Link href={`/encounters/${item.encounter_id}`} className="dashboard-row-link">
                    <div>
                      <p>{item.patient_name}</p>
                      <span>Encounter #{item.encounter_id} · {formatRelativeTime(item.created_at)}</span>
                    </div>
                    <div className="dashboard-row-meta">
                      <span className="status-chip status-chip--pending">Pending</span>
                      {item.red_flag_count > 0 && <span className="red-flag-chip">{item.red_flag_count} red flags</span>}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="app-muted">No encounters waiting for confirmation.</p>
          )}
        </article>

        <article className="card dashboard-panel dashboard-panel--recent fade-up" style={{ animationDelay: "170ms" }}>
          <h2>Recent Encounters</h2>
          {dashboardLoading && !dashboardData ? (
            <ul className="recent-encounter-list">
              {Array.from({ length: 5 }).map((_, idx) => (
                <li key={idx} className="dashboard-skeleton-row" />
              ))}
            </ul>
          ) : dashboardData && dashboardData.recent_encounters.length > 0 ? (
            <ul className="recent-encounter-list">
              {dashboardData.recent_encounters.map((item) => (
                <li key={item.encounter_id}>
                  <Link href={`/encounters/${item.encounter_id}`} className="dashboard-row-link">
                    <div>
                      <p>{item.patient_name}</p>
                      <span>Encounter #{item.encounter_id} · {formatRelativeTime(item.created_at)}</span>
                    </div>
                    <div className="dashboard-row-meta">
                      <span className={item.pending_confirmation ? "status-chip status-chip--pending" : "status-chip status-chip--confirmed"}>
                        {item.pending_confirmation ? "Pending" : "Confirmed"}
                      </span>
                      {item.red_flag_count > 0 && <span className="red-flag-chip">{item.red_flag_count} red flags</span>}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="app-muted">No encounters yet. Start a new encounter.</p>
          )}
        </article>

        <article className="card dashboard-panel dashboard-panel--timeline fade-up" style={{ animationDelay: "220ms" }}>
          <h2>System Timeline</h2>
          {dashboardLoading && !dashboardData ? (
            <ul className="timeline-list">
              {Array.from({ length: 5 }).map((_, idx) => (
                <li key={idx} className="dashboard-skeleton-row" />
              ))}
            </ul>
          ) : dashboardData && dashboardData.timeline.length > 0 ? (
            <ul className="timeline-list">
              {dashboardData.timeline.map((item) => (
                <li key={item.id}>
                  <span className="timeline-dot timeline-dot--neutral" />
                  <div>
                    <p>{item.label}</p>
                    <span>{formatRelativeTime(item.created_at)}</span>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="app-muted">No recent activity yet.</p>
          )}
        </article>
      </section>
    </div>
  );
}
