# Smart Contract Security

## Overview

Smart contracts are immutable, public, and hold real money. Once deployed, the bytecode cannot be patched — fixing a bug requires deploying a new contract and migrating state, which is expensive and often socially impossible. The combination of immutability + financial value + adversarial environments (anyone can call any public function on a public network) means smart contract security is a discipline closer to formal verification than to traditional application security. This page covers the recurring vulnerability classes, the patterns that prevent them, and the tooling (Slither, Mythril, Echidna) that catches them.

The canonical catalogue of smart contract weaknesses is the [SWC Registry](https://swcregistry.io/), a maintained taxonomy of 38+ weakness types (SWC-100 through SWC-141) referenced by audit reports. ConsenSys maintains a [best-practices guide](https://consensys.github.io/smart-contract-best-practices/) that pairs each pattern with mitigations.

## Reentrancy and the DAO Hack

Reentrancy is the most famous smart contract vulnerability. The DAO hack of June 2016 exploited a recursive call: the attacker's `splitDAO` function called back into the DAO's `withdrawRewardFor` function before the DAO updated the attacker's balance, draining ~3.6M ETH (then ~$50M). The hard fork that rolled back this hack created Ethereum Classic.

The pattern in code:

```solidity
// VULNERABLE
contract Vulnerable {
    mapping(address => uint256) public balances;
    function withdraw() external {
        uint256 amt = balances[msg.sender];
        (bool ok, ) = msg.sender.call{value: amt}("");   // external call BEFORE state change
        require(ok);
        balances[msg.sender] = 0;                         // state change AFTER external call
    }
}

contract Attacker {
    Vulnerable target;
    constructor(address t) { target = Vulnerable(t); }
    receive() external payable {
        if (address(target).balance >= 1 ether) target.withdraw();   // re-enter
    }
    function pwn() external payable {
        target.deposit{value: 1 ether}();
        target.withdraw();    // triggers receive() → withdraw() → receive() → ...
    }
}
```

The bug is the *ordering*: the external call happens while the contract's internal state still shows the attacker as having a balance. Each recursive `withdraw()` reads the same stale balance.

### Checks-Effects-Interactions

The canonical fix is the **checks-effects-interactions** pattern:

1. **Checks**: validate preconditions (`require(balances[msg.sender] >= amount)`).
2. **Effects**: update internal state (`balances[msg.sender] -= amount`).
3. **Interactions**: external calls last (`msg.sender.call{value: amount}("")`).

With state updated first, a recursive call sees zero balance and bails out:

```solidity
function withdraw() external {
    uint256 amt = balances[msg.sender];
    require(amt > 0, "nothing");
    balances[msg.sender] = 0;                          // EFFECT first
    (bool ok, ) = msg.sender.call{value: amt}("");     // INTERACTION last
    require(ok, "transfer failed");
}
```

This pattern prevents re-entrancy across single-function boundaries. It does *not* prevent cross-function reentrancy (where function A makes an external call and the attacker calls function B which reads state that A has not yet updated). For that, you need a mutex.

### OpenZeppelin's ReentrancyGuard

[OpenZeppelin Contracts](https://docs.openzeppelin.com/contracts/) ship `ReentrancyGuard`, a simple mutex implemented with a storage slot:

```solidity
abstract contract ReentrancyGuard {
    uint256 private constant NOT_ENTERED = 1;
    uint256 private constant ENTERED = 2;
    uint256 private _status;
    constructor() { _status = NOT_ENTERED; }
    modifier nonReentrant() {
        require(_status != ENTERED, "reentrant");
        _status = ENTERED;
        _;
        _status = NOT_ENTERED;
    }
}
```

`nonReentrant` costs one `SLOAD` (cold 2600, warm 100) plus one `SSTORE` (2900 dirty). Post-Cancun, OpenZeppelin v5 ships `ReentrancyTransientGuard` using `TSTORE`/`TLOAD` (transient storage, EIP-1153): same semantics, but the write is 100 gas and clears at end of transaction — a ~50× gas saving on heavily-reentered contracts.

## Integer Overflow and SafeMath

Pre-0.8 Solidity had no overflow checks. `uint8(255) + uint8(1)` silently wrapped to 0. The classic exploit was `transfer(address[] calldata to, uint256 value)`: a loop summed `value * to.length` in a `uint8` (or in any type whose max was reached with a large-enough `to.length`), the sum wrapped to a small number, and the contract sent a small amount but debited each recipient as if it had sent the full amount. Variants of this hit BeautyChain (BEC token, 2018) and several others.

[SafeMath](https://docs.openzeppelin.com/contracts/4.x/utilities#math) was the manual fix:

```solidity
library SafeMath {
    function add(uint256 a, uint256 b) internal pure returns (uint256) {
        uint256 c = a + b;
        require(c >= a, "overflow");
        return c;
    }
}
```

Since Solidity 0.8.0 (December 2020), the compiler inserts overflow checks by default — `a + b` reverts on overflow with `Panic(0x11)`. This makes SafeMath mostly obsolete for new contracts; the residual use case is `unchecked { ... }` blocks for performance where you've proven the inputs are bounded. Panic codes (`0x11` overflow, `0x12` divide-by-zero, `0x32` array out of bounds) are distinguishable from `revert("msg")` at the ABI level.

## Access Control

Failure modes:

- **No access control** on a privileged function (e.g. Parity's `initWallet` in the multi-sig library allowed anyone to call `initWallet` and become owner — 150K+ ETH frozen forever in November 2017).
- **Wrong comparison** (`==` instead of `!=`, `>=` flipped to `<=`).
- **Using `tx.origin` instead of `msg.sender`** — `tx.origin` is the EOA that originated the transaction. A contract calls you, you call another contract that calls the privileged contract, and the privileged contract sees `tx.origin == user` — `user` is tricked into running the call chain.
- **Role defined as `bytes32` constant but compared with a string** — type confusion.
- **Two-step ownership transfer not implemented** — `transferOwnership` directly assigns, the new owner types a wrong address, contract is bricked.

OpenZeppelin's `Ownable`, `AccessControl`, and `AccessControlDefaultAdminRules` are battle-tested. The two-step pattern (current owner proposes, new owner accepts) is now the recommended default:

```solidity
function transferOwnership(address newOwner) external onlyOwner {
    _pendingOwner = newOwner;
    emit OwnershipTransferStarted(newOwner);
}
function acceptOwnership() external {
    require(msg.sender == _pendingOwner, "not pending");
    _transferOwnership(msg.sender);
}
```

## Front-Running and MEV

Public mempools leak pending transactions. Searchers (MEV bots) parse them, simulate, and submit competing transactions with higher gas prices to be ordered first by the block producer. Three patterns:

- **Sandwich attacks**: victim swaps token A → B on a constant-product AMM. The attacker front-runs by buying B first (price up), lets the victim's large swap execute at a worse price, then back-runs by selling B (price down). The victim loses ~1-3% per swap, the attacker pockets the difference minus fees.
- **Just-in-time liquidity**: attacker sees a large swap pending, adds liquidity right before the swap (capturing fees), and withdraws right after — the LP risk is socialised onto existing LPs.
- **Displacement**: a liquidation opportunity is pending; an attacker front-runs with their own liquidation call to grab the reward.

Mitigations:

- **Commit-reveal**: the user submits a hash of `(action, salt)`, waits a block, then reveals. Front-runners can't bid on the action because they don't know what it is.
- **Slippage tolerance**: DEX routers accept `amountOutMin` — if the actual output is below the bound, the tx reverts. This caps sandwich loss to ~1-3% rather than the entire trade.
- **Private order flow**: services like Flashbots Protect, MEV-Share, and CoW Swap's batch auctions route transactions directly to block builders, bypassing the public mempool and the searchers that scan it.
- **Threshold encryption**: encrypt transactions such that sequencers can include but not decrypt until the block is final — research-stage but eliminates front-running at the protocol level.

## Oracle Manipulation

Smart contracts that consume off-chain data (price feeds, randomness, weather) rely on oracles. The two failure modes are *stale* data and *manipulated* data. The classic wrong pattern uses an AMM spot price as a price oracle:

```solidity
// VULNERABLE: uses Uniswap V2 reserves as the price oracle
uint256 price = IUniswapV2Pair(pair).token0() == token
    ? reserves.reserve0 * 1e18 / reserves.reserve1
    : reserves.reserve1 * 1e18 / reserves.reserve0;
```

Spot prices move with pool size: a $10M pool sees its spot price move 10% on a $1M trade. A flash loan borrower can swing the spot price within a single transaction, exploit a downstream protocol that consumes this price, then unwind — all atomic, all risk-free if the downstream doesn't check freshness.

The fix is a *time-weighted average price* (TWAP). Uniswap V3's `oracle` module stores price * accumulators; consumers compute `(accumulator_now - accumulator_then) / (t_now - t_then)`. Manipulating a TWAP requires holding the skewed price across many blocks, which is capital-intensive and visible on-chain.

Chainlink's [price feeds](https://docs.chain.link/data-feeds) are the production default. Audited patterns include:

- Heartbeat checks: revert if `block.timestamp - updatedAt > heartbeat`.
- Deviation checks: revert if the latest round differs from the previous by more than a sanity bound.
- Multi-feed aggregation: use Chainlink + Uniswap TWAP + Pyth, require they agree within tolerance.

## Flash Loan Attacks

Flash loans are uncollateralised loans that must be repaid within one transaction — if not repaid, the entire tx reverts. They're a *tool*, not a vulnerability; the vulnerability is the downstream protocol that allows atomic price manipulation. The 2020 bZx hack illustrates:

1. Attacker borrows 10,000 ETH via dYdX flash loan.
2. Uses 5,500 ETH to long WBTC on Kyber — Kyber's price was thin and the trade pushed WBTC's reported price 3× higher.
3. bZx protocol used Kyber as its oracle and saw the inflated WBTC price; the attacker borrowed against the inflated collateral.
4. Unwinds: repays dYdX with 5,500 ETH and keeps ~700 ETH profit (~$360k then).

The root cause was the *oracle*, not the flash loan — the same attack works for any atomic lender with sufficient capital, but flash loans made it capital-free. Cream Finance (October 2021, $130M) used the same pattern: the attacker flash-borrowed yUSDLP tokens, used them as collateral whose price Cream computed from a thin AMM, and borrowed against inflated value.

## Other Recurring Vulnerabilities

- **Unchecked `call` return values**: `(bool ok, ) = token.call(...)` ignores `ok`; the call "succeeds" while the underlying token reverted. Mitigation: `SafeERC20.safeTransfer` checks the bool and the return data length.
- **Delegatecall to attacker-controlled address**: a proxy's implementation slot is writable by a privileged function; an attacker can point `implementation` at their own contract and run any function in the proxy's storage. Mitigation: EIP-1967 slot, plus a 2-day timelock on upgrades.
- **Signature replay**: a contract accepts signed authorisations; the same signature is replayed across chains. Mitigation: include `(chainId, contract, nonce, signer)` in the EIP-712 payload.
- **Denial of service via push payments**: a contract iterates over recipients and pushes ETH — one recipient is a contract that reverts, blocking the entire loop forever. Mitigation: pull-over-push — let each user `claim()` separately.
- **First-depositor inflation (ERC-4626)**: the first vault depositor can manipulate `totalAssets` via a direct donation to skew share price. Mitigation: virtual assets & shares (OpenZeppelin's `ERC4626` uses offset constants).

## Static Analysis: Slither

[Slither](https://github.com/crytic/slither) is a static analyzer (Trail of Bits) that runs in seconds on a codebase. It parses the AST produced by `solc` and runs ~100 detectors including:

- Reentrancy (paths where external call precedes state write).
- Unchecked `transfer` / `call` return values.
- Shadowed state variables.
- `tx.origin` in authentication.
- Conformance to ERC-20 / 721 / 4626 interfaces.
- Const-on-assignment bugs (e.g. `a = b + c` where `a` is `constant`).
- Storage layout differences between base and child contracts (upgrade hazards).

```bash
pip install slither-analyzer
slither . --filter reentrancy-eth    # find ether-leaking reentrancy paths
slither . --print human-summary     # high-level summary
```

Slither also has a *flat* contract export mode (`sol-flat-tree`) for verifying on Etherscan, and supports custom detectors in Python. Its weakness: false positives on intentionally-non-reentrant patterns (where a modifier guards the function).

## Symbolic Execution: Mythril

[Mythril](https://github.com/Consensys/mythril) is a symbolic execution engine (ConsenSys Diligence). It explores all execution paths up to a configurable depth, modelling the EVM state symbolically and using an SMT solver (Z3) to find inputs that violate assertions or known property patterns.

```bash
pip install mythril
myth analyze contract.sol --execution-depth 50 --max-transaction-depth 5
```

Mythril finds *concrete* exploits — it produces inputs that trigger the bug, not just line numbers. It excels at integer bugs, self-destruct paths, and unprotected Suicide. Its weakness: scaling beyond ~50 instructions of path depth is expensive; complex storage dependencies between contracts are hard to model.

## Fuzzing and Property Tests: Echidna

[Echidna](https://github.com/crytic/echidna) (Trail of Bits) is a property-based fuzzer. You write *properties* as Solidity functions that must always return `true`; Echidna generates random call sequences and tries to break them:

```solidity
contract TestContract is Ownable, ReentrancyGuard {
    // ... contract under test ...

    function echidna_owner_never_zero() public view returns (bool) {
        return owner() != address(0);
    }
    function echidna_balance_monotonic() public view returns (bool) {
        return totalDeposits >= lastTotalDeposits;
    }
}
```

```bash
echidna-test TestContract.sol --contract TestContract --test-mode property
```

Echidna is the canonical tool for invariants that span multiple transactions (e.g. "the sum of balances always equals totalSupply", "no user can withdraw more than they deposited"). Where Slither finds local bugs and Mythril finds single-transaction exploits, Echidna finds state-machine bugs that emerge only after a sequence of calls.

## Audit Workflow

A production audit typically includes:

1. **Spec & threat model**: write down what the contract does and what attackers can do.
2. **Manual review**: read every line; trace privileged paths and external calls.
3. **Slither**: catch the cheap stuff in seconds.
4. **Echidna / Mythril**: fuzz invariants over the call graph.
5. **Formal verification**: Certora, Halmos, or `kontrol` (KEVM) for the most valuable invariants.
6. **External review**: at least one team that didn't write the code signs off.

For a deeper best-practices reference, ConsenSys Diligence's [smart-contract best-practices](https://consensys.github.io/smart-contract-best-practices/) and the OpenZeppelin [contracts documentation](https://docs.openzeppelin.com/contracts/) cover audit checklists and tested reference implementations.

## Interview Questions

### Q1: Explain the DAO hack and how it would be prevented today.

The DAO's `splitDAO` function transferred ETH to the user and only then zeroed their balance. The attacker's contract re-entered `splitDAO` from its `receive` function before the zero-out, draining the contract recursively. Today, the checks-effects-interactions pattern plus a `nonReentrant` modifier prevents it. The historical fix was the chain hard-fork that created Ethereum Classic.

### Q2: Why does Solidity 0.8 make SafeMath mostly obsolete?

The compiler inserts `JUMPI` checks after each arithmetic operation that revert with `Panic(0x11)` on overflow (~50 gas per op). The remaining use case for SafeMath-style libraries is `unchecked { ... }` for arithmetic where you've proven inputs are bounded (iteration counters, modular arithmetic).

### Q3: What's the difference between Slither, Mythril, and Echidna?

Slither is static analysis — fast, finds local patterns (reentrancy candidates, unchecked returns, shadowed state). Mythril is symbolic execution — slower, finds concrete exploits but only on short paths. Echidna is property-based fuzzing — finds state-machine bugs that span transactions, requires you to write properties. A good audit uses all three: Slither to cheaply remove noise, Mythril to confirm reachable exploits, Echidna to verify cross-call invariants.

### Q4: A flash loan attacker drains your lending protocol in a single transaction. What went wrong?

Not the flash loan — the *oracle*. If you priced collateral by reading an AMM spot price, the attacker flash-borrowed capital, manipulated the spot price within the atomic tx, exploited the under-collateralisation, then unwound. The fix is to use a TWAP oracle with a multi-block window or a Chainlink feed with heartbeat and deviation checks. Flash loans are not the vulnerability; they're the means by which someone with no capital can trigger the underlying oracle flaw.

## References

- [SWC Registry — smart contract weakness catalogue](https://swcregistry.io/)
- [ConsenSys smart-contract best practices](https://consensys.github.io/smart-contract-best-practices/)
- [OpenZeppelin Contracts documentation](https://docs.openzeppelin.com/contracts/)
- [Slither static analyzer (Trail of Bits)](https://github.com/crytic/slither)
- [Mythril symbolic execution (ConsenSys)](https://github.com/Consensys/mythril)
- [Echidna property-based fuzzer (Trail of Bits)](https://github.com/crytic/echidna)
- [EIP-712: typed structured data signing](https://eips.ethereum.org/EIPS/eip-712)
- [EIP-1153: transient storage (used by ReentrancyTransientGuard)](https://eips.ethereum.org/EIPS/eip-1153)
- [Chainlink Data Feeds documentation](https://docs.chain.link/data-feeds)

## Related Topics

- [Solidity](./solidity.md) — Contract structure, modifiers, inheritance, ABI encoding
- [EVM Internals](./evm-internals.md) — Gas model, storage layout, call opcodes
- [Blockchain Security (overview)](./blockchain-security.md) — Bridges, MEV, consensus-level attacks
- [ERC Standards](./erc-standards.md) — Token contracts and their security implications
