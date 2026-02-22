"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, getToken, setToken, subscribeToAuthChanges } from "@/lib/api";

function toErrorMessage(err: unknown): string {
  const raw = err instanceof Error ? err.message : "Unable to create account.";
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

export default function SignUpPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email: "", password: "", name: "", specialty: "general" });
  const [message, setMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const syncAndRedirect = () => {
      if (getToken()) router.replace("/");
    };
    syncAndRedirect();
    return subscribeToAuthChanges(syncAndRedirect);
  }, [router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setIsSubmitting(true);
    setMessage("Creating account...");
    try {
      const resp = await apiFetch<{ access_token: string }>("/auth/signup", {
        method: "POST",
        body: JSON.stringify(form)
      });
      setToken(resp.access_token);
      router.push("/");
      router.refresh();
    } catch (err) {
      setMessage(toErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="auth-shell auth-shell--signin fade-up">
      <article className="auth-story auth-story--signin">
        <div className="signin-hero__pattern" aria-hidden />
        <div className="signin-topbar">
          <span className="signin-topbar__brand">
            <img src="/diagassist-logo.svg" alt="" />
            DiagAssistAI
          </span>
          <div className="signin-topbar__links">
            <span>Secure</span>
            <span>Fast</span>
            <span>Traceable</span>
          </div>
        </div>
        <div className="signin-hero__content">
          <p className="eyebrow">Registration</p>
          <h1>Create your clinician account.</h1>
          <p>Set up your profile to access specialty-specific prompts, patient records, and encounter workflows.</p>
          <div className="signin-chip-row">
            <span>Role-aware workflows</span>
            <span>Secure access</span>
            <span>Ready in minutes</span>
          </div>
        </div>

        <div className="signin-hero__visual">
          <div className="signin-orbital">
            <span className="signin-orbital__ring" />
            <span className="signin-orbital__ring signin-orbital__ring--two" />
            <img src="/diagassist-logo.svg" alt="" className="signin-orbital__logo" />
          </div>
          <div className="signin-hero__stats">
            <div className="signin-stat-card">
              <strong>4 Specialties</strong>
              <span>Guided onboarding choices</span>
            </div>
            <div className="signin-stat-card">
              <strong>&lt; 1 min</strong>
              <span>Account setup duration</span>
            </div>
          </div>
        </div>
      </article>

      <article className="auth-card auth-card--signin fade-up" style={{ animationDelay: "120ms" }}>
        <h2>Register</h2>
        <p className="auth-card__subtle">Set up your clinician profile.</p>
        <form onSubmit={onSubmit} className="auth-form">
          <label>
            Name
            <input
              value={form.name}
              autoComplete="name"
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
              minLength={2}
            />
          </label>
          <label>
            Email
            <input
              type="email"
              value={form.email}
              autoComplete="email"
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={form.password}
              autoComplete="new-password"
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
              minLength={8}
            />
          </label>
          <label>
            Specialty
            <select value={form.specialty} onChange={(e) => setForm({ ...form, specialty: e.target.value })}>
              <option value="general">General</option>
              <option value="pediatrics">Pediatrics</option>
              <option value="physiotherapy">Physiotherapy</option>
              <option value="dermatology">Dermatology</option>
            </select>
          </label>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating account..." : "Create account"}
          </button>
        </form>
        {message && <p className="auth-message">{message}</p>}
        <p className="auth-card__subtle">
          Already registered? <Link href="/auth/signin">Sign in</Link>
        </p>
      </article>
    </section>
  );
}
