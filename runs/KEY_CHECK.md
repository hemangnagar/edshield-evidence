# Key check (2026-10-14T23:18:10+00:00)

- `ANTHROPIC_API_KEY` set: **NO**
- base URL used by this branch: `https://api.anthropic.com`
- `ANTHROPIC_BASE_URL` in this container: `https://api.anthropic.com` ; equal to the official URL. Every script on this branch pins the official URL regardless, so spend cannot be routed elsewhere.)
- Claude Code cloud's own credential is not an API key in this container's environment; the scripts refuse to run without `ANTHROPIC_API_KEY`, so there is no silent fall-back to it.

**Blocked.** No key. Add `ANTHROPIC_API_KEY` as an environment secret (cloud environment menu → Edit → Network secrets / environment variables) and restart; see WAITING.md.
