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

---

## ADR-002: Local-first execution, public demo replays recorded experiments

- **Status:** Accepted
- **Date:** 2026-10-13

### Context

The intended product is a web application where users compose an architecture
in a visual editor and run real experiments against it. Running experiments
means starting containers and holding access to the Docker socket, which is
root-equivalent on the host. Containers share the host kernel.

### Problem

Where does experiment execution run: on the user's machine, or on a server we
host for anyone on the internet?

### Options considered

1. **Local-first.** The user clones the repository and runs the whole
   application (UI, control plane, lab) on their own machine against
   `localhost`. Safe and free, and measurements are real; requires Docker.
2. **Publicly hosted execution.** Every user gets an isolated sandbox (for
   example a Firecracker or gVisor microVM), with authentication, quotas and
   abuse protection. Lowest friction for visitors, but this is a project of its
   own in security and cost, and noisy neighbours distort measurements.
3. **Hybrid.** Option 1 for running experiments, plus a public, read-only demo
   that replays recorded results of real experiments (topology, metrics,
   traces), clearly labelled as recordings.

### Decision

Option 3 as the target. Until the replay demo exists, ChaosNet is local-only.

### Rationale

- No untrusted user ever gets a path to the Docker socket.
- Visitors (for example reviewers of the project) can still see real results
  without installing anything.
- The principle "measure real behaviour, never fabricate" holds: replays are
  recordings of real runs, never synthesised data.

### Consequences

- The control plane binds to `127.0.0.1` only and has no authentication in the
  MVP. This is acceptable only because of this decision.
- Experiment results need a self-contained, exportable format so they can be
  replayed by a static site. This is planned for around v0.2.
- Option 2 remains possible later: ADR-001 keeps execution separable into an
  agent that could run inside a per-user sandbox. It would need its own ADR and
  security design.
