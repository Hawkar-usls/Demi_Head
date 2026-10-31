# JANUS repository recovery in Demi_Head

The owner selected `Hawkar-usls/Demi_Head` as backup storage. The workflow
`JANUS repository backup and clean recovery` runs daily and on manual dispatch.
It stores a full, standalone Git bundle as a Demi_Head Actions artifact, rather
than pushing foreign branches or workflows into this repository's main branch.
Each snapshot is retained for seven days. Its immutable receipt remains in the
`janus-recovery` branch, with `janus-recovery/LATEST.json` pointing to the latest
successful stored snapshot. An expired artifact is not an available restore point.

The bundle includes all fetched refs and reachable history: code, tracked
configuration, state, tracked model weights and previous generations. It does
not include private local Habitat records, secrets, untracked runtime databases,
NAS media, LFS payloads or submodule repositories. This is repository recovery;
it is not evidence that all JANUS services can boot or that external state was saved.

Before storage, a clean mirror is restored from the bundle. SHA-256, bundle
verification, full strict Git object validation and equality of every ref must
pass. The restored Beetle consumer suite then runs in a read-only container with
no network, no credentials, no capabilities and limited CPU, memory and processes.
Failure prevents publication of a new successful receipt. Older receipts survive.

To recover: download the artifact linked in a non-expired receipt, verify the
bundle SHA-256 and `refs.json` SHA-256 against the receipt, then run:

```text
git clone --mirror janus-demiurge.bundle recovered.git
git -C recovered.git bundle verify ../janus-demiurge.bundle
git -C recovered.git fsck --full --strict
```

Use a new empty destination and compare all refs with `refs.json`. Select the
required generation in a separate working copy. Recovery never overwrites an
existing repository and never runs snapshot code on the host. The backup path
does not change JANUS generator permissions or permit autonomous merges.
