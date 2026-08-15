# Glossary

This glossary translates the project's metaphors into testable engineering terms.

## DemiHead

The adapter layer between an observed local process and Janus outputs. It is "demi" because it does not own or perform the source workload; it derives a bounded secondary representation from allowed observations.

## Source

A documented, allowlisted telemetry surface. A source is not the process's private memory or payload.

## Foreign process

An independently running application that DemiHead does not launch, inject into, impersonate, or control by default.

## Ambient workload

Activity already occurring on the host. DemiHead may observe its OS-exposed traces, but cannot claim the source computation as its own work.

## Useful number

A numeric signal with a defined transform, unit or scale, timestamp, freshness, confidence, and provenance. Random-looking bytes or a hash are not automatically useful.

## Chaos

Irregular variation in observed metrics. This is an informal project term, not a claim that the source is mathematically chaotic or a certified entropy source.

## Structuring

Converting samples into windows, deltas, normalized signals, quality states, and deterministic output envelopes.

## Anti-dispersion

The project term for reducing unstable presentation of noisy measurements through bounded normalization, freshness gates, and confidence. It is not a physical anti-dispersion mechanism.

## Trigger

A deterministic condition evaluated over valid signal frames. A trigger must name its threshold, hysteresis, cooldown, and effect scope.

## Face

A named projection of shared state for one purpose. Multiple faces may present the same observation differently, but they may not fabricate different source truth.

## Mirror face

A read-only projection of normalized state.

## Steward face

A projection that can recommend or adjust DemiHead's own sampling pressure. External process control is outside the v0.1 authority boundary.

## Registry face

A projection that emits bounded, machine-readable evidence records.

## Passive

No modification of the observed process. Passive does not mean free: sampling still consumes measurable resources.

## Resource budget

The maximum CPU, memory, I/O, and scheduling lag DemiHead is allowed to consume before degrading, holding, or stopping itself.

## Fail closed

When data quality, permissions, or budget are invalid, DemiHead withholds an actionable output and reduces or stops its own work.
