"use client";

import { FormEvent, useState } from "react";
import { apiFetch, setToken } from "@/lib/api";

export default function SignUpPage() {
  const [form, setForm] = useState({ email: "", password: "", name: "", specialty: "general" });
  const [message, setMessage] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setMessage("Creating account...");
    try {
      const resp = await apiFetch<{ access_token: string }>("/auth/signup", {
        method: "POST",
        body: JSON.stringify(form)
      });
      setToken(resp.access_token);
      setMessage("Account created and signed in.");
    } catch (err) {
      setMessage((err as Error).message);
    }
  }

  return (
    <div className="card">
      <h2>Create clinician account</h2>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: "0.7rem", maxWidth: "420px" }}>
        <label>
          Name
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </label>
        <label>
          Email
          <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </label>
        <label>
          Password
          <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
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
        <button type="submit">Create account</button>
      </form>
      <p>{message}</p>
    </div>
  );
}
