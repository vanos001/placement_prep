# EVM Internals

## Overview

The Ethereum Virtual Machine (EVM) is a stack-based, big-endian, 256-bit virtual machine that executes smart-contract bytecode. It is the execution engine behind every Ethereum transaction that touches code, and the same bytecode runs inside every EVM-compatible chain — Optimism, Base, Arbitrum (in AVM/Stylus modes this differs, but the EVM core is preserved), Polygon, BNB Chain, and many others. This page walks through the EVM as a virtual machine, its gas and storage model, the call and creation opcodes, the deprecation of `SELFDESTRUCT`, and the upcoming EVM Object Format (EOF) that reshapes how bytecode is laid out and validated.

## The EVM as a Stack Machine

The EVM is a *stack machine* with a maximum stack depth of **1024 items**, each item being a **256-bit word**. There is no register file; all intermediate computation flows through the stack. Bytecode is a linear sequence of one-byte opcodes, optionally followed by immediate arguments (only `PUSH1`..`PUSH32` have immediates, in the legacy format). The program counter (`PC`) is also a 256-bit value, though in practice it indexes a 32-bit-range code byte array.

Architectural constraints worth memorising:

- **Word size**: 256 bits (32 bytes). Smaller types are stored packed in 32-byte slots, but every stack value is 256-bit. Keccak-256 and the elliptic-curve precompiles operate natively on this width.
- **Stack cap**: 1024 items. Hitting 1024 with `JUMPDEST` and `PUSH` loops is a common DoS probe; many clients throw earlier (e.g. 1024 is hard limit, gas costs make it expensive but possible).
- **No floating point**: integer arithmetic only. Division truncates. `ADDMOD`, `MULMOD` give 4096-bit intermediates for a single op.
- **Determinism**: no source of randomness, no I/O, no wall-clock beyond `block.timestamp` / `block.number` (post-merge these are slot-derived and rounded).

A minimal "return the calldata length" contract in Yul (compiled via `--strict-assembly`) looks like:

```
/// yul: return-cds.yul
{
    let n := calldataload(0)
    let ptr := mload(0x40)
    mstore(ptr, n)
    return(ptr, 0x20)
}
```

The disassembly is essentially `CALLDATALOAD(0) PUSH1 0x40 MLOAD MSTORE PUSH1 0x20 RETURN`. Every EVM operation is a single byte (with the exception of `PUSH`), and opcodes ≥ `0x60` (`PUSH1`) carry their immediates inline.

## Gas Model

Gas is the metering layer that prevents unbounded computation. Each opcode has a fixed cost in the schedule defined by EIP-150, EIP-2929, EIP-3529, and successors. Post-Berlin, accessed-then-touched addresses and storage slots become "warm" (cost 100 for `SLOAD`) on first touch and "cold" (2600 for `SLOAD` on a never-touched account) on subsequent calls within the same transaction. EIP-2929 closed a class of griefing attacks where cold access was charged at the cheaper warm rate.

| Resource | Cost (Berlin / London) |
|----------|------------------------|
| `ADD`, `SUB`, `LT`, `EQ` | 3 |
| `MUL`, `DIV`, `MOD` | 5 |
| `SLOAD` cold / warm | 2600 / 100 |
| `SSTORE` (zero→nonzero) | 20000 |
| `SSTORE` (nonzero→nonzero) | 2900 (after 5000 dirty) |
| `SSTORE` (nonzero→zero, refund) | 4800 refund |
| `CREATE` | 32000 |
| `CREATE2` | 32000 + 6 * init_code_size |
| `CALL` cold address | 2600 |
| `LOG0` | 375 + 8 * topic? 0 + 8 * data |
| `KECCAK256` | 30 + 6 * (words) |

Two further constraints matter:

1. **63/64 rule (EIP-150)**: any `CALL` reserves `floor(gas / 64)` for the caller and forwards at most the rest. This prevents a caller from being starved by a child call reverting.
2. **Refund cap (EIP-3529)**: gas refunds from clearing storage were capped at 20% of the gas spent in the transaction (previously 50%). This kills the "gas token" griefing vector where contracts intentionally stored and cleared state to harvest refunds.

EIP-1559 separates fees into a *base fee* (burned) and a *priority fee* (paid to the validator). The block-level gas target is 15M; if a block uses more, the next base fee rises by up to 12.5% (denominator 8). The fee market is now a first-price auction only on the priority fee, which significantly reduces user overpayment.

## Memory vs. Storage vs. Calldata

The EVM has three writable regions, with wildly different cost models:

```
+---------------+-------------+---------------------------+----------------------------------+
| Region        | Cost       | Lifetime                  | Model                            |
+---------------+-------------+---------------------------+----------------------------------+
| calldata      | very cheap  | tx (read-only here)        | linear, 16 gas / 32-byte word   |
| memory        | quadratic   | call frame                  | byte-addressed, zero-initialised |
| storage       | very costly | persistent across txs      | 256-bit key → 256-bit value     |
| transient (TSTORE) | cheap | tx                         | EIP-1153, 100/2200 gas           |
+---------------+-------------+---------------------------+----------------------------------+
```

- **Calldata** is the transaction's payload. It is the cheapest way to pass large data — rollups post batches via calldata (and now via EIP-4844 blobs, which live in a separate fee market). Reading calldata uses `CALLDATALOAD`, `CALLDATASIZE`, `CALLDATACOPY`.
- **Memory** is a byte array, zero-initialised, grown in 32-byte increments. Expanding memory costs gas quadratically: `3 * words + (words² / 512)` where `words = ceil(byte_offset / 32)`. This makes large in-memory buffers (unbounded loops of `MSTORE`) very expensive.
- **Storage** is the persistent key-value map backing the contract. Keys and values are 256-bit. `SSTORE` writes; `SLOAD` reads. Post-Berlin, the cost depends on whether the slot is warm or cold and on its prior value (zero vs. nonzero), enabling the dirty-write refund structure described above.
- **Transient storage** (EIP-1153, live on mainnet since the Cancun upgrade) introduces `TSTORE`/`TLOAD`, scratch space that lives only for the duration of the transaction. It is dramatically cheaper than `SSTORE` and unlocks reentrancy locks without 20k-gas writes — this is the foundation of the new OpenZeppelin `ReentrancyTransientGuard`.

## Opcode Taxonomy

There are roughly 140 active opcodes (with EOF adding more). They cluster into:

- **Stack**: `POP`, `PUSH*`, `DUP*` (1..16), `SWAP*` (1..16)
- **Arithmetic**: `ADD`, `SUB`, `MUL`, `DIV`, `SDIV`, `MOD`, `SMOD`, `ADDMOD`, `MULMOD`, `EXP`, `SIGNEXTEND`
- **Comparison / bitwise**: `LT`, `GT`, `SLT`, `SGT`, `EQ`, `ISZERO`, `AND`, `OR`, `XOR`, `NOT`, `BYTE`, `SHL`, `SHR`, `SAR`
- **Environment**: `ADDRESS`, `BALANCE`, `ORIGIN`, `CALLER`, `CALLVALUE`, `CALLDATASIZE`, `CALLDATALOAD`, `CALLDATACOPY`, `CODESIZE`, `CODECOPY`, `GASPRICE`, `EXTCODESIZE`, `EXTCODECOPY`, `EXTCODEHASH`, `RETURNDATASIZE`, `RETURNDATACOPY`, `BLOCKHASH`, `COINBASE`, `TIMESTAMP`, `NUMBER`, `PREVRANDAO` (formerly `DIFFICULTY`), `GASLIMIT`, `CHAINID`, `SELFBALANCE`, `BASEFEE`, `BLOBHASH`, `BLOBBASEFEE`
- **Block context**: `BLOBBASEFEE` (Cancun), `MLOAD`/`MSTORE`/`MSTORE8`, `SLOAD`/`SSTORE`, `TLOAD`/`TSTORE`
- **Flow**: `STOP`, `JUMP`, `JUMPI`, `PC`, `MSIZE`, `GAS`, `JUMPDEST`
- **Logging**: `LOG0`..`LOG4`
- **System**: `CREATE`, `CREATE2`, `CALL`, `CALLCODE`, `DELEGATECALL`, `STATICCALL`, `SELFDESTRUCT` (post-Shanghai non-functional in many cases), `RETURN`, `REVERT`
- **Precompiles** (not opcodes, accessed by `CALL` to addresses `0x01`..`0x0c`): `ecrecover`, SHA-256, RIPEMD-160, identity, modular exponentiation, BN-256 ecAdd, ecMul, pairing, blake2-f, point evaluation (KZG, used by EIP-4844), `false`/`p256verify` (Prague).

Reference for the canonical cost tables is the [evm.codes](https://www.evm.codes/) reference maintained by the Ethereum organization; the [Yellow Paper Appendix G](https://ethereum.github.io/yellowpaper/paper.pdf) is the formal source.

## CREATE vs. CREATE2

`CREATE` deploys a new contract from `msg.sender`. The new address is:

```
keccak256(rlp([sender, sender_nonce]))[:12:]
```

i.e. it depends only on the deployer and their nonce. This is convenient but means the same init code deployed twice from the same account at different nonces yields different addresses — so counterfactual deployment (knowing the address before sending a tx) is impossible.

`CREATE2` (EIP-1014) was introduced to support counterfactual deployment, the backbone of wallet abstraction (Safe, ERC-4337), state channels, and CREATE2-based factory patterns like Uniswap V2 pairs. The address is:

```
keccak256(0xff ++ sender ++ salt ++ keccak256(init_code))[12:]
```

where `salt` is a 32-byte user-chosen value and `init_code` is the creation bytecode. Because the address is deterministic and depends only on (sender, salt, init_code), one can compute it before any transaction is sent. Critical caveat: if `CREATE2` redeploys (after a `SELFDESTRUCT` or, post-EIP-6787, in practice never), the new contract starts with a **zeroed nonce** but inherits no other state.

A common factory pattern:

```solidity
function deploy(bytes32 salt, bytes memory init) external returns (address addr) {
    bytes memory code = abi.encodePacked(type(MyContract).creationCode, abi.encode(msg.sender));
    assembly {
        addr := create2(callvalue(), add(code, 0x20), mload(code), salt)
        if iszero(addr) { revert(0, 0) }
    }
}
```

## CALL vs. DELEGATECALL vs. STATICCALL

The trio of external call opcodes differ in *whose* context the call runs in:

```
                caller's storage   caller's balance   msg.sender        address(this)
CALL            callee             callee             caller            callee
DELEGATECALL    caller             caller             caller's msg      caller
STATICCALL      callee             callee             caller            callee (read-only)
```

- **CALL** forwards ETH and switches `msg.sender` to the caller. Storage and `address(this)` become the callee's. The most common call form.
- **DELEGATECALL** executes the callee's code *in the caller's context*. Storage, `address(this)`, `msg.value`, and `msg.sender` are inherited from the caller. This is the opcode that powers proxy patterns — the proxy holds state and the implementation holds code. Get it wrong and you have Parity's November 2017 multi-sig incident (a `DELEGATECALL` to a contract whose `initWallet` had no access control wiped storage across hundreds of wallets).
- **STATICCALL** enforces no state mutation. Any `SSTORE`, `CREATE`, `LOG`, `SELFDESTRUCT`, or `CALL` with non-zero `value` reverts. Useful for safe view-function invocation across contract boundaries.

A subtle point: `DELEGATECALL` does **not** forward `msg.value` as a separate field for `CALL`-style access; `msg.value` in a delegatecall is the value of the *original* call that entered the proxy. This bit pattern of "inherit everything" is why delegatecall is dangerous: a single line of inline assembly `delegatecall(gas(), impl, 0, 0, 0, 0)` can be turned into "give the implementation any power over my storage" — including the storage slot holding the implementation pointer itself.

## SELFDESTRUCT and EIP-6787

`SELFDESTRUCT` historically: (a) sent all remaining ETH to a beneficiary, (b) marked the contract for deletion at the end of the transaction, (c) **reset the contract's nonce to zero**, allowing re-creation with `CREATE` from the same address. EIP-6787 (included in the Cancun hard fork) changes this for the Verkle-tree transition: `SELFDESTRUCT` now only deletes state when called *within the same transaction that created the contract*. Otherwise it merely sends the ETH balance — storage, code, and nonce all persist.

This kills two ecosystems:

1. **State rent / gas tokens**: contracts like GST2 and CHI relied on minting storage during cheap gas, then self-destructing to harvest refunds. EIP-3529 already cut refunds to 20%; EIP-6787 finishes the job by removing the deletion altogether.
2. **Metamorphic contracts** (CREATE2 redeploy patterns that want fresh nonces): these no longer work because the contract cannot be destroyed post-creation tx.

Forwards compatibility with the Verkle tree: Verkle trees (EIP-4762) need a bounded state growth, and `SELFDESTRUCT`'s "delete only in same-tx-as-create" rule preserves the tree-invariant property — the cell for the account remains addressable across the witness boundary.

## The EVM Object Format (EOF)

EOF (EVM Object Format) is a set of EIPs (3540, 3670, 4200, 4750, 5450, 6206, 7069, 7480, 7692) that restructure EVM bytecode into a versioned, sectioned, validated container. As of late 2024 the spec is targeted at the Fusaka fork; some testnets have deployed it.

### Why EOF?

Legacy bytecode has no header. A client executing `JUMP` must scan for `JUMPDEST` (the only valid jump target) at runtime — a quadratic risk mitigated only by precomputed jump-destination tables. Code is data: `CODECOPY` lets a contract introspect its own bytes; this makes formal verification, ahead-of-time compilation, and on-chain analysis hard. There is no separation between code and data, no integrity check on the format, no way to introspect "what functions does this contract expose".

### EOF Container Layout

```
+-----------------------------------------------------------+
| EOF container                                             |
+-----------------------------------------------------------+
| magic        : 0xEF00 (2 bytes, big-endian)               |
| version      : 1   (1 byte)                               |
| section_sizes: section_id (1) + payload_size (3 bytes)    |
|   types_section_size                                      |
|   code_section_size                                      |
|   (data_section_size if present)                         |
| types_section : function signatures + max_stack_height    |
| code_section  : EOF bytecode (no JUMP/JUMPI, only RJUMP)  |
| data_section  : raw bytes (accessible via CODECOPY /      |
|                 DATALOAD / DATALOADN)                     |
+-----------------------------------------------------------+
```

Each section is length-prefixed; the magic `0xEF00` distinguishes EOF from legacy bytecode (which cannot start with `0xEF` because there is no opcode `0xEF`).

### What EOF forbids

EIP-3670 enforces *code validation*: opcodes must exist (otherwise `INVALID`), `RJUMP`/`RJUMPI` targets must land on section boundaries, stack heights must match the declared `max_stack_height` for each function, and gas costs are validated ahead of execution. The payoff is:

- No runtime `JUMPDEST` analysis (faster execution, smaller clients).
- A *real* function table (`CALLF`/`RETF` opcodes — EIP-4750) replaces bespoke dispatcher patterns.
- Stack underflow is impossible — the validator proves it statically.
- Tooling (compilers, verifiers) sees clean separation of code and data.

### Migration

Legacy contracts continue to work — EOF is opt-in via the `0xEF00` magic. New contracts can be EOF, old ones are unaffected. The [EIP-3670 specification](https://eips.ethereum.org/EIPS/eip-3670) defines the validation rules; [EIP-3540](https://eips.ethereum.org/EIPS/eip-3540) defines the container; the [EIP-3541](https://eips.ethereum.org/EIPS/eip-3541) forbids code starting with `0xEF` outside EOF.

## Interview Questions

### Q1: Why is the EVM 256-bit? Wouldn't 64-bit be faster?

256-bit aligns with Keccak-256 (the hash function underpinning the Merkle-Patricia tries), the secp256k1 scalar field, and 32-byte storage slots. Going 64-bit would force each `SLOAD` to assemble four 64-bit loads into a 256-bit value. Also, KECCAK256/SHA-3 has a 1600-bit state, so each "absorb" round operates on 136 bytes; 256-bit words minimise padding overhead.

### Q2: What stops a contract from spending unbounded gas inside a single CALL?

The 63/64 rule (EIP-150) forces the caller to retain at least `floor(gas/64)`. The callee can use only what was forwarded. Beyond that, the block gas limit caps any single transaction, and individual opcodes have positive cost (no free opcode exists, post-Istanbul `SLOAD` is no longer 200). The quadratic memory-expansion curve prevents unbounded in-memory buffers.

### Q3: Why does DELEGATECALL exist if it's so dangerous?

It exists because it is the only way to implement upgradeable contracts: the proxy holds state, the implementation holds code, and the call transparently delegates execution. Without `DELEGATECALL`, every upgrade would require a state migration. The danger is not the opcode — it is *unsandboxed* delegatecall. OpenZeppelin's `Proxy` and the EIP-1967 storage slot convention (`keccak256("eip1967.proxy.implementation") - 1`) make this pattern safe by avoiding storage collisions.

### Q4: I want to deploy a contract whose address I know before sending any transaction. Which opcode and which inputs?

Use `CREATE2`. Address = `keccak256(0xff ++ deployer ++ salt ++ keccak256(init_code))[12:]`. Pre-compute the address off-chain, then deploy with the chosen salt; users can pre-fund the address (e.g. for counterfactual Safe wallets). The only catch: `init_code` is part of the address computation, so a different creation code produces a different address even with the same salt.

## References

- [Ethereum Yellow Paper (Appendix G — gas schedule)](https://ethereum.github.io/yellowpaper/paper.pdf)
- [Ethereum.org EVM docs](https://ethereum.org/en/developers/docs/evm/)
- [evm.codes — interactive opcode reference](https://www.evm.codes/)
- [EIP-1014: CREATE2](https://eips.ethereum.org/EIPS/eip-1014)
- [EIP-150: 63/64 rule and call cost changes](https://eips.ethereum.org/EIPS/eip-150)
- [EIP-3529: gas refund reduction](https://eips.ethereum.org/EIPS/eip-3529)
- [EIP-3670: EOF — code validation](https://eips.ethereum.org/EIPS/eip-3670)
- [EIP-3540: EOF — container format](https://eips.ethereum.org/EIPS/eip-3540)
- [EIP-6787: SELFDESTRUCT only in same-tx-as-create](https://eips.ethereum.org/EIPS/eip-6787)
- [EIP-1153: transient storage](https://eips.ethereum.org/EIPS/eip-1153)

## Related Topics

- [Ethereum Internals](./ethereum-internals.md) — State trie, EIP-1559 fee market, EIP-4844 blobs
- [Solidity](./solidity.md) — High-level language compiled to EVM bytecode
- [Smart Contract Security](./smart-contract-security.md) — Reentrancy, access control, audit tooling
- [ERC Standards](./erc-standards.md) — Token standards implemented on top of the EVM
