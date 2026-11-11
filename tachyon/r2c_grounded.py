"""TACHYON-R2C: bounded source-grounded research candidate, never a physics authority.

Public source paraphrases may be used for fit and retrieval. Secret clock questions,
labels, laboratory measurements and independent assessment must NOT enter this module.
R2B generator remains unchanged; R2C trains a separate research-only checkpoint.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re

from tachyon.science_generator import (
    ScienceHold, require, load_json, training_rows, make_vocab, vectorize,
    prepare_tensors, build_model, generate, sha, canonical, tokens, MAX_SOURCE,
    MAX_TARGET, PAD, HOLDOUT_DOIS, HOLDOUT_FAMILIES,
)

SCHEMA = "janus.tachyon.r2c.source_grounded_generator.v1"
EXPECTED = {
    "SR_EINSTEIN_1905": "10.1002/andp.19053221004",
    "GR_SHAPIRO_1964": "10.1103/PhysRevLett.13.789",
    "BELL_1964": "10.1103/PhysicsPhysiqueFizika.1.195",
    "HENSEN_2015": "10.1038/nature15759",
    "GRW_1986": "10.1103/PhysRevD.34.470",
    "QBAYES_2002": "10.1103/PhysRevA.65.022305",
}
ALLOWED_DOMAINS = {"relativity", "quantum_causality", "quantum_measurement"}
STOP = frozenset("и в на о об по как что это для или из при с со ли да не есть его ее их но от почему можно ли ли какова это такое является ли означает ли способ".split())

def new_source_rows(cards_path):
    data, digest = load_json(cards_path)
    require(data.get("schema") == "janus.tachyon.r2c.source_cards.v1", "R2C_SCHEMA")
    policy = data.get("policy", {})
    for key in ("clock_lab_measurements_used", "existing_r2b_clock_holdout_used",
                "independent_blind_test_in_repository", "auto_deployment"):
        require(policy.get(key) is False, "R2C_SOURCE_POLICY_LEAK")
    sources = data.get("sources", [])
    require(isinstance(sources, list) and len(sources) == len(EXPECTED), "R2C_SOURCE_COUNT")
    require({s.get("family"): s.get("doi") for s in sources} == EXPECTED, "R2C_SOURCE_ALLOWLIST")
    require(all(s.get("doi") not in HOLDOUT_DOIS and s.get("family") not in HOLDOUT_FAMILIES
                for s in sources), "R2C_CLOCK_SOURCE_LEAK")
    rows = []
    for s in sources:
        require(s.get("url") == "https://doi.org/" + s["doi"], "R2C_DOI_URL")
        require(s.get("domain") in ALLOWED_DOMAINS, "R2C_DOMAIN")
        require(s.get("provenance_status") ==
                "PUBLISHER_METADATA_VERIFIED_AUTHOR_PARAPHRASE_NOT_INDEPENDENTLY_ADJUDICATED",
                "R2C_PROVENANCE")
        require(isinstance(s.get("answer"), str) and len(s["answer"]) >= 100,
                "R2C_ANSWER")
        require(isinstance(s.get("tags"), list) and len(s["tags"]) >= 4 and
                all(isinstance(t, str) and len(t) > 2 for t in s["tags"]), "R2C_TAGS")
        require(isinstance(s.get("questions"), list) and len(s["questions"]) == 2 and
                all(isinstance(q, str) and len(q) >= 30 for q in s["questions"]), "R2C_QA")
        require(s.get("formula") and s.get("dimensions"), "R2C_EQUATION_PROVENANCE")
        for question in s["questions"]:
            rows.append({"family": s["family"], "question": question, "answer": s["answer"],
                         "provenance": "PUBLIC_PRIMARY_SOURCE_AUTHOR_PARAPHRASE"})
    require(len(rows) == 12, "R2C_NEW_PAIR_COUNT")
    return data, digest, rows

def full_training_rows(video_path, papers_path, cards_path):
    video, vsha = load_json(video_path)
    papers, psha = load_json(papers_path)
    old = training_rows(video, papers)
    cards, csha, additional = new_source_rows(cards_path)
    rows = old + additional
    require(len(rows) == 36 and len({x["family"] for x in rows}) == 13, "R2C_TRAIN_INVENTORY")
    require(not {r["family"] for r in rows} & HOLDOUT_FAMILIES, "R2C_EVAL_LEAK")
    return rows, (vsha, psha, csha), cards

def train(video_path, papers_path, cards_path, outdir, epochs=30, seed=20261111):
    require(isinstance(epochs, int) and 1 <= epochs <= 40, "R2C_CPU_LIMIT")
    rows, digests, cards = full_training_rows(video_path, papers_path, cards_path)
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset
    torch.set_num_threads(min(2, os.cpu_count() or 1))
    random.seed(seed)
    torch.manual_seed(seed)
    vocab = make_vocab(rows)
    model = build_model(len(vocab))
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.0015, weight_decay=0.003)
    x, y = prepare_tensors(rows, {word: i for i, word in enumerate(vocab)})
    losses = []
    for ep in range(epochs):
        torch.manual_seed(seed + ep)
        model.train()
        loss_total, batches = 0.0, 0
        gen = torch.Generator().manual_seed(seed + ep)
        for xb, yb in DataLoader(TensorDataset(x, y), batch_size=8, shuffle=True, generator=gen):
            optimizer.zero_grad(set_to_none=True)
            logits = model(xb, yb[:, :-1])
            loss = nn.functional.cross_entropy(
                logits.reshape(-1, logits.size(-1)), yb[:, 1:].reshape(-1),
                ignore_index=PAD)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            loss_total += float(loss.item())
            batches += 1
        if ep == 0 or ep == epochs - 1 or (ep + 1) % 5 == 0:
            losses.append({"epoch": ep+1, "teacher_forced_loss": round(loss_total/batches, 6)})
    p = Path(outdir)
    p.mkdir(parents=True, exist_ok=True)
    checkpoint = p / "r2c_research_only.pt"
    torch.save({
        "schema": SCHEMA, "model_state": model.state_dict(), "vocab": vocab,
        "width": 64, "seed": seed, "epochs": epochs, "train_input_shas": list(digests),
        "auto_deploy": False, "holdout_data_in_training": False,
    }, checkpoint)
    receipt = {
        "schema": "janus.tachyon.r2c.training_receipt.v1",
        "checkpoint_sha256": sha(checkpoint.read_bytes()),
        "train_input_shas": list(digests),
        "training_pairs": len(rows), "training_families": len({r["family"] for r in rows}),
        "new_primary_source_families": len(EXPECTED),
        "parameter_count": sum(p.numel() for p in model.parameters()),
        "training_loss": losses,
        "independent_external_evaluation": False,
        "lab_clock_labels_read": False, "lab_clock_measurements_read": False,
        "scientifically_admitted": False, "auto_deployed": False,
        "authority_delta": 0, "status": "TRAINED_RESEARCH_ONLY_HOLD",
    }
    (p / "training_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False)+"\n", encoding="utf8")
    return receipt

def _terms(s):
    return {t for t in tokens(s) if len(t) > 2 and t not in STOP}

def retrieve(question, cards, top_k=2):
    require(1 <= top_k <= 3 and isinstance(question, str) and 6 <= len(question) < 3000,
            "R2C_QUERY_LIMIT")
    query = _terms(question)
    candidates = []
    for s in cards["sources"]:
        document = " ".join(s["tags"] + s["questions"] + [s["title"], s["answer"]])
        keyword_set = _terms(document)
        matched = query & keyword_set
        # Public, deterministic lexical support; not a learned entailment check.
        score = len(matched) / max(1.0, math.sqrt(len(query) * len(keyword_set)))
        if len(matched) >= 2 and score >= 0.07:
            candidates.append((score, s["family"], s, sorted(matched)))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [{"family": s["family"], "doi": s["doi"], "url": s["url"],
             "title": s["title"], "domain": s["domain"], "answer": s["answer"],
             "formula": s["formula"], "dimensions": s["dimensions"],
             "matched_query_terms": terms, "lexical_support_score": round(score, 6)}
            for score, _, s, terms in candidates[:top_k]]

def physics_sanity(hits):
    """Independent deterministic checks of elementary identities, NOT peer review."""
    from itertools import product
    results = []
    for hit in hits:
        family = hit["family"]
        if family == "SR_EINSTEIN_1905":
            gamma_inverse = math.sqrt(1 - 0.6**2)
            result = {"test": "proper_time_ratio_beta_0.6", "actual": gamma_inverse,
                      "expected": 0.8, "passed": abs(gamma_inverse-0.8) < 1e-12}
        elif family == "GR_SHAPIRO_1964":
            # [G] [M] / [c]^3 = (m^3 kg^-1 s^-2)(kg)/(m s^-1)^3 = s.
            dim = {"metres": 3-3, "kilograms": -1+1, "seconds": -2+3}
            result = {"test": "shapiro_GM_over_c_cubed_dimensions",
                      "actual": dim, "expected": {"metres": 0, "kilograms": 0, "seconds": 1},
                      "passed": dim == {"metres": 0, "kilograms": 0, "seconds": 1}}
        elif family == "BELL_1964":
            vals = [abs(a0*b0+a0*b1+a1*b0-a1*b1)
                    for a0,a1,b0,b1 in product((-1,1), repeat=4)]
            result = {"test": "local_deterministic_CHSH_algebra",
                      "actual": max(vals), "expected": 2,
                      "passed": max(vals) == 2}
        elif family == "QBAYES_2002":
            p = 0.3*1.0 + 0.7*0.0
            result = {"test": "born_rule_two_level_projector_example",
                      "actual": p, "expected": 0.3, "passed": abs(p-0.3)<1e-12}
        else:
            result = {"test": "no_claim_specific_numeric_or_dimensional_test",
                      "actual": None, "expected": None, "passed": None}
        result["family"] = family
        result["scope"] = "ELEMENTARY_SANITY_ONLY_NOT_PHYSICAL_VERIFICATION"
        results.append(result)
    return results

def review_gate(question, matches):
    """Fail-closed; even matched statements remain non-independent paraphrases."""
    if not matches:
        return {"decision": "ABSTAIN", "reason": "NO_SOURCE_MATCH",
                "review_required": True, "claim_proven": False}
    return {"decision": "SOURCE_GROUNDED_DRAFT", "reason": "CITED_AUTHOR_PARAPHRASE",
            "review_required": True, "claim_proven": False}

def explain(question, cards, checkpoint_path=None):
    hits = retrieve(question, cards)
    gate = review_gate(question, hits)
    result = {"question": question, "gate": gate, "physics_sanity": physics_sanity(hits), "sources": [
        {k: hit[k] for k in ("family","doi","url","title","matched_query_terms",
                             "lexical_support_score","formula","dimensions")}
        for hit in hits],
        "supported_source_paraphrase": hits[0]["answer"] if hits else None,
        "neural_unverified_draft": None,
        "scientific_limit": "SOURCE_RETRIEVAL_AND_LANGUAGE_GENERATION_DO_NOT_PROVE_CAUSAL_PHYSICS",
        "lab_measurements_consulted": False, "claim_of_retrocausal_signal": False,
    }
    if checkpoint_path is not None and hits:
        import torch
        torch.set_num_threads(min(2, os.cpu_count() or 1))
        state = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        require(state.get("schema") == SCHEMA and
                state.get("auto_deploy") is False and
                state.get("holdout_data_in_training") is False, "R2C_CHECKPOINT_HOLD")
        model = build_model(len(state["vocab"]), state["width"])
        model.load_state_dict(state["model_state"])
        # Candidate text is never admitted, even if word overlap looks convincing.
        result["neural_unverified_draft"] = generate(model, state["vocab"], question)
    return result

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    a = sub.add_parser("train")
    a.add_argument("--video", required=True)
    a.add_argument("--papers", required=True)
    a.add_argument("--cards", required=True)
    a.add_argument("--outdir", required=True)
    a.add_argument("--epochs", type=int, default=30)
    b = sub.add_parser("explain")
    b.add_argument("--cards", required=True)
    b.add_argument("--question", required=True)
    b.add_argument("--checkpoint")
    b.add_argument("--out", required=True)
    opt = ap.parse_args()
    if opt.mode == "train":
        result = train(opt.video, opt.papers, opt.cards, opt.outdir, opt.epochs)
    else:
        cards, digest, _ = new_source_rows(opt.cards)
        result = explain(opt.question, cards, opt.checkpoint)
        result["cards_sha256"] = digest
        result["model_scientifically_admitted"] = False
        out = Path(opt.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("x", encoding="utf8") as f:
            json.dump(result, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k not in
                      ("neural_unverified_draft", "supported_source_paraphrase", "training_loss")},
                     ensure_ascii=False, sort_keys=True))

if __name__ == "__main__":
    main()
