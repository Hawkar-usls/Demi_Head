"""TACHYON R4.0: bounded causal-screening examples, not a physics theorem.

Only elementary finite-dimensional quantum channels / toy maps are executed.
Spacetime-QFT and physical retro-signaling claims ALWAYS require independent review.
No trained model, future target, production inference, or live external data is used.
"""
from __future__ import annotations
import math

I = ((1+0j, 0j), (0j, 1+0j))
X = ((0j, 1+0j), (1+0j, 0j))
P0 = ((1+0j, 0j), (0j, 0j))
P1 = ((0j, 0j), (0j, 1+0j))
RESET1 = ((0j, 1+0j), (0j, 0j))


def dagger(a):
    return tuple(tuple(a[j][i].conjugate() for j in range(len(a))) for i in range(len(a[0])))


def mul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(len(b)))
                       for j in range(len(b[0]))) for i in range(len(a)))


def kron(a, b):
    return tuple(tuple(a[i // len(b)][j // len(b[0])] *
                       b[i % len(b)][j % len(b[0])]
                       for j in range(len(a[0]) * len(b[0])))
                 for i in range(len(a) * len(b)))


def add_many(matrices):
    return tuple(tuple(sum(m[i][j] for m in matrices)
                       for j in range(len(matrices[0][0])))
                 for i in range(len(matrices[0])))


def trace(a):
    return sum(a[i][i] for i in range(len(a)))


def is_cptp_kraus(kraus, atol=1e-12):
    """A two-dimensional Kraus completeness check: sum K^dagger K == I."""
    if not kraus:
        return False
    summed = add_many([mul(dagger(k), k) for k in kraus])
    return all(abs(summed[i][j] - I[i][j]) <= atol
               for i in range(2) for j in range(2))


def bell_phi_plus_density():
    v = (1 / math.sqrt(2), 0, 0, 1 / math.sqrt(2))
    return tuple(tuple(complex(v[i] * v[j]) for j in range(4))
                 for i in range(4))


def local_b_map(rho_ab, kraus, *, conditioned=False):
    """Apply B-only Kraus maps and return reduced A density.

    If conditioned, the trace is renormalized and a *late herald is required*.
    Such a branch is NOT an unconditional channel available to earlier A.
    """
    if not conditioned and not is_cptp_kraus(kraus):
        raise ValueError("Unconditioned local channel must be trace preserving")
    outputs = []
    for k in kraus:
        op = kron(I, k)
        outputs.append(mul(mul(op, rho_ab), dagger(op)))
    joint = add_many(outputs)
    probability = trace(joint)
    if conditioned:
        if abs(probability) <= 1e-12:
            raise ValueError("Zero probability postselection")
        joint = tuple(tuple(x / probability for x in row) for row in joint)
    a = tuple(tuple(sum(joint[2*i+b][2*j+b] for b in range(2))
                    for j in range(2)) for i in range(2))
    return {"rho_a": a, "branch_probability": float(probability.real),
            "requires_late_herald": conditioned}


def a_z_probabilities(rho_a):
    return tuple(round(float(rho_a[i][i].real), 12) for i in range(2))


def finite_ctc_fixed_points(mapping):
    """Classical finite-state fixed points; NOT evidence a spacetime CTC exists."""
    if not mapping or any(not isinstance(v, int) or v < 0 or v >= len(mapping)
                          for v in mapping):
        raise ValueError("Mapping must be finite and closed")
    return [i for i, v in enumerate(mapping) if i == v]


def scalar_dispersion_diagnostic(k, mass_squared):
    """Natural units c=hbar=1. Negative mass^2 is an instability diagnostic.

    A group/phase velocity is not a front velocity or controllable signal speed.
    """
    if not all(math.isfinite(float(x)) for x in (k, mass_squared)):
        raise ValueError("Nonfinite parameters")
    w2 = k*k + mass_squared
    if w2 < 0:
        return {"regime": "EXPONENTIAL_INSTABILITY", "growth_rate": math.sqrt(-w2),
                "physical_superluminal_channel_proven": False}
    if w2 == 0:
        return {"regime": "ZERO_FREQUENCY_BOUNDARY", "physical_superluminal_channel_proven": False}
    w = math.sqrt(w2)
    return {"regime": "OSCILLATORY", "group_velocity_formal": abs(k / w),
            "front_velocity_inferred": False, "physical_superluminal_channel_proven": False}


QFT_FIELDS = ("metric_and_geometry", "chronology_horizon_type",
              "hadamard_state_and_domain", "renormalized_stress_tensor",
              "semiclassical_backreaction", "physical_boundary_conditions")
PROSPECTIVE_FIELDS = ("early_immutable_commit", "late_independent_entropy",
                      "independent_clock_and_leakage_audit", "unconditioned_all_trial_data",
                      "prespecified_null_and_multiplicity", "external_custodian",
                      "independent_replication")


def screen_claim(model):
    """Fail closed: never outputs VERIFIED_PHYSICAL_RETROCAUSALITY.

    Verdicts flag missing methodology, never validate an unexecuted QFT model.
    """
    typ = model.get("kind")
    if typ == "postselection":
        return {"verdict": "CONDITIONAL_ONLY__NO_BACKWARD_SIGNAL",
                "reason": "Herald-conditioned samples are not an earlier accessible channel"}
    if typ == "deutsch_ctc":
        return {"verdict": "HYPOTHETICAL_FIXED_POINT__PHYSICAL_INTERFACE_UNVERIFIED"}
    if typ == "ctc_spacetime":
        missing = [k for k in QFT_FIELDS if not model.get(k)]
        if missing:
            return {"verdict": "HOLD_QFT_GEOMETRY_OR_BACKREACTION_INCOMPLETE", "missing": missing}
        return {"verdict": "HUMAN_QFT_REVIEW_REQUIRED__NOT_PHYSICAL_PROOF",
                "reason": "A manifest cannot verify the Hadamard condition or solve semiclassical gravity"}
    if typ == "prospective_backward_signal":
        missing = [k for k in PROSPECTIVE_FIELDS if not model.get(k)]
        if missing:
            return {"verdict": "HOLD_PROSPECTIVE_CAUSAL_WITNESSES_MISSING", "missing": missing}
        return {"verdict": "READY_FOR_EXTERNAL_EXAM__NO_RETROCAUSAL_RESULT"}
    if typ == "tachyonic_scalar":
        return {"verdict": "MASS_SIGN_ALONE_NOT_FTL_EVIDENCE"}
    return {"verdict": "ABSTAIN_UNSUPPORTED_MODEL_CLASS", "supported_kinds":
            ["postselection", "deutsch_ctc", "ctc_spacetime",
             "prospective_backward_signal", "tachyonic_scalar"]}
