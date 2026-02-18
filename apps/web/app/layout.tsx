import "./globals.css";
import { AppHeader } from "@/components/app-header";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="bg-orb bg-orb--one" />
        <div className="bg-orb bg-orb--two" />
        <AppHeader />

        <main className="app-shell">
          <div className="disclaimer">
            <strong>Educational demo; not for real clinical use.</strong> Decision support only. Final diagnosis must be clinician-confirmed.
          </div>
          {children}
          <footer className="app-footer">
            DiagAssistAI demo uses synthetic data only. All outputs require clinician confirmation.
          </footer>
        </main>
      </body>
    </html>
  );
}
