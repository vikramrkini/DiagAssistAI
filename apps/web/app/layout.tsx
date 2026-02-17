import Link from "next/link";
import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header style={{ borderBottom: "1px solid #d5e4eb", background: "white" }}>
          <main style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: "0.7rem", paddingBottom: "0.7rem" }}>
            <strong>DiagAssistAI</strong>
            <nav style={{ display: "flex", gap: "0.8rem" }}>
              <Link href="/auth/signin">Sign in</Link>
              <Link href="/clinician/profile">Clinician</Link>
              <Link href="/patients">Patients</Link>
              <Link href="/encounters/new">New Encounter</Link>
              <Link href="/settings">Settings</Link>
            </nav>
          </main>
        </header>

        <main>
          <div className="disclaimer" style={{ marginBottom: "1rem" }}>
            <strong>Educational demo; not for real clinical use.</strong> Decision support only. Final diagnosis must be clinician-confirmed.
          </div>
          {children}
          <footer style={{ marginTop: "1.5rem", color: "#4b6573", fontSize: "0.9rem" }}>
            DiagAssistAI demo uses synthetic data only.
          </footer>
        </main>
      </body>
    </html>
  );
}
