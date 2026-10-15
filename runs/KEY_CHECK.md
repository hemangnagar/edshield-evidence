# Key check (2026-10-15T12:42:19+00:00)

- platform key: **NONE of ('EDSHIELD_PLATFORM_API_KEY', 'ANTHROPIC_API_KEY') is set**
- base URL used by this branch: `https://api.anthropic.com`
- `ANTHROPIC_BASE_URL` in this container: `https://api.anthropic.com` ; equal to the official URL. Every script on this branch pins the official URL regardless, so spend cannot be routed elsewhere.)
- Claude Code cloud's own credential is not an API key in this container's environment; the scripts refuse to run without one of ('EDSHIELD_PLATFORM_API_KEY', 'ANTHROPIC_API_KEY'), so there is no silent fall-back to it.

**Blocked.** No key. Add the platform org's key as an environment secret named `EDSHIELD_PLATFORM_API_KEY` (cloud environment menu → Edit → environment variables) and start a new session; see WAITING.md.
