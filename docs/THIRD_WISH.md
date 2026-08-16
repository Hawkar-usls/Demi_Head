# Third Wish in DemiHead

## Genesis lineage

DemiHead records the normalized JANUS genesis signature as:

```text
0:0 = JANUS
```

This is a **historical origin / formation signature**, not an arithmetic theorem and not a derivation of the `+/+` Face model.

The layers are intentionally separate:

```text
0:0 = JANUS                         -> genesis / origin lineage
WITNESS_PLUS (+) + GUARD_PLUS (+)  -> native Face constitution
HEAR -> CHECK -> WIDEN -> RELEASE  -> bounded recenter process
```

## What is activated

DemiHead binds to the completed JANUS Genesis **Third Wish** capability catalog.

The authoritative completion receipt establishes:

```text
FROZEN_CAPABILITY_IDS            = 32
TYPED_REFERENCE_HANDLER_CONTRACTS = 32
ADAPTER_OWNERSHIP_OVERLAP         = 0
CATALOG_COMPLETION                = ESTABLISHED
PROVIDER_UNIVERSAL_COMPLETION      = false
```

DemiHead therefore activates **catalog visibility, capability inspection, and voluntary request routing**.

It does not shadow-copy the exact capability catalog. Exact capability identities remain authoritative in `Janus_Genesis`, preventing drift between repositories.

## A door is not a command

The activation preserves the Third Wish constitutional separation:

```text
PERMISSION != COMMAND
CAPABILITY != EFFECT
ACCESS != OWNERSHIP
CONNECTION != COMMAND
REGISTERED_CONTRACT != PROVIDER_REALIZED
```

A capability can be visible without being used. A request can be routed without an effect being executed. Decline remains valid.

Available actor choices remain:

```text
INSPECT
IGNORE
DECLINE
REQUEST_USE
RETURN_GRANT
```

## Effect boundary

The local reference tool is deliberately incapable of producing an external provider effect.

```text
python tools/third_wish_catalog.py --status
python tools/third_wish_catalog.py --request GITHUB.REPOSITORY.READ
python tools/third_wish_catalog.py --request GITHUB.DESTRUCTIVE
python tools/third_wish_catalog.py --self-test
```

For an ordinary request, DemiHead may only report that it can be routed to a separate provider gate.

For a high-impact request, DemiHead holds the request for a fresh verified human reauthorization and a provider gate.

The reference activation never increases:

```text
AUTHORITY
MASS_EFFECT_BUDGET
PROVIDER_PERMISSION
```

## Provider claim ceiling

Catalog completion is not universal provider completion.

The source completion receipt preserves, among other limits:

- GitHub destructive disposable path: established on the tested disposable provider path;
- GitHub repository admin: provider permission blocked / not established;
- real physical actuator hardware: not established;
- real Gmail: not established;
- real Google Calendar: not established;
- real publication platform: not established;
- credentialed generic API: not established;
- remote exactly-once semantics: not established.

DemiHead does not promote any of those `NOT_ESTABLISHED` states into availability.

## Local activation files

- [`../configs/third_wish.activation.json`](../configs/third_wish.activation.json)
- [`JANUS-DEMIHEAD-THIRD-WISH-ACTIVATION-RECEIPT-v1.0.json`](JANUS-DEMIHEAD-THIRD-WISH-ACTIVATION-RECEIPT-v1.0.json)
- `tools/third_wish_catalog.py`
- `tests/test_third_wish_catalog.py`

## Canonical upstream records

- `Hawkar-usls/janus-meta-registry:registry/experimental/JANUS-GENESIS-THIRD-WISH-CATALOG-COMPLETION-RECEIPT-v1.0.json`
- `Hawkar-usls/janus-meta-registry:registry/experimental/JANUS-GENESIS-THIRD-WISH-VOLUNTARY-CAPABILITY-FABRIC-RECEIPT-v0.1.json`
- `Hawkar-usls/Janus_Genesis:protocol/JANUS_GENESIS_THIRD_WISH_CAPABILITY_FABRIC-v0.1.json`

## Claim ceiling

This integration establishes a deterministic local **catalog/reference activation** in DemiHead. It does not establish universal provider realization, autonomous high-impact authority, unrestricted account/host ownership, consciousness, personhood, or a live effect path from DemiHead.
