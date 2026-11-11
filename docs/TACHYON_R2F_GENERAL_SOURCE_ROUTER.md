# TACHYON-R2F — Stop turning every out-of-physics question into a dead end

## What was broken, and what was not

The R2D result `4/4 out-of-domain abstentions` was correct behavior **for the narrow physics-only evaluator**, not an ordinary user-facing success measure. A scientific specialist should refuse unsupported physics claims. However, routing an everyday user's NAS, apple gardening, baking or live football question to that same science-only index is a **product routing failure**.

R2F introduces a separate, non-neural, evidence-aware cross-domain dispatcher. It **does not** change the physics R2D benchmark, hidden clock holdouts, any checkpoint or the JANUS Ocean environment.

## Four previously rejected public test cases

| Prior case | R2F routing | Why |
|---|---|---|
| NAS electricity cost | `GENERAL_SOURCE_ANSWER` | Cited U.S. Department of Energy and ENERGY STAR advice; no invented user hardware data or cost |
| Choose winter apple cultivar | `GENERAL_SOURCE_ANSWER` | University Extension horticulture summaries; regional fit still requires location details |
| Why no-yeast pizza dough fails to rise | `GENERAL_SOURCE_ANSWER` | King Arthur Baking explanatory sources; simple causal explanation |
| 'How did the last football team of the championship play?' | `NEEDS_CLARIFICATION` | No specific team, league or match; supplying a score would be fabricated |

Each general source card contains authored short Russian guidance and explicit URLs. All source domains are allowlisted. These cards stay in `data/tachyon/r2f/` and **are never added to R2B/R2C neural training data**. Source content is not the source of authority for new physics discoveries.

## Unknown questions

Unmatched questions now receive a structured `EXTERNAL_SEARCH_REQUIRED` request carrying the original query and a live/freshness flag. A host-side search provider can fulfill that request and return supported evidence **in a subsequent integration**. This prototype DOES NOT silently perform a live web query within GitHub Actions; it DOES NOT invent current sports results. Ambiguous live sports requests receive a concrete clarifying question.

## Evaluation boundaries

The same 18 known public prompts are used to test the **routing implementation**, not novel generalization. Reporting 3/3 canned general answers and one clarification is not evidence that the small Transformer understands gardening, storage or baking. R2D physics-only abstention (4/4) is retained for independent scientific scoring. An external sealed blind scientific review is still pending (issue #74).

## Safety and authority

- No model retraining or hidden label access; `scientifically_admitted` always `false`.
- No changes to production, main or JANUS Ocean.
- General cards contain advice, not measured facts about the user's specific NAS or weather.
- Evidence-based fallback is limited to the available cards; unseen topics require a real source provider before answering.
- Dynamic/fresh facts may only be reported after checking current evidence, not from stale cards.

Status: `TACHYON_R2F / CROSS_DOMAIN_ROUTING_RESEARCH_ONLY / SCIENTIFIC_HOLD`.
