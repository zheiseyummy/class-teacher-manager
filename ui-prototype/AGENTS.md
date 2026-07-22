# Prototype Instructions

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

Build app UI in `src/`. Keep `.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`, and `tests/sites-worker.test.mjs` intact so the same local prototype can be handed to Sites. Before a Sites handoff, run `npm run build` and `npm run test:sites`; the build must leave `dist/client/index.html`, `dist/server/index.js`, and `dist/.openai/hosting.json`.

## Product direction

- This is an isolated interaction prototype for a Windows, offline-first teacher workbench; it must not modify the formal PySide6 application.
- Match the supplied reference's cobalt sidebar, pale gray workspace, white work panels, compact information density, and restrained semantic colors.
- Use the product's real modules and teacher workflows instead of copying exam-only labels or metrics from the visual reference.
- Keep the interface quiet, office-oriented, and suitable for long sessions. No EXE packaging is needed until the user explicitly requests it.
