import Link from "next/link";

const aboutStories = [
  {
    title: "Built Around Clinical Control",
    description:
      "DiagAssistAI is designed so every recommendation remains clinician-guided, with transparent outputs that support decisions instead of replacing judgment.",
    image:
      "https://images.unsplash.com/photo-1551076805-e1869033e561?auto=format&fit=crop&w=1800&q=80",
    alt: "Doctor reviewing digital patient records on a tablet"
  },
  {
    title: "Engineered For Traceability",
    description:
      "From intake summary to differential rationale, the platform keeps reasoning visible and structured so teams can review and communicate clearly.",
    image:
      "https://images.unsplash.com/photo-1579154204601-01588f351e67?auto=format&fit=crop&w=1800&q=80",
    alt: "Clinical workstation with charts and patient data",
    reverse: true
  },
  {
    title: "Focused On Operational Flow",
    description:
      "The interface is built for real care-team pace, helping clinicians move from transcript to plan faster with less friction across each encounter.",
    image:
      "https://images.unsplash.com/photo-1584515933487-779824d29309?auto=format&fit=crop&w=1800&q=80",
    alt: "Healthcare professionals collaborating in a hospital setting"
  }
] as const;

export default function AboutPage() {
  return (
    <div className="marketing-page marketing-page--subpage fade-up">
      <div className="marketing-page__overlay marketing-page__overlay--one" aria-hidden />
      <div className="marketing-page__overlay marketing-page__overlay--two" aria-hidden />

      <section className="marketing-hero marketing-hero--subpage">
        <div className="marketing-hero__copy">
          <p className="eyebrow">About DiagAssistAI</p>
          <h1>Built to support clinical teams with reliable, review-ready intelligence.</h1>
          <p>
            DiagAssistAI helps clinicians move from intake to confident decisions with structured outputs, clear
            reasoning, and a workflow optimized for production care environments.
          </p>
        </div>
      </section>

      <section className="marketing-section fade-up" style={{ animationDelay: "120ms" }}>
        <div className="marketing-story-list">
          {aboutStories.map((item, index) => (
            <article
              key={item.title}
              className={"reverse" in item && item.reverse ? "marketing-story marketing-story--reverse stagger-card" : "marketing-story stagger-card"}
              style={{ animationDelay: `${160 + index * 80}ms` }}
            >
              <div className="marketing-story__card">
                <h3>{item.title}</h3>
                <p>{item.description}</p>
              </div>
              <div className="marketing-story__media">
                <img src={item.image} alt={item.alt} loading="lazy" />
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="marketing-section fade-up" style={{ animationDelay: "200ms" }}>
        <div className="hero__actions">
          <Link href="/auth/signup" className="button">
            Register
          </Link>
          <Link href="/auth/signin" className="button button--ghost">
            Sign in
          </Link>
        </div>
      </section>
    </div>
  );
}
