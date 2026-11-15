# M3 Colab Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use the qskill-executing-plans skill to implement this plan task-by-task. Steps use checkbox syntax for tracking.
> This plan specifies behaviour, files, outcomes and test cases, not implementation code or signatures. Read the actual files before changing them.

**Goal:** Produce a reproducible, traceable baseline run of the pinned Qwen2.5-3B-Instruct model on development cases from Colab.

**Architecture:** Keep validation, prompt assembly, generation orchestration and artifact writing in a Python module. Keep the Colab notebook limited to private-repository access, runtime checks, dependency setup and calling the module. M3 uses Transformers for the base-model baseline; Unsloth is reserved for M4 QLoRA.

**Tech Stack:** Python standard library for orchestration and tests; PyTorch, Transformers and Accelerate on a Colab GPU; JSONL inputs and outputs; Jupyter notebook format.

**Spec:** `docs/superpowers/specs/2026-11-15-m3-colab-baseline-design.md`

**Plan slug:** `2026-11-15-m3-colab-baseline` — every commit for this plan starts with `[2026-11-15-m3-colab-baseline]`.

## Global Constraints

- Model: `Qwen/Qwen2.5-3B-Instruct`, revision `aa8e72537993ba99e69dfaafa59ed015b17504d1`.
- Use only `data/evaluation/dev_cases.jsonl`; do not read or use golden draft.
- User messages come only from the dev `prompt` field; do not include `expected_behavior`, grading constraints, rubric or notes.
- Read system text from `prompts/story_system_v1.txt` without changing it.
- Keep M3 inference on Transformers; do not install or use Unsloth, do not train, fine-tune or select a checkpoint.
- Require a real Colab GPU for model generation; do not report local or CPU smoke checks as a model run.
- Save outputs only under a new, configurable, Git-ignored `outputs/` directory; never overwrite a prior run.
- Do not place GitHub credentials, model tokens or other secrets in notebook cells, logs, output files or URLs.
- Record the model revision, source commit, prompt/input hashes, runtime/dependency versions, GPU details and effective generation settings.
- The Qwen research license is for non-commercial research/evaluation; do not distribute the model or weights as part of M3.
- M2 review gates remain pending; M3 development outputs do not close M2 or establish final quality.

---

## File Map

- `src/kids_story/baseline.py`: validate the selected development input, build the two-message request, call the model backend, and manage run artifacts.
- `tests/test_baseline.py`: verify input rules, message isolation, output states and artifact integrity without loading weights.
- `tests/fixtures/baseline_dev_synthetic.jsonl`: clearly synthetic rows for baseline-runner logic tests; never used for training or model quality claims.
- `requirements/m3-colab.lock.txt`: exact M3 package versions compatible with the selected Colab runtime; record the runtime-provided PyTorch version and avoid silently replacing it.
- `notebooks/m3_baseline_colab.ipynb`: authenticate to the user's private repository through a Colab Secret, check GPU and runtime, load the pinned dependencies, configure paths and call the Python module.
- `docs/COLAB_RUNBOOK.md`: replace prospective M3 instructions with the notebook flow and actual verified commands; keep M4/Unsloth instructions separate.
- `docs/AI_DESIGN.md`: record the fixed M3 model revision, license scope, baseline settings and M4 Unsloth boundary.
- `docs/EXPERIMENT_LOG.md`: record an actual run only after the user runs the notebook; until then, leave run results empty and state that Colab generation has not been executed.
- `README.md`: add the real M3 setup and verification commands after they have been run; distinguish local structural checks from Colab generation.

## Task 1: Validate inputs and define baseline records

**Files:**
- Create: `src/kids_story/baseline.py`
- Create: `tests/test_baseline.py`
- Create: `tests/fixtures/baseline_dev_synthetic.jsonl`

**Interfaces:**
- Consumes: the spec's development JSONL, system prompt and baseline configuration.
- Produces: validated cases, model messages that exclude evaluator-only data, and per-case result records for the generation task.

- [x] **Step 1: Write failing logic tests**

Test cases:

- valid synthetic development rows -> accepted in input order
- missing, malformed, blank or duplicate IDs -> rejected before any model load
- missing, non-text or blank `prompt` -> rejected before any model load
- valid row containing `expected_behavior`, rubric and constraints -> model messages include only the fixed system text and `prompt`

- [x] **Step 2: Run the focused tests and confirm the new cases fail**

Run from PowerShell with `PYTHONPATH` set to `src`: `python -m unittest discover -s tests -p test_baseline.py -v`.

- [x] **Step 3: Build input and message preparation behaviour**

Unit: `validate_dev_cases` in `src/kids_story/baseline.py`.
- Takes: the development JSONL path.
- Returns: ordered cases with the required `id` and non-empty `prompt`.
- Rules: reject malformed rows, duplicate IDs and invalid prompts before model initialization; never change the source file.

Unit: `build_messages` in `src/kids_story/baseline.py`.
- Takes: one validated case and the existing system text.
- Returns: system and user messages in that order.
- Rules: use the prompt verbatim; do not add evaluator-only fields or inferred plot details.

- [x] **Step 4: Run focused and regression tests**

Run `python -m unittest discover -s tests -p test_baseline.py -v` and `python -m unittest discover -s tests -v`.
Expected: baseline logic tests and all existing M1/M2 tests pass.

- [x] **Step 5: Commit Task 1**

Commit subject: `[2026-11-15-m3-colab-baseline] Add baseline input and message validation`

Commit trailer: `Plan: docs/superpowers/plans/2026-11-15-m3-colab-baseline.md` and `Task: 1`.

## Task 2: Generate and preserve raw baseline outputs

**Files:**
- Modify: `src/kids_story/baseline.py`
- Modify: `tests/test_baseline.py`
- Modify: `tests/fixtures/baseline_dev_synthetic.jsonl`

**Interfaces:**
- Consumes: validated cases/messages from Task 1 and a model backend that can be replaced with a fake backend during tests.
- Produces: one result record per input ID, `run_config.json`, and a verified completion manifest when the run is exhaustive.

- [x] **Step 1: Write failing generation and artifact tests**

Test cases:

- successful fake generation -> raw text, token count, finish reason, elapsed time, case ID and messages hash are recorded
- one case fails after model loading -> an error record is written for that ID and other cases are still attempted
- every input has either a result or explicit error -> run status reflects whether any case failed
- one input has no result or error record -> no completion manifest is written
- all cases succeed -> completion status is `complete` and all artifact hashes verify
- one or more cases fail -> status is `completed_with_errors` and the run is not described as a complete baseline
- model load or GPU check fails before generation -> no completion manifest is written
- token budget is reached -> raw partial output and finish reason are kept without automatic continuation
- output text is preserved exactly as returned by the model
- changed system prompt or input file -> resulting run configuration has a different corresponding hash
- existing run output directory -> rejected without changing its files

- [x] **Step 2: Run focused tests and confirm generation/artifact cases fail**

Run `python -m unittest discover -s tests -p test_baseline.py -v`.

- [x] **Step 3: Add the pinned Transformers generation path**

Unit: `run_baseline` in `src/kids_story/baseline.py`.
- Takes: validated cases, fixed model ID/revision, generation settings and a new output path.
- Returns: a run result whose records cover every input ID as a success or an explicit error.
- Rules: require a GPU before model loading; use the pinned tokenizer/model revision; seed the run once and retain the effective settings; generate each case independently; never retry or post-process output; refuse existing output paths.

The model prompt is exactly the existing system prompt plus the dev case's `prompt`. Baseline settings start at seed 42, sampling enabled, temperature 0.7, `top_p` 0.9, repetition penalty 1.0 and `max_new_tokens` 512. Store the effective values; do not imply that this token budget guarantees the target whitespace length.

Write `generations.jsonl` with one success or error record per input, `run_config.json` with model/tokenizer revision, commit, prompt/input hashes, runtime/dependency/GPU details and effective generation settings. Write `COMPLETE.json` only after every input is represented and the required hashes match. Use `complete` when every case succeeded and `completed_with_errors` when every case was attempted but at least one failed.

- [x] **Step 4: Run focused and regression tests**

Run `python -m unittest discover -s tests -p test_baseline.py -v` and `python -m unittest discover -s tests -v`.
Expected: success/error records and completion states match the cases above; all M1/M2 tests still pass.

- [x] **Step 5: Commit Task 2**

Commit subject: `[2026-11-15-m3-colab-baseline] Add pinned Qwen baseline generation and artifacts`

Commit trailer: `Plan: docs/superpowers/plans/2026-11-15-m3-colab-baseline.md` and `Task: 2`.

## Task 3: Prepare the Colab notebook and handoff documents

**Files:**
- Create: `requirements/m3-colab.lock.txt`
- Create: `notebooks/m3_baseline_colab.ipynb`
- Modify: `docs/COLAB_RUNBOOK.md`
- Modify: `docs/AI_DESIGN.md`
- Modify: `docs/EXPERIMENT_LOG.md`
- Modify: `README.md`
- Modify: `tests/test_baseline.py`

**Interfaces:**
- Consumes: the Python baseline runner from Task 2 and the user's Colab account/runtime.
- Produces: a notebook that either stops with a clear environment/authentication message or completes the configured baseline run without exposing secrets.

- [x] **Step 1: Write failing notebook/lock validation cases**

Test cases:

- notebook file is valid JSON with ordered setup, environment-check and run sections
- no-GPU runtime -> notebook stops before model loading and marks no generation as run
- missing required dependency -> notebook reports the missing package and stops before model loading
- private-repository access is configured through a Colab Secret -> token is not shown in cell output, logs or URLs
- Unsloth appears only in the documented M4 scope and is not installed/imported for M3
- pinned model ID/revision, prompt paths and output path configuration -> match the approved spec

- [x] **Step 2: Run focused tests and confirm notebook cases fail**

Run `python -m unittest discover -s tests -p test_baseline.py -v`.

- [x] **Step 3: Create the thin Colab workflow and locked environment**

The notebook proceeds in this order: authenticate to the private repository without printing credentials; record the source commit; check Python, existing PyTorch, CUDA, GPU type and available VRAM; stop if no GPU is available; install only the locked M3 inference dependencies; verify package versions; mount Drive through the Colab interface when durable storage is selected; configure a new output directory; call the Python runner; verify output hashes.

Keep Colab-provided PyTorch unless an incompatibility is demonstrated and the replacement is explicitly recorded. Do not use Hugging Face tokens for this public model. Do not mount or upload data beyond the development input and run outputs. Do not install Unsloth in M3. If an authentication secret or GPU is absent, stop before reading cases or loading model weights and display a specific instruction. Save verified run artifacts to the user-selected Drive path when mounted; otherwise leave them in the configured runtime path and clearly state that Colab storage is temporary.

Update the runbook, AI design and experiment log to distinguish implemented notebook behaviour from a model run not yet executed. README commands must be added only after those commands have actually run in the corresponding environment.

- [x] **Step 4: Validate notebook structure, tests and documentation claims**

Run `python -m json.tool notebooks/m3_baseline_colab.ipynb` and `python -m unittest discover -s tests -v` locally. Confirm that the notebook's runtime checks do not claim a real Colab GPU run and that no secret, weight or output artifact is tracked by Git.

Expected: notebook parses, all M1/M2 and new baseline tests pass, docs label actual local checks and unrun Colab generation separately.

- [x] **Step 5: Commit Task 3**

Commit subject: `[2026-11-15-m3-colab-baseline] Add Colab baseline notebook and runbook`

Commit trailer: `Plan: docs/superpowers/plans/2026-11-15-m3-colab-baseline.md` and `Task: 3`.

## Completion Check

M3 implementation is ready for a real run when Tasks 1–3 pass locally, the notebook is checked in, the model/revision and environment are fixed, and all source/docs are consistent. M3 is not complete until the user actually runs the notebook on a Colab GPU and the output artifacts/configuration are verified. No model quality metric is claimed by these structural tests.
