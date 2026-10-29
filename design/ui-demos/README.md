# NoahsArk UI Direction Demos

**DRAFT · PROTOTYPE.** Three static, dependency-free UI direction comparisons using identical NoahsArk fixture data. This is not a 39-route implementation, UI freeze, live control plane, or production readiness claim.

## Run on the LAN

From the repository root, run exactly:

```bash
python3 -m http.server 8099 --bind 0.0.0.0 -d design/ui-demos
```

Open locally at `http://localhost:8099/`.

For a LAN review, replace `localhost` with the host machine's LAN address.

Do not replace `<linux-lan-ip>` in committed documentation with an actual address.

## Review route and clicks

1. Start at `index.html` and open **Cloudline**, **Precision Desk**, and **Focus Flow**.
2. In each direction, open **Task Detail** using the primary action, navigation, or a decision queue row; return with **Mission Control**.
3. Toggle **Theme** and reload to confirm local theme persistence.
4. Check the same fixture semantics in every direction:
   - all five independent axes;
   - `COMPLETED` does not read as PASS;
   - expected / received / verified evidence counts differ;
   - business PASS + incomplete evidence remains not eligible for formal PASS;
   - OFFLINE retains OCCUPIED and GRANTED; release is independent of verdict;
   - blocked, stale, partial evidence, and unknown-progress facts are explicit.
5. Review desktop, tablet, and mobile reflow; keyboard focus; reduced-motion behavior; and browser console independently.

## Files

- `DESIGN.md` — research log and the shared + per-direction contracts.
- `index.html` — comparison selector.
- `cloudline.html`, `precision-desk.html`, `focus-flow.html` — three runnable directions.
- `fixtures.js` — the single shared local fixture projection imported by `app.js`.
- `app.js`, `styles.css` — dependency-free shared UI behavior and styles.

No network calls, external assets, package install, build step, credentials, real host identities, private IPs, or backend connections are used.
