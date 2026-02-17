import Link from "next/link";

export default function HomePage() {
  return (
    <div className="card">
      <h1>Clinician-in-the-loop intake and decision support</h1>
      <p>This tool provides differential suggestions and evidence snippets. It does not diagnose.</p>
      <div style={{ display: "flex", gap: "0.6rem" }}>
        <Link href="/auth/signin">Sign in</Link>
        <Link href="/encounters/new">Start encounter</Link>
      </div>
    </div>
  );
}
