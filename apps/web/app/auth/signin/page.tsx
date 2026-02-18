"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, getToken, setToken, subscribeToAuthChanges } from "@/lib/api";

function toErrorMessage(err: unknown): string {
  const raw = err instanceof Error ? err.message : "Unable to sign in.";
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

export default function SignInPage() {
  const router = useRouter();
  const [email, setEmail] = useState("general@demo.local");
  const [password, setPassword] = useState("demo12345");
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
    setMessage("Signing in...");
    try {
      const resp = await apiFetch<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password })
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
    <section className="auth-shell">
      <article className="auth-story card fade-up">
        <p className="eyebrow">Secure Access</p>
        <h1>Welcome back to your clinical workspace.</h1>
        <p>Continue with your clinician account to review patients, run intake extraction, and issue final diagnoses.</p>
        <ul>
          <li>Human-review-first decision support</li>
          <li>Evidence-linked differential outputs</li>
          <li>Audit-ready encounter records</li>
        </ul>
      </article>

      <article className="auth-card card fade-up" style={{ animationDelay: "120ms" }}>
        <h2>Sign in</h2>
        <p className="auth-card__subtle">Use your clinic credentials.</p>
        <form onSubmit={onSubmit} className="auth-form">
          <label>
            Email
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
        {message && <p className="auth-message">{message}</p>}
        <p className="auth-card__subtle">
          New here? <Link href="/auth/signup">Create a clinician account</Link>
        </p>
      </article>
    </section>
  );
}
