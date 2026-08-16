# JANUS Nexus Real Subprocess Termination Holdout

This gate is the first Nexus recovery test in this line that kills a **real child process** after durable lifecycle state has been written, then starts a separate recovery process against the same SQLite files.

It remains deliberately narrower than a power-loss or production crash claim.

## Frozen scope

The holdout is frozen for the Ubuntu/POSIX GitHub Actions environment. `subprocess.Popen.kill()` is used as the abrupt child-termination primitive. The parent does not ask the child to clean up its lifecycle state.

Five frozen cases are exercised:

```text
KILL-01  STARTING
KILL-02  LISTENER_BOUND with an actual 127.0.0.1 listening socket
KILL-03  TRANSPORT_ADMITTED
KILL-04  DISPATCH_STARTED + durable STARTED dispatch evidence
KILL-05  DISPATCH_COMPLETED + durable COMPLETED dispatch evidence
```

Freeze SHA-256:

`0b815e6864bedcba152add9c17861cb30115f24d772ce3a01b3613868ec9f159`

## Cross-process durability sequence

Each case follows the same broad pattern:

```text
parent process
  -> spawn crash-probe child
child
  -> write SQLite lifecycle state with FULL synchronous mode
  -> optionally write persistent dispatch evidence
  -> fsync ready marker
parent
  -> observe ready marker
  -> kill child abruptly
  -> reopen lifecycle database
  -> verify killed child left expected non-terminal state
  -> spawn separate recovery CLI process
recovery process
  -> reread lifecycle + dispatch evidence from disk
  -> apply certified v1.10 manual recovery semantics
parent
  -> verify final durable state and evidence preservation
```

## Actual loopback resource case

`KILL-02` goes beyond a synthetic phase row. The child uses the certified localhost socket guard/lifecycle preparation path to bind a real ephemeral `127.0.0.1` listener and persist `LISTENER_BOUND`. The parent kills the process, verifies the lifecycle row survives, and verifies the operating system released the killed process's socket before manual recovery.

This still does not imply cross-host network authority.

## Recovery expectations

Abrupt termination in the selected pre-dispatch states may be terminalized `CLOSED_CLEAN` only by the existing v1.10 operator recovery path and only when dispatch evidence is absent.

Abrupt termination at `DISPATCH_STARTED` or `DISPATCH_COMPLETED` is recovered only to `CLOSED_AMBIGUOUS`. Durable dispatch evidence remains present and automatic retry remains forbidden.

## What this gate does not test

```text
power cable removal
kernel panic
filesystem or block-device corruption
disk cache loss
SQLite file truncation
container host reboot
Windows process termination semantics
cross-host transport
persistent daemon behavior
automatic restart
automatic retry
external-effect execution
```

A PASS therefore supports only a **POSIX subprocess-termination durability claim** for the frozen cases, not universal crash safety.

## Next gate

After certification, the next meaningful durability boundary is storage fault injection: truncated/corrupted lifecycle or dispatch databases, read-only filesystems, ENOSPC-style write failure, and WAL/checkpoint disruption. Those cases must fail closed without evidence reset or automatic retry.
