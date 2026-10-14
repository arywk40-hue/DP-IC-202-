# INDRA review and Codex build pack

Reviewed main: 6bcda6b689868682cabfd95808eeb611dcb4aed3. Date: 14 October 2026.

Read INDRA_review.md first: current-code findings, sources/licences, physical and N-node design, executed planning receipts, and outstanding questions.

Then paste master prompt 0 from Codex_prompts.md into Codex, followed by phases A-N one at a time. Those prompts specify files to create/change, commands, tests, acceptance criteria and evidence gates.

planning_simulation.py and planning_results.json are the standalone synthetic engineering reference and its actual output. They do not measure weather accuracy, board behavior or real radio performance. export_probe.json records regenerated model-header parity/reproduction results.

Reproduce the planning simulation with Python 3.12, numpy 2.3.4 and scipy 1.16.3:

```sh
python -m pip install numpy==2.3.4 scipy==1.16.3
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python planning_simulation.py --output planning_results_new.json --seeds 10 --rounds 200
```

No repository files were changed. Codex is the coding tool; INDRA uses conventional ML/rules and has no runtime LLM integration. Teammate UI location, native local data, independent labels, radio profile and physical validation remain outstanding.
