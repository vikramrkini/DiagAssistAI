"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

interface AppSettings {
  demo_mode: boolean;
  store_audio: boolean;
  openai_key_configured: boolean;
  specialty_depth: Record<string, string>;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    apiFetch<AppSettings>("/settings").then(setSettings).catch((e) => setMsg(e.message));
  }, []);

  async function save() {
    if (!settings) return;
    try {
      const updated = await apiFetch<AppSettings>("/settings", {
        method: "PUT",
        body: JSON.stringify({ demo_mode: settings.demo_mode, store_audio: settings.store_audio, specialty_depth: settings.specialty_depth })
      });
      setSettings(updated);
      setMsg("Settings saved.");
    } catch (e) {
      setMsg((e as Error).message);
    }
  }

  if (!settings) return <div className="card">{msg || "Loading..."}</div>;

  return (
    <div className="card">
      <h2>Settings</h2>
      <label style={{ display: "block", marginBottom: "0.5rem" }}>
        <input
          type="checkbox"
          checked={settings.demo_mode}
          onChange={(e) => setSettings({ ...settings, demo_mode: e.target.checked })}
          style={{ width: "auto", marginRight: "0.45rem" }}
        />
        Demo mode
      </label>
      <label style={{ display: "block", marginBottom: "0.8rem" }}>
        <input
          type="checkbox"
          checked={settings.store_audio}
          onChange={(e) => setSettings({ ...settings, store_audio: e.target.checked })}
          style={{ width: "auto", marginRight: "0.45rem" }}
        />
        Store raw audio (demo only)
      </label>

      <p>OpenAI key configured: {settings.openai_key_configured ? "yes" : "no"}</p>
      <pre style={{ background: "#f1f7fb", padding: "0.75rem", borderRadius: "8px" }}>{JSON.stringify(settings.specialty_depth, null, 2)}</pre>
      <button onClick={save}>Save settings</button>
      <p>{msg}</p>
    </div>
  );
}
