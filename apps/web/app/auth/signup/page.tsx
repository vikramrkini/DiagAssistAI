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
  const [form, setForm] = useState({
    email: "",
    password: "",
    name: "",
    specialty: "general",
    account_type: "private_practice",
    organization_name: ""
  });
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
    if (form.account_type === "hospital" && !form.organization_name.trim()) {
      setMessage("For an organization account, provide the organization name.");
      return;
    }
    setIsSubmitting(true);
    setMessage("Creating account...");
    try {
      const payload = {
        email: form.email,
        password: form.password,
        name: form.name,
        specialty: form.specialty,
        account_type: form.account_type,
        organization_name: form.organization_name.trim() || undefined
      };
      const resp = await apiFetch<{ access_token: string }>("/auth/signup", {
        method: "POST",
        body: JSON.stringify(payload)
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
    <section className="auth-shell auth-shell--signin auth-shell--signin-centered fade-up">
      <article className="auth-card auth-card--signin auth-card--signin-centered fade-up" style={{ animationDelay: "120ms" }}>
        <p className="eyebrow">Registration</p>
        <h1 className="auth-signin-title">Create your account to continue.</h1>
        <p className="auth-signin-copy">
          Choose whether you are onboarding as an individual clinician or creating an organization account.
        </p>
        <h2>Register</h2>
        <p className="auth-card__subtle">Set your account details below.</p>
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
            Account type
            <select value={form.account_type} onChange={(e) => setForm({ ...form, account_type: e.target.value })}>
              <option value="private_practice">Individual clinician account</option>
              <option value="hospital">Organization account</option>
            </select>
          </label>
          {form.account_type === "hospital" ? (
            <label>
              Organization name
              <input
                value={form.organization_name}
                onChange={(e) => setForm({ ...form, organization_name: e.target.value })}
                placeholder="Northside Medical Center"
                required
              />
            </label>
          ) : (
            <label>
              Practice name (optional)
              <input
                value={form.organization_name}
                onChange={(e) => setForm({ ...form, organization_name: e.target.value })}
                placeholder="Dr. Smith Practice"
              />
            </label>
          )}
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
        <p className="auth-signin-meta">You can update profile and organization details later from settings.</p>
        <p className="auth-card__subtle">
          Already registered? <Link href="/auth/signin">Sign in</Link>
        </p>
      </article>
    </section>
  );
}
