# No-Code Watchdog — Project Context

Read this file first in any new session. Update it whenever a phase finishes or a
decision changes, so the next session (or a fresh agent) can pick up cold.

## What this is

A hosted watchdog for self-hosted n8n instances. Users connect their n8n via
base URL + API key; the product inventories workflows, monitors executions for
failures/silence, generates plain-English LLM summaries of what each workflow
does, and alerts by email when something breaks. V1 is n8n-only. Solo builder,
limited coding experience — keep code simple and readable over clever.

Full original product spec (problem statement, target users, MVP scope,
suggested data model) was given by the user at project kickoff — see chat
history if the rationale behind a decision is unclear; this file tracks
*current state*, not the original brief.

## Locked-in decisions (don't re-litigate without asking)

- **Backend**: Python 3.13 + FastAPI, sync SQLAlchemy 2.0 + Alembic (not async —
  simpler mental model for routes using regular `def`, FastAPI threadpools them).
- **DB**: Postgres via Docker Compose, **host port 5433** (not 5432 — see
  "Gotchas" below for why).
- **Auth**: email+password, signed session cookie via `itsdangerous` (not JWT).
  Password hashing: `bcrypt` library directly (not passlib — see Gotchas).
- **Secrets**: n8n API keys encrypted at rest with `cryptography.fernet.Fernet`.
- **LLM for summaries**: local Ollama on the user's M5 MacBook (24GB). Wired up
  in Phase 4 via `app/llm.py`'s `generate_text()`, kept as the one function to
  change when this deploys to a VPS without the Mac's GPU. Model is
  `gemma4:e4b`, not the originally-planned `qwen2.5:7b-instruct` — that model
  was never actually pulled locally, and the user chose to use what was
  already available (`gemma4:e4b`/`gemma4:latest`, same image; `qwen3:14b` was
  also tried, see Phase 4 below for why it lost out) rather than spend time
  downloading the original pick. Revisit if summary quality ever needs it.
- **Email alerts**: Resend, called directly over HTTP via `httpx` in
  `app/email.py` (no `resend` SDK dependency — same style as `N8nClient`).
  Wired up in Phase 3, deferred (empty `RESEND_API_KEY`) through Phase 8. As
  of Phase 9, a real `RESEND_API_KEY` is set in `apps/api/.env` — but no
  domain is verified on Resend yet, so the account is still in **sandbox
  mode**: it can only send `to` the email address on the Resend account
  itself (`binsvarghese6@gmail.com`), to any other recipient it 403s. Real
  multi-user delivery still needs a verified sending domain — see Phase 9
  below and Gotcha 11.
- **Scheduler**: APScheduler, in-process (not Celery/Redis — not needed at this
  scale). Implemented in Phase 3 as a single `BackgroundScheduler` job
  (`app/scheduler.py`) wired into FastAPI's `lifespan`. Only correct for a
  single uvicorn worker process — if this ever deploys with multiple workers,
  each would run its own scheduler and duplicate every tick (re-sync N times,
  but alerts still dedupe correctly via the DB). Revisit then (e.g. run the
  scheduler as a separate process, or add a DB-based leader lock); not a
  problem at current scale (`uvicorn --reload`, one process).
- **Frontend**: Next.js (App Router), built in Phase 6 — `apps/web`. Every page is a
  Client Component (`"use client"`, plain `fetch`/`useState`/`useEffect`, no
  SWR/react-query) rather than Server Components with the framework's
  cookie-forwarding/async-params machinery — deliberate simplicity choice given
  "limited coding experience, keep code simple." Auth is the existing FastAPI
  signed cookie (not NextAuth) checked once via a context provider; see Phase 6
  below for specifics.
- **Repo shape**: monorepo, `apps/api` (backend) + `apps/web` (frontend, built in
  Phase 6).
- **Visual design system**: "The Instrument Panel" — dark, near-black, one amber
  brand color (`terminal-amber`) reserved for primary actions only, status colors
  (failing/silent/orphaned/healthy/unused) kept in a separate closed palette so
  brand and status are never confused. Built in Phase 8 via the `impeccable` +
  `emil-design-eng` Claude Code skills (installed project-locally under
  `.claude/skills/` and `.agents/skills/` — see Phase 8 below). Source of truth:
  root `PRODUCT.md` (strategic — register, users, brand personality, anti-
  references) and root `DESIGN.md` (visual — color/type/component tokens,
  named rules like "The Calm Default Rule"). Read both before making any future
  visual change to `apps/web`; don't reinvent tokens that already exist there.

## IMPORTANT — unrelated sibling project, do not touch

`/Users/binsevarghese/Documents/Binse/Projects/watchdog_open_code/` is a
**separate, unrelated build** (different tool, OpenCode CLI) that happens to
attempt a similar idea. The user explicitly said to leave it alone and
continue only in this `watchdog/` directory. Do not read, edit, or run
anything there. Its local Postgres (Homebrew, port 5432) is also unrelated —
that's why this project's Docker Postgres runs on **5433** instead of the
default 5432, to avoid colliding with that other project's DB.

## Environment / how to run locally

```bash
docker compose up -d postgres adminer   # Postgres on localhost:5433, Adminer UI on localhost:8081
cd apps/api
source .venv/bin/activate               # venv built with Homebrew python3.13 (NOT system python3.14 — see Gotchas)
uvicorn app.main:app --reload --reload-dir app --port 8000
```

Frontend (Phase 6 — `apps/web`), separate terminal:

```bash
cd apps/web
npm run dev      # Next.js + Turbopack on http://localhost:3000
```

`apps/web/.env.local` has `NEXT_PUBLIC_API_URL=http://localhost:8000` — the
only place the API's base URL is configured. The backend's CORS
(`app/main.py`) only allows `http://localhost:3000`, so both sides need to
agree on "localhost" (not `127.0.0.1`) for the session cookie to ride along
on cross-origin requests.

n8n is **not** part of `docker-compose.yml` (changed during the Phase 3→4
transition — see below). It's the user's own pre-existing standalone
container, started separately:

```bash
docker start n8n   # if not already running; UI + API at http://localhost:5678
```

### Switched from throwaway dev n8n to the user's real instance

Phase 1–3 used a disposable `watchdog-n8n-dev` container defined in
`docker-compose.yml` (`n8n` service, port 5678), seeded only with two test
workflows created via n8n's internal API (see Gotcha 8's last line). At the
Phase 3→4 boundary the user asked to switch to their own pre-existing
standalone n8n container (name `n8n`, image `n8nio/n8n:latest`, **not**
managed by this project's Docker Compose — created independently, outside
this repo) which already has a real owner account and real workflows.

What changed:
- `watchdog-n8n-dev` container, its compose service block, and its
  `watchdog_n8n_data` volume were all removed. `docker-compose.yml` now only
  defines `postgres` and `adminer`.
- The user's standalone `n8n` container had no host port published and
  wasn't reachable via OrbStack's `orb.local` domain from this machine (DNS
  didn't resolve — unclear why, didn't dig further since the port route
  worked). With explicit user confirmation, it was recreated (stop + rm +
  run) with `-p 5678:5678` and `-e N8N_SECURE_COOKIE=false` added, mounting
  the **same** `n8n_data` volume (confirmed via `docker inspect` before
  touching anything) so all existing workflows/credentials/login are
  preserved. Image reference kept identical (`n8nio/n8n:latest`).
- It stays a plain `docker run` container, intentionally **not** added back
  into `docker-compose.yml` — it's the user's own resource, not part of this
  product's stack, just something the API happens to connect to over
  `localhost:5678` like any other external n8n instance would be.
- **The old `Connection` DB row was dead** after the switch: its encrypted
  API key was generated against the throwaway instance's owner account and
  would have gotten `unauthorized` against the real instance, even though
  `n8n_base_url` (`http://localhost:5678`) happens to be unchanged. Since
  there's no PATCH endpoint for connections (only POST/DELETE), this was
  fixed with a one-off script (not a new endpoint — same pattern as other
  phases' direct-function smoke tests) that: tested the user's new, real API
  key (generated the proper way this time, via n8n's own Settings → API UI)
  with `N8nClient.test_connection()`, deleted the old connection (cascaded
  its now-meaningless `Workflow`/`Execution`/`Alert` rows), created a fresh
  `Connection` for the same user pointing at the real instance, and called
  `sync_connection()` on it for real.
  - Result: **10 real workflows synced, 0 executions**. Confirmed this is
    correct, not a sync bug — `GET /api/v1/executions` against the raw n8n
    API independently returns `{"data": [], "nextCursor": null}` too, so
    this real instance's workflows genuinely have no execution history yet.
    Means real workflows are now available for Phase 4 summary-generation
    testing, but "failing"/"silent" health-status testing will still need
    actual runs against these real workflows first (everything will read as
    `unused` until something executes).

`.env` already exists in `apps/api/` with working dev keys (Fernet key, session
secret) — already generated, don't regenerate unless rotating. As of Phase 9,
`RESEND_API_KEY` is a real key (`ALERTS_FROM_EMAIL=onboarding@resend.dev`,
Resend's no-domain-needed sandbox sender) and email sending has been verified
to work for real — but see Gotcha 11: with no domain verified on Resend, it
can currently only deliver `to` `binsvarghese6@gmail.com`, every other
recipient 403s. `FRONTEND_URL` (new in Phase 9, default
`http://localhost:3000`) is used to build links in emails (currently just the
password-reset link). `OLLAMA_MODEL=gemma4:e4b` (see Phase 4) — actually
wired up and in use now.

The background scheduler (periodic n8n sync + health/alert check, every
`sync_interval_minutes`) starts automatically with the app via FastAPI's
`lifespan` — no separate process to run.

## Gotchas hit so far (don't repeat these)

1. **System Python is 3.14** (`python3` / Homebrew default) — too new,
   `pydantic-core`/`psycopg2-binary` wheels don't support it yet. The venv at
   `apps/api/.venv` was built with `/opt/homebrew/bin/python3.13` specifically.
   If the venv ever needs rebuilding, use 3.13, not `python3`.
2. **`psycopg2-binary` must be `>=2.9.10`** for Python 3.13 (2.9.9 fails to
   build from source on this machine).
3. **`pydantic[email]` extra is required** for `EmailStr` fields — plain
   `pydantic` alone throws `ImportError: email-validator is not installed` at
   import time, which crashes the whole app on startup.
4. **`passlib` 1.7.4 is incompatible with modern `bcrypt` (>=4.1)** — its
   internal self-test (`detect_wrap_bug`) crashes with
   `ValueError: password cannot be longer than 72 bytes`. Fixed by dropping
   `passlib` entirely and calling `bcrypt.hashpw`/`bcrypt.checkpw` directly in
   `app/security.py`. Do not reintroduce passlib.
5. **`uvicorn --reload` without `--reload-dir app` watches the whole project
   including `.venv`**, causing reload storms whenever pip installs anything.
   Always pass `--reload-dir app`.
6. Port 5432 conflict — see "unrelated sibling project" section above. This
   project's Postgres is on host port **5433**.
7. **Alembic autogenerate never adds a `server_default`** even when the
   SQLAlchemy model has a Python-side `default=`. A new NOT NULL column
   (e.g. `Workflow.is_orphaned` in Phase 3) on a table that already has rows
   fails on `alembic upgrade` unless you hand-edit the generated migration to
   add `server_default=sa.text(...)`. Always check autogenerated
   `add_column(... nullable=False)` calls against tables with existing data.
8. **Local models (`gemma4:e4b`, `qwen3:14b`) won't follow "write 2-4 plain
   sentences, no markdown/jargon" instructions directly** when given a
   workflow's raw node/connection list, no matter how the prompt is phrased
   (tried: blunt instructions, a strict system-role prompt + `num_predict`
   token cap, a few-shot example). `gemma4:e4b` always wrote a long
   multi-section markdown report with headers/tables and named generic
   node-type pseudonyms (`Switch`, `Call`, `Condition`...) verbatim;
   `qwen3:14b` (with `"think": false`) rendered a literal ASCII tree diagram
   of the node graph instead — equally off-spec, just differently. Fix was
   **two LLM calls, not better wording**: let the model write whatever
   detailed/technical analysis it wants first, then feed *that text* back in
   a second call asking it to condense to plain sentences — both models stay
   on-task once the input is prose instead of a structured node list. See
   `app/summaries.py`'s `_build_analysis_prompt`/`_build_condense_prompt`. If
   summary quality ever degrades again, suspect this same failure mode before
   re-tweaking prompt wording.
9. **n8n webhook nodes need a top-level `webhookId` (UUID) field, not just
   `parameters.path`**, or n8n's API will report the workflow as
   `active: true` / published but the webhook still 404s
   ("not registered") when called. The n8n editor adds this automatically;
   hand-built workflow JSON (e.g. via the public API, like our test
   workflows) must set it explicitly. Cost real debugging time in Phase 2 —
   also tried restarting the n8n container before finding the real cause,
   which was a red herring (restarting isn't needed once `webhookId` is set).
10. **Concurrent `POST /connections/{id}/workflows/{id}/summary` requests for
    the same workflow can crash with an unhandled `IntegrityError`.** Found
    via real usage post-Phase-7: the two-call LLM round trip takes up to ~2
    minutes, long enough that a user navigates away and back; the
    "Generating..." button is plain React state that doesn't survive the
    component unmounting, so it resets to "Generate summary" and looks like
    it stopped — clicking it again fires a second request while the first is
    still running server-side. Both find no existing `WorkflowSummary` row,
    both proceed, and the loser's `db.commit()` in `app/summaries.py`'s
    `generate_workflow_summary` hits the `workflow_summaries_workflow_id_key`
    unique constraint. That unhandled exception produces a 500 that skips
    `CORSMiddleware`'s header injection (a Starlette quirk: unhandled
    exceptions bypass the middleware that adds CORS headers to normal
    responses), so the browser misreports it as a CORS error rather than a
    real one. Fixed two ways: `generate_workflow_summary` now catches that
    `IntegrityError`, rolls back, and updates the row the other request
    already created instead of erroring; and `app/connections.py`'s route
    tracks in-progress workflow IDs in memory (`_summaries_in_progress` +
    `threading.Lock`) and returns a clean 409 ("Already generating a summary
    for this workflow - wait for it to finish") if a second request for the
    same workflow arrives before the first finishes. The in-memory lock is
    single-process only — revisit if the scheduler/API ever runs with
    multiple uvicorn workers.
11. **A Resend account with no verified domain ("sandbox mode") can only
    send `to` the email address registered on that Resend account itself.**
    Confirmed by hitting it for real in Phase 9: sending `to` any other
    address (even a different real inbox the user owns) returns a 403
    `validation_error` - "You can only send testing emails to your own email
    address (...). To send emails to other recipients, please verify a
    domain...". The `from` address in this mode should be Resend's sandbox
    sender `onboarding@resend.dev` (a `from` on a domain you don't own/can't
    verify, like a personal `@gmail.com` address, fails separately). This
    means every alert/forgot-password email currently only actually delivers
    to `binsvarghese6@gmail.com` - anyone else gets a 403 that's swallowed
    into `email_error`/a generic success message, looking like it worked
    when it didn't send. Don't mistake this for a code bug; it resolves once
    a real domain is verified on Resend.

## Current state (Phase 1-9 - DONE, production-readiness items next)

### Phase 9 — done

Scope: account/password endpoints that were missing from the REST surface
(account deletion, change password, forgot/reset password), plus getting a
real Resend API key wired up for the first time.

- **Resend setup, before any of the endpoint work**: the user added a real
  `RESEND_API_KEY` and a personal email, but pasted them into the root
  **`.env.example`** (the committed template meant to stay secret-free) by
  mistake, instead of `apps/api/.env` (the file `app/config.py` actually
  loads). Moved the real values into `apps/api/.env` and restored
  `.env.example` back to blank placeholders. Also caught that the personal
  email the user wanted as `ALERTS_FROM_EMAIL` was a `@gmail.com` address —
  Resend can't let you send `from` a domain you don't own/can't verify, so
  swapped it for Resend's built-in sandbox sender `onboarding@resend.dev`
  (no domain setup needed) instead. Sent one real test email via
  `app/email.py`'s `send_email()` directly to confirm delivery actually
  works — first attempt to the user's other personal address 403'd
  ("You can only send testing emails to your own email address
  (binsvarghese6@gmail.com)"), which is how Gotcha 11's sandbox-mode
  restriction was actually discovered, not assumed. Second attempt to
  `binsvarghese6@gmail.com` succeeded.
- `app/security.py` — added `create_reset_token`/`read_reset_token`: a
  second `URLSafeTimedSerializer` instance, separate salt
  (`"watchdog-password-reset"`) and a 1-hour `RESET_TOKEN_MAX_AGE_SECONDS`,
  distinct from the existing 14-day session token serializer so reset links
  can't be reused as session tokens or vice versa.
- `app/schemas.py` — `ChangePasswordRequest`, `ForgotPasswordRequest`,
  `ResetPasswordRequest`.
- `app/config.py` — new `frontend_url` setting (default
  `http://localhost:3000`), used to build the reset-password link embedded
  in the forgot-password email.
- `app/auth.py` — four new routes:
  - `DELETE /auth/me` — deletes the user (cascades to every connection/
    workflow/execution/alert/summary via the existing model relationships)
    and clears the session cookie. Every prior phase's test cleanup had to
    delete throwaway users via direct DB access because this didn't exist —
    it now exists and was used for its own test cleanup in this phase.
  - `PATCH /auth/me/password` — verifies `current_password` against the
    stored hash before accepting `new_password`; 400 if it doesn't match.
  - `POST /auth/forgot-password` — looks up the user by email but **always
    returns the same generic message** regardless of whether the email is
    registered, specifically so the endpoint can't be used to enumerate
    which emails have accounts. If the user exists, mints a reset token and
    emails a `{frontend_url}/reset-password?token=...` link via the existing
    `send_email()` — failures (e.g. the sandbox-mode 403 from Gotcha 11) are
    swallowed the same way `app/alerts.py` already swallows email failures,
    so a user requesting a reset always sees success even if the email
    didn't actually arrive. Known limitation, not a bug to fix here — same
    root cause as Gotcha 11.
  - `POST /auth/reset-password` — validates the token (signature + 1hr
    expiry) and updates the password hash; 400 on an invalid/expired/
    tampered token.
- Frontend (`apps/web/`):
  - New `/account` page — change-password form plus a danger-zone
    delete-account card, same visual pattern as the existing
    `/connections/[id]/settings` page (`Card` with `border-failing/40`,
    native `window.confirm` before deleting).
  - New `/forgot-password` page (email form → generic "if that email has an
    account..." message) and `/reset-password` page (reads `?token=` via
    `useSearchParams`, wrapped in `<Suspense>` per Next.js's requirement for
    that hook, sets a new password, redirects to `/login`).
  - `/login` gained a "Forgot password?" link; `Nav.tsx`'s user-email label
    is now a link to `/account` instead of plain text.
  - `npx tsc --noEmit` and `npm run lint` both clean.
- **Tests**: 18 new cases added to `tests/test_auth.py` covering delete
  (success + requires-auth), change password (correct/wrong current
  password + requires-auth), forgot-password (known email sends, unknown
  email returns the identical generic response with no email attempted),
  and reset-password (valid token, invalid token, tampered token) —
  `send_email` monkeypatched per test so none of these hit the real Resend
  API. Full suite: **78/78 passing**.
- **Verified in a real headless browser** (Playwright, same scratch-install-
  then-discard pattern as Phases 6/8 — not a project dependency): signup → 
  `/account` → wrong-current-password rejected with the right error → 
  correct change succeeds → logout/login with the new password works →
  `/forgot-password` submit shows the generic message → `/reset-password`
  with no token shows the "missing its token" guidance → delete account
  redirects to `/login` → re-signup with the same email succeeds, proving
  the row was actually gone, not just logged out. Zero unexpected
  `pageerror`s (the 401 console noise on logged-out-page auth probes is the
  same expected, harmless pattern noted in Phase 6/8). Also exercised
  `DELETE /auth/me` directly over HTTP (not just through the UI) to clean up
  a leftover throwaway account from an earlier failed test run, confirming
  the endpoint works standalone too. Scratch Playwright install discarded
  afterward.

Not done yet / immediate next steps:
- **Resend still needs a verified sending domain** before alerts or
  password resets can reach any real user other than
  `binsvarghese6@gmail.com` — see Gotcha 11. This has been carried over and
  re-stated every phase since Phase 3; don't re-raise it again until the
  user brings up getting a domain.
- No "resend the verification" / email-verification-on-signup flow — signup
  accepts any email address with no confirmation step. Not asked for; flag
  only if the user wants it.
- The multi-worker scheduler caveat (Phase 3) is still open, unrelated to
  this phase.

### Phase 8 — done

Scope: visual redesign of `apps/web` — the UI was functionally complete (Phase
6/7) but visually default Tailwind (white bg, black text, Arial, bare
`bg-green-100`-style status badges). User asked for a "professional" redesign
and specifically asked to use the `impeccable` and `emil-design-eng` Claude
Code skills.

- **Skills installed project-locally** (not in this session's default skill
  set — had to be installed mid-session):
  - `npx impeccable install` → `.claude/skills/impeccable/` (also wrote a
    design-detector PostToolUse hook, `.impeccable/hook.cache.json`).
  - `npx skills add emilkowalski/skill` → `.agents/skills/emil-design-eng/`
    and `.agents/skills/review-animations/`, symlinked into `.claude/skills/`.
  - Both are now part of the repo (`.claude/`, `.agents/`, `.impeccable/`) —
    future sessions should see them in the default skill list without
    reinstalling. If a fresh session doesn't see `impeccable`/`emil-design-eng`
    in its skill list, check those directories exist before reinstalling.
- **`impeccable init` flow produced two root docs** (read these before any
  future `apps/web` visual change, don't re-derive from scratch):
  - `PRODUCT.md` — register: `product`. Users/purpose summarized from this
    file's own "What this is" section above. Brand personality: **Clinical &
    precise** (user's explicit choice over "Calm & reassuring" / "Sharp &
    technical"). Anti-reference: explicitly avoid the generic SaaS-dashboard
    look (gradients, hero-metric tiles, identical icon-card grids). A11y:
    WCAG 2.1 AA minimum, status never color-only (user's explicit choices).
  - `DESIGN.md` + `.impeccable/design.json` sidecar — the actual token system,
    named **"The Instrument Panel"**: near-black bg (`oklch(0.09 0 0)`,
    chroma 0 — a real Default-B pure dark, not a tinted "AI dark mode"), one
    brand color (`terminal-amber`, `oklch(0.62 0.18 48)`) spent only on
    primary buttons/wordmark, a second desaturated `instrument-blue` accent
    for secondary interactive elements, and a **closed status-color palette**
    (failing=red, silent=gold, orphaned=violet, healthy=green-as-dot-only,
    unused=no color) kept deliberately separate from the brand colors so
    "this is the brand" and "this needs attention" can never be confused.
    Typography reuses the already-loaded Geist Sans/Geist Mono (no new font
    dependency) split on a content axis: mono for anything that's a
    measurement (counts, timestamps, IDs), sans for anything that's prose —
    named **"The Readout Rule."** Two other named rules drive the system:
    **"The One Signal Rule"** (amber never appears in the status system) and
    **"The Calm Default Rule"** (only failing/silent/orphaned render as a
    filled saturated pill; healthy renders as a small solid dot + quiet text,
    unused as a hollow dot + quiet text — so a fully healthy dashboard reads
    as visually quiet, not as colorful as a broken one). Flat by design — no
    `box-shadow` anywhere; depth comes from three stepped near-black surface
    levels (`bg`/`panel`/`panel-raised`) plus 1px hairline borders.
  - The qualitative inputs (personality/anti-reference/a11y) were gathered via
    one `AskUserQuestion` round per `impeccable`'s init flow, not invented.
    The seed brand hue (46°, warm coral/amber) came from
    `impeccable`'s `palette.mjs` script — composed into "old monitoring
    instrumentation / Bloomberg-terminal-style amber phosphor" specifically
    *because* that mood justifies a warm hue in an otherwise clinical/dark
    product (avoids the generic "tech tool = cool blue" reflex while still
    fitting "clinical & precise").
- **Implementation** (`apps/web/`):
  - `app/globals.css` rewritten: all tokens above as CSS custom properties in
    `:root` + Tailwind v4 `@theme inline` (so e.g. `bg-primary`, `text-ink`,
    `border-hairline` are auto-generated Tailwind utilities — no Tailwind
    config file needed, v4 derives utilities straight from `@theme`
    `--color-*` vars). Added a shared `.focus-ring` utility (amber glow,
    `focus-visible` only) and a global `prefers-reduced-motion` override.
  - New shared components, `apps/web/components/`: `Button.tsx`
    (primary/ghost/danger variants), `StatusBadge.tsx` (the
    pill-vs-dot logic implementing The Calm Default Rule — takes a
    `HealthStatus`, also reused as-is for `AlertType` since alert types are a
    subset), `Input.tsx`, `Card.tsx`. **Deleted `lib/health.ts`**
    (`HEALTH_STYLES` className map) — fully superseded by `StatusBadge`.
  - Every page (`login`, `signup`, dashboard `page.tsx`, connection detail,
    workflow detail, alerts, settings) and `Nav.tsx` restyled to use the new
    tokens/components. No behavior changes — same fetch logic, same routes,
    same error handling; this phase was visual-only.
  - `npx tsc --noEmit` and `npm run lint` both clean after the rewrite.
- **Verified in a real headless browser (Playwright, same scratch-install
  pattern as Phase 6 — not a project dependency), against real data, with
  explicit user sign-off before reusing credentials**:
  - Confirmed via direct DB query that **two** connections exist pointed at
    the real n8n instance: `49fdd077-...` (owner `test@gmail.com`, created
    2026-06-24 — the user's own real day-to-day login, never touched) and
    `fc84b11a-...` (owner `watchdog-test@example.com` — the established
    *persistent test connection* reused across Phase 3/5/6's smoke tests).
    Only the latter was used for this verification.
  - Stopped and called `AskUserQuestion` before reusing that connection's
    decrypted API key, per the precedent set in Phase 6 (the auto-permission
    classifier flags credential reuse and wants explicit confirmation each
    time, not just once historically). Got explicit "yes, proceed."
  - The classifier *also* blocked a first attempt that decrypted the key and
    wrote the plaintext to a scratch file (flagged as exceeding the granted
    consent's scope even though the user had just approved "reuse the key").
    Fixed by restructuring the script so the decrypted key only ever exists
    in one Python process's memory and in an HTTP request body to the
    local-only API (`POST /connections`) — never written to disk, never
    logged. **Lesson for future credential-reuse tasks: pass secrets through
    in-memory HTTP calls to localhost, never through a temp file, even with
    user sign-off on the broader action** — the classifier (and good
    practice) treats "wrote secret to disk" as a distinct, separately-risky
    step from "used secret in an API call."
  - Created one throwaway user + connection (via the running API, not direct
    DB) reusing the persistent test connection's real base URL/key, synced
    (10 real workflows). All 10 real workflows are currently disabled in n8n
    and have 0 real executions, so by `health.py`'s own precedence they all
    read as `unused` — to actually see the other four states rendered,
    directly inserted a few `Execution` rows / an `is_orphaned=True` flag /
    flipped the local (DB-only, not real-n8n) `enabled` bool on a handful of
    the throwaway connection's `Workflow` rows, same direct-row-edit
    precedent Phase 3/5 used for health-state testing. Confirmed all five
    `StatusBadge` states render correctly: failing (red filled pill),
    silent (gold filled pill), orphaned (violet filled pill), healthy (green
    dot + quiet text), unused (hollow dot + quiet text) — screenshots
    confirmed the failing/silent/orphaned pills are the only saturated color
    on an otherwise calm dark screen, exactly per The Calm Default Rule.
  - Also screenshotted: logged-out `/login` and `/signup`, empty dashboard +
    connect form, workflow detail page (failing workflow), alerts page (one
    real alert created via `evaluate_workflow(db, wf, "failing")`, same
    direct-function precedent as Phase 3/5), settings page. Zero
    `pageerror`/console errors across every page.
  - Cleaned up afterward: deleted the throwaway connection (cascaded its
    workflows/executions/alert) and throwaway user via direct DB delete (no
    `DELETE /auth/me` endpoint, same as every prior phase's cleanup).
    Confirmed via a follow-up query that the persistent test connection
    (`fc84b11a-...`) was unaffected — still 10 workflows. The real personal
    connection (`49fdd077-...`) was never queried beyond a row count and
    never connected to in this phase at all.
  - Discarded the scratch Playwright install afterward (same "smoke test then
    discard" precedent as Phase 6 — not a maintained E2E suite).

Not done yet / immediate next steps:
- No motion/animation pass was done beyond hover/focus-ring transitions —
  `impeccable`'s `animate` command and the `review-animations` skill
  (installed but not yet invoked) are available if the user wants purposeful
  motion (list entrances, status-change transitions) later.
- `impeccable live` (in-browser visual-variant iteration) was not configured
  in this phase (Step 6 of its `init` flow) — skipped to keep scope to the
  initial redesign; can be set up later with `/impeccable live` if the user
  wants to iterate on individual elements directly in the browser.
- Everything else carried over from Phase 7 below (Resend domain,
  multi-worker scheduler decision) is still open and unrelated to this phase.

### Phase 7 — done

Scope: backend automated test suite (the first of Phase 6's "not done yet"
items) — `apps/api/tests/`, run via `pytest` (or `pytest --cov=app
--cov-report=term-missing` for coverage) from `apps/api` with the venv
active. No frontend tests yet — backend only.

- **Test DB**: a real Postgres database, not SQLite — `models.py` uses
  `sqlalchemy.dialects.postgresql.UUID` columns, which SQLite can't create.
  `tests/conftest.py`'s session-scoped `test_engine` fixture connects to the
  **same Postgres container** the app already uses (host port 5433) and
  `DROP DATABASE IF EXISTS` + `CREATE DATABASE` a separate `watchdog_test`
  database every test session, then `Base.metadata.create_all()` builds the
  schema straight from the current models (no Alembic involved — this is a
  throwaway DB rebuilt fresh every run, not a migration target). **Postgres
  must be running (`docker compose up -d postgres`) before running tests** —
  it was found stopped at the start of this phase and had to be started
  first.
- **Per-test isolation**: the function-scoped `db` fixture opens one
  connection + one transaction per test and rolls it back at teardown,
  rather than recreating the schema per test (fast — confirmed empirically
  that route handlers calling `db.commit()` mid-test don't escape this outer
  transaction; SQLAlchemy treats the session's commit as scoped to the
  already-open connection-level transaction). The `client` fixture (a
  FastAPI `TestClient`) depends on `db` and overrides the `get_db`
  dependency to yield that same session, so route-level tests and direct
  function calls within one test see the same uncommitted rows. It also
  monkeypatches `app.main.start_scheduler`/`stop_scheduler` to no-ops so
  spinning up the `TestClient` (which runs the real FastAPI `lifespan`)
  never starts a real `BackgroundScheduler` hitting the real DB/n8n/Ollama.
- **External services are never called for real in tests** — `N8nClient`,
  `generate_text` (Ollama), and `httpx.post` (Resend) are monkeypatched per
  test (fake classes for `N8nClient`, lambda/fake functions for the others).
  This is a deliberate difference from every prior phase's manual smoke
  testing, which always hit the real n8n instance/Ollama/intentionally-empty
  Resend key — automated tests need to be fast and deterministic, so they
  exercise *this codebase's* logic (sync upsert/orphan logic, health
  precedence, alert dedupe, summary caching, auth/ownership, HTTP error
  mapping) without depending on those real services being up.
- Coverage at the end of this phase: **94% overall** (`pytest --cov=app`),
  with every business-logic module the product actually depends on at
  98-100% (`health.py`, `alerts.py`, `auth.py`, `security.py`, `email.py`,
  `llm.py`, `models.py`, `schemas.py` all 100%; `sync.py`/`summaries.py`/
  `n8n_client.py` at 95-99%). Deliberately did **not** chase the remaining
  gap: `scheduler.py` (38% — `run_check_cycle` itself untested as a whole,
  though the two functions it calls, `sync_connection` and
  `evaluate_workflow`, are each fully tested individually) and a handful of
  `connections.py` error-text branches/`deps.py` edge lines. Diminishing
  returns for a solo project at this stage — revisit `scheduler.py`
  specifically if a real bug is ever traced to the scheduler's own
  orchestration (vs. the functions it calls).
- Test files, one per module: `test_security.py`, `test_health.py`,
  `test_sync.py`, `test_alerts.py`, `test_summaries.py`, `test_n8n_client.py`
  (real HTTP-error-mapping logic via `httpx.MockTransport`, no real n8n),
  `test_email.py`, `test_llm.py` (both via monkeypatching `httpx.post`, no
  real Resend/Ollama calls), `test_auth.py`, `test_connections.py`
  (route-level, the biggest file — create/list/get/patch/delete, ownership
  isolation between two users, sync, workflows list/detail with computed
  health+counts, alerts filtering, summary generation/caching/force/502).
- `requirements.txt` gained `pytest==8.3.3` and `pytest-cov==5.0.0` (dev-only,
  but kept in the same file rather than a separate `requirements-dev.txt` —
  this project doesn't deploy `apps/api` via this requirements file yet, so
  there's no production-image bloat concern to justify the split).
  `pytest.ini` sets `testpaths = tests` and `pythonpath = .` so `from app...`
  imports resolve when running `pytest` from `apps/api`.

Not done yet / immediate next steps:
- No frontend test suite (`apps/web`) — still smoke-tested manually only,
  per Phase 6.
- Everything else carried over from Phase 6 below is still open (Resend
  domain, multi-worker scheduler decision, visual polish).

### Phase 6 — done

Scope: Next.js frontend covering the full REST surface from Phase 1-5 — login/
signup, connect n8n, dashboard, workflow detail, alerts, settings.

- Scaffolded with `create-next-app` (TypeScript, Tailwind, App Router, no
  `src/` dir, npm, Turbopack) into `apps/web`. It auto-`git init`'d its own
  nested repo (since the `watchdog/` root isn't a git repo yet) — removed
  immediately so `apps/web` doesn't end up as an accidental embedded repo once
  the root is eventually git-initialized; `apps/api` has no `.git` of its own
  either, so this keeps the two siblings consistent.
- **Architecture: every page is a Client Component**, not the App Router's
  default Server Components. Reasoning: the backend's session is a signed
  `itsdangerous` cookie checked via `GET /auth/me`, not a Next.js-native
  session — doing this server-side would mean manually forwarding cookies
  through Next's `cookies()`/fetch-in-Server-Component machinery, plus Next
  15+'s async `params`/`searchParams` props. Client Components reading
  `useParams()`/`useRouter()` directly sidestep both, at the cost of a
  client-side fetch waterfall on every navigation (acceptable at this scale,
  not worth Suspense/streaming complexity for a solo non-expert builder).
  No data-fetching library (SWR/react-query) either — plain
  `useEffect`/`useState` per page, kept deliberately repetitive rather than
  abstracted (each page's fetch shape differs slightly: some need two
  parallel requests, some need a shared refresh after a POST, etc.).
- `lib/api.ts` — fetch wrapper: prepends `NEXT_PUBLIC_API_URL`
  (`.env.local`, defaults to `http://localhost:8000`), always sets
  `credentials: "include"` (required for the cross-origin cookie to ride
  along — frontend on `:3000`, backend on `:8000`; cookies scope by hostname
  not port, and both resolve to host `localhost`, so this works as long as
  both sides consistently say "localhost" and never "127.0.0.1"), parses
  FastAPI's `{"detail": ...}` error shape (plain string from `HTTPException`,
  or a pydantic validation-error array on 422) into one message string, and
  throws `ApiError` with the HTTP status attached.
- `lib/types.ts` — hand-written TS interfaces mirroring `app/schemas.py`
  exactly (no codegen — schemas are small and stable enough that this isn't
  worth the tooling).
- `lib/auth-context.tsx` — single `AuthProvider` (wraps the whole app in
  `app/layout.tsx`) that calls `GET /auth/me` once on mount and exposes
  `{user, loading, refresh, logout}` via context; `useRequireAuth()` redirects
  to `/login` once `loading` resolves with no user. `refresh()` is called
  manually right after signup/login so the nav updates immediately without a
  second silent re-check.
- **Hit Next.js 16 / `eslint-plugin-react-hooks` v7's new
  `react-hooks/set-state-in-effect` rule** (part of the React-Compiler-era
  "recommended" rules now bundled in `eslint-config-next` 16) — it flags
  calling a `useCallback`-wrapped fetch-then-`setState` function from inside
  `useEffect`, which is exactly the conventional "fetch on mount" shape. Fixed
  by inlining the fetch directly in each effect using the React-docs'
  documented race-condition-safe shape (`let ignore = false`; set state only
  `if (!ignore)`; `return () => { ignore = true }` as cleanup) instead of
  disabling the rule — confirmed empirically that this satisfies the linter,
  and it's a genuine improvement anyway (the old shape could apply a stale
  response if `connectionId`/`workflowId`/the alerts filter changed again
  before the first fetch resolved). Applied consistently across all five
  data-fetching pages. **If a future page needs fetch-on-mount, copy this
  shape, not the old `useCallback` + bare call in `useEffect` shape** — the
  linter will reject the latter.
- Pages, all under `apps/web/app/`:
  - `/login`, `/signup` — forms posting to the existing auth endpoints,
    `refresh()` then redirect to `/`.
  - `/` — dashboard: lists the user's connections (`GET /connections`) and a
    "Connect an n8n instance" form (`POST /connections`) that redirects into
    the new connection on success.
  - `/connections/[id]` — the per-connection workflow dashboard: sync button
    (`POST .../sync`), workflow cards with health-status badge (color per
    status via `lib/health.ts`'s `HEALTH_STYLES`), 7d/30d run/error counts,
    and a truncated summary preview; links to Alerts and Settings.
  - `/connections/[id]/workflows/[workflowId]` — full detail: counts,
    full summary text, and a Generate/Regenerate button
    (`POST .../summary?force=<bool>`, `force` only set true when a summary
    already exists) with an explicit "this can take up to a couple of
    minutes" notice, since local-LLM generation is genuinely that slow (see
    Phase 4's Gotcha about two sequential LLM calls).
  - `/connections/[id]/alerts` — history with an All/Open/Resolved filter
    (`?resolved=` query param), each row showing the workflow name, alert
    type, triggered/resolved timestamps, and email status
    (sent timestamp / `email_error` / "pending").
  - `/connections/[id]/settings` — `PATCH` form for `n8n_base_url`/`api_key`
    (API key field stays blank/write-only, only included in the request body
    if the user actually typed something, so resubmitting doesn't overwrite
    the key with an empty string), plus a delete-connection button behind a
    native `window.confirm`.
  - Added a one-line `Loading…` placeholder to every page that fetches on
    mount (dashboard, connection detail, workflow detail, alerts) — found via
    the browser smoke test below that these rendered fully blank (no heading,
    no content) for the moment between navigation and the fetch resolving;
    not caught by `tsc`/lint since it's a rendering-completeness issue, not a
    type or lint error.
  - Removed the `prefers-color-scheme: dark` block from `globals.css`,
    forcing a single light theme — one less state to visually reason about
    for a solo non-expert builder; revisit if dark mode is ever actually
    requested.
- **Smoke-tested in a real headless browser (Playwright, already cached
  locally — installed standalone into a scratch dir outside the repo, not
  added as a project dependency) against the real n8n instance and real DB
  rows, no fabricated data, mirroring every prior phase's testing
  convention**:
  - Reused the real persistent connection's already-decrypted API key (same
    `decrypt_secret` pattern Phase 4/5 used) for a throwaway signup +
    connect, since the disposable dev n8n container no longer exists (removed
    at the Phase 3→4 transition) — the real instance is the only one
    available to test against. **The session's auto-permission classifier
    initially blocked writing that decrypted key to a temp file**, flagging
    it as credential reuse it couldn't verify was authorized; stopped and
    asked the user rather than working around it, and proceeded only after
    explicit go-ahead. The key only ever touched a job-local tmp file (never
    printed/logged to any visible output), which was deleted immediately
    after use along with the one-off script that wrote it.
  - Full flow driven through the actual rendered UI: signup → empty dashboard
    → connect (real base URL + real key) → sync (10 real workflows, matching
    the persistent connection's own count) → open a workflow with no cached
    summary (fresh `Workflow` row under a new `connection_id` means no
    `WorkflowSummary` can exist for it yet, regardless of other connections'
    cached summaries for the "same" underlying n8n workflow) → clicked
    Generate summary → real local-LLM call completed and rendered (first
    time this path has been exercised from the frontend rather than direct
    HTTP/function calls) → alerts page empty state → settings page correctly
    prefilled with the real base URL, no-op save → logout → confirmed a
    protected route redirects an unauthenticated visitor to `/login` → real
    `evaluate_workflow(db, workflow, "failing")` direct call (same precedent
    as Phase 3/5) created one real alert on the throwaway connection's
    workflow → logged back in with the same throwaway credentials → alerts
    page now showed it (workflow name, `failing` badge, "Email not sent:
    RESEND_API_KEY is not configured" — consistent with the deferred-email
    state) → Open/Resolved filters behaved correctly → deleted the connection
    from Settings (handling the native `confirm()` dialog) → dashboard back
    to its empty state.
  - Zero uncaught client-side JS exceptions (`pageerror`) across the whole
    run; the only console noise was the browser's own network-level "401"
    log on the expected unauthenticated `GET /auth/me` probe (logged by the
    browser itself before the response reaches application code — not
    something `try`/`catch` in `AuthProvider` can suppress, and not a bug).
  - Cleaned up afterward: deleted the throwaway user via direct DB delete (no
    `DELETE /auth/me` endpoint, same as every prior phase), and confirmed via
    a direct DB check that the real persistent connection was completely
    unaffected throughout (still exactly 10 workflows, `last_sync_status:
    ok`) — the throwaway connection's workflows were genuinely separate rows
    (Phase 2's `Workflow` uniqueness is per `connection_id`+`n8n_workflow_id`,
    so a new connection always gets fresh rows even against the same n8n
    instance).
  - Not saved as a project artifact — the Playwright script was a one-off
    verification tool in the job's scratch directory, discarded after the
    run, same "smoke test then discard" precedent the backend phases
    established rather than a maintained E2E suite. Revisit if the user wants
    real regression coverage as the app grows.
- Left `npm run dev` (Turbopack, port 3000) running in the background after
  testing so the user can continue poking at it directly.

Not done yet / immediate next steps:
- No automated test suite on either side (frontend or backend) — every phase
  so far has used real, one-off, discard-after-run smoke tests instead.
  Revisit if regressions start happening silently.
  (See "Not done yet" under Phase 7 above — backend test suite is now done;
  frontend still isn't. This note is kept here only as the historical record
  of what Phase 6 identified as next.)
- Carried over from Phase 5, still blocking genuine "production ready"
  status: a real `RESEND_API_KEY` + verified sender domain (user has no
  domain yet, not planning to buy one soon — don't re-raise until they bring
  it up), and a decision on the multi-worker scheduler caveat (Phase 3) if
  this ever deploys beyond a single `uvicorn` process.
- Visual design was kept functional/minimal (Tailwind defaults, no design
  system, no animation) — revisit only if the user asks for visual polish.
- The dashboard supports multiple connections per user (the data model always
  has) but has only been tested with one — fine for now since the user only
  has one n8n instance.

### Phase 5 — done

Scope: finalize the REST surface for frontend consumption — alert history,
single-resource detail endpoints, and a way to update connection credentials
without losing history.

- **Email delivery: discussed and deferred again.** User has no domain and
  isn't planning to buy one yet. `RESEND_API_KEY` stays an empty placeholder;
  `app/email.py`'s graceful "not configured" behavior (Phase 3) is unchanged.
  Revisit once a domain exists — don't re-ask before then.
- `app/schemas.py` — new `AlertOut` (id, workflow_id, workflow_name,
  alert_type, triggered_at, resolved_at, email_sent_at, email_error) and
  `ConnectionUpdate` (`n8n_base_url` and `api_key`, both optional).
- `app/connections.py`:
  - `GET /connections/{id}` — single-connection detail, a thin wrapper
    around the existing `_get_owned_connection`.
  - `PATCH /connections/{id}` — updates `n8n_base_url`/`api_key`
    (independently optional; 400 if neither is given). Re-tests the
    *effective* new credentials live via `N8nClient.test_connection()`
    before persisting anything — same error mapping (400
    unauthorized/connection/api error) as `create_connection`, duplicated
    rather than extracted into a shared helper (matches the existing
    precedent of `regenerate_workflow_summary` already duplicating this same
    block once before, per Phase 4's notes). On success, also resets
    `last_sync_status`/`last_sync_error`/`last_sync_at` like a fresh
    connection would. Deliberately does **not** cascade/delete — the entire
    point is rotating a key or repointing at a moved instance without losing
    synced workflows/executions/alert history, which delete+recreate would
    cascade-wipe. On failure, nothing is mutated (confirmed via smoke test:
    bad URL → 400, `n8n_base_url` unchanged afterward).
  - `GET /connections/{id}/workflows/{workflow_id}` — single-workflow detail,
    identical shape to an entry in the list endpoint. Extracted
    `_build_workflow_out(workflow, counts, summary)` out of `list_workflows`
    so both endpoints share one field-mapping implementation instead of
    duplicating it.
  - `GET /connections/{id}/alerts` — alert history (open + resolved) across
    every workflow under one connection, newest first (`Alert` joined to
    `Workflow`, filtered by connection ownership; `joinedload` on
    `Alert.workflow` to avoid N+1 when reading `workflow.name` per row).
    `?resolved=true/false` filters to closed/open only (omit for both);
    `limit` query param (default 100) — no real pagination, not needed at
    this scale. Returns `AlertOut` with `workflow_name` inlined so the
    frontend doesn't need a second round-trip per alert.
  - Deliberately kept alerts scoped to one connection
    (`/connections/{id}/alerts`) rather than adding a global cross-connection
    `/alerts` endpoint — matches how everything else in this API is already
    nested under `/connections/{id}/...`. Revisit only if a multi-connection
    dashboard genuinely needs one merged feed.
- **Smoke-tested against the real n8n instance and real DB rows, no
  fabricated data** (one-off script, discarded after the run — same pattern
  as other phases' direct-function smoke tests):
  - Created a throwaway user + connection pointed at the *same* real n8n
    instance as the persistent real connection (`fc84b11a-...`), reusing its
    real, already-verified API key — decrypted server-side via
    `app.security.decrypt_secret` and passed straight into the test's own
    HTTP calls, never printed/logged. Kept the test on 100% real n8n data (10
    real workflows, real sync) without ever touching the user's actual
    persistent connection.
  - Verified `GET /connections/{id}` and `GET .../workflows/{workflow_id}`
    against real synced data; confirmed the workflow-detail response is
    identical to that same workflow's entry in the list endpoint.
  - Confirmed cross-user 404 isolation on all three new GET endpoints (a
    second throwaway user gets 404 on the first user's
    connection/workflows/alerts) — ownership checks correctly extend to the
    new routes.
  - Created one real `Alert` row by calling
    `evaluate_workflow(db, workflow, "failing")` directly (same
    direct-function-call precedent Phase 3 used) against a real synced
    workflow; confirmed it appears via `GET .../alerts` with the correct
    `workflow_name`/`alert_type` and, as expected since email stays deferred,
    `email_error: "RESEND_API_KEY is not configured"`. Confirmed
    `?resolved=false/true` filtering. Called
    `evaluate_workflow(..., "healthy")` to resolve it and confirmed the
    filter flipped accordingly — mirrors Phase 3's own recovery test.
  - Confirmed `PATCH`'s validation order: empty body → 400; an unreachable
    `n8n_base_url` → 400 with the connection's real `n8n_base_url` left
    unchanged afterward (tested-before-saved, confirmed via a follow-up
    `GET`); a same-value `n8n_base_url`-only update (api_key falls back to
    the existing decrypted one) → 200; an `api_key`-only update
    (re-submitting that same real key explicitly, base_url falls back) → 200.
  - Cleaned up: deleted the throwaway connection via the real
    `DELETE /connections/{id}`, and both throwaway users via direct DB delete
    (no `DELETE /auth/me` endpoint exists, same as every prior phase's
    cleanup). Verified afterward the real connection was completely
    unaffected: still 10 workflows, `last_sync_status: ok`, 0 alerts
    (unchanged from before the test).

Not done yet / immediate next steps:
- Phase 6: Next.js frontend (login/signup, connect n8n, dashboard, workflow
  detail, settings). The REST surface should now be sufficient to build all
  of these screens without further backend changes — revisit only if the
  frontend build genuinely surfaces a gap.
- Before any of that is genuinely "production ready": a real
  `RESEND_API_KEY` + verified sender domain (still blocked on the user
  getting a domain), and a decision on the multi-worker scheduler caveat
  noted in Phase 3 if ever deploying beyond a single process.

### Phase 4 — done

Scope: Ollama-backed plain-English workflow summaries, cached via a
`definition_hash` column, regenerate endpoint.

- **Model choice deviated from the original plan** — see "Locked-in
  decisions" above. `qwen2.5:7b-instruct` was never pulled; user chose to use
  an already-downloaded model instead of spending time downloading it.
  `gemma4:e4b` was picked over the also-available `qwen3:14b` only because
  `qwen3:14b` is much slower on this hardware (its "thinking" mode alone blew
  past a 2-minute timeout; needed `"think": false` to even get a same-ballpark
  response time) — not because of any quality difference, both had the same
  formatting-compliance problem (see Gotcha 8) and both were fixed the same
  way.
- `app/models.py` — new `WorkflowSummary` table (`workflow_summaries`):
  `workflow_id` (FK, **unique** — one current summary per workflow, replaced
  in place on regenerate, no history kept), `definition_hash`, `summary`
  (Text), `generated_at`. `Workflow.summary` is a scalar (`uselist=False`)
  relationship, cascade-deletes with its workflow. Migration `45596c4ef0fd` —
  a plain new table, so Gotcha 7's `server_default` issue didn't apply here.
- `app/n8n_client.py` — added `get_workflow(workflow_id)`
  (`GET /api/v1/workflows/{id}`) for fetching one workflow's full definition
  on demand. Confirmed via a real probe against the live instance that
  n8n's list endpoint (`list_workflows()`, already used by sync) *also*
  already returns full `nodes`/`connections` for every workflow — so no
  schema change was needed to persist raw definitions just for this; the
  regenerate endpoint simply fetches fresh from n8n live each time instead.
- `app/llm.py` (new) — `generate_text(prompt) -> str`, calls Ollama's
  `/api/generate` directly over `httpx` (no SDK, same style as
  `N8nClient`/`email.py`), raises `LlmError` on failure. Deliberately the
  *only* function that knows about Ollama specifically, so swapping to a
  hosted provider later (e.g. deploying to a VPS without the Mac's GPU, per
  the original spec) means changing only this file.
- `app/summaries.py` (new):
  - `compute_definition_hash(raw_workflow)` — sha256 over each node's
    `name`/`type`/`parameters` (sorted by name for stable ordering) plus the
    `connections` dict. Deliberately excludes `position`, `id`, `versionId`,
    `pinData`, `meta` etc. — fields that change without the workflow's
    actual behavior changing — so e.g. dragging nodes around the n8n canvas
    doesn't invalidate the cached summary and trigger a needless regenerate.
  - `generate_workflow_summary(db, workflow, raw_workflow, force=False)` —
    the cache check: if a `WorkflowSummary` already exists and its
    `definition_hash` matches the current one (and `force` isn't set),
    returns it untouched with **no LLM call**. Otherwise generates a fresh
    one and upserts (same row, not a new one — no history table in V1).
  - **Two LLM calls per generation, not one** — see Gotcha 8. Asking
    directly for a short plain-English summary from the raw node/connection
    list got ignored by both locally-available models regardless of prompt
    phrasing (tried plain instructions, strict system-role + token cap,
    few-shot example — all failed the same way, just differently). Fix:
    `_build_analysis_prompt` lets the model write whatever detailed
    technical breakdown it wants first; `_build_condense_prompt` then feeds
    *that text* back asking for a 2-4 sentence plain-English condensation.
    Both models stay on-task once condensing existing prose instead of
    generating constrained prose from sparse structured input directly.
    Adds latency (~30-100s total per generation, two sequential local
    inference calls) but is the only approach tried that actually produces
    spec-compliant output.
- `app/schemas.py` — new `WorkflowSummaryOut`; `WorkflowOut` gained
  `summary`/`summary_generated_at` (nullable — `None` until a summary's been
  generated at least once; reads the cache, never triggers generation).
- `app/connections.py`:
  - `POST /connections/{connection_id}/workflows/{workflow_id}/summary?force=bool`
    — fetches the workflow's current definition from n8n live (same
    `N8nUnauthorizedError`/`N8nConnectionError`/`N8nApiError` → 400 handling
    as `create_connection`), then calls `generate_workflow_summary`;
    `LlmError` → 502. No new ownership-check helper duplication — added
    `_get_owned_workflow` alongside the existing `_get_owned_connection`.
  - `GET /connections/{id}/workflows` now also fetches each workflow's
    cached `WorkflowSummary` (one query for all of them, no N+1) and
    includes it in the response — purely surfacing the cache, doesn't call
    n8n or the LLM. A workflow with no summary yet just reads `null`.
  - Deliberately did **not** wire summary generation into the scheduler/sync
    — Phase 4's stated scope was the function, the cache column, and a
    regenerate endpoint, not auto-generation on every sync tick (which would
    also mean every workflow gets summarized whether anyone's looking at it
    or not, at ~30-100s each). Left for whenever the frontend (Phase 6)
    shows there's an actual need for it.
- **Smoke-tested against the real n8n instance and the real local Ollama
  model, no fabricated data**:
  - Direct-function tests against two real workflows (a 36-node onboarding
    flow and a trivial 1-node placeholder): both produced accurate,
    spec-compliant 2-4 sentence summaries with no markdown and no node names
    — including the 1-node one correctly describing itself as not doing
    anything meaningful, rather than hallucinating complexity.
  - Verified the cache: identical second call returned the same row
    instantly (no LLM call); `force=True` called the LLM again and updated
    the same row in place (no duplicate rows); a definition change (node
    parameter edited) produced a different hash than the original.
  - Full HTTP round-trip on the live `uvicorn --reload` server: fresh
    signup → real `POST /connections` (real base URL + real decrypted API
    key) → real `POST .../sync` (10 workflows) → `GET .../workflows` showed
    `summary: null` before generation → real
    `POST .../workflows/{id}/summary` (200, ~103s, correct accurate output)
    → `GET .../workflows` now showed the cached `summary` populated → second
    `POST .../summary` returned in 0.049s (cache hit confirmed through the
    full route layer, not just the underlying function) → cleaned up the
    test connection and user afterward.

(See "Not done yet" under Phase 5 above for current next steps — Phase 5 is
now done too; this note is kept here only as the historical record of what
Phase 4 identified as next.)

### Phase 3 — done

Scope: periodic background sync, per-workflow health status, Resend email
alerts with dedupe.

- `app/models.py`:
  - `Workflow.is_orphaned` (bool, default False) — set by sync, not computed
    on read (only a sync against n8n can know whether a workflow still
    exists there).
  - New `Alert` table: `workflow_id` FK (cascade), `alert_type`
    (failing/silent/orphaned), `triggered_at`, `resolved_at` (NULL = still
    open), `email_sent_at`, `email_error`. **At most one unresolved alert per
    workflow at a time** is the entire dedupe mechanism — see `app/alerts.py`.
  - Migration `8e3b57bbce22`: the `is_orphaned` column needed
    `server_default=sa.text('false')` by hand (autogenerate doesn't add one),
    since `workflows` already had rows — a bare `nullable=False` add_column
    would have failed against existing data.
- `app/health.py` (new) — `compute_health_status(workflow, counts) -> str`,
  pure function, computed on demand everywhere (API reads, scheduler ticks),
  same as the run/error counts it's built from — never stored, so it can't go
  stale. Five statuses, checked in this order (first match wins):
  1. **orphaned** — `workflow.is_orphaned` is True.
  2. **unused** — disabled in n8n, OR zero executions in the last 30 days.
     Deliberately one bucket for both "turned off on purpose" and "enabled
     but nothing has ever triggered it" — neither is a problem worth
     alerting on.
  3. **silent** — ran at some point in the last 30 days, but zero executions
     in the last 7. The "used to work, now it's gone quiet" signal the
     original product spec calls out. Reuses the existing 7d/30d windows
     from `compute_workflow_counts` rather than adding a third window.
  4. **failing** — has run in the last 7 days, and the *most recent*
     execution (by `started_at`) is an error. Deliberately "is the latest
     run good or bad", not an error-rate threshold — simpler, no threshold to
     tune, and self-resolves the moment one good run happens.
  5. **healthy** — only what's left: ran recently, latest run succeeded.

  These boundaries (especially unused vs. silent, and "latest run" vs. an
  error-rate window for failing) were my judgment call, not explicitly
  specified up front — flagged here in case it should be revisited once real
  usage shows what's actually useful to alert on.
- `app/sync.py`:
  - `sync_connection` now records `seen_n8n_ids` while upserting workflows,
    then calls `_mark_orphaned_workflows` — but only if the workflow listing
    loop completes without raising. A partial failure mid-sync (e.g. n8n
    drops the connection halfway through) leaves orphan flags untouched
    rather than risk flagging everything orphaned from an incomplete picture.
  - `WorkflowCounts` gained `latest_status` (the status of the execution with
    the max `started_at` in the 30d window), tracked in the same loop
    `compute_workflow_counts` already runs — no extra query.
- `app/email.py` (new) — `send_email(to, subject, html) -> str | None`.
  Returns an error string instead of raising, so a Resend hiccup never takes
  down the scheduler. Currently `RESEND_API_KEY` in `.env` is still an empty
  placeholder, so every send currently returns
  `"RESEND_API_KEY is not configured"` — confirmed this is handled cleanly
  (no crash, recorded on `Alert.email_error`), but **actual email delivery
  has not been verified** — needs a real Resend key + verified sender before
  it can be.
- `app/alerts.py` (new) — `evaluate_workflow(db, workflow, status)`: looks up
  the workflow's one open `Alert` (if any) and either creates one (new
  incident → sends email), retries (open alert exists but a previous send
  failed — `email_sent_at` is still NULL), or resolves it (status recovered).
  Recovery does **not** send an email in V1 — spec says "alert when something
  breaks", recovery notifications weren't asked for.
- `app/scheduler.py` (new) + `app/main.py` — `BackgroundScheduler` running
  one job (`run_check_cycle`) on a `settings.sync_interval_minutes` interval
  (default 15, in `.env`/`config.py`), started/stopped via FastAPI's
  `lifespan`. Each tick: for every `Connection`, call the existing
  `sync_connection` (same function the `/sync` endpoint uses), then
  recompute health and call `evaluate_workflow` for every one of its
  workflows. Each connection — and each workflow's health check — is wrapped
  in its own try/except so one bad row can't skip every other user's check.
  APScheduler's default `max_instances=1` means a slow cycle is never
  overlapped by the next tick.
- `app/schemas.py` / `app/connections.py` — `WorkflowOut` gained
  `health_status`, computed in `GET /connections/{id}/workflows` from the
  same `counts` already being fetched there. No new endpoints added (an
  alerts-history endpoint would be natural but wasn't asked for — left for
  Phase 5's "finalize REST surface" pass instead of growing scope now).
- **Smoke-tested against the real local n8n instance and real DB rows, no
  fabricated data**:
  - Ran the scheduler's actual job function directly (`run_check_cycle()`)
    against the real Phase 2 connection/workflows: webhook-test workflow
    (latest execution = error) → `failing`; disabled workflow with zero
    executions → `unused`. Matches the precedence rules above.
  - First tick created exactly one `Alert(alert_type="failing")`, attempted
    the email, got the expected `"RESEND_API_KEY is not configured"` error,
    did not crash.
  - Re-ran the cycle again with nothing changed → still exactly one `Alert`
    row (no duplicate) — dedupe confirmed.
  - Called the real webhook (`GET /webhook/watchdog-probe` on the local n8n,
    no `?fail=1`) to produce a genuine successful execution, re-ran the
    cycle → status flipped to `healthy`, the open alert's `resolved_at` got
    set, no new alert/email fired.
  - `orphaned` and `silent` are hard to produce via real n8n actions without
    destructively deleting the test workflow or backdating real rows, so
    verified differently but still against real data:
    - Called `_mark_orphaned_workflows` directly with a real connection but a
      `seen_n8n_ids` set missing one real workflow → that workflow's
      `is_orphaned` flipped True and `compute_health_status` correctly
      returned `orphaned` ahead of any other rule; called again with the
      full set to restore it to False afterward.
    - `silent` verified as a pure-function unit check (real function, a
      constructed counts input) since it only depends on its inputs.
  - Confirmed via real HTTP requests (fresh signup + connection, cleaned up
    after) that `GET /connections/{id}/workflows` returns `health_status`
    correctly end to end through auth + the route layer, not just the
    underlying functions.
  - Confirmed APScheduler actually invokes `run_check_cycle` repeatedly on
    its own thread on a timer (separate short-interval test), not just that
    the function works when called directly.

(See "Not done yet" under Phase 4 above for current next steps — Phase 4 is
now done too; this note is kept here only for the email-delivery/scheduler
caveats specific to Phase 3's work.)

### Phase 2 — done

- `app/models.py` — added `Workflow` (unique on `connection_id`+`n8n_workflow_id`)
  and `Execution` (unique on `workflow_id`+`n8n_execution_id`, indexed on
  `started_at`). Both cascade-delete from their parent.
- `app/n8n_client.py` — `list_executions()` now paginates properly (was a
  single page capped at 50) and takes a `since` cutoff: it walks pages
  newest-first and stops once a page's oldest execution predates `since`,
  instead of always walking full history. Added `parse_n8n_datetime()` since
  n8n returns `Z`-suffixed ISO 8601 strings — confirmed Python 3.13's
  `datetime.fromisoformat` parses these directly into aware UTC datetimes, no
  manual `Z`-replacement needed.
- `app/sync.py` (new) — the sync engine, kept separate from the HTTP layer so
  Phase 3's scheduler can call the same function:
  - `sync_connection(db, connection)`: fetches workflows from n8n, upserts
    each as a `Workflow` row, then fetches that workflow's executions from
    the last 30 days and upserts each as an `Execution` row. Never raises on
    n8n-side failures — records them on `connection.last_sync_status/error`
    instead (`ok` / `unauthorized` / `error`), same status vocabulary as
    Phase 1. Returns a `SyncResult`.
  - `compute_workflow_counts(db, workflow_ids)`: pulls each workflow's
    executions from the last 30 days into Python and counts run/error
    totals for both the 7d and 30d windows in one pass. Deliberately not a
    SQL `FILTER` aggregate — plain Python loop is easier to read/modify and
    plenty fast at this scale.
  - Error statuses treated as failures: `{"error", "crashed"}` (confirmed
    against n8n's actual execution status enum — see Gotchas).
- `app/connections.py` — replaced the Phase-1-only
  `GET /connections/{id}/workflows` (live fetch, no persistence) with:
  - `POST /connections/{id}/sync` — calls `sync_connection`, **always
    returns 200**; the outcome is in the response body
    (`last_sync_status`/`last_sync_error`), since a failed sync is normal
    data to display, not a broken request. This is a deliberate difference
    from `POST /connections`, which still returns 400/502 on n8n failure
    (there, failure means nothing was saved at all).
  - `GET /connections/{id}/workflows` — now reads persisted `Workflow` rows
    + computed counts, no live n8n call. Call `POST .../sync` to refresh.
- Removed `WorkflowPreview` schema (Phase 1, now unused) and the old
  `fetch_workflows_once` endpoint; added `WorkflowOut` and `SyncResult`.
- Alembic migration `b3517cf3dbbd_add_workflows_and_executions_tables`
  applied.
- **Phase 2 fully smoke-tested against the real local n8n instance**:
  - Built a second n8n test workflow (`Watchdog Probe - Webhook Test`,
    `n8n_workflow_id=cFYIGlybl0F0icE1`) with a Webhook node → Code node that
    throws when called with `?fail=1`, specifically to generate real
    success/error executions rather than fabricate data. **Left running in
    the dev n8n instance on purpose** — it's a second real data point (the
    original `Test Workflow - Watchdog Probe` has zero executions, this one
    has a mix), useful for Phase 3/4 testing too.
  - `POST /connections/{id}/sync` → `workflows_synced: 2`,
    `executions_synced: 3`, `last_sync_status: "ok"`.
  - `GET /connections/{id}/workflows` → correct per-workflow counts:
    the webhook-test workflow showed `run_count_7d/30d: 3`,
    `error_count_7d/30d: 1`; the untouched workflow showed all zeros.
  - Re-ran sync a second time → row counts in `workflows`/`executions`
    stayed the same (2 / 3) — confirmed upsert, not insert-duplicate.
  - Pointed the connection's `n8n_base_url` at an unreachable port and
    synced → 200 response, `last_sync_status: "error"` with a clear
    message, zero rows lost, nothing crashed. Restored the URL and
    re-synced clean afterward.

### Phase 1 — done
- Repo scaffold: `docker-compose.yml` (postgres@5433, adminer@8081), `.env`,
  `requirements.txt`.
- `app/config.py` — pydantic-settings, reads `apps/api/.env`.
- `app/database.py` — SQLAlchemy engine/session/Base.
- `app/models.py` — `User`, `Connection` tables only so far (workflows,
  executions, workflow_summaries, alerts come in Phase 2/3).
- `app/security.py` — bcrypt password hashing, Fernet encrypt/decrypt for
  n8n API keys, itsdangerous signed session tokens.
- `app/deps.py` — `get_current_user` dependency reading the session cookie.
- `app/schemas.py` — Signup/Login/User/Connection/WorkflowPreview pydantic
  models.
- `app/n8n_client.py` — `N8nClient` wrapper: paginated `list_workflows()`,
  `list_executions()`, `test_connection()`, with distinct exceptions
  (`N8nUnauthorizedError`, `N8nConnectionError`, `N8nApiError`).
- `app/auth.py` — `POST /auth/signup`, `/auth/login`, `/auth/logout`,
  `GET /auth/me`. **Tested and working** (signup → cookie set → `/auth/me`
  returns user → logout → `/auth/me` 401 → login works again).
- `app/connections.py` — `POST/GET/DELETE /connections`,
  `GET /connections/{id}/workflows` (one-shot fetch, not persisted yet —
  persistence is Phase 2 by design). Connection creation tests the n8n
  credentials live before saving (calls `test_connection()`), stores
  encrypted API key, tracks `last_sync_status`/`last_sync_error`/`last_sync_at`.
- Alembic migration `eb1876b6840d_create_users_and_connections_tables` applied
  to the DB.
- `app/main.py` wires both routers + CORS for `http://localhost:3000`.
- **Phase 1 fully smoke-tested end to end, including against a real local n8n
  instance** (added as a `n8n` service in `docker-compose.yml`, host port
  5678 — dev/test target only, not part of the product). Verified:
  - signup → session cookie set → `/auth/me` works → logout → 401 → login
    works again
  - `POST /connections` against an unreachable URL → clean 400, not a crash,
    nothing saved
  - `POST /connections` against a real n8n with a wrong API key → clean 400
    "n8n rejected this API key", nothing saved
  - `POST /connections` against the real n8n with a valid API key → 201,
    `last_sync_status: "ok"`
  - `GET /connections/{id}/workflows` → correctly returns the real workflow
    (`name`, `enabled`) created via n8n's own API for this test
  - To get a working n8n API key for local testing: n8n has no public
    endpoint to create API keys, so we used its internal REST API directly —
    `POST /rest/owner/setup` (one-time, creates the owner account) then
    `POST /rest/api-keys` with `{"label","scopes":[...],"expiresAt":null}`.
    n8n currently grants a broad default scope set regardless of what's
    requested. This is fine for a local throwaway dev instance; it is **not**
    how a real user would generate their key (they'd use n8n's Settings → API
    UI) — don't reuse this internal-API trick against a real user's instance.

## Task tracker

Each session has been using the harness's TaskCreate/TaskUpdate tool with one
task list per phase's breakdown of work (not persisted across sessions so
far — if a new session can't see a task list, recreate one from this file's
"Not done yet" section under "Current state" above).
