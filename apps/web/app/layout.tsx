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
          {children}
          <footer className="app-footer">DiagAssistAI clinical decision support platform.</footer>
        </main>
      </body>
    </html>
  );
}
