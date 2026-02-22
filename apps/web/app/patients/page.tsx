"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import type { Patient } from "@diagassist/shared";
import { apiFetch } from "@/lib/api";

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [sex, setSex] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    try {
      setPatients(await apiFetch<Patient[]>("/patients"));
    } catch (e) {
      setMsg((e as Error).message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function createPatient(e: FormEvent) {
    e.preventDefault();
    try {
      await apiFetch<Patient>("/patients", {
        method: "POST",
        body: JSON.stringify({ name, dob: dob || null, sex: sex || null })
      });
      setName("");
      setDob("");
      setSex("");
      setMsg("Patient created.");
      load();
    } catch (err) {
      setMsg((err as Error).message);
    }
  }

  return (
    <div className="app-page">
      <div className="card">
        <h2>Patients</h2>
        <form onSubmit={createPatient} className="app-patient-form">
          <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <input type="date" value={dob} onChange={(e) => setDob(e.target.value)} />
          <input placeholder="Sex" value={sex} onChange={(e) => setSex(e.target.value)} />
          <button type="submit">Add</button>
        </form>
        <p>{msg}</p>
      </div>

      <div className="card">
        <ul className="app-list">
          {patients.map((p) => (
            <li key={p.id}>
              <Link href={`/patients/${p.id}`}>{p.name}</Link> <span className="app-muted">({p.sex || "-"})</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
