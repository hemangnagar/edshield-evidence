# Notes on this report folder

Run on Hemang's PC on 2026-10-04 with `scripts/baseline.sh` at commit `6c0f163`, all four steps. Two things were changed after the run and before the commit. Neither touches a bundle, a policy or a verdict.

## The step 1 bundle is split into three parts

`01_piilo_holdout_model_python.bundle.json` is 139,429,092 bytes, over GitHub's 100 MB file limit, so it is stored as `.part00`, `.part01` and `.part02`. Join them before reading the bundle or re-running `python -m edshield_evidence.report` on this folder:

```bash
cat 01_piilo_holdout_model_python.bundle.json.part* > 01_piilo_holdout_model_python.bundle.json
sha256sum 01_piilo_holdout_model_python.bundle.json
# 704cf09998043cfc8dbbaf2230cf280f2e9599681e6b918a28c2044d56ecdf55
```

## Example text from the PIILO essays was removed

The two PIILO diagnostics files (`01_…` and `02_…`) held example text from the essays: `partial_examples` (1 per run) and `over_redaction_sample` (50 per run, each with a token and its context). Those lists were removed from the two files, and `summary.md` was regenerated from them, so no essay text is in this folder. All counts are unchanged. The K-12 examples in steps 3 and 4 are synthetic and were kept.

The complete files are on the PC that ran the baseline, outside git, in `tmp/originals-2026-10-04-6c0f163/`.
