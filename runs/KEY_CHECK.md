# Key check (2026-10-15T12:48:58+00:00)

- platform key found in `EDSHIELD_PLATFORM_API_KEY`
- key fingerprint: prefix `sk-ant-usr…`, sha256 `b58f60816e0a5915`
- base URL used by this branch: `https://api.anthropic.com`
- `ANTHROPIC_BASE_URL` in this container: `https://api.anthropic.com` ; equal to the official URL. Every script on this branch pins the official URL regardless, so spend cannot be routed elsewhere.)
- Claude Code cloud's own credential is not an API key in this container's environment; the scripts refuse to run without one of ('EDSHIELD_PLATFORM_API_KEY', 'ANTHROPIC_API_KEY'), so there is no silent fall-back to it.

- ping: model `claude-haiku-5-5`, stop `max_tokens`, usage `{'input_tokens': 10, 'output_tokens': 5, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0}`, request id `req_011Cg43rC3ij8e4TTbrUzDTP`
- cost of this check: $0.000003

**Org / workspace:** the API does not return the org name. Hemang: open the Console → Usage and confirm this request (model Haiku 5.5, 1 request at the time above) landed on the org that holds the platform credits.
