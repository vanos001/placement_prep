# Remote Attestation: Proving Software State to a Stranger

A cloud tenant asks: is the hypervisor under my VM actually the one we
audited? A car asks: is this ECU running the signed firmware? A bank asks:
is the HPU that holds my keys uncompromised? Remote attestation is the
mechanism that turns those questions into verifiable proofs: a hardware
root of trust measures code as it loads, an untamperable signer vouches for
the measurement, and the relying party checks both the signature chain and
the measurement values against expectations. This page walks the TPM 2.0
quote flow, the TEE-specific variants (SGX DCAP, SEV-SNP, ARM CCA), and the
failure modes that make real deployments harder than the protocol diagrams.

Related pages in this repo: [TPM 2.0](../../cryptography/tpm-2.0.md) covers
the TPM key hierarchy itself; [ARM CCA](../../arch/advanced/arm-cca-realms.md) and
the confidential-computing pages under [arch/advanced](../../arch/advanced/README.md) cover the hardware-enforcement side that attestation
describes; [secure boot](../../linux/security/secure-boot.md) is the
local-verification cousin.

## The core pattern: measure, sign, verify

Every attestation scheme is a three-actor protocol:

```text
=== scenario 1: honest boot ===
  pcr0 <- extend(EV_POST_CODE              ) = 9ef814b42fa0be12...
  pcr0 <- extend(EV_EFI_GPT                ) = aaf51febf5ed5e45...
  pcr4 <- extend(EV_EFI_BOOT_LOADER        ) = acdc8027c53d5697...
  pcr4 <- extend(EV_COMPACT_HASH/kernel    ) = de7c98fd26edb5f4...
  pcr4 <- extend(EV_IPL/initramfs          ) = 4356b6fedb8592c5...
verification steps:
  1. nonce match: True
  2. replayed pcr0 == quoted: True; pcr4: True
  3. event digests match allowlist (exact order): True
  verdict: ATTESTED - release sealed secrets

=== scenario 2: tampered kernel, stale honest-boot quote ===
  pcr0 <- extend(EV_POST_CODE              ) = 9ef814b42fa0be12...
  pcr0 <- extend(EV_EFI_GPT                ) = aaf51febf5ed5e45...
  pcr4 <- extend(EV_EFI_BOOT_LOADER        ) = acdc8027c53d5697...
  pcr4 <- extend(EV_COMPACT_HASH/kernel    ) = 40d675ca06b3187a...
  pcr4 <- extend(EV_IPL/initramfs          ) = 0f5288b4f98bf89c...
verification steps:
  1. nonce match: True
  2. replayed pcr0 == quoted: True; pcr4: False
  3. event digests match allowlist (exact order): False
  verdict: DENY

=== scenario 3: untampered boot, REPLAYED quote (stale nonce) ===
  pcr0 <- extend(EV_POST_CODE              ) = 9ef814b42fa0be12...
  pcr0 <- extend(EV_EFI_GPT                ) = aaf51febf5ed5e45...
  pcr4 <- extend(EV_EFI_BOOT_LOADER        ) = acdc8027c53d5697...
  pcr4 <- extend(EV_COMPACT_HASH/kernel    ) = de7c98fd26edb5f4...
  pcr4 <- extend(EV_IPL/initramfs          ) = 4356b6fedb8592c5...
verification steps:
  1. nonce match: False
  2. replayed pcr0 == quoted: True; pcr4: True
  3. event digests match allowlist (exact order): True
  verdict: DENY

verdicts: honest=True, tampered=False, replayed=False
the tampered boot is caught by PCR replay AND allowlist; the replayed
quote passes the PCR check (PCRs are honest!) and is caught ONLY by
the fresh nonce - which is why nonce handling is the load-bearing step.
```

The two load-bearing details: the **nonce** (without it, a prover replays
an old quote from a compromised-but-attested boot), and the **PCR extend
semantics** - measurements are accumulated as
`PCR[n] = SHA256(PCR[n] || measurement)`, an order-sensitive hash chain
that cannot be truncated or re-ordered without changing the final value.

## TPM 2.0 quotes: PCRs and the event log

The TPM's PCR banks (SHA-256 on modern parts) hold the measurements; the
**event log** holds what each measurement *was* (measured boot: firmware
stages, option ROMs, bootloader, kernel, initramfs; andIMA-style runtime
measurements if configured). The verifier needs both:

- the quote proves the PCR values (signed by an attestation key whose
  certificate chains to the manufacturer);
- the event log lets the verifier *replay* the events through the extend
  operation and check they arrive at the quoted PCR values - which
  catches both a lying log and a mis-extended bank.

The demo below implements the replay: it walks a synthetic event log,
extends the PCRs, compares to the quoted values, and evaluates the
allow/deny policy - the exact computation a verifier service (Key Broker,
attestation agent, fleet admission controller) performs thousands of
times a day.

```python
#!/usr/bin/env python3
"""PCR replay and quote verification model (TPM 2.0 style).

- extend(pcr, m) = SHA256(pcr || m): order-sensitive accumulation
- replay the event log, compare to quoted PCR values
- policy: allowlist (exact digests, exact order) + nonce freshness.
Deterministic; pure stdlib."""
import hashlib

H = lambda b: hashlib.sha256(b).hexdigest()


def extend(pcr, measurement_hex):
    return H(bytes.fromhex(pcr) + bytes.fromhex(measurement_hex))


EVENT_LOG = [
    # (pcr, event type, digest) - firmware -> bootloader -> kernel -> initramfs
    (0, "EV_POST_CODE",       "aa" * 32),
    (0, "EV_EFI_GPT",         "bb" * 32),
    (4, "EV_EFI_BOOT_LOADER", "cc" * 32),
    (4, "EV_COMPACT_HASH/kernel", "dd" * 32),
    (4, "EV_IPL/initramfs",   "ee" * 32),
]

QUOTED = {"pcr0": None, "pcr4": None}   # set from the honest-boot replay
NONCE_PROVIDED = "f00d" * 8             # verifier's fresh challenge
NONCE_IN_QUOTE = "f00d" * 8             # nonce inside the quote blob

ALLOWLIST = {
    0: ["aa" * 32, "bb" * 32],
    4: ["cc" * 32, "dd" * 32, "ee" * 32],
}


def replay():
    pcrs = {0: "0" * 64, 4: "0" * 64}
    for pcr, ev, digest in EVENT_LOG:
        pcrs[pcr] = extend(pcrs[pcr], digest)
        print(f"  pcr{pcr} <- extend({ev[:26]:<26}) = {pcrs[pcr][:16]}...")
    return pcrs


def verify(pcrs):
    print("verification steps:")
    ok = True
    n_ok = NONCE_PROVIDED == NONCE_IN_QUOTE
    print(f"  1. nonce match: {n_ok}")
    ok &= n_ok
    r0 = pcrs[0] == QUOTED["pcr0"]
    r4 = pcrs[4] == QUOTED["pcr4"]
    print(f"  2. replayed pcr0 == quoted: {r0}; pcr4: {r4}")
    ok &= (r0 and r4)
    got0 = [d for (p, _e, d) in EVENT_LOG if p == 0]
    got4 = [d for (p, _e, d) in EVENT_LOG if p == 4]
    a_ok = got0 == ALLOWLIST[0] and got4 == ALLOWLIST[4]
    print(f"  3. event digests match allowlist (exact order): {a_ok}")
    ok &= a_ok
    print(f"  verdict: {'ATTESTED - release sealed secrets' if ok else 'DENY'}")
    return ok


# scenario 1: honest boot - the quote is computed over the PCRs the
# replay actually produces, so every check passes
print("=== scenario 1: honest boot ===")
pcrs = replay()
QUOTED["pcr0"], QUOTED["pcr4"] = pcrs[0], pcrs[4]
ok = verify(pcrs)

# scenario 2: attacker swaps the kernel digest but has no AK to sign a
# fresh quote - verifier still holds the honest-boot quote values
print()
print("=== scenario 2: tampered kernel, stale honest-boot quote ===")
EVENT_LOG[3] = (4, "EV_COMPACT_HASH/kernel", "ba" * 32)
tampered = replay()
ok2 = verify(tampered)

# scenario 3: attacker keeps the honest boot but REPLAYS its old quote
# against a fresh challenge - the nonce step is the only defense needed
print()
print("=== scenario 3: untampered boot, REPLAYED quote (stale nonce) ===")
EVENT_LOG[3] = (4, "EV_COMPACT_HASH/kernel", "dd" * 32)   # restore honest log
NONCE_PROVIDED, NONCE_IN_QUOTE = "cafe" * 8, "f00d" * 8
QUOTED["pcr0"], QUOTED["pcr4"] = pcrs[0], pcrs[4]
ok3 = verify(replay())
print()
print(f"verdicts: honest={ok}, tampered={ok2}, replayed={ok3}")
print("the tampered boot is caught by PCR replay AND allowlist; the replayed")
print("quote passes the PCR check (PCRs are honest!) and is caught ONLY by")
print("the fresh nonce - which is why nonce handling is the load-bearing step.")
```

```text
=== baseline run ===
PCR replay (start from all-zero banks):
  pcr0 <- extend(EV_POST_CODE              ) = 9ef814b42fa0be12...
  pcr0 <- extend(EV_EFI_GPT                ) = aaf51febf5ed5e45...
  pcr4 <- extend(EV_EFI_BOOT_LOADER        ) = acdc8027c53d5697...
  pcr4 <- extend(EV_COMPACT_HASH/kernel    ) = de7c98fd26edb5f4...
  pcr4 <- extend(EV_IPL/initramfs          ) = 4356b6fedb8592c5...

verification steps:
  1. nonce match: True
  2. replayed pcr0 == quoted: False; pcr4: False
  3. event digests match allowlist (exact order): True
  verdict: DENY

=== tampered boot: kernel digest swapped; quote replayed from the
    good boot (attacker skipped re-measuring) ===
PCR replay (start from all-zero banks):
  pcr0 <- extend(EV_POST_CODE              ) = 9ef814b42fa0be12...
  pcr0 <- extend(EV_EFI_GPT                ) = aaf51febf5ed5e45...
  pcr4 <- extend(EV_EFI_BOOT_LOADER        ) = acdc8027c53d5697...
  pcr4 <- extend(EV_COMPACT_HASH/kernel    ) = 40d675ca06b3187a...
  pcr4 <- extend(EV_IPL/initramfs          ) = 0f5288b4f98bf89c...

verification steps:
  1. nonce match: True
  2. replayed pcr0 == quoted: False; pcr4: True
  3. event digests match allowlist (exact order): False
  verdict: DENY

baseline verdict ok=False; tampered run: replayed-PCR check now passes
only because the attacker stole the quote - the NONCE (fresh per
challenge) is what defeats that replay in the real protocol.
```

The tamper scenario is the pedagogical heart: extending different
measurements produces different PCR values, and a stale quote fails only
the *nonce* step - which is why skipping nonce checking is the classic
production bug that turns attestation into theater.

## The TEE variants, briefly

Each confidential-computing platform reshuffles the same pattern:

| platform | root of trust   | measurement                   | verifier-side check          |
|----------|-----------------|-------------------------------|-------------------------------|
| TPM measured boot | discrete TPM | PCRs + event log (boot chain) | replay + allowlist (above)    |
| Intel SGX (DCAP) | CPU Quoting Enclave | MRENCLAVE/MRSIGNER (enclave hash) | DCAP certificate chain from Intel SGX Root CA |
| AMD SEV-SNP | PSP in package | launch digest + report (signed by VCEK, chained to VLEK/VRK) | verify report signature chain + measurement + policy fields |
| ARM CCA realms | HW RoT + RMM | realm measurement (RIM), four-stage | verify realm token vs platform token (VSI) |

The recurring verification-side question is not the cryptography - it is
*what digest means what*: reference values are infrastructure (who signs
the firmware digest, how are updates rolled, what happens on a BIOS
release). Fleets solve it with attestation services that hold versioned
allowlists and fail-closed on unknown digests - and the operational
failure mode is almost never a broken signature; it is a legitimate
component update nobody allowlisted, locking the fleet out.

## Failure modes worth knowing by name

- **TOCTOU between measure and execute**: measuring a block device does
  not guarantee the executed pages match later; TOCTO U mitigations live
  in the measured-path (dm-verity-style root hashes, IMA appraisal) - see
  [dm-verity](../../linux/kernel/drivers/dm-verity.md).
- **Quote replay**: covered above; the nonce is the fix, nonces must be
  cryptographically fresh per challenge.
- **Rollback attacks** on the verifier's allowlist: an attacker replays
  an *old legitimate* measurement of a vulnerable firmware version.
  Defense: monotonic version counters in the policy (or in TPM NV
  counters).
- **Side-channel re-attacks post-attestation**: attestation proves state
  at boot; it says nothing about runtime adversaries - pairing with
  runtime guards (Sandboxing, IFC) is standard for high-assurance stacks.

## Interview probes

- Walk a TPM 2.0 quote verification: name every object (AK, AK cert, PCR
  banks, nonce, event log) and what a mismatch in each tells you.
- Why is `PCR[n] = H(PCR[n] || m)` order-sensitive, and how does the
  verifier use the event log to distinguish "wrong software" from
  "lying log"?
- SGX's MRENCLAVE is a single hash of the enclave: what does that make
  easy compared to TPM's boot-chain PCRs, and what fleet-ops problem
  does it create on every library update?
- Where exactly do rollback attacks sit in the protocol, and which
  counter stops them?

## References

1. Trusted Computing Group, "TPM 2.0 Library Specification" (canonical
   spec; [trustedcomputinggroup.org](https://trustedcomputinggroup.org/resource/tpm-library-specification/)
   - 403s to scripted probes, canonical and search-verified) - part 1
   sections 15-17 (PCR, attestation) and part 2 structures.
2. [SEV-SNP guest API - kernel documentation](https://docs.kernel.org/virt/coco/sev-guest.html)
   - the attestation report request/verify flow as implemented on Linux.
3. [TPM TPM proxy + device driver docs](https://docs.kernel.org/security/tpm/tpm_vtpm_proxy.html)
   - the kernel-side TPM integration surface.
4. [TPM 2.0 (this repo)](../../cryptography/tpm-2.0.md) - the key
   hierarchies and NV infrastructure this page's quotes rely on.
