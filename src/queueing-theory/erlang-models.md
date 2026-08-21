# Erlang B and Erlang C Models

Agner Krarup Erlang was a Danish mathematician who, while working for the Copenhagen Telephone Company in 1909–1917, derived the first quantitative results for telephone exchange capacity planning. His two formulas — **Erlang B** for loss systems and **Erlang C** for delay systems — remain the bedrock of call-center staffing, telephony trunk dimensioning, and any system where you must answer the question "how many servers do I need so that the probability of rejection or long wait stays below a target?".

## The Setup: Offered Traffic in Erlangs

Both formulas are functions of two inputs:

- **c**: the number of identical, parallel servers (trunks, agents, CPU cores, threads).
- **A**: the **offered traffic** in **Erlangs** (a dimensionless unit). One Erlang is the traffic that occupies exactly one server for one full busy hour.

If calls arrive at rate λ (calls/sec) and each has mean holding (service) time 1/μ seconds, then:

```
A = λ / μ          (offered load in Erlangs)
```

Equivalently A = λ × E[S] where E[S] is the mean service time. The system is stable when A < c (offered load less than number of servers); when A ≥ c the queue is unstable and the formulas do not apply.

The two models differ in what happens when all c servers are busy at the moment of a new arrival:

| Model | Behaviour when all c servers busy | Kendall notation |
|-------|------------------------------------|------------------|
| **Erlang B** | New arrival is **blocked / lost** (cleared from system) | M/M/c/c (no queue) |
| **Erlang C** | New arrival **waits** in an infinite FIFO queue | M/M/c (with queue) |

Both assume Poisson arrivals, exponential service times, identical servers, and statistical equilibrium.

## Erlang B: The Loss Formula

### Derivation sketch

For the M/M/c/c queue (c servers, system capacity = c, no queue), the steady-state probability of n customers in the system is given by the **truncated Poisson distribution** (a.k.a. the Erlang loss distribution):

```
            (A^n) / n!
P_n = ──────────────────────── ,   n = 0, 1, ..., c
       Σ_{k=0}^{c} (A^k) / k!
```

The **blocking probability** B(c, A) is the probability that an arrival finds all c servers busy:

```
B(c, A) = P_c = (A^c / c!) / Σ_{k=0}^{c} (A^k / k!)
```

This is **Erlang's B-formula** (1917). A remarkable property called **PASTA** (Poisson Arrivals See Time Averages) lets us equate "fraction of arrivals that are blocked" with "fraction of time all servers are busy" — both equal B(c, A).

### Recursion for numerical stability

Direct evaluation of factorials overflows quickly for large c. Erlang B admits the **stable recurrence**:

```
B(0, A) = 1
B(c, A) = (A · B(c-1, A)) / (c + A · B(c-1, A))
```

This is numerically stable in floating point even for c in the thousands. The same recursion is the basis of every commercial Erlang calculator.

### Inverse problem: trunk sizing

Given an offered load A and a target blocking probability B_target (commonly 0.01 = 1%, the long-standing telephony standard), find the smallest c such that B(c, A) ≤ B_target. This is a binary search over the recursion above.

### Worked Example: PBX trunk sizing

A company's PBX needs to carry an offered load of **A = 5 Erlangs** (e.g., 200 calls/hour with average 90 seconds each: 200 × 90/3600 = 5 Erlangs). The target blocking probability is **1%**.

Apply the recursion:

```
B(0, 5) = 1
B(1, 5) = (5·1)/(1 + 5·1)         = 5/6   ≈ 0.8333
B(2, 5) = (5·0.8333)/(2 + 5·0.8333) = 4.167/6.167 ≈ 0.6760
B(3, 5) = (5·0.6760)/(3 + 5·0.6760) = 3.380/6.380 ≈ 0.5298
B(4, 5) = (5·0.5298)/(4 + 5·0.5298) = 2.649/6.649 ≈ 0.3985
B(5, 5) = (5·0.3985)/(5 + 5·0.3985) = 1.993/6.993 ≈ 0.2850
B(6, 5) = (5·0.2850)/(6 + 5·0.2850) = 1.425/7.425 ≈ 0.1920
B(7, 5) = (5·0.1920)/(7 + 5·0.1920) = 0.960/7.960 ≈ 0.1206
B(8, 5) = (5·0.1206)/(8 + 5·0.1206) = 0.603/8.603 ≈ 0.0701
B(9, 5) = (5·0.0701)/(9 + 5·0.0701) = 0.350/9.350 ≈ 0.0375
B(10,5) = (5·0.0375)/(10+ 5·0.0375)= 0.188/10.19 ≈ 0.0184
B(11,5) = (5·0.0184)/(11+ 5·0.0184)= 0.092/11.09 ≈ 0.0083  ✓ < 1%
```

So **11 trunks** carry 5 Erlangs at ≤1% blocking. The marginal efficiency of the 11th trunk is small (only 0.4% blocking reduction per trunk at this point), while the 1st through 5th trunks are extremely efficient — this **economies of scale** is the same "trunking efficiency" that statistical multiplexing exploits in packet networks.

### Erlang B table (excerpt, blocking probabilities)

```
A in Erlangs →   1      2      5     10     20     50
c =  1        0.500  0.667  0.833  0.909  0.952  0.980
c =  2        0.200  0.400  0.676  0.826  0.909  0.961
c =  5        0.003  0.037  0.285  0.638  0.809  0.918
c = 10        ~0     ~0     0.018  0.215  0.558  0.832
c = 20        ~0     ~0     ~0     0.008  0.160  0.703
c = 50        ~0     ~0     ~0     ~0     ~0     0.052
```

This is the same table appearing in ITU-T E.490/E.500 recommendations for network dimensioning.

## Erlang C: The Delay Formula

### Derivation sketch

For the M/M/c queue (c servers, infinite queue), the steady-state probabilities are:

```
            (A^n)/n!                                for 0 ≤ n ≤ c
P_n = ────────────────────────── × P_0
              1

            (A^c)/(c!) × (A/c)^(n-c)                 for n ≥ c
P_n = ────────────────────────────────── × P_0
              1
```

where P_0 normalises the distribution:

```
              1
P_0 = ─────────────────────────────────────────────────────────
       [ Σ_{k=0}^{c-1} (A^k)/k! ] + (A^c)/(c!) × (c / (c - A))
```

(The second term is the contribution from the geometric tail, valid only when A < c.)

The **probability of waiting** (a.k.a. the Erlang C probability, the delay probability) is the probability that an arrival finds all c servers busy and must join the queue:

```
              (A^c)/(c!) × (c / (c - A))
C(c, A) = ─────────────────────────────────────────────────────
           [ Σ_{k=0}^{c-1} (A^k)/k! ] + (A^c)/(c!) × (c / (c - A))
```

### Average waiting time

Once you have C(c, A), the **conditional average wait** (given you must wait) and the **unconditional average wait** follow immediately:

```
W_q | (wait > 0) = 1 / (cμ - λ)        (mean of an exponential with rate cμ - λ)

W_q = C(c, A) × 1 / (cμ - λ)           (average queueing delay over all arrivals)

W = W_q + 1/μ                          (sojourn time = wait + service)

L_q = λ × W_q                          (Little's Law applied to the queue)
```

**Service-level** targets in call centres are usually stated as "X% of calls answered within Y seconds", computed as:

```
P(Wait > t) = C(c, A) × exp(-(cμ - λ) × t)
```

For example, "80/20" = answer 80% of calls within 20 seconds. Setting P(Wait > 20) = 0.20 and solving for c gives the staffing requirement.

### Worked Example: Call Centre Staffing

A call centre receives λ = 0.4 calls/sec (1440 calls/hour). Average handling time per call is 180 seconds, so μ = 1/180 ≈ 0.00556 calls/sec per agent. Offered load:

```
A = λ / μ = 0.4 × 180 = 72 Erlangs
```

Target service level: **answer 80% of calls within 20 seconds**. We must find the smallest c such that:

```
P(Wait > 20) = C(c, 72) × exp(-(c·0.00556 - 0.4) × 20) ≤ 0.20
```

Trying c = 80 (10% over offered load):

```
ρ = A/c = 72/80 = 0.90 (per-server utilization)
cμ - λ = 80·0.00556 - 0.4 = 0.445 - 0.4 = 0.045 calls/sec
C(80, 72) ≈ 0.748 (from a calculator)
P(Wait > 20) = 0.748 × exp(-0.045 × 20) = 0.748 × exp(-0.9) = 0.748 × 0.407 = 0.304
```

Too high (30.4%). Try c = 90:

```
ρ = 72/90 = 0.80
cμ - λ = 90·0.00556 - 0.4 = 0.100
C(90, 72) ≈ 0.444
P(Wait > 20) = 0.444 × exp(-0.100 × 20) = 0.444 × exp(-2) = 0.444 × 0.1353 = 0.0601
```

Now we are below target (6% < 20%). Binary-search the interval [80, 90]:

```
c=85: ρ=0.847, cμ-λ=0.0725, C(85,72)≈0.610, P=0.610×exp(-1.45)=0.610×0.235=0.143
c=84: ρ=0.857, cμ-λ=0.0667, C(84,72)≈0.640, P=0.640×exp(-1.33)=0.640×0.264=0.169
c=83: ρ=0.867, cμ-λ=0.0611, C(83,72)≈0.671, P=0.671×exp(-1.22)=0.671×0.295=0.198 ≈ 0.20 ✓
```

So **83 agents** are needed to meet an 80/20 service level for 1440 calls/hour with 180-second AHT. Useful sanity check: at c = 83 the average per-server utilization is 86.7% — right at the edge of the comfortable operating envelope, consistent with the rule of thumb "never run production above ~80%".

Average wait at this staffing:

```
W_q = C(83, 72) / (cμ - λ) = 0.671 / 0.0611 ≈ 10.97 seconds
```

So 80% of calls wait under 20 seconds, the *average* wait is ~11 seconds, but the conditional average (given you wait at all) is 1/(cμ-λ) = 16.4 seconds — illustrating the long tail of the exponential wait distribution.

## Practical Caveats

1. **Erlang B and C assume exponential service times.** Real call-handling times are log-normal (longer tail) and real server response times are heavy-tailed. Replace with Erlang-3 or simulation for high-precision work.
2. **Poisson arrivals** break down under "flash crowds" (a viral post, an incident) — busy-hour engineering is essential, but always pair with overload controls.
3. **Finite-queue versions** exist: Erlang B extended with retrials, Erlang C with bounded buffer (M/M/c/K), and the Engset model for finite population sizes (used in wireless cell dimensioning with a small number of subscribers).
4. **Abandonment** (callers hanging up before answer) is captured by the **Erlang-A** model (M/M/c + M, with exponential patience). Modern workforce-management software uses Erlang-A, not Erlang C.

## Applications Beyond Telephony

| Domain | Use |
|--------|-----|
| **Call centres** | Agent staffing to meet 80/20 or 90/10 SLAs |
| **Mobile networks** | Cell-sector channel dimensioning (with retries → Engset) |
| **Hospital bed planning** | C-section recovery beds, ICU beds |
| **Cloud compute** | VM/instance sizing for elastic services with rejection (Erlang B) or queueing (Erlang C) |
| **Customer service chat** | Chat-agent staffing with concurrency limits |

## References

1. Erlang, A. K. *Løsning af nogle Problemer fra Sandsynlighedsregningen af Betydning for de automatiske Telefoncentraler*. Elektroteknikeren, 1917. English translation: *Solution of some problems in the theory of probabilities of significance in automatic telephone exchanges*. Reprinted in E. Brockmeyer et al., *The Life and Works of A.K. Erlang*, Copenhagen, 1948. — [ITU historical reference](https://www.itu.int/en/ITU-T/studygroups/com12/history/Erlang.pdf)
2. ITU-T Recommendation E.490.1 (06/2020). *Overview of traffic engineering related to network performance*. — [ITU-T E.490.1](https://www.itu.int/rec/T-REC-E.490.1)
3. ITU-T Recommendation E.500. *Framework for traffic engineering and network performance measurement*. — [ITU-T E.500 series](https://www.itu.int/rec/T-REC-E.500)
4. Harchol-Balter, M. *Performance Modeling and Design of Computer Systems*, Ch. 7 (Multi-server systems: M/M/c and M/M/c/c). Cambridge University Press, 2013. Free preprint chapters: [https://www.cs.cmu.edu/~harchol/PerformanceModeling/](https://www.cs.cmu.edu/~harchol/PerformanceModeling/)
5. Kleinrock, L. *Queueing Systems, Vol. 1: Theory*. Wiley, 1975. — Chapter 5 covers multi-server Erlang models.
6. Gross, D., Shortle, J., Thompson, J., Harris, C. *Fundamentals of Queueing Theory*, 5th ed. Wiley, 2018. ISBN 978-1-118-94352-7.
7. Garnett, O., Mandelbaum, A., Reiman, M. *Designing a Call Center with Impatient Customers*. Manufacturing & Service Operations Management, 2003. — Introduces Erlang-A.
8. Wikipedia: [Erlang B](https://en.wikipedia.org/wiki/Erlang_B), [Erlang unit](https://en.wikipedia.org/wiki/Erlang_(unit)).

## Interview Questions

1. Derive Erlang B from the M/M/c/c steady-state distribution. Where does the truncation at c come from?
2. Why does the recursion `B(c, A) = (A·B(c-1, A))/(c + A·B(c-1, A))` give a numerically stable algorithm where direct evaluation of `A^c / c!` does not?
3. A call centre receives 600 calls/hour, AHT = 4 minutes, target = 80% answered within 30 seconds. Approximately how many agents are needed? Verify with the Erlang C recursion.
4. What is the difference between Erlang B and Erlang C in terms of Kendall notation? When is each appropriate?
5. What is the **PASTA** property, and why is it essential to the interpretation of B(c, A) as a "blocking probability"?
6. Explain why per-server utilization ρ = A/c cannot safely exceed ~0.85 in an Erlang C system. What happens to C(c, A) and W_q as ρ → 1?
