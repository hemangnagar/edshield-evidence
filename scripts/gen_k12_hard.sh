#!/usr/bin/env bash
# Generate the k12_hard regression set once, from edshield's generator at the
# pinned commit, run as a subprocess from a checkout (the installed package
# does not ship eval/). Writes evidence/sets/k12_hard_seed1.jsonl + .sha256.
#
#   scripts/gen_k12_hard.sh                 # clones edshield at the pinned commit into a temp dir
#   EDSHIELD_SRC=/path/to/edshield scripts/gen_k12_hard.sh   # use an existing checkout (checked out at the pin)
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PIN="$(python3 -c 'import edshield_evidence as e; print(e.EDSHIELD_COMMIT)')"
REPO="$(python3 -c 'import edshield_evidence as e; print(e.EDSHIELD_REPO)')"
N="${K12_N:-400}"; SEED="${K12_SEED:-1}"
OUT="$HERE/evidence/sets/k12_hard_seed${SEED}.jsonl"

if [ -n "${EDSHIELD_SRC:-}" ]; then
  SRC="$EDSHIELD_SRC"
else
  SRC="$(mktemp -d)/edshield"
  git clone -q "$REPO" "$SRC"
fi
HEAD="$(git -C "$SRC" rev-parse HEAD)"
if [ "$HEAD" != "$PIN" ]; then
  git -C "$SRC" checkout -q "$PIN"
fi
echo "edshield source at $(git -C "$SRC" rev-parse --short HEAD) (pin ${PIN:0:7})"

TMP="$(mktemp -d)"
# The generator is edshield's; this repo only runs it and converts its output.
python3 "$SRC/eval/k12_bench.py" --n "$N" --style hard --seed "$SEED" --out "$TMP/k12_hard.json"
sha256sum "$TMP/k12_hard.json" | sed 's#  .*#  (generator output, PIILO format)#'
python3 -m edshield_evidence.datasets convert-piilo "$TMP/k12_hard.json" --out "$OUT" --prefix k12h-
cat > "${OUT%.jsonl}.manifest.json" <<JSON
{
  "set": "k12_hard_seed${SEED}",
  "role": "regression",
  "visibility": "dev-visible",
  "generator": "edshield eval/k12_bench.py --style hard --n ${N} --seed ${SEED}",
  "generator_commit": "${PIN}",
  "generator_output_sha256": "$(sha256sum "$TMP/k12_hard.json" | cut -d' ' -f1)",
  "file": "$(basename "$OUT")",
  "sha256": "$(sha256sum "$OUT" | cut -d' ' -f1)",
  "note": "Generated once from the pinned edshield commit. Used to choose nothing; regression only. Not an acceptance set."
}
JSON
rm -rf "$TMP"
echo "wrote $OUT and ${OUT%.jsonl}.manifest.json"
