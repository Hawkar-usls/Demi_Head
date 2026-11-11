# TACHYON-R2H — bounded multi-run CPU training after source gateway integration

## Rationale

R2D found 0/8 numeric text matches for the frozen original tiny R2B and R2C generators. Increasing runner count alone does not fix the training-data bottleneck. R2H tests **two distinct research tasks**, each with two independent random initializations, while keeping the scientific and privacy gates closed.

## The experiment

Four isolated GitHub-hosted `ubuntu-24.04` CPU jobs, at most `max-parallel=4`, `timeout-minutes=16`, `actions` permissions `contents: read`, matrix `fail-fast=false`, no GPU, no auto-schedule, no recursive workflow dispatch, no use of organization-wide runner sharing, and no production deployment.

Lane A (`tachyon`, 2 jobs): retrain the **unchanged** R2C 64-width generator from verified 36 educational pairs (the R2A video paraphrase corpus pinned to Meta Registry commit `a7f77b02ba6f66efc3a0df5d275de7e57eb0e28d`, plus reviewed theory source cards), seeds 117 and 223, bounded 22 and 30 epochs. Compare raw answers on 8 **public previously published** numeric R2D developer questions. This is not independent blind data, a clock-measurement test or proof of physical competence.

Lane B (`evidence-router`, 2 jobs): train an 8-class tiny hashed character neural routing policy, seeds 337 and 449, on 83 **author-written synthetic training prompts** plus explicitly source-indexed labels. Classes: special-relativity formula, Born formula, other theoretical source, NAS, garden, pizza source, live news and abstain. Evaluate on the same 18 public R2D development prompts. The learned model only suggests a route; real replies require trusted source retrieval and deterministic formula validation. High routing accuracy would not imply general-purpose intelligence.

## Never-train source exclusions

- No private heldout question keys, atomic-clock measurements, or raw external measurement CSV is fed to any optimizer. The previous CSV SHA-256 is checked for integrity only and remains outside the model training input.
- The 18 R2D public developer questions are excluded byte-for-byte from the new router training data. Their outcomes are **known**, hence not externally blinded. The scientific source families for clocks remain excluded.
- Live Wikipedia/OpenAlex/GDELT search snippets must not automatically flow to training. A future curator needs rights assessment, provenance, independent source verification, deduplication, explicit science safety checks, and train/eval family separation.
- GitHub Actions runners are temporary. Four checkpoint archives and one comparison artifact expire according to the workflow's 14-day retention; an independent long-term archive and SHA verification are needed before expiry.

## Acceptance

Train-only loss decline and token overlap are not admission criteria. Each lane produces a checkpoint SHA-256 and explicit public diagnostic (numeric textual matches or source-routing accuracy, live false positives). The comparison job **never** writes to main, deploys Ocean, or chooses a production champion. If any job fails, no comparison is marked completed. A separate scientific custodian (issue #74) still controls the true blind evaluation.

## GitHub runner ethics and budget

GitHub Actions has plan-specific concurrent-hosted-runner limits. The 256-job matrix syntax ceiling is **not** an entitlement to reserve 256 active machines. This pilot deliberately limits concurrency to 4 and caps the maximum reserved job time to 64 total runner-minutes for training plus 3 for comparison (actual may be less). Do not loop or saturate the fleet merely to consume compute. Only expand if new held-out metrics justify it and within the repository's GitHub Actions limits and policy.

## Deployment boundary

This is isolated research in `Hawkar-usls/Demi_Head` staged above R2G. Source search is in draft `Hawkar-usls/Janus` PR #51; no live host/NAS or the JANUS Ocean model is modified by R2H. Production gateway deployment is separately gated by authenticated ingress, quota, GDELT rate limiting and a user-authorized target. GDELT's HTTP429 in GitHub runners is a provider availability issue, not a physics-data verdict.

Status: `R2H / FOUR_BOUNDED_RESEARCH_CANDIDATES / PUBLIC_DEV_ONLY / SCIENTIFIC_HOLD`.
