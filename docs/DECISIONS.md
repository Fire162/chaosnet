# Architecture Decision Records

Significant architectural decisions, newest last. Each record states the context,
the options considered, the decision, and its consequences. Records are never
edited after acceptance except to change their status; a changed decision gets a
new record that supersedes the old one.

---

## ADR-001: Control plane as a modular monolith with lease-based fault cleanup

- **Status:** Accepted
- **Date:** 2026-10-13
- **Issue:** #1

### Context

ChaosNet needs a control plane: the component that starts lab services, injects
and removes faults, drives an experiment through its phases, and collects
results. The data plane is the lab itself: the demo services, Toxiproxy, and the
load generator, through which real requests flow.

The MVP runs on a single developer machine (macOS, Docker Desktop) for a single
user. The most dangerous failure mode of a chaos tool is a fault that outlives
the experiment that created it: the lab stays degraded and every later
measurement is wrong. Toxiproxy keeps toxics in memory indefinitely and has no
notion of experiments or expiry.

### Problem

How should the control plane be structured, and how do we guarantee that faults
are removed even when the control plane crashes?

### Options considered

1. **Modular monolith.** One FastAPI process with internal modules (topology,
   experiments, execution, faults, measurements); experiments run as asyncio
   tasks. Simple to build, debug and explain. A crash orphans active faults.
2. **Control plane + separate executor agent.** API and executor in separate
   processes communicating over HTTP or a queue. Isolates privileged operations
   and fits a future Linux-VM backend, but introduces a distributed system
   (protocol, versioning, partial failure) with no benefit for the MVP.
3. **Declarative reconciler.** Persist desired state; a loop continuously
   converges actual infrastructure to it. Cleanup after restart falls out of the
   design, but experiment phases are awkward to express purely as state and
   eventual consistency is harder to debug.

### Decision

Option 1, borrowing reconciliation from option 3 for faults only, plus an
external dead man's switch. Fault cleanup has three layers:

1. **Normal path:** the experiment runner removes its faults when a phase ends,
   including on cancellation and errors.
2. **Control plane restart:** every fault is persisted *before* it is applied,
   with an owning experiment and an `expires_at` deadline. A reconcile pass on
   startup and periodically removes any fault that has expired or is not
   recorded as owned by a live experiment.
3. **Control plane gone:** a small watchdog running next to Toxiproxy expects a
   heartbeat (lease renewal) from the control plane. If the lease is not renewed
   within a timeout, it resets all toxics.

### Rationale

- The monolith is the simplest structure that meets MVP needs and is easy to
  reason about end to end.
- Layer 2 alone is insufficient: the reconciler runs inside the control plane, so
  it cannot clean up while the control plane is down. Cleanup must not depend on
  the component whose failure it is meant to cover; layer 3 addresses this.
- The watchdog is deliberately tiny, so it is far less likely to fail together
  with the control plane.

### Consequences

- The `execution` and `faults` modules keep narrow interfaces so they can later
  be moved into a separate executor (option 2) when the Network Lab needs a
  privileged agent inside a Linux VM.
- Faults that the watchdog removes leave the experiment record in an inconsistent
  state; the reconciler must mark such experiments as aborted on restart.
- Not covered: if Docker or its VM dies, the watchdog dies too, but so do the
  in-memory toxics, so the lab still ends up clean.
- Assumes a single user on a local machine. Hosting experiment execution for
  other users is out of scope and requires its own security design.
