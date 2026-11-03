# P5-W7 Production UI Integration Evidence

**Date:** 2026-10-30
**Scope:** `design/ui-app` only. This evidence records browser and deterministic
checks for the existing native-ESM Cloudline console. It does not claim hardware
connectivity, production deployment, a Phase 6 result, or acceptance.

## Delivered integration behavior

- All **39/39** registered routes still resolve through `routes.json` and the
  runtime route manifest. API mode maps every route to one read endpoint.
- API mode is explicit (`?api=1` / data-source selector). Failures render an
  alert, request facts, retry, and an explicit fixture switch; failures never
  become an empty or success projection.
- Task Live, run detail, and attempt detail refresh their read-only projection
  every 10 seconds in API mode. The Live event timeline renders returned
  `events` / `timeline` facts; an absent event list remains an explicit empty
  projection and does not invent a runtime outcome.
- Permission presentation fails closed in a browser without an authoritative
  session: the default role is `OBSERVER`, an unknown role also resolves to
  `OBSERVER`, and restricted controls remain visible but disabled with a reason.
  An available stored session token is sent only as `X-NoahsArk-Session`; the UI
  does not render a token and a verified authoritative role locks the demo-role
  selector.
- Loading, error, empty, unknown-progress, five-axis, evidence, STOP/lease,
  and release states retain their existing fail-closed semantics. In particular,
  `INDETERMINATE` renders no percentage and `NOT_EVALUATED` / `NOT_RUN` stay
  unchanged when API data is adapted.
- Chinese and English chrome remains available through the language control;
  `lang` is updated on the document element. Landmark, skip-link, focus-visible,
  `aria-busy`, loading status, and error alert semantics are preserved.

## Deterministic checks

Run from the repository UI directory:

```bash
cd /home/bszheng/NoahsArk/design/ui-app
npm run check
git -C /home/bszheng/NoahsArk diff --check
```

Result on 2026-10-30 (corrected after the independent browser finding):

- `checks/contract-check.mjs`: **102 passed, 0 failed**.
- `checks/smoke-check.mjs`: **298 passed, 0 failed**.
- Coverage includes 39 route-to-endpoint mappings, 39 route renderer imports,
  API event projection, unknown-progress, exact formal-PASS tuple, API
  preservation of `NOT_EVALUATED` / `NOT_RUN`, default/unknown-role denial, and
  bilingual registration.
- There is no separate frontend bundler, lint, or TypeScript typecheck in this
  dependency-free native ESM app. JavaScript LSP is unavailable in this
  environment; the Node checks above are the project-native static/runtime gate.

## Playwright browser smoke

Server:

```bash
cd /home/bszheng/NoahsArk/design/ui-app
node checks/serve.mjs 8100
```

Using the Playwright browser against `http://127.0.0.1:8100`:

- Desktop: **1440×960**.
- Mobile: **390×844**.
- Route coverage: all **39/39** routes were visited in four groups (10 + 10 +
  10 + 9); each yielded non-empty `#route-view` content and its registered
  route title.
- Mobile check on Task Live: no horizontal document overflow; `main#main-content`
  and skip-link target exist.
- Keyboard/accessibility: visible skip link and main landmark exist; navigation
  and actions have accessible names; switching to `OBSERVER` disabled the visible
  `请求 STOP` control with `aria-disabled=true` and an explanatory title.
- Bilingual check: language toggle changed `document.documentElement.lang`
  between `en` and `zh-CN` while retaining the route content.
- The earlier API-mode console-clean claim was invalid: an independently
  observed browser session with a stored `naa-session` attempted the optional
  `/api/v1/auth/session` bootstrap endpoint and recorded a 404 console error.
  The startup path now does not invoke that optional endpoint; the session token
  header behavior remains available for API reads. The final Playwright MCP
  rerun is required after this correction before treating the console-clean
  criterion as satisfied.

## Limitations and production boundary

- The UI is still the existing candidate native-ESM application. No production
  bundler, deployed static hosting, TLS, OIDC flow, or independently provisioned
  browser session was exercised.
- The local API used in this check provided read projections only; no write,
  approval, STOP, release, hardware, Node Agent, lstest, audio, serial, or TCL
  action was sent or claimed.
- Login/logout credential entry is intentionally not added here, and no
  credential value is exposed. Stored session-token header forwarding remains
  available to API reads, but optional session discovery is not performed by UI
  startup because the project-native static proxy may not expose that endpoint.
- Polling is the available event-consumption fallback. A durable SSE/WebSocket
  contract is not introduced because the backend exposes no such contract in
  this wave.
- This evidence is W7 UI integration evidence only. It is not a claim of W6
  real-device completion, production acceptance, Phase 6 readiness, or real
  node connectivity.
