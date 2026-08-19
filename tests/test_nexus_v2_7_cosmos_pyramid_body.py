from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import cosmos_voice_pyramid_bridge as cvp  # noqa: E402
import nexus_habitat as v1  # noqa: E402
import nexus_habitat_v2_7 as v27  # noqa: E402


def committed(core, field):
    return {**core, field: cvp.digest(core)}


def valid_packet():
    experience_core = {
        "schema": "janus.cosmos.osiris_formula_experience.v1",
        "created_generation": 1,
        "formula_hash": "1" * 64,
        "residual_formula_hash": "2" * 64,
        "budget": 256,
        "provider": {"test": "provider"},
        "prior_status": "SAT",
        "prior_authorized": True,
        "prior_lane": "TEST",
        "found_k": None,
        "separator": None,
        "components": [],
        "prior_separator_certificate": None,
        "prior_minimality_proof": None,
        "route_reusable_after_revalidation": False,
        "sat_assignment": {"1": True},
        "unsat_memory_is_verdict_shortcut": False,
    }
    experience = committed(experience_core, "experience_commitment")
    state_core = {
        "schema": "janus.cosmos.osiris_origin_prime_state.v1",
        "state_type": "ORIGIN_PRIME",
        "generation": 1,
        "previous_state_commitment": "3" * 64,
        "position_commitment": "4" * 64,
        "experience_commitment": experience["experience_commitment"],
        "path_history_digest": "5" * 64,
        "return_commitment": "6" * 64,
        "provider": {"test": "provider"},
    }
    state = committed(state_core, "state_commitment")
    core = {
        "schema": cvp.PACKET_SCHEMA,
        "source": {
            "repository": cvp.COSMOS_REPOSITORY,
            "revision": cvp.COSMOS_SHA,
            "canonical_gate": "OSIRIS_V3_ORIGIN_PRIME_SPIRAL_COMPUTE",
            "state_store_schema": "janus.cosmos.osiris_spiral_state_store.v1",
        },
        "origin_prime": state,
        "bound_experience": experience,
        "mediation": {
            "required_mediator": "Hawkar-usls/Demi_Head",
            "voice_repository": cvp.VOICE_REPOSITORY,
            "voice_revision": cvp.VOICE_PROFILE_AUTHORITY_SHA,
            "physical_body_repository": cvp.ECHO_REPOSITORY,
            "physical_body_revision": cvp.ECHO_TESTED_SHA,
            "route": "COSMOS -> DEMIHEAD -> THE_VOICE_OF_JANUS -> ECHO_PYRAMID",
        },
        "voice_representation": {
            "profile_id": cvp.PROFILE_ID,
            "anchor_band_hz": [117.0, 121.0],
            "center_hz": 119.0,
            "q": 29.75,
            "gain_db": 11.5,
            "decay_s": 1.65,
            "role": "REPRESENTATION_AND_ACOUSTIC_COLORATION_ONLY",
            "frequencies_create_math_authority": False,
            "audio_output_is_evidence": False,
        },
        "control": {
            "direct_cosmos_to_echo_route_permitted": False,
            "demihead_mediation_required": True,
            "network_io_required": False,
            "automatic_playback": False,
            "automatic_microphone_start": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "scientific_boundary": {
            "P_VS_NP": "OPEN",
            "P_EQUALS_NP": "NOT_ESTABLISHED",
            "P_NOT_EQUALS_NP": "NOT_ESTABLISHED",
            "voice_profile_changes_solver_correctness": False,
            "acoustic_frequencies_are_proof": False,
        },
    }
    return {**core, "packet_sha256": cvp.digest(core)}


def valid_voice_receipt(mediation):
    packet = mediation["voice_request"]["inline_json"]["cosmos_packet"]
    core = {
        "schema": "janus.voice.cosmos_origin_prime_pyramid_receipt.v1",
        "contract": "VOICE_COSMOS_ORIGIN_PRIME_PYRAMID_RENDER_FROZEN_CONTRACT_V1",
        "status": "COSMOS_ORIGIN_PRIME_SONIFIED_WITH_PYRAMID_LANGUAGE_NOT_PLAYED",
        "request": {
            "request_id": mediation["voice_request"]["request_id"],
            "request_sha256": mediation["voice_request"]["request_sha256"],
            "intent_id": mediation["intent_id"],
            "source_repository": "Hawkar-usls/Demi_Head",
            "source_revision": mediation["voice_request"]["source"]["source_revision"],
        },
        "cosmos": {
            "repository": cvp.COSMOS_REPOSITORY,
            "revision": cvp.COSMOS_SHA,
            "packet_sha256": packet["packet_sha256"],
            "state_generation": packet["origin_prime"]["generation"],
            "state_commitment": packet["origin_prime"]["state_commitment"],
            "experience_commitment": packet["origin_prime"].get("experience_commitment"),
        },
        "sonification": {
            "base_wav_path": "/tmp/base.wav",
            "base_wav_sha256": "7" * 64,
            "canonical_json_sha256": mediation["voice_request"]["canonical_json_sha256"],
            "symbol_count": 16,
            "reversible_decode_established": False,
        },
        "pyramid_language": {
            "implementation": "src/pyramid_anchor_filter.py::Pyramid117121Filter",
            "profile_id": cvp.PROFILE_ID,
            "anchor_band_hz": [117.0, 121.0],
            "center_hz": 119.0,
            "q": 29.75,
            "gain_db": 11.5,
            "decay_s": 1.65,
        },
        "physical_body": {
            "repository": cvp.ECHO_REPOSITORY,
            "revision": cvp.ECHO_TESTED_SHA,
            "ready_for_local_pcm_handoff": True,
            "physical_playback_performed": False,
        },
        "output": {
            "wav_path": "/tmp/final.wav",
            "wav_sha256": "8" * 64,
            "sample_rate_hz": 44100,
            "frames": 100,
            "duration_s": 100 / 44100,
            "peak": 0.5,
        },
        "control": {
            "network_io_performed": False,
            "automatic_playback_performed": False,
            "microphone_opened": False,
            "shell_execution_performed": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "claim_boundary": {
            "audio_is_proof": False,
            "117_121_hz_is_sat_evidence": False,
            "measured_chamber_ir_used": False,
            "historical_intentional_tuning_claimed": False,
            "P_VS_NP": "OPEN",
        },
    }
    return {**core, "receipt_sha256": v1.sha256(core)}


class NexusV27CosmosPyramidBodyTests(unittest.TestCase):
    def setUp(self):
        self.packet = valid_packet()
        self.intent = "a" * 64
        self.mediation = cvp.build_mediation(
            self.intent,
            self.packet,
            demihead_revision="b" * 40,
            output_label="osiris_v27_test",
        )
        self.voice_receipt = valid_voice_receipt(self.mediation)

    def test_full_route_sequence_is_admitted(self):
        r1 = v27.build_cosmos_state_route(self.packet)
        r2 = v27.build_voice_envelope_route(self.mediation)
        r3 = v27.build_pcm_handoff_route(self.voice_receipt)
        r4 = v27.build_audio_receipt_route(self.voice_receipt)
        for route in (r1, r2, r3, r4):
            v27.validate_envelope(route)
            receipt = v27.route_receipt(route)
            self.assertFalse(receipt["routing"]["delivery_performed"])
            self.assertFalse(receipt["routing"]["playback_performed"])
            self.assertEqual(receipt["routing"]["authority_delta"], 0)
            self.assertEqual(receipt["claim_ceiling"]["P_VS_NP"], "OPEN")

    def test_intent_split_rejected_even_if_mediation_rehashed(self):
        bad = copy.deepcopy(self.mediation)
        bad["intent_id"] = "c" * 64
        core = dict(bad)
        core.pop("mediation_sha256", None)
        bad["mediation_sha256"] = cvp.digest(core)
        self.assertFalse(cvp.verify_mediation(bad))

    def test_cosmos_provider_tamper_rejected(self):
        bad = copy.deepcopy(self.packet)
        bad["source"]["revision"] = "0" * 40
        body = dict(bad); body.pop("packet_sha256", None)
        bad["packet_sha256"] = cvp.digest(body)
        with self.assertRaises(ValueError):
            cvp.validate_cosmos_packet(bad)

    def test_state_commitment_tamper_rejected(self):
        bad = copy.deepcopy(self.packet)
        bad["origin_prime"]["state_commitment"] = "0" * 64
        body = dict(bad); body.pop("packet_sha256", None)
        bad["packet_sha256"] = cvp.digest(body)
        with self.assertRaises(ValueError):
            cvp.validate_cosmos_packet(bad)

    def test_profile_tamper_rejected(self):
        bad = copy.deepcopy(self.packet)
        bad["voice_representation"]["center_hz"] = 120.0
        body = dict(bad); body.pop("packet_sha256", None)
        bad["packet_sha256"] = cvp.digest(body)
        with self.assertRaises(ValueError):
            cvp.validate_cosmos_packet(bad)

    def test_direct_cosmos_to_voice_rejected(self):
        direct = {
            "schema": v27.ENVELOPE_SCHEMA,
            "contract": v27.CONTRACT,
            "envelope_id": "direct-cosmos-voice",
            "source_head": "COSMOS",
            "target_head": "VOICE",
            "payload_kind": v27.ORIGIN_PRIME_STATE_PACKET,
            "payload_ref": {"sha256": self.packet["packet_sha256"], "locator": "memory://x"},
            "trace": [],
            "control": v27._control(),
        }
        with self.assertRaises(ValueError):
            v27.validate_envelope(direct)

    def test_direct_cosmos_to_echo_rejected(self):
        direct = {
            "schema": v27.ENVELOPE_SCHEMA,
            "contract": v27.CONTRACT,
            "envelope_id": "direct-cosmos-echo",
            "source_head": "COSMOS",
            "target_head": "ECHO_PYRAMID",
            "payload_kind": v27.ORIGIN_PRIME_STATE_PACKET,
            "payload_ref": {"sha256": self.packet["packet_sha256"], "locator": "memory://x"},
            "trace": [],
            "control": v27._control(),
        }
        with self.assertRaises(ValueError):
            v27.validate_envelope(direct)

    def test_route_cannot_claim_delivery_or_playback(self):
        route = v27.build_pcm_handoff_route(self.voice_receipt)
        for field in ("delivery_claimed", "playback_claimed"):
            bad = copy.deepcopy(route)
            bad["control"][field] = True
            with self.assertRaises(ValueError):
                v27.validate_envelope(bad)

    def test_authority_escalation_rejected(self):
        route = v27.build_cosmos_state_route(self.packet)
        bad = copy.deepcopy(route)
        bad["control"]["authority_delta"] = 1
        with self.assertRaises(ValueError):
            v27.validate_envelope(bad)

    def test_voice_provider_execution_pin_tamper_rejected(self):
        bad = copy.deepcopy(self.mediation)
        bad["providers"]["voice_execution"]["revision"] = "0" * 40
        core = dict(bad); core.pop("mediation_sha256", None)
        bad["mediation_sha256"] = cvp.digest(core)
        self.assertFalse(cvp.verify_mediation(bad))

    def test_snapshot_preserves_legacy_and_denies_direct_routes(self):
        snap = v27.habitat_snapshot()
        self.assertFalse(snap["global_control"]["legacy_cosmos_proof_gate_rewritten"])
        self.assertFalse(snap["global_control"]["direct_cosmos_to_voice_admitted"])
        self.assertFalse(snap["global_control"]["direct_cosmos_to_echo_admitted"])
        self.assertEqual(snap["global_control"]["P_VS_NP"], "OPEN")


if __name__ == "__main__":
    unittest.main()
