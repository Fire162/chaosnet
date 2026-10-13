# Learning log

Concepts encountered while building ChaosNet, in the order we met them.
Includes the questions I got wrong or only partly right, because those are the
ones worth revisiting.

---

## 2026-10-13: Control plane, reconcile, and fault cleanup

### Control plane vs. data plane

Terms borrowed from networking. In a router, the **data plane** forwards packets
using a forwarding table; the **control plane** (OSPF, BGP) decides what goes
into that table.

In ChaosNet the data plane is the lab: the demo services, Toxiproxy and the load
generator, through which real requests flow. The control plane is our backend:
it never carries requests, it decides what runs and which faults are active.

Key consequence: when the control plane dies, the data plane keeps running,
including any fault that was active at that moment.

### Imperative vs. declarative control, and reconciliation

- **Imperative:** "add toxic", later "remove toxic". The intent to remove lives
  only in the memory of the running process.
- **Declarative:** persist the desired state ("fault F1 may exist until 14:05,
  owned by experiment E7"). A **reconcile loop** repeatedly compares actual state
  (ask Toxiproxy) with desired state (database) and removes the difference. It
  needs no memory of the past, so it works after a restart.

### TTL and the dead man's switch

A fault has a deadline (`expires_at`, a TTL). But a deadline does nothing unless
some running component enforces it.

**Question:** the control plane crashes at 14:02 while a fault is active and is
never restarted. What happens?

- *My answer, part 1:* the lab stays degraded forever. **Correct.**
- *My answer, part 2:* give the fault a time limit so it resets at 14:10.
  **Partly correct.** The TTL idea is right, but I missed *who* performs the
  reset. The reconciler runs inside the dead control plane, so nobody does.

**Principle:** cleanup must not depend on the component whose failure it is
meant to cover.

**Fix:** a dead man's switch, also called a lease. The control plane sends a
heartbeat every few seconds; a separate tiny watchdog resets all faults if the
heartbeat stops. The safe state is triggered by the *absence* of a signal.
Kubernetes and etcd use leases the same way. See ADR-001.
