# Product

## Register

product

## Users

Solo builder running self-hosted n8n, expanding later to a small team of
technical operators. They connect their own n8n instance and use this
dashboard to answer one question repeatedly: "is everything still working?"
The job is monitoring, not configuration — they come here to scan workflow
health, read what a workflow does (via generated summaries), and check alert
history when something breaks. Sessions are short and frequent, often
triggered by an email alert or a moment of "let me just check."

## Product Purpose

A hosted watchdog for self-hosted n8n instances: inventories workflows,
tracks execution health (failing / silent / orphaned / unused / healthy),
generates plain-English summaries of what each workflow does, and emails
when something breaks. Success looks like the user trusting the dashboard
enough to stop manually opening n8n to check on things.

## Brand Personality

Clinical & precise. This is an ops/monitoring tool, not a product the user
spends leisure time in — it should read like instrumentation: legible at a
glance, calm under a real incident, no decoration that doesn't encode a
fact. Trust is built through accuracy and restraint, not warmth.

## Anti-references

Avoid the generic SaaS dashboard look: no purple/blue gradients, no
identical icon+heading+text card grids, no hero-metric-with-gradient-accent
stat tiles, no decorative illustrations. If a screen could be mistaken for
a generic analytics-SaaS template, it's failed.

## Design Principles

- **Status is the headline.** Health state (healthy/failing/silent/
  orphaned/unused) is the single most important fact on any screen showing
  a workflow — everything else is supporting detail, never competing for
  attention with it.
- **Default to calm.** A healthy workflow should be visually quiet. Reserve
  visual weight (color, contrast, motion) for things that actually need
  attention — alerting fatigue from a noisy "everything is fine" view
  defeats the product's purpose.
- **No decoration without information.** Every color, icon, and visual
  treatment should encode a real fact about the system (a status, a count,
  a trend) — nothing purely ornamental.
- **Built for scanning under stress, not first impressions.** Optimize for
  someone glancing at this after getting an alert email at an odd hour, not
  for a polished first-run demo.
- **Trustworthy precision.** A monitoring tool that's visually overstated or
  imprecise erodes confidence faster than one that's plain. Numbers, statuses,
  and timestamps should always read as exact, not approximate or decorative.

## Accessibility & Inclusion

WCAG 2.1 AA minimum: body text ≥4.5:1 contrast, large/bold text ≥3:1,
visible focus states, full keyboard navigation, `prefers-reduced-motion`
alternative for every animation. Status must never be color-only — pair
every health/alert state with a label or icon so it reads correctly for
color-blind users.
