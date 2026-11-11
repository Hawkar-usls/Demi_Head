"""R3.7: real measured-data provenance/split/forecast guards (offline fixtures)."""
import copy
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import tempfile
import unittest

from tachyon.r37_real_ocv_evaluator import (
    EARLY_HOURS, MODEL_TYPES, TRAIN, TEST, VALIDATION,
    manifest_check, parse_csv, git_blob_sha1,
    fit_on_early, predict, eval_trace, choose_frozen, run, sha
)

MANIFEST=Path("data/tachyon/r37/real_ocv_group_holdout_manifest.json")

def fixture(battery,kind):
    # 1441 full-day hours, self-authored only for unit tests. No public lab
    # rows or confidential answers in this fixture.
    header="Timestamp [h],BATT_999_OCV_V_100-SOC\n"
    vals=[]
    for k in range(1441):
        t=k/60.
        direction=-1 if kind=="charge" else 1
        v=3.45+direction*(.03*math.exp(-t/.4)+.01*math.exp(-t/6))
        vals.append(f"{t:.12f},{v:.9f}\n")
    return (header+"".join(vals)).encode("utf8")

class R37RealHoldout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=json.loads(MANIFEST.read_text(encoding="utf8"))
        manifest_check(cls.original)

    def test_source_license_and_blob_pins_and_battery_disjoint(self):
        m=self.original
        self.assertEqual(len(m["input_files"]),16)
        self.assertEqual(m["source_license"],"CC BY 4.0")
        self.assertFalse(m["rights_and_security"]["neural_weight_training_authorized"])
        self.assertEqual(set(TRAIN)&set(VALIDATION),set())
        self.assertEqual(set(TRAIN)&set(TEST),set())
        self.assertEqual(set(VALIDATION)&set(TEST),set())
        self.assertEqual({x["battery_group"] for x in m["input_files"]},
                         set(TRAIN+VALIDATION+TEST))

    def test_cannot_change_test_group_or_grant_self_neural_training(self):
        m=copy.deepcopy(self.original)
        m["experiment_pre_registration"]["test_batteries"]=["APR"]
        with self.assertRaisesRegex(ValueError,"R37_GROUP_SPLIT_OR_MODEL_SELECTION_DRIFT"):
            manifest_check(m)
        m=copy.deepcopy(self.original)
        m["rights_and_security"]["neural_weight_training_authorized"]=True
        with self.assertRaisesRegex(ValueError,"R37_NO_AUTO_PROMOTION"):
            manifest_check(m)

    def test_git_blob_integrity_verified_and_mismatch_rejected(self):
        raw=fixture("APR","charge")
        f=copy.deepcopy(self.original["input_files"][0])
        f.update(size_bytes=len(raw),github_blob_sha1=git_blob_sha1(raw))
        self.assertEqual(len(parse_csv(raw,f)),1)
        bad=copy.deepcopy(f);bad["github_blob_sha1"]="0"*40
        with self.assertRaisesRegex(ValueError,"R37_ORIGINAL_SOURCE_GIT_BLOB_MISMATCH"):
            parse_csv(raw,bad)

    def test_nonmonotonic_or_impossible_real_data_rejected(self):
        raw=fixture("APR","charge")
        f=copy.deepcopy(self.original["input_files"][0])
        text=raw.decode("utf8")
        broken=text.replace("0.000000000000,","12.000000000000,",1)
        altered=broken.encode("utf8")
        f.update(size_bytes=len(altered),github_blob_sha1=git_blob_sha1(altered))
        with self.assertRaisesRegex(ValueError,"R37_OUT_OF_ORDER_TIME"):
            parse_csv(altered,f)
        bad=text.replace("3.490000000","nan")
        # If value not found in this fixture, change an exact known printed
        # numeric value in the second line deterministically.
        lines=bad.splitlines(True)
        lines[1]=lines[1].split(",")[0]+",nan\n"
        altered="".join(lines).encode("utf8")
        f.update(size_bytes=len(altered),github_blob_sha1=git_blob_sha1(altered))
        with self.assertRaisesRegex(ValueError,"R37_UNPHYSICAL_OCV_OR_TIME"):
            parse_csv(altered,f)

    def test_early_window_stops_at_hour_four(self):
        f=copy.deepcopy(self.original["input_files"][0])
        raw=fixture("APR","charge")
        f.update(size_bytes=len(raw),github_blob_sha1=git_blob_sha1(raw))
        points=parse_csv(raw,f)[0][1]
        fit=fit_on_early(points,"single_exp")
        self.assertTrue(fit["taus"])
        self.assertTrue(math.isfinite(predict(fit,20.)))
        report=eval_trace(points)
        self.assertEqual(set(report),set(MODEL_TYPES))
        self.assertEqual(report["single_exp"]["forecast_count"],1200)

    def test_selection_only_on_validation_and_no_preapproval(self):
        rows=[]
        for b in VALIDATION:
            scores={m:{"forecast_MAE_V":.03 if m=="single_exp" else .04,
                       "forecast_RMSE_V":.03,"forecast_count":1200}
                    for m in MODEL_TYPES}
            rows.append({"battery_group":b,"scores":scores})
        f=choose_frozen(rows,self.original)
        self.assertEqual(f["model_family_selected_by_validation"],"single_exp")
        self.assertFalse(f["candidate_is_selected"])
        self.assertEqual(len(f["pretest_selection_receipt_sha256"]),64)
        self.assertEqual(f["scientific_admission"],"HOLD")

    def test_real_data_test_groups_are_fetched_only_after_seal_written(self):
        fixture_manifest=copy.deepcopy(self.original)
        blobs={}
        for f in fixture_manifest["input_files"]:
            raw=fixture(f["battery_group"],
                        "charge" if "charge" in f["path"]
                        and "discharge" not in f["path"] else "discharge")
            f["github_blob_sha1"]=git_blob_sha1(raw)
            f["size_bytes"]=len(raw)
            blobs[f["path"]]=raw
        manifest_check(fixture_manifest)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"manifest.json"
            out=Path(td)/"out"
            path.write_text(json.dumps(fixture_manifest))
            fetch_order=[]
            def fetch(f):
                fetch_order.append(f["group_role"])
                if f["group_role"]=="TEST":
                    self.assertTrue(
                        (out/"r37_pretest_selection_seal.json").exists())
                return blobs[f["path"]]
            result=run(path,out,fetch)
            self.assertEqual(result["raw_source_files_received"],16)
            self.assertEqual(result["total_traces_test"],4)
            self.assertEqual(result["scientific_admission"],"HOLD")
            self.assertFalse(result["neural_weights_trained"])
            self.assertTrue(result["no_test_battery_used_to_choose_formula_structure"])
            self.assertEqual(fetch_order[:8],["TRAIN"]*8)
            self.assertEqual(fetch_order[8:12],["VALIDATION"]*4)
            self.assertEqual(fetch_order[12:],["TEST"]*4)
            self.assertEqual(result["receipt_sha256"],
                sha({k:v for k,v in result.items() if k!="receipt_sha256"}))
            with self.assertRaisesRegex(ValueError,"R37_FAIL_CLOSED_EXISTING_OUTPUT"):
                run(path,out,fetch)

if __name__=="__main__":
    unittest.main()
