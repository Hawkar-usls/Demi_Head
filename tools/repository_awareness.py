from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "repository_awareness.json"


class InventoryError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise InventoryError(f"{path} must contain a JSON object")
    return value


def token_from_env(names: list[str]) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def normalize_repository(raw: dict[str, Any]) -> dict[str, Any]:
    private = bool(raw.get("private", False))
    visibility = raw.get("visibility") or ("private" if private else "public")
    return {
        "name": str(raw.get("name", "")),
        "full_name": str(raw.get("full_name", "")),
        "default_branch": str(raw.get("default_branch") or "UNKNOWN"),
        "visibility": str(visibility),
        "archived": bool(raw.get("archived", False)),
        "fork": bool(raw.get("fork", False)),
        "html_url": raw.get("html_url"),
        "description": raw.get("description"),
    }


def fetch_owner_inventory(*, owner: str, api_url: str, token: str | None) -> list[dict[str, Any]]:
    if not token:
        raise InventoryError("Authenticated owner inventory requires GITHUB_TOKEN or GH_TOKEN")

    endpoint = api_url.rstrip("/") + "/user/repos"
    query = {
        "affiliation": "owner",
        "per_page": "100",
        "sort": "full_name",
        "direction": "asc",
    }

    repositories: list[dict[str, Any]] = []
    page = 1
    while True:
        query["page"] = str(page)
        url = endpoint + "?" + urllib.parse.urlencode(query)
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "JANUS-DemiHead-Repository-Awareness/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": f"Bearer {token}",
        }
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise InventoryError(f"GitHub inventory request failed: HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise InventoryError(f"GitHub inventory request failed: {exc.reason}") from exc

        if not isinstance(payload, list):
            raise InventoryError("GitHub inventory response must be a list")

        owned = [
            item
            for item in payload
            if isinstance(item, dict)
            and str(item.get("owner", {}).get("login", "")).lower() == owner.lower()
        ]
        repositories.extend(normalize_repository(item) for item in owned)

        if len(payload) < 100:
            break
        page += 1

    repositories.sort(key=lambda item: item["full_name"].lower())
    return repositories


def build_inventory(*, owner: str, self_repository: str, repositories: list[dict[str, Any]], source: str, authenticated: bool) -> dict[str, Any]:
    normalized = [normalize_repository(item) if "private" in item else dict(item) for item in repositories]
    normalized.sort(key=lambda item: str(item.get("full_name", "")).lower())

    public_count = sum(item.get("visibility") == "public" for item in normalized)
    private_count = sum(item.get("visibility") == "private" for item in normalized)
    archived_count = sum(bool(item.get("archived")) for item in normalized)
    other_count = sum(item.get("full_name") != self_repository for item in normalized)

    return {
        "schema": "janus.demihead.repository_portfolio.runtime.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "owner": owner,
        "self_repository": self_repository,
        "source": source,
        "authenticated_inventory": authenticated,
        "accounting": {
            "repository_count": len(normalized),
            "other_repository_count": other_count,
            "public_repository_count": public_count,
            "private_repository_count": private_count,
            "archived_repository_count": archived_count,
        },
        "invariants": {
            "repository_awareness_is_context_not_authority": True,
            "discovery_grants_write_permission": False,
            "repository_count_is_evidence_count": False,
            "fork_origin_is_idea_ownership": False,
        },
        "repositories": normalized,
    }


def save_local_inventory(path: Path, inventory: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def load_best_available(config: dict[str, Any]) -> dict[str, Any]:
    discovery = config["discovery"]
    local_cache = ROOT / discovery["local_cache"]
    if local_cache.exists():
        return load_json(local_cache)
    return load_json(ROOT / discovery["public_snapshot"])


def find_repositories(inventory: dict[str, Any], needle: str) -> list[dict[str, Any]]:
    q = needle.casefold()
    matches = []
    for repo in inventory.get("repositories", []):
        haystack = " ".join(str(repo.get(key) or "") for key in ("name", "full_name", "description", "default_branch")).casefold()
        if q in haystack:
            matches.append(repo)
    return matches


def refresh(config: dict[str, Any], *, require_authenticated: bool = False) -> dict[str, Any]:
    discovery = config["discovery"]
    token = token_from_env(list(discovery.get("token_env_precedence", [])))
    if require_authenticated and not token:
        raise InventoryError("Authenticated owner inventory requested, but no GITHUB_TOKEN/GH_TOKEN is available")

    if token:
        repositories = fetch_owner_inventory(owner=config["owner"], api_url=discovery["api_url"], token=token)
        source = "github_authenticated_owner_inventory"
        authenticated = True
    else:
        public_snapshot = load_json(ROOT / discovery["public_snapshot"])
        repositories = list(public_snapshot.get("repositories", []))
        source = "committed_public_snapshot_no_token"
        authenticated = False

    inventory = build_inventory(
        owner=config["owner"],
        self_repository=config["self_repository"],
        repositories=repositories,
        source=source,
        authenticated=authenticated,
    )
    save_local_inventory(ROOT / discovery["local_cache"], inventory)
    return inventory


def print_status(inventory: dict[str, Any]) -> None:
    accounting = inventory.get("accounting", {})
    total = accounting.get("repository_count", accounting.get("public_repository_count", 0))
    other = accounting.get("other_repository_count", accounting.get("public_other_repository_count", 0))
    private = accounting.get("private_repository_count", "UNKNOWN_WITHOUT_AUTH")
    print(f"owner={inventory.get('owner')}")
    print(f"self={inventory.get('self_repository')}")
    print(f"source={inventory.get('source')}")
    print(f"repositories={total}")
    print(f"other_repositories={other}")
    print(f"private_repositories={private}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DemiHead repository-awareness inventory for the JANUS portfolio.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--require-authenticated", action="store_true")
    parser.add_argument("--find")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    config = load_json(Path(args.config))
    try:
        inventory = refresh(config, require_authenticated=args.require_authenticated) if args.refresh else load_best_available(config)
    except InventoryError as exc:
        print(f"repository-awareness: {exc}", file=sys.stderr)
        return 2

    result: Any = find_repositories(inventory, args.find) if args.find else inventory

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.find:
        for repo in result:
            print(f"{repo.get('full_name')} [{repo.get('visibility', 'unknown')}] branch={repo.get('default_branch', 'UNKNOWN')}")
    else:
        print_status(inventory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
