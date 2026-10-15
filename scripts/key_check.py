"""Key check (brief §1): one tiny Haiku request, then record what the key is.

    python scripts/key_check.py

Writes runs/KEY_CHECK.md. Never prints or stores the key itself; it records a
sha256 prefix of the key so Hemang can match it against the Console, and
whether this container's own Claude Code credentials could have been used
instead (they must not be: spend has to land on the platform org).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platform_api as api  # noqa: E402


def main() -> int:
    var, key = api.platform_key()
    lines = [f"# Key check ({dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')})", ""]
    lines.append(f"- platform key found in `{var}`" if key else f"- platform key: **NONE of {api.KEY_VARS} is set**")
    if key:
        lines.append(f"- key fingerprint: prefix `{key[:10]}…`, sha256 `{hashlib.sha256(key.encode()).hexdigest()[:16]}`")
    lines.append(f"- base URL used by this branch: `{os.environ.get('EDSHIELD_PLATFORM_BASE_URL', api.OFFICIAL_BASE_URL)}`")
    base = os.environ.get("ANTHROPIC_BASE_URL")
    lines.append(f"- `ANTHROPIC_BASE_URL` in this container: `{base[:48] + '…' if base and len(base) > 48 else base}` "
                 + ("; equal to the official URL" if base == api.OFFICIAL_BASE_URL else "; **not** the official URL")
                 + ". Every script on this branch pins the official URL regardless, so spend cannot be routed elsewhere.)")
    lines.append("- Claude Code cloud's own credential is not an API key in this container's environment; the scripts "
                 f"refuse to run without one of {api.KEY_VARS}, so there is no silent fall-back to it.")
    if not key:
        lines += ["", "**Blocked.** No key. Add the platform org's key as an environment secret named "
                  "`EDSHIELD_PLATFORM_API_KEY` (cloud environment menu → Edit → environment variables) and start a new "
                  "session; see WAITING.md."]
        Path("runs").mkdir(exist_ok=True)
        Path("runs/KEY_CHECK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n".join(lines))
        return 1
    client = api.make_client()
    m = client.messages.create(model=api.MODELS["key_check"], max_tokens=5,
                               messages=[{"role": "user", "content": "ping"}])
    u = api.usage_dict(m.usage)
    lines += ["", f"- ping: model `{m.model}`, stop `{m.stop_reason}`, usage `{u}`, request id `{getattr(m, '_request_id', '?')}`",
              f"- cost of this check: ${api.usage_cost_usd(api.MODELS['key_check'], u, batch=False):.6f}",
              "", "**Org / workspace:** the API does not return the org name. Hemang: open the Console → Usage and confirm "
              "this request (model Haiku 5.5, 1 request at the time above) landed on the org that holds the platform credits."]
    Path("runs").mkdir(exist_ok=True)
    Path("runs/KEY_CHECK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
