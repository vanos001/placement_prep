# Solidity

## Overview

Solidity is a statically typed, contract-oriented language designed for the EVM. It compiles to EVM bytecode via the Solidity compiler (`solc`) and, increasingly, via the intermediate Yul IR (`--via-ir` pipeline). Solidity is the dominant language on Ethereum and EVM-compatible chains — high-value contracts (Uniswap, Aave, Compound, MakerDAO) are written in it — but it is not the only option: Vyper, Fe, and Huff all target the same VM with different trade-offs. This page covers Solidity's contract structure, state layout, function types, modifiers, events, inheritance, libraries, ABI encoding, and a comparison to Vyper.

## Contract Structure

A Solidity source file is a sequence of `pragma`, `import`, and contract-like declarations. A "contract-like" declaration can be a `contract`, `library`, `interface`, or `abstract contract`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

library SafeMath {
    function add(uint256 a, uint256 b) internal pure returns (uint256) {
        unchecked { return a + b; }
    }
}

contract Vault {
    address public immutable owner;       // set in constructor, embedded in bytecode
    IERC20 public token;                 // storage slot 0
    mapping(address => uint256) private _balances;  // storage slot 1

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor(address token_) {
        owner = msg.sender;
        token = IERC20(token_);
    }

    function deposit(uint256 amount) external {
        require(token.transferFrom(msg.sender, address(this), amount), "tf");
        _balances[msg.sender] += amount;
    }

    function balanceOf(address who) external view returns (uint256) {
        return _balances[who];
    }
}
```

The `SPDX-License-Identifier` is mandatory in newer compiler versions (file refuses to compile otherwise). `pragma` pins the compiler version range; `^0.8.24` allows any 0.8.x where x ≥ 24.

## State Variables and Storage Layout

Storage is a key-value map of 32-byte keys to 32-byte values. Solidity packs small state variables into a single 32-byte slot, in declaration order. The rules:

- Each slot is 32 bytes.
- The first variable that doesn't fit in the current slot starts a new slot.
- `struct` fields always start a new slot and pack within it.
- `array` (dynamic or fixed) occupies its own slot, which holds only the *length* (for dynamic arrays) — the elements live at `keccak256(slot)`, `keccak256(slot) + 1`, ... (for value types) or in a separate mapping layout (for mappings).
- `mapping` occupies its own slot, which is unused; the value for key `k` lives at `keccak256(h(k) . p)` where `p` is the slot, `.` is concatenation, and `h` depends on the key type (for value types, the key itself padded; for strings/bytes, the keccak hash).
- `constant` and `immutable` are *not* in storage: constants are inlined at compile time, immutables are appended to the runtime bytecode and replaced at construction.

```
contract Layout {
    uint8   a;      // slot 0, byte 0
    uint8   b;      // slot 0, byte 1
    uint16  c;      // slot 0, bytes 2..3
    address d;      // slot 0, bytes 4..23  (still 32 total)
    uint256 e;      // slot 1
    uint128 f;      // slot 2, bytes 0..15
    uint128 g;      // slot 2, bytes 16..31
    uint256[] h;    // slot 3 holds length; elements at keccak256(3)+0, keccak256(3)+1, ...
    mapping(address => uint256) i;   // slot 4 unused on-chain; element at keccak256(abi.encodePacked(address, 4))
}
```

This packing matters: reading two variables in the same slot costs one `SLOAD` (2600 cold / 100 warm); reading across two slots doubles the gas. State layout is also the reason OpenZeppelin's upgradeable contracts use storage *gaps* — `uint256[50] __gap;` — so future versions can append fields without shifting existing slots (which would be a silent storage-corruption bug on upgrade).

## Functions: view, pure, payable

Solidity function mutability is one of: `pure`, `view`, `payable`, or default (write). The compiler enforces it statically.

| Mutability | Can read state? | Can write state? | Can receive ETH? |
|------------|-----------------|-------------------|-------------------|
| `pure`     | No              | No                | No                |
| `view`     | Yes             | No                | No                |
| default    | Yes             | Yes               | No (would revert on `msg.value > 0`) |
| `payable`  | Yes             | Yes               | Yes               |

Visibility is independent of mutability: `public`, `external`, `internal`, `private`. `private` is *not* private at the protocol level — anyone with a node can read the storage slot. It's a compiler-level visibility hint, not a cryptographic one. External callers cannot call `internal`/`private` functions directly, but the bytecode still contains them and they can be invoked via assembly (`call` to the function selector offset).

A `public` function automatically generates a *getter* of the same name. `public` state variables also auto-generate getters — a common gas-optimisation is to mark state `external` and provide a separate `view` getter that returns multiple fields at once.

## Modifiers

Modifiers are reusable wrapper code — they prepend logic before `_` (the function body) and append after:

```solidity
modifier nonReentrant() {
    require(_locked == 1, "reentrant");
    _locked = 2;
    _;
    _locked = 1;
}
```

Modifiers are inlined at the call site, so a modifier stack overflow (modifier calling modifier in a deep chain) consumes real bytecode. Solidity ≥0.5 limits modifier body stack depth to avoid infinite inlining, but multi-modifier chains still grow linearly with bytecode per use.

Important: modifiers see the *same* storage context as the function they wrap, including `msg.sender`. A classic bug is `onlyOwner` defined with `msg.sender == owner` — when used inside a `DELEGATECALL` proxy, `msg.sender` is the *original* caller and `owner` reads from the proxy's storage; if `owner` is stored in the implementation's slot rather than the EIP-1967 slot, you have a privilege-escalation bug.

## Events and Logs

Events emit log records that the EVM stores in the transaction receipt (not state). They are the canonical off-chain indexing primitive — The Graph, Dune, Alchemy webhooks, all rely on event logs. An event declaration defines a `topic0` (the keccak of the signature) plus up to three indexed topics (1..3) for fast Bloom-filter lookups.

```solidity
event Transfer(address indexed from, address indexed to, uint256 value);
event LogBig(bytes32 indexed h, bytes payload);  // payload goes to data, not topics
emit Transfer(msg.sender, to, amount);
```

- **Indexed** fields (max 3, plus `topic0` for the signature) end up in the Bloom filter — queryable by node-level indexing without scanning receipts.
- **Non-indexed** fields are ABI-encoded into the data portion of the log.
- For `string` and `bytes` (variable length), `indexed` puts the keccak hash in the topic, not the value itself — a common pitfall for event-decoding libraries.
- The Bloom filter is a 2048-bit bitmap appended to the block header. A light client can verify "no event matching this filter is in block N" in O(1) per block.

## Inheritance and C3 Linearization

Solidity supports multiple inheritance. The contract inheritance graph is linearised using the Python C3 algorithm; the resulting linearisation determines both storage layout and `super`-call order. The rule is:

> C3 linearises by taking the most-derived contract first, then for each contract recursively linearising its parents left-to-right, filtering out duplicates preserving the right-most occurrence.

```solidity
contract A { function f() public virtual pure returns (string memory) { return "A"; } }
contract B is A { function f() public virtual override pure returns (string memory) { return string.concat(super.f(), "B"); } }
contract C is A { function f() public virtual override pure returns (string memory) { return string.concat(super.f(), "C"); } }
contract D is B, C { function f() public pure override(B, C) returns (string memory) { return string.concat(super.f(), "D"); } }
// new D().f()  →  "ACBD"   (C3 linearisation: D, C, B, A)
```

The `override` keyword is mandatory since 0.8.x — the compiler enforces that the overriding function explicitly declares which base it overrides. Constructors run in the linearised order from most-base to most-derived.

## Libraries and `using...for`

A `library` is a stateless (or with `internal` storage-free) collection of functions. Calling a library function with `internal` visibility is inlined at the call site (no CALL gas). Calling an `external` library function compiles to a `DELEGATECALL` to the library's address — the library code runs in the caller's context, accessing the caller's storage (but only via `storage` parameters passed in explicitly).

```solidity
using SafeMath for uint256;
uint256 x = 1;
uint256 y = x.add(2);   // syntactic sugar: SafeMath.add(x, 2)
```

OpenZeppelin's `SafeERC20`, `Math`, `Strings`, `Counters` are all libraries. Since 0.8.0, built-in overflow checks make SafeMath unnecessary for new contracts in most cases — but the pattern survives for unchecked arithmetic (`unchecked { ... }` block) and for older 0.7 targets.

## ABI Encoding

Solidity's ABI is the wire format for calling functions and reading events. The ABI spec defines:

- **Type tuples** packed into a "head + tail" structure.
- The head is an array of fixed-size slots; for dynamic types, the slot holds a pointer (offset) into the tail.
- The tail holds the actual bytes for dynamic types (bytes, string, arrays, structs containing dynamic types).

```
// ABI-encode of  (uint256, string, uint256[2]) = (42, "hi", [1, 2])
// 32-byte words:
//   word 0: 0x...2a          (42)
//   word 1: 0x60             (offset to "hi" tail = 0x60)
//   word 2: 0x...01          (1)
//   word 3: 0x...02          (2)
//   word 4: 0x...02          (string length = 2)
//   word 5: 0x6869...        ("hi" right-padded)
//  total 6 * 32 = 192 bytes
```

The first four bytes of any function call are the **selector**: `bytes4(keccak256("transfer(address,uint256)"))`. `abi.encodePacked` skips the head/tail layout and packs values tightly — useful for hashing (`keccak256(abi.encodePacked(a, b))`), but dangerous because the encoding is *not* injective (`abi.encodePacked(uint8(1), uint16(2)) == abi.encodePacked(uint16(0x102))`). EIP-712 typed-data signing solves this by giving each field a type and a domain separator — see the [EIP-712 specification](https://eips.ethereum.org/EIPS/eip-712).

### EIP-712 typed data

EIP-712 defines a structured signing format that human-readable wallets (MetaMask, Rabby) render as a typed form rather than opaque hex. The signed message is:

```
keccak256(
  "\x19\x01" ++
  domainSeparator ++
  hashStruct(someStruct)
)
```

where `domainSeparator = keccak256(abi.encode(typeHash, name, version, chainId, verifyingContract, salt))` and `hashStruct` is `keccak256(typeHash ++ abi.encode(struct fields))`. Without EIP-712, signature replay across contracts (the same struct signed for VaultA can be replayed on VaultB) was a routine bug — EIP-712's `verifyingContract` field fixes this.

## Solidity vs. Vyper

[Vyper](https://docs.vyperlang.org/) is a Pythonic, intentionally-limited language targeting the EVM. Its design philosophy: *simplicity over expressivity, auditability over performance*. The differences:

| Feature | Solidity | Vyper |
|---------|----------|-------|
| Inheritance | Multiple, C3 linearised | Single only — no inheritance at all |
| Modifiers | Yes | No — write explicit checks |
| Inline assembly | Yes (`assembly { ... }`) | No |
| Function overloading | Yes | No |
| Recursion | Yes | No (bounded call stack) |
| Infinite loops | Possible | Bounded by gas; forbidden by style |
| `unchecked` arithmetic | Optional | Always checked; no `unchecked` |
| Code generation | Legacy + IR (`--via-ir`) | Native, predictable bytecode |
| Auditability | Lower (many constructs) | Higher (fewer footguns) |

Vyper's stance is that most hacks happen because of language features (modifier inlining hiding side effects, inheritance shadowing, assembly escape hatches). Removing them makes the code *bigger* but easier to formally verify. Curve, the largest stablecoin DEX, is written primarily in Vyper — though the July 2023 Vyper compiler reentrancy bug (CVE-2023-4336) hit Curve's Vyper-locked pools and ~$70M was drained, showing language limitations are not a silver bullet.

Solidity wins on expressivity and ecosystem: most libraries, audit tooling (Slither, Echidna), and OpenZeppelin contracts target it. Vyper wins for code where the auditors must read every line and prove properties by hand — pools, vesting contracts, governance contracts.

## Interview Questions

### Q1: What's the difference between `external`, `public`, `internal`, and `private`?

`public` is callable from anywhere and generates a getter; the compiler exposes an entry point with the function selector. `external` is callable only via a message call (not from inside the contract directly — `this.f()` instead of `f()`), but is slightly cheaper for big calldata because arguments are read from calldata rather than copied to memory. `internal` is callable from the contract and its derivatives (children, libraries); calls are inlined. `private` is `internal` but additionally not visible to derived contracts — though, again, "private" is a compile-time concept; the bytecode and storage are publicly readable by anyone running a node.

### Q2: Why does `keccak256(abi.encodePacked(uint8(1), uint16(0x0200)))` collide with another pack?

`abi.encodePacked` removes the type information and packs tightly: both expressions produce the 3-byte sequence `0x01 0x02 0x00`. To avoid collisions, either use `abi.encode` (which pads every value to 32 bytes) or include a length prefix, or use EIP-712 typed data where the type hash binds the encoding to a schema.

### Q3: When would you use `immutable` vs. `constant`?

A `constant` is evaluated at compile time and inlined everywhere — it cannot depend on `msg.sender` or `block.chainid`. An `immutable` is set exactly once in the constructor and then embedded in the runtime bytecode as a `PUSH32` value. Use `constant` for true literals (token decimals, role hashes), `immutable` for constructor-time configured values (governance timelock address, deployment-time owner). Both save one `SLOAD` per read vs. a normal storage variable.

### Q4: How does Solidity handle reentrancy at the language level?

It doesn't — there's no built-in mutex. The compiler emits `CALL` opcodes the same way regardless of re-entrance risk. The protection is a *convention*: the checks-effects-interactions pattern, modifiers like OpenZeppelin's `ReentrancyGuard` (and the post-Cancun `ReentrancyTransientGuard` using `TSTORE`), and pull-over-push payment patterns. Solidity 0.8's checked arithmetic protects against overflow, but not against reentrancy.

## References

- [Solidity documentation (latest)](https://docs.soliditylang.org/)
- [Solidity by Example](https://solidity-by-example.org/)
- [Solidity compiler (solc) source](https://github.com/ethereum/solidity)
- [EIP-712: typed structured data signing](https://eips.ethereum.org/EIPS/eip-712)
- [EIP-1967: proxy storage slots](https://eips.ethereum.org/EIPS/eip-1967)
- [Vyper language documentation](https://docs.vyperlang.org/)
- [Solidity ABI specification](https://docs.soliditylang.org/en/latest/abi-spec.html)
- [EIP-170: contract code size limit (24KB)](https://eips.ethereum.org/EIPS/eip-170)
- [CVE-2023-4336: Vyper reentrancy bug](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-4336)

## Related Topics

- [EVM Internals](./evm-internals.md) — Stack, gas, opcodes, calls, EOF
- [Smart Contract Security](./smart-contract-security.md) — Reentrancy, integer overflow, access control
- [ERC Standards](./erc-standards.md) — Token standards implemented in Solidity
- [Ethereum Internals](./ethereum-internals.md) — State trie, MEV, rollup architecture
