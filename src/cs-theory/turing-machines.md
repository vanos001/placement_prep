# Turing Machines

## Formal Definition

A Turing machine (TM) is a 7-tuple M = (Q, Σ, Γ, δ, q₀, q_accept, q_reject) where:

| Component | Description |
|-----------|-------------|
| Q | Finite set of states |
| Σ | Input alphabet (does not include blank ⊔) |
| Γ | Tape alphabet (Σ ⊂ Γ, includes ⊔) |
| δ | Transition function: Q × Γ → Q × Γ × {L, R} |
| q₀ | Start state |
| q_accept | Accept state |
| q_reject | Reject state (q_accept ≠ q_reject) |

The TM has an **infinite tape** divided into cells, each holding a symbol from Γ. A **read/write head** scans one cell at a time. At each step, δ determines the next state, symbol to write, and head movement.

## Church-Turing Thesis

> Any function that is effectively computable by an algorithm can be computed by a Turing machine.

This is a **thesis**, not a theorem — it cannot be proved because "effectively computable" is informal. However, every proposed model of computation (lambda calculus, μ-recursive functions, Post systems, modern programming languages) has been shown equivalent to TMs.

## Variations

### Multi-tape Turing Machine

k tapes, each with its own head. Transition: δ: Q × Γᵏ → Q × Γᵏ × {L, R, S}ᵏ.

**Theorem**: Multi-tape TMs are equivalent in power to single-tape TMs (simulation overhead: O(n²) time).

### Non-deterministic Turing Machine (NTM)

δ: Q × Γ → 𝒫(Q × Γ × {L, R}). The machine "guesses" the correct transition. It accepts if **any** computation path reaches q_accept.

**Theorem**: NTMs are equivalent in power to deterministic TMs (simulation overhead: 2^O(n) time).

### Enumerators

A TM with a printer. It enumerates a language L by printing all strings in L. Equivalent to recognizable languages.

## Universal Turing Machine

A UTM U takes as input ⟨M, w⟩ (an encoding of TM M and input w) and simulates M on w. This is the theoretical basis for stored-program computers — the machine and its input share the same tape.

```python
def simulate_tm(tape, transitions, start_state):
    """Simplified TM simulation."""
    head = 0
    state = start_state
    while state not in ('q_accept', 'q_reject'):
        symbol = tape[head] if head < len(tape) else '⊔'
        if (state, symbol) not in transitions:
            state = 'q_reject'
            break
        new_state, write_symbol, direction = transitions[(state, symbol)]
        if head < len(tape):
            tape[head] = write_symbol
        state = new_state
        head += 1 if direction == 'R' else -1
    return state == 'q_accept'
```

## Decidability Classes

| Class | Definition | Example |
|-------|-----------|--------|
| Decidable | TM halts on all inputs (accepts or rejects) | A_DFA, A_CFG |
| Recognizable | TM halts on accepted inputs, may loop on rejected | A_TM |
| Undecidable | No TM decides it | Halting problem |

## Interview Questions

**Q: What is the Church-Turing thesis and why can't it be proved?**
A: It states that any effectively computable function can be computed by a TM. It's a thesis because "effectively computable" is an informal, intuitive notion — there's no formal system to reason about. All known computational models have been proven equivalent, lending strong evidence.

**Q: Are multi-tape TMs more powerful than single-tape TMs?**
A: No. They are equivalent in the languages they recognize. A multi-tape TM can be simulated by a single-tape TM with quadratic overhead. They differ only in efficiency, not computational power.

**Q: What is a Universal Turing Machine and why does it matter?**
A: A UTM simulates any other TM given its description. It proves that a single fixed machine can perform any computation, which is the theoretical foundation for general-purpose computers and the concept of software.

## References

- [Introduction to the Theory of Computation — Sipser](https://www.cengage.com/c/introduction-to-the-theory-of-computation-sipser-3e/)
- [Computability — Nigel Cutland](https://www.cambridge.org/core/books/computability/)
- See also: [Computability](./computability.md), [Formal Languages](./formal-languages.md), [Complexity Classes](./complexity-classes.md)
