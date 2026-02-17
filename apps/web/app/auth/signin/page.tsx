"use client";

import { FormEvent, useState } from "react";
import { apiFetch, setToken } from "@/lib/api";

export default function SignInPage() {
  const [email, setEmail] = useState("general@demo.local");
  const [password, setPassword] = useState("demo12345");
  const [message, setMessage] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setMessage("Signing in...");
    try {
      const resp = await apiFetch<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password })
      });
      setToken(resp.access_token);
      setMessage("Signed in. You can now access clinician and encounter pages.");
    } catch (err) {
      setMessage((err as Error).message);
    }
  }

  return (
    <div className="card">
      <h2>Sign in</h2>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: "0.7rem", maxWidth: "420px" }}>
        <label>
          Email
          <input value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        <button type="submit">Sign in</button>
      </form>
      <p style={{ marginTop: "0.8rem" }}>{message}</p>
    </div>
  );
}
