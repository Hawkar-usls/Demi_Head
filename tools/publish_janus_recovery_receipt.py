"""Append a verified public recovery receipt to a fixed Demi_Head ledger branch."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen

REPOSITORY = "Hawkar-usls/Demi_Head"
BRANCH = "janus-recovery"
BASE = "https://api.github.com/repos/" + REPOSITORY


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise ValueError("FIXED_STORAGE_REPOSITORY_REQUIRED")
    value = json.loads(args.manifest.read_text())
    if (value.get("schema") != "janus.repository_recovery.v1" or
            value.get("status") != "REPOSITORY_RECOVERY_VERIFIED" or
            value.get("source_repository") != "Hawkar-usls/Janus-Demiurge" or
            not all(value.get("checks", {}).get(key) is True for key in
                    ("bundle_sha256_matches", "bundle_verify", "git_fsck_full_strict", "all_refs_match"))):
        raise ValueError("VERIFIED_REPOSITORY_RECOVERY_REQUIRED")
    run_id, attempt = os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"]
    if not re.fullmatch(r"\d+", run_id) or not re.fullmatch(r"\d+", attempt):
        raise ValueError("INVALID_RUN_BINDING")
    artifact_id = os.environ["RECOVERY_ARTIFACT_ID"]
    if not re.fullmatch(r"\d+", artifact_id):
        raise ValueError("ARTIFACT_REQUIRED")
    value["run_url"] = f"https://github.com/{REPOSITORY}/actions/runs/{run_id}"
    value["artifact_url"] = value["run_url"] + f"/artifacts/{artifact_id}"
    value["artifact_retention_days"] = 7
    value["artifact_id"] = int(artifact_id)
    value["workflow_sha"] = os.environ["GITHUB_SHA"]
    value["storage_status"] = "GITHUB_ACTIONS_ARTIFACT_STORED"
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()

    def api(path, data=None):
        request = Request(BASE + path, data=json.dumps(data).encode() if data is not None else None,
                          headers={"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                                   "Accept": "application/vnd.github+json", "Content-Type": "application/json",
                                   "User-Agent": "JANUS-Recovery-Ledger"})
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    try:
        previous = api("/git/ref/heads/" + BRANCH)["object"]["sha"]
    except HTTPError as error:
        if error.code != 404:
            raise
        previous = api("/git/ref/heads/main")["object"]["sha"]
        api("/git/refs", {"ref": "refs/heads/" + BRANCH, "sha": previous})
    history_path = f"janus-recovery/history/{run_id}-{attempt}.json"
    # Git Data API publishes latest + immutable per-run receipt in one commit.
    parent = api("/git/commits/" + previous)
    try:
        api("/contents/" + history_path + "?ref=" + BRANCH)
    except HTTPError as error:
        if error.code != 404:
            raise
    else:
        raise ValueError("RUN_RECEIPT_ALREADY_EXISTS")
    blob = api("/git/blobs", {"content": base64.b64encode(payload).decode(), "encoding": "base64"})
    tree = api("/git/trees", {"base_tree": parent["tree"]["sha"], "tree": [
        {"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]}
        for path in (history_path, "janus-recovery/LATEST.json")]})
    commit = api("/git/commits", {"message": "Record verified JANUS recovery " + run_id,
                                  "tree": tree["sha"], "parents": [previous]})
    request = Request(BASE + "/git/refs/heads/" + BRANCH, method="PATCH",
                      data=json.dumps({"sha": commit["sha"], "force": False}).encode(),
                      headers={"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                               "Content-Type": "application/json", "User-Agent": "JANUS-Recovery-Ledger"})
    with urlopen(request, timeout=30):
        pass
    print("RECOVERY_RECEIPT=https://github.com/" + REPOSITORY + "/blob/" + BRANCH + "/janus-recovery/LATEST.json")


if __name__ == "__main__":
    main()
