"use client";

import { FormEvent, useEffect, useState } from "react";
import type { ClinicianProfile } from "@diagassist/shared";
import { apiFetch } from "@/lib/api";

export default function ClinicianProfilePage() {
  const [profile, setProfile] = useState<ClinicianProfile | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<ClinicianProfile>("/clinicians/me").then(setProfile).catch((e) => setError(e.message));
  }, []);

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!profile) return;
    try {
      const updated = await apiFetch<ClinicianProfile>("/clinicians/me", {
        method: "PUT",
        body: JSON.stringify({
          name: profile.name,
          specialty: profile.specialty,
          sub_specialty: profile.sub_specialty,
          org: profile.org,
          preferences_json: profile.preferences_json
        })
      });
      setProfile(updated);
      setError("Saved.");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (error && !profile) return <div className="card">{error}</div>;
  if (!profile) return <div className="card">Loading...</div>;

  return (
    <div className="card">
      <h2>Clinician profile</h2>
      <form onSubmit={save} style={{ display: "grid", gap: "0.7rem" }}>
        <label>
          Name
          <input value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} />
        </label>
        <label>
          Email
          <input value={profile.email} disabled />
        </label>
        <label>
          Specialty
          <select value={profile.specialty} onChange={(e) => setProfile({ ...profile, specialty: e.target.value as ClinicianProfile["specialty"] })}>
            <option value="general">General</option>
            <option value="pediatrics">Pediatrics</option>
            <option value="physiotherapy">Physiotherapy</option>
            <option value="dermatology">Dermatology</option>
          </select>
        </label>
        <label>
          Sub-specialty
          <input value={profile.sub_specialty ?? ""} onChange={(e) => setProfile({ ...profile, sub_specialty: e.target.value })} />
        </label>
        <label>
          Organization
          <input value={profile.org ?? ""} onChange={(e) => setProfile({ ...profile, org: e.target.value })} />
        </label>
        <button type="submit">Save profile</button>
      </form>
      <p>{error}</p>
    </div>
  );
}
