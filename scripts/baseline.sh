#!/usr/bin/env bash
# End-to-end baseline: export -> judge -> summary -> ledger.
#
#   scripts/baseline.sh                      # all four steps
#   scripts/baseline.sh --steps "3 4"        # a subset
#   scripts/baseline.sh --report-dir evidence/reports/2026-10-04-abc1234
#
# Steps (brief §7), all under policy coppa:
#   1  piilo_holdout × rules+model × python, seeds 0 1 2 + seed-0 repeat
#   2  piilo_holdout × rules+model × python,onnx (parity)
#   3  k12_hard      × rules+model × python, seeds 0 1 2 + seed-0 repeat
#   4  k12_hard      × rules only  × python, seeds 0 1 2 + seed-0 repeat (the floor)
#
# Environment:
#   EDSHIELD_EVIDENCE_PIILO   directory holding validation.json (steps 1-2; skipped with a note if unset)
#   EDSHIELD_ALLOW_DOWNLOAD   defaults to 1 so edshield can fetch the model from the Hub
#   EDSHIELD_EVIDENCE_ONNX_DIR   local dir with onnx/model_quantized.onnx (step 2; else the Hub snapshot)
#   EDSHIELD_EVIDENCE_MODEL_DIR  local checkpoint dir for the python runtime (else the Hub model)
#   BASELINE_SEEDS            default "0 1 2"
#
# The judge decides; this script records. Exit code is non-zero only when a
# step could not run (exporter error, judge input error), never on a verdict.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"
export EDSHIELD_ALLOW_DOWNLOAD="${EDSHIELD_ALLOW_DOWNLOAD:-1}"
STEPS="1 2 3 4"
REPORT_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --steps) STEPS="$2"; shift 2;;
    --report-dir) REPORT_DIR="$2"; shift 2;;
    -h|--help) sed -n 2,24p "$0"; exit 0;;
    *) echo "unknown argument $1" >&2; exit 2;;
  esac
done
SEEDS="${BASELINE_SEEDS:-0 1 2}"
POLICY="${BASELINE_POLICY:-coppa}"
JUDGE="$HERE/judge/dist/run-evidence.mjs"
[ -f "$JUDGE" ] || { echo "judge missing: git submodule update --init" >&2; exit 2; }
if [ -z "$REPORT_DIR" ]; then
  SHORT="$(git rev-parse --short HEAD 2>/dev/null || echo nogit)"
  REPORT_DIR="evidence/reports/$(date -u +%Y-%m-%d)-$SHORT"
fi
mkdir -p "$REPORT_DIR"
echo "report directory: $REPORT_DIR"

MODEL_ARGS=()
[ -n "${EDSHIELD_EVIDENCE_MODEL_DIR:-}" ] && MODEL_ARGS+=(--model-dir "$EDSHIELD_EVIDENCE_MODEL_DIR")
ONNX_ARGS=()
[ -n "${EDSHIELD_EVIDENCE_ONNX_DIR:-}" ] && ONNX_ARGS+=(--onnx-dir "$EDSHIELD_EVIDENCE_ONNX_DIR")

# step <n> <key> <policy key> <exporter args...>
step() {
  local n="$1" key="$2" pkey="$3"; shift 3
  echo; echo "== step $n: $key"
  local bundle="$REPORT_DIR/$key.bundle.json" policy="$REPORT_DIR/$key.policy.json" verdict="$REPORT_DIR/$key.verdict.json"
  python -W ignore -m edshield_evidence.export_views --policy "$POLICY" --out "$bundle" "$@"
  python -m edshield_evidence.policy select policies/regression.json "$pkey" --bundle "$bundle" --out "$policy"
  set +e
  node "$JUDGE" "$bundle" "$policy" --out "$verdict"
  local rc=$?
  set -e
  case $rc in
    0) echo "judge: pass";; 1) echo "judge: fail";; 2) echo "judge: insufficient";;
    *) echo "judge: input error (exit $rc)" >&2; exit $rc;;
  esac
  python -m edshield_evidence.ledger append --report "$REPORT_DIR" --key "$key"
}

skip() {
  local key="$1" why="$2"
  echo; echo "== skipped $key: $why"
  echo "$why" > "$REPORT_DIR/$key.skipped.txt"
}

# The model steps need torch + transformers (and onnxruntime for parity). Without them the
# step is skipped with a note in the report rather than silently falling back to rules.
MODEL_WHY=""
python -c "import torch, transformers" 2>/dev/null || MODEL_WHY="torch/transformers are not installed (pip install -e '.[hf]'); the model steps run locally"
ONNX_WHY="$MODEL_WHY"
[ -n "$ONNX_WHY" ] || python -c "import onnxruntime" 2>/dev/null || ONNX_WHY="onnxruntime is not installed (pip install -e '.[onnx]')"

for s in $STEPS; do
  case "$s" in
    1) if [ -n "$MODEL_WHY" ]; then skip 01_piilo_holdout_model_python "$MODEL_WHY";
       elif [ -n "${EDSHIELD_EVIDENCE_PIILO:-}" ]; then
         step 1 01_piilo_holdout_model_python piilo_holdout/rules+model \
           --dataset piilo_holdout --detector rules+model --runtime python --seeds $SEEDS --repeat-seed 0 ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"}
       else skip 01_piilo_holdout_model_python "EDSHIELD_EVIDENCE_PIILO is not set; the PIILO holdout is local data"; fi;;
    2) if [ -n "$ONNX_WHY" ]; then skip 02_piilo_holdout_model_parity "$ONNX_WHY";
       elif [ -n "${EDSHIELD_EVIDENCE_PIILO:-}" ]; then
         step 2 02_piilo_holdout_model_parity piilo_holdout/parity \
           --dataset piilo_holdout --detector rules+model --runtime python,onnx ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} ${ONNX_ARGS[@]+"${ONNX_ARGS[@]}"}
       else skip 02_piilo_holdout_model_parity "EDSHIELD_EVIDENCE_PIILO is not set; the PIILO holdout is local data"; fi;;
    3) if [ -n "$MODEL_WHY" ]; then skip 03_k12_hard_model_python "$MODEL_WHY"; else
       step 3 03_k12_hard_model_python k12_hard/rules+model \
         --dataset k12_hard --detector rules+model --runtime python --seeds $SEEDS --repeat-seed 0 ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"}; fi;;
    4) step 4 04_k12_hard_rules_python k12_hard/rules \
         --dataset k12_hard --detector rules --runtime python --seeds $SEEDS --repeat-seed 0;;
    *) echo "unknown step $s" >&2; exit 2;;
  esac
done

echo
python -m edshield_evidence.report "$REPORT_DIR"
# GitHub refuses files over 100 MB; the PIILO step 1 bundle is ~140 MB. Parts join back byte for byte.
python -m edshield_evidence.bundles split "$REPORT_DIR"
echo "summary: $REPORT_DIR/summary.md"
head -1 "$REPORT_DIR/summary.md"
