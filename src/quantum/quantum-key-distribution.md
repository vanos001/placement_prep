# Quantum Key Distribution and BB84

Every key exchange covered elsewhere in this book -- DH, ECDH, ML-KEM
([Kyber](../cryptography/kyber-mlkem.md)) -- rests on a conjecture: that some
math problem is hard for the adversary's computers. Quantum key distribution
(QKD) makes a different claim: the key's secrecy rests on physical law. If an
eavesdropper learns anything about the flying qubits, she *must* disturb
them in a measurable way, because the no-cloning theorem forbids copying an
unknown quantum state and measurement disturbs it. QKD therefore delivers
something classical cryptography cannot: an eavesdropping detector, with
security that is information-theoretic rather than computational. This page
walks the BB84 protocol end to end, derives the famous 25%-vs-11% error-rate
arithmetic, simulates the intercept-resend attack, and then confronts the
uncomfortable operational realities -- the authentication chicken-and-egg,
distance limits, and why NSA still prefers post-quantum math.

## No-Cloning in Two Lines

If a unitary `U` cloned arbitrary states, then for any two states it would
satisfy `<psi|phi> = <psi|phi>^2`, which forces `|<psi|phi>|` to be 0 or 1 --
impossible for a continuum of states. Consequences for key distribution:

- Eve cannot split off a copy of each flying qubit and measure her copy
  later; she must choose a measurement *on the original*.
- No quantum amplifier exists -- this is also why QKD cannot be repeated
  like a classical signal (see [distance limits](#practical-limits)).
- Optical fiber classical repeaters don't apply; every attempt to read or
  boost the quantum signal is a disturbance.

For where this same theorem shows up in error correction, see
[Quantum Error Correction](./quantum-error-correction.md); for the qubit and
basis formalism, see [Quantum Fundamentals](./quantum-fundamentals.md).

## BB84: The Protocol

Alice encodes random bits in one of two conjugate bases: rectilinear Z
(`|0>`, `|1>`) or diagonal X (`|+>` = `(|0>+|1>)/sqrt(2)`, `|->` =
`(|0>-|1>)/sqrt(2)`). Measuring a Z-state in X (or vice versa) yields a
perfectly random bit -- conjugacy is what powers the detector.

```text
step  Alice bit/basis   Eve basis   Eve resends    Bob basis   Bob's bit  kept?  error?
 1    0 / Z             Z (right)   |0>            Z           0          yes    no
 2    0 / Z             X (wrong)   |+>            Z           random     yes    50%
 3    1 / X             X (right)   |->            X           1          yes    no
 4    1 / Z             X (wrong)   |+>            Z           random     yes    50%
 5    0 / X             Z (wrong)   |0>            X           random     no     -
 6    1 / Z             Z (right)   |1>            X           random     no     -
```

Steps 1-6 make the whole threat model visible: when Eve guesses right, she
is invisible; when she guesses wrong (rows 2 and 4), her resent state is a
random coin *in Alice's basis*, corrupting a sifted bit half the time. Rows
5-6 show the honest mismatch case -- those qubits are discarded regardless.

The full run:

1. **Quantum phase.** Alice sends `n` qubits, each a random bit in a random
   basis; Bob measures each in an independent random basis.
2. **Sifting.** Over an authenticated classical channel, both announce
   bases (never bits) and keep positions where bases matched -- about `n/2`.
3. **Parameter estimation.** Both publicly reveal a random sample of the
   sifted bits and compare. Sample error rate = the quantum bit error rate
   (QBER).
4. **Abort test.** If QBER exceeds threshold (~11% for BB84 with one-way
   post-processing), Alice and Bob assume Eve learned too much and abort.
5. **Error correction + privacy amplification.** Reconcile remaining bits
   (leaking some), then hash the string down to a shorter key about which
   Eve's mutual information is negligible.

## The Intercept-Resend Arithmetic

From the table: Eve picks the wrong basis with probability 1/2; a wrong
basis corrupts a sifted bit with probability 1/2. So among sifted bits:

```text
QBER_intercept-resend = 1/2 * 1/2 = 25%   (clean channel: 0%)
```

Equivalently, 1/8 of *all transmitted* qubits are disturbed. Alice and Bob
compare a random `m`-bit sample of the sifted key; each sampled bit is
wrong with probability 1/4 under attack, so detection probability is
`1 - (3/4)^m` -- with m = 100, evasion odds are about 3e-13. The simulation
below runs exactly this protocol and recovers both numbers:

```python
"""BB84 with an intercept-resend eavesdropper.

Per qubit: Alice sends a random bit in a random basis (Z or X); Bob
measures in a random basis; bases-matching qubits form the sifted key.
Eve measures every qubit in a random basis and resends her outcome.
Sampling m sifted bits tests for her: P(detect) = 1 - (3/4)^m.
"""
import random

N = 2_000
TRIALS = 200
SEED = 20260827

def run(eavesdrop: bool, m: int, rng: random.Random):
    sifted_n = sifted_ok = 0
    errors = []                       # 1 if Bob's sifted bit flipped
    for _ in range(N):
        a_bit, a_basis = rng.getrandbits(1), rng.getrandbits(1)
        b_basis = rng.getrandbits(1)
        if eavesdrop:
            e_basis = rng.getrandbits(1)
            e_bit = a_bit if e_basis == a_basis else rng.getrandbits(1)
            b_bit = e_bit if b_basis == e_basis else rng.getrandbits(1)
        else:
            b_bit = a_bit             # noiseless quantum channel
        if b_basis == a_basis:        # bases agree -> sifted bit
            sifted_n += 1
            sifted_ok += a_bit == b_bit
            errors.append(a_bit != b_bit)
    idx = rng.sample(range(sifted_n), m)
    return sifted_n / N, 1.0 - sifted_ok / sifted_n, any(errors[i] for i in idx)

rng = random.Random(SEED)
print(f"BB84 intercept-resend simulation: n={N} qubits, {TRIALS} runs")
for eavesdrop in (False, True):
    qbers, fracs, det = [], [], 0
    for _ in range(TRIALS):
        frac, qber, detected = run(eavesdrop, m=20, rng=rng)
        fracs.append(frac)
        qbers.append(qber)
        det += detected
    tag = "with Eve   " if eavesdrop else "no Eve     "
    print(f"{tag}: sifting fraction={sum(fracs) / TRIALS:.3f}  "
          f"QBER={sum(qbers) / TRIALS:.4f}  "
          f"detection(m=20)={det / TRIALS:.4f}")
print()
print("Detection probability vs number of compared sifted bits m (with Eve):")
print(f"{'m':>4} {'measured':>9} {'analytic 1-(3/4)^m':>19}")
for m in (1, 2, 4, 8, 16, 32):
    det = sum(run(True, m=m, rng=rng)[2] for _ in range(TRIALS))
    print(f"{m:>4} {det / TRIALS:>9.4f} {1 - 0.75 ** m:>19.4f}")
```

Output (runs in about a second; QBER lands on the predicted 25%, sifting on 50%, and the detection curve tracks `1 - (3/4)^m` within sampling noise):

```text
BB84 intercept-resend simulation: n=2000 qubits, 200 runs
no Eve     : sifting fraction=0.500  QBER=0.0000  detection(m=20)=0.0000
with Eve   : sifting fraction=0.501  QBER=0.2492  detection(m=20)=1.0000

Detection probability vs number of compared sifted bits m (with Eve):
   m  measured  analytic 1-(3/4)^m
   1    0.2700              0.2500
   2    0.4100              0.4375
   4    0.7050              0.6836
   8    0.8950              0.8999
  16    0.9850              0.9900
  32    1.0000              0.9999
```

## Why the Abort Threshold Is ~11%

Intercept-resend is a *naive* attack; a smarter Eve trades knowledge against
noise. Security proofs quantify the trade: Shor and Preskill's 2000 proof
(PRL 85, 441) shows BB84 with one-way post-processing is information-
theoretically secure as long as QBER stays below about 11%. Below threshold,
privacy amplification squeezes Eve's partial information out faster than
error correction leaks it; above it, abort. Two consequences worth
remembering in interviews: (1) the 25% QBER of intercept-resend is 2.3x the
abort threshold, so the naive attacker is caught with overwhelming
probability, not merely detected in principle; (2) the threshold is a
*proof* boundary, and real systems run with large margins (a few percent
QBER) because channel noise itself consumes the budget -- a system can fail
not by being attacked but by having a bad day of fiber birefringence.

## E91 in One Paragraph

Ekert's 1991 protocol replaces Alice's random bases with entangled pairs and
uses a Bell-inequality test as the eavesdropping check: a third party (or
one endpoint) distributes `(|0>|1> - |1>|0>)/sqrt(2)` pairs, and Alice and
Bob measure in rotating bases. If measurement statistics violate a Bell
inequality, no eavesdropper can hold a pre-existing description of the
outcomes -- the violation certifies secrecy directly. Conceptually E91 is the
ancestor of device-independent QKD, where security follows from observed
correlations even if you distrust the hardware that produced them.

## Decoy States: Patching the Real-World Loophole

Ideal BB84 assumes single photons. Real cheap transmitters emit weak
coherent pulses with a Poisson photon-number distribution: mostly empty,
mostly one photon, sometimes two or more. The **photon-number-splitting
(PNS)** attack exploits the multi-photon tail: Eve splits off one photon,
lets the rest through undisturbed, stores hers until the basis announcement,
then reads the bit -- perfectly hidden below the 11% threshold. The fix
(anticipated by Hwang, PRL 91, 057901 (2003), and formalized in Lo, Ma and
Chen, PRL 94, 230504 (2005)) is **decoy states**: Alice varies the pulse
intensity at random, announcing intensities only afterward. Single-photon
and multi-photon pulses then survive channel loss with *statistically
different* yields per intensity class, so any PNS filtering shows up as an
anomaly in those yield statistics. Decoy-state BB84 turned fragile
laboratory protocols into deployable systems and is standard in commercial
gear.

## Real Deployments

The Micius satellite demonstrated QKD's flagship result: satellite-to-ground
QKD at kilobit-per-second-scale key rates over distances up to about
1,200 km (Liao et al., Nature 549, 43-47, 2017), because the atmosphere is
nearly loss-free compared to fiber at that scale. Entanglement
distribution between ground stations 1,200 km apart followed the same year
(Science 356, 1140). On the ground, commercial point-to-point QKD has been
sold for years -- ID Quantique in Geneva and Toshiba's QKD business are the
canonical vendors -- typically metro-distance links that AES-encrypt traffic
with frequently refreshed QKD keys. National testbeds (China's
Beijing-Shanghai trusted-node backbone, EuroQCI efforts in the EU) treat QKD
as one component of broader quantum-communications programs rather than a
drop-in replacement for IPsec.

## The Authentication Circularity

QKD's classical channel must be authenticated, or a man-in-the-middle runs
BB84 twice -- once with each party -- and no disturbance ever appears at
either end. Authentication needs a pre-shared secret (Wegman-Carter MACs,
which consume key material) or signatures (which need PKI and are exactly
what quantum computers threaten). So QKD never bootstraps trust from
nothing: it is a **key-growing** primitive that converts a small shared
secret into a long stream of key, forever chaining back to the first
provisioned secret. Any vendor pitch of "unconditionally secure
communications" without mentioning the authenticated channel is selling the
weakest link twice.

## Practical Limits

- **Distance.** Fiber attenuates ~0.2 dB/km; at 500 km that is 100 dB of
  loss. Classical amplifiers are forbidden (no-cloning), and quantum
  repeaters remain experimental, so deployed fiber links run point-to-point
  at metro-to-hundreds-of-km scale, joined by *trusted nodes* -- hops whose
  operators can read the key, i.e., holes in the security model.
- **Key rate.** Secret key rate falls exponentially with channel loss;
  single-photon detectors add dead time and dark counts. Rates are fine for
  symmetric-key refresh (the use case) and hopeless for bulk data transport.
- **Cost and integration.** Dedicated dark fiber or free-space optics,
  specialty hardware, and a key-management layer to ship QKD keys into
  conventional encryptors.

## QKD vs Post-Quantum Cryptography

| Property | QKD (BB84) | PQC (e.g., ML-KEM, FIPS 203) |
|---|---|---|
| Security basis | Physics of measurement | Lattice hardness conjectures |
| Scope | Point-to-point links | Anywhere TLS/KEMs run (software) |
| Distance/repeaters | No amplification; trusted nodes | Network-routed, any distance |
| Authentication needs | Pre-shared secret or PQC anyway | Standard PKI |
| Maturity | Niche commercial links, testbeds | Standards finalized, deploying at scale |
| Failure mode | Detected disturbance (if within limits) | Algorithm broken by future math |

NIST standardized ML-KEM and siblings (FIPS 203/204/205) as the migration
path, and NSA's position is unambiguous: its QKD FAQ states the agency does
not recommend QKD or quantum cryptography for securing National Security
Systems traffic and directs adopters to post-quantum algorithms (CNSA 2.0)
instead -- citing cost, integration burden, and the authentication and
trusted-node gaps above. The reasoned interview answer: PQC is a software
patch with hardware-grade reach; QKD is a physics experiment with an
authentication dependency -- and they are complements under research, not
competitors in today's deployments.

## References

- [C. Bennett, G. Brassard, "Quantum Cryptography: Public Key Distribution and Coin Tossing" (1984, reprint with editorial note)](https://arxiv.org/abs/2003.06557)
- [H.-K. Lo, X. Ma, K. Chen, "Decoy State Quantum Key Distribution", PRL 94, 230504 (2005)](https://doi.org/10.1103/PhysRevLett.94.230504)
- [S.-K. Liao et al., "Satellite-to-ground quantum key distribution", Nature 549, 43-47 (2017)](https://doi.org/10.1038/nature23655)
- [NSA: Quantum Key Distribution (QKD) and Quantum Cryptography (QC) FAQ](https://www.nsa.gov/Cybersecurity/Quantum-Key-Distribution-QKD-and-Quantum-Cryptography-QC)
- [NIST FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism Standard (ML-KEM)](https://csrc.nist.gov/pubs/fips/203/final)
