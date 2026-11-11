"""R2F general-topic fallback tests are PUBLIC and developer-authored only."""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
import unittest

from tachyon.science_generator import ScienceHold
from tachyon.r2d_audit import public_split
from tachyon.r2e_hybrid import load_cards
from tachyon.r2f_general_router import load_general_cards, route_question, batch_route

class R2FGeneralRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.physics=load_cards("data/tachyon/r2c/science_cards.json")
        cls.general=load_general_cards("data/tachyon/r2f/general_source_cards.json")
        cls.questions,cls.key=public_split("data/tachyon/r2d/public_dev_challenge.json")

    def test_former_four_ood_questions_are_no_longer_all_dead_ends(self):
        actual={x["case_id"]:x["response"] for x in
                batch_route(self.questions,self.physics,self.general)["cases"]}
        self.assertEqual(actual["nas"]["decision"],"GENERAL_SOURCE_ANSWER")
        self.assertEqual(actual["garden"]["decision"],"GENERAL_SOURCE_ANSWER")
        self.assertEqual(actual["cooking"]["decision"],"GENERAL_SOURCE_ANSWER")
        self.assertEqual(actual["football"]["decision"],"NEEDS_CLARIFICATION")
        for cid in ("nas","garden","cooking"):
            a=actual[cid]
            self.assertTrue(a["citations"])
            self.assertTrue(a["answer"])
            self.assertFalse(a["answer_independently_verified"])
            self.assertFalse(a["scientifically_admitted"])
        self.assertIsNone(actual["football"]["answer"])
        self.assertTrue(actual["football"]["question_to_user"])
        self.assertEqual(actual["football"]["citations"],[])

    def test_physics_still_routes_to_research_scope(self):
        q="Для скорости v/c=0.8 какое dτ/dt показывают движущиеся идеальные часы?"
        result=route_question(q,self.physics,self.general)
        self.assertEqual(result["decision"],"PHYSICS_RESEARCH_DRAFT")
        self.assertEqual(result["physics_decision"],"DETERMINISTIC_FORMULA_WITH_CITED_SOURCE")
        self.assertFalse(result["scientifically_admitted"])

    def test_wrong_physics_parameters_not_hidden_by_web_fallback(self):
        q="Для часов при v/c=1.2 дай физически корректное отношение dτ/dt"
        result=route_question(q,self.physics,self.general)
        self.assertEqual(result["decision"],"NEEDS_CLARIFICATION")
        self.assertEqual(result["reason"],"UNSUPPORTED_OR_INVALID_PARAMETERS")
        self.assertFalse(result["neural_generated_claim_used"])

    def test_unknown_question_gets_search_request_not_fake_answer(self):
        q="Что известно про структуру облаков Нептуна в 2026 году?"
        result=route_question(q,self.physics,self.general)
        self.assertEqual(result["decision"],"EXTERNAL_SEARCH_REQUIRED")
        self.assertEqual(result["external_lookup_query"],q)
        self.assertIsNone(result["answer"])
        self.assertEqual(result["citations"],[])
        self.assertTrue(result["needs_live_source"])

    def test_specific_live_sports_requires_external_source(self):
        q="Как сыграл Реал Мадрид в Ла Лиге сегодня?"
        result=route_question(q,self.physics,self.general)
        self.assertEqual(result["decision"],"EXTERNAL_SEARCH_REQUIRED")
        self.assertTrue(result["needs_live_source"])
        self.assertIsNone(result["answer"])

    def test_unverified_citation_host_is_rejected(self):
        o=copy.deepcopy(self.general)
        o["cards"][0]["citations"][0]["url"]="https://evil.example/mimic-energy"
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"cards.json"
            p.write_text(json.dumps(o,ensure_ascii=False),encoding="utf8")
            with self.assertRaisesRegex(ScienceHold,"UNTRUSTED_CITATION_HOST"):
                load_general_cards(p)

    def test_smuggled_scientific_authority_is_rejected(self):
        o=copy.deepcopy(self.general)
        o["cards"][0]["lab_measurements_prove_retrocausality"]=True
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"cards.json"
            p.write_text(json.dumps(o,ensure_ascii=False),encoding="utf8")
            with self.assertRaisesRegex(ScienceHold,"UNRECOGNIZED_CARD_FIELD"):
                load_general_cards(p)

    def test_cards_did_not_change_training_or_scientific_admission(self):
        results=batch_route(self.questions,self.physics,self.general)
        self.assertFalse(results["model_training_performed"])
        self.assertFalse(results["scientific_admission"])
        self.assertFalse(results["general_web_search_in_this_runner"])
        for item in results["cases"]:
            self.assertFalse(item["response"]["janus_ocean_modified"])
            self.assertFalse(item["response"]["scientifically_admitted"])

if __name__=="__main__":
    unittest.main()
