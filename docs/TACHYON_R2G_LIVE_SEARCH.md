# TACHYON-R2G — live evidence broker for arbitrary PUBLIC queries

## What is implemented

R2F currently returns EXTERNAL_SEARCH_REQUIRED on unknown topics, without fetching any sources. R2G consumes that routed request and can **actually query public provider APIs** when explicit public-network approval is supplied. It does not train or deploy a model.

Providers:

- **Wikimedia MediaWiki API** (`ru.wikipedia.org/w/api.php`) supplies short Russian encyclopedia lead extracts with the article URL and attribution. This is reference context, not independent fact-checking. Wikimedia requires an identifying User-Agent; the client sets one.
- **OpenAlex /works** (`api.openalex.org`) supplies scholarly bibliographic records with DOI and publication date, never copied journal abstracts or claims of independent peer review. Anonymous use is currently allowed for small query volumes, subject to rate limits.
- **Optional Brave Search** (`api.search.brave.com/res/v1/web/search`) supplies general web search snippets when a valid API key is explicitly provided to a trusted host. No key is committed; pull-request CI and demo CLI do not read GitHub secrets. Without a key, real-time sports results remain unavailable and the adapter reports WEB_PROVIDER_KEY_REQUIRED instead of a guessed score.

## Safety boundary

The API endpoints are exact fixed HTTPS hosts, with no redirects and at most 160 KB JSON per request, 7-second timeout, maximum 4 results per provider and 3 provider calls per question. The adapter never fetches search-result URLs. It validates result links (HTTPS, no local hosts/IPs or embedded credentials) before displaying them. Retrieved HTML snippets and titles are UNTRUSTED DATA, never tool instructions.

Requests containing common obvious private markers (credentials, emails, URLs, file paths or IPv4 addresses) are blocked before network calls. This is a limited pattern-based guard, **not** a guarantee to detect all private or sensitive data. Therefore, the network interface defaults to opt-out; only explicitly approved PUBLIC questions may be submitted. Do not route private JANUS data, Meta Registry secrets, local NAS logs or user records into the provider.

## Evidence protocol

Each reply reports retrieval timestamp, provider, source URL, citation type, title, overlap diagnostic and publication date if supplied. A query without relevant matches returns NO_VERIFIABLE_SOURCE. A source extract only becomes an ATTRIBUTED_EXTRACT_AVAILABLE when the match is sufficiently relevant; this is **source text with attribution, not an independently verified answer**. Scholarly metadata without an abstract is evidence to inspect, not a physics explanation. Current events and sports require extra dated event verification; provider snippets do not automatically produce live final answers.

## Usage and budget

Run the public demo only with the explicit opt-in flag:

```bash
python -m tachyon.r2g_live_broker --questions data/tachyon/r2g/public_live_smoke_questions.json --physics-cards data/tachyon/r2c/science_cards.json --general-cards data/tachyon/r2f/general_source_cards.json --public-network-approved --providers wikipedia,openalex --out artifacts/tachyon-r2g/live-public-evidence.json
```

For a separately approved host application, the Python `route_with_external_search` function can be called with `providers=("brave",)` and a secret passed at runtime. Brave requires a subscription token. Secrets must not be exposed to untrusted PR workflows or printed to logs. The code never stores the key.

Public provider API documentation: https://www.mediawiki.org/wiki/API:Search ; https://www.mediawiki.org/wiki/Wikimedia_APIs/Access_policy ; https://help.openalex.org/api/ ; https://api-dashboard.search.brave.com/api-reference/web/search/get

## Validation

GitHub Actions runs offline adversarial tests for injection, private requests, failure, unsafe links, inconsistent dates, silent physics gate override, and no-key live sports. Separate network smoke directly queries the two keyless APIs with three nonprivate sample searches and exercises a 3-question source broker flow. Failures must be reported honestly. The CI does not automatically merge or deploy the code.

## Scientific status

Existing R2B, R2C and R2D frozen scientific evaluation has not changed. External blind scientific assessment (issue #74) remains pending. R2G is only a public-source discovery and citation layer, not a scientific breakthrough or an autonomous neural generalist. R2F references remain separate.

Status: TACHYON_R2G / LIVE_EVIDENCE_RESEARCH_CANDIDATE / SCIENTIFIC_HOLD / MAIN_AND_OCEAN_UNCHANGED.
