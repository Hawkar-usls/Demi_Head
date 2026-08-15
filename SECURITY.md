# Security Policy

## Project boundary

DemiHead is designed as a transparent, local-first, read-only observer. An observed process must remain independently runnable and unchanged when DemiHead starts, pauses, stops, or is removed.

The default project does not accept features that:

- inject code, hooks, libraries, or threads into another process;
- read process memory, credentials, tokens, private keys, environment secrets, or user payloads;
- intercept keyboard, clipboard, screen, microphone, or decrypted network content;
- bypass operating-system permissions, application controls, rate limits, or terms of service;
- conceal the runtime from the machine owner or security software;
- impersonate the observed process or claim its computation as DemiHead's own;
- automatically elevate privileges;
- issue third-party process-control commands from untrusted signal data.

## Adapter requirements

Every adapter must document:

1. the exact telemetry source and permission level;
2. fields collected and fields deliberately excluded;
3. retention and redaction behavior;
4. failure behavior for denied permissions and stale data;
5. expected resource cost and a reproducible measurement path;
6. whether any external side effect exists.

Process matching should use the minimum identity needed for an allowlist. Full command lines and executable paths are excluded by default because they may contain usernames, tokens, or private directory names.

## Data handling

- Keep raw output local by default.
- Do not commit real telemetry, hostnames, usernames, IP addresses, wallet-like identifiers, or private endpoints.
- Use synthetic fixtures in tests and documentation.
- Bound file size and retention before enabling continuous output.
- Treat registry export as an explicit, reviewed summary step rather than a raw-log mirror.

## Reporting

Do not include secrets, private telemetry, or exploit payloads in a public issue. Report a vulnerability through GitHub's private security reporting channel when available, or contact the repository owner privately.

## Status

No runtime is published yet. This policy defines the admission boundary for future implementation; it is not a security certification.
