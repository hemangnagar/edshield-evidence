Thanks for stopping and reporting. The torch install is not needed: use the INT8 ONNX runtime instead, which the brief planned for CPU. onnxruntime, transformers and sentencepiece are already installed, and the ONNX export downloads from the allowed hf.co hosts. Continue from step 4 as follows:

- Skip torch entirely. Confirm `pip install -e /workspace/edshield-evidence` is done and edshield resolves from site-packages (the pinned 0.2.0 release).
- Do steps 5 to 9 exactly as written, but every `make` invocation uses `RUNTIME=onnx`: `make score-llm-view RUNTIME=onnx`, then `python scripts/build_failure_table.py llm`, then `pip install -e /workspace/edshield`, then `make eval-candidate ROUND=0 RUNTIME=onnx`, then copy and pack the outputs.
- If the first model call fails because a hf.co host is blocked, report the exact host named in the error and stop.

Reply with the status requested in the setup message (installed packages, where edshield resolves from, the LLM-view numbers from results/llm_view/summary.json, the round 0 numbers and the sanity flag) and wait for the task message.
