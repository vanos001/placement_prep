# Blockchain Security

## Overview

Blockchain security spans multiple layers: consensus-level attacks, smart contract vulnerabilities, bridge exploits, oracle manipulation, and economic attacks. Unlike traditional systems where security relies on perimeter defense, blockchain security assumes the network is adversarial and designs protocols that remain secure under worst-case assumptions. Understanding these attack vectors is critical for building and auditing decentralized applications.

## Cross-Chain Protocols and Bridges

### What Are Bridges?

Bridges enable asset and data transfer between independent blockchains. They lock assets on the source chain and mint corresponding representations on the destination chain, often using relayers or validators to verify cross-chain messages.

```mermaid
flowchart LR
    subgraph Chain A [Source Chain (Ethereum)]
        LOCK[Lock Contract]
        USER_A[User]
    end
    subgraph RELAY [Bridge Infrastructure]
        R1[Relayer/Validator 1]
        R2[Relayer/Validator 2]
        R3[Relayer/Validator 3]
    end
    subgraph Chain B [Destination Chain (Polygon)]
        MINT[Mint Contract]
        USER_B[User]
    end
    USER_A -->|Deposit| LOCK
    LOCK -->|Event| R1
    LOCK -->|Event| R2
    LOCK -->|Event| R3
    R1 -->|Message| MINT
    R2 -->|Message| MINT
    R3 -->|Message| MINT
    MINT -->|Mint tokens| USER_B
```

### Bridge Architecture Types

| Architecture | Trust Model | Example | Weakness |
|-------------|-------------|---------|----------|
| **MPC/Threshold** | t-of-n signers | Multichain, Wormhole | Centralization of key holders |
| **Optimistic** | Fraud proof period | Across Protocol | Withdrawal delay, assumes honest challenger |
| **ZK** | Cryptographic proof | zkBridge, Succinct | Proof generation latency, trusted setup (SNARK) |
| **Native (Rollup)** | L1 settlement | Optimism, Arbitrum | Same security as L1 for data, not execution |
| **Light client** | On-chain light client verification | IBC (Cosmos), Hyperlane | High gas cost for verification, header sync |

### Bridge Security Failures

Bridges have been the single largest source of crypto losses. Notable incidents:

| Bridge | Loss | Attack Vector |
|--------|------|---------------|
| Ronin Bridge (2022) | $625M | Compromised 5 of 9 validator private keys |
| Wormhole (2022) | $326M | Signature verification bypass in Solana contract |
| Nomad (2022) | $190M | Initialized root hash to zero, allowing any proof to pass |
| Harmony Horizon (2022) | $100M | 2-of-5 multisig compromised |
| Multichain (2023) | $125M+ | Operator key compromise / alleged rug pull |

> **Interview Angle**: "Why are bridges so vulnerable?" — Bridges face the fundamental problem of securing cross-chain state without a shared consensus. They must either trust a small validator set (creating a honeypot) or use expensive on-chain verification. The inter-chain trust boundary is inherently weaker than intra-chain consensus.

## Smart Contract Security

### Reentrancy Attacks

Reentrancy occurs when an external call to an untrusted contract allows that contract to re-enter the calling function before the first invocation completes. The attacker exploits the fact that the caller's state (e.g., balance) hasn't been updated yet.

```solidity
// VULNERABLE: Reentrancy via ETH transfer
contract VulnerableVault {
    mapping(address => uint256) public balances;

    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount);
        // External call BEFORE state update — vulnerable
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success);
        balances[msg.sender] -= amount;  // State update AFTER call
    }
}

// ATTACK CONTRACT
contract Attacker {
    VulnerableVault public vault;
    
    receive() external payable {
        if (address(vault).balance >= 1 ether) {
            vault.withdraw(1 ether);  // Re-enter during callback
        }
    }
    
    function attack() public payable {
        vault.deposit{value: 1 ether}();
        vault.withdraw(1 ether);  // Triggers reentrancy chain
    }
}
```

**Mitigations**:
1. **Checks-Effects-Interactions pattern**: Always update state before external calls
2. **ReentrancyGuard (OpenZeppelin)**: Mutex lock that prevents re-entry during execution
3. **Pull over push**: Let users withdraw rather than pushing funds
4. **Pull payment pattern**: Use `withdraw()` instead of `transfer()` to contracts

### Flash Loan Attacks

Flash loans are uncollateralized loans that must be repaid within a single atomic transaction. While intended for arbitrage and refinancing, they enable powerful attack vectors when combined with governance or oracle manipulation.

```mermaid
flowchart TD
    subgraph Single Transaction
        BORROW[1. Borrow $10M from Aave] --> MANIP[2. Manipulate price on low-liquidity pool]
        MANIP --> EXPLOIT[3. Exploit protocol relying on manipulated price]
        EXPLOIT --> REPAY[4. Repay $10M + fee to Aave]
        REPAY --> PROFIT[5. Keep profit (~$1M)]
    end
```

**Real examples**:
- **bZx (2020)**: Borrowed from dYdX, opened a massive short on Kyber, manipulated the price of WBTC, then profited on bZx's loan.
- **Cream Finance (2021)**: Used a flash loan to manipulate the price of AMP, then borrowed against inflated collateral.

### Oracle Attacks

Oracles provide smart contracts with off-chain data (prices, events, random numbers). Compromised oracles break the fundamental assumption that on-chain logic operates on accurate data.

| Attack Type | Description | Mitigation |
|-------------|-------------|------------|
| **Spot price manipulation** | Manipulate DEX pool price within a single tx | TWAP (time-weighted average price) |
| **Flash loan oracle manipulation** | Use flash loan to skew spot price | Chainlink with circuit breakers |
| **Stale price** | Oracle stops updating, contracts use old price | Heartbeat checks, freshness validation |
| **Arbitrage oracle** | Use one DEX as oracle, exploit on another | Aggregate multiple sources |

```solidity
// Vulnerable: Using spot price from a single DEX
function getPrice(address token) public view returns (uint256) {
    // Attacker can manipulate this with a flash loan
    return UniswapV2Library.getReserves(factory, token, WETH).value1;
}

// Safer: Chainlink with freshness check
function getPrice(address token) public view returns (uint256) {
    (, int256 price, , uint256 updatedAt, ) = Chainlink.feed(token).latestRoundData();
    require(block.timestamp - updatedAt < 3600, "Stale price");
    require(price > 0, "Invalid price");
    return uint256(price);
}
```

### Common Smart Contract Vulnerabilities

| Vulnerability | Description | Impact | Prevention |
|---------------|-------------|--------|------------|
| **Reentrancy** | Recursive external calls | Fund theft | Checks-Effects-Interactions, ReentrancyGuard |
| **Integer overflow/underflow** | Arithmetic wraparound | Logic bypass | Solidity 0.8+ (built-in checks), SafeMath |
| **Access control** | Missing authorization | Unauthorized actions | Ownable, AccessControl (OpenZeppelin) |
| **Front-running** | TX ordering by block producer | MEV extraction | Commit-reveal, private mempools |
| **Denial of Service** | Gas griefing, block gas limit | Contract unusable | Pull payments, bounded loops |
| **Delegatecall injection** | Malicious implementation swap | Full contract takeover | Verify implementation, transparent proxies |
| **Signature replay** | Reusing valid signatures | Repeated actions | Nonces, EIP-712 typed data |
| **Unchecked return values** | Ignoring low-level call results | Silent failures | Use SafeERC20, check return values |

## Consensus-Level Attacks

### 51% Attacks

When a single entity controls more than 50% of hash power (PoW) or stake (PoS), they can:
- **Double-spend**: Create a longer chain that reverses a confirmed transaction
- **Censorship**: Refuse to include certain transactions
- **Selfish mining**: Earn disproportionate rewards
- **Chain reorganization**: Rewrite recent history

On PoS chains, 51% attacks are mitigated by slashing — malicious validators lose their staked collateral, making attacks economically irrational. The cost of a sustained attack on Ethereum (34%+ of ~30M staked ETH ≈ ~$100B at peak) is prohibitively expensive.

### Eclipse Attacks

An eclipse attack isolates a target node from honest peers by surrounding it with attacker-controlled connections. The victim sees a false view of the network, enabling double-spending attacks against that node.

**Attack steps**:
1. Attacker fills the victim's peer table with attacker IPs
2. Victim's inbound/outbound connections are all to attacker nodes
3. Attacker feeds the victim a fabricated blockchain fork
4. Victim accepts payments on the fork that the attacker later reverses

**Mitigations**: Ethereum's discv5 peer discovery protocol uses random sampling from the routing table to resist eclipse attacks. Connection limits and peer scoring (EIP-4844-style reputation) further reduce vulnerability.

### Sybil Attacks

A Sybil attack creates many pseudonymous identities to gain disproportionate influence. In PoW, Sybil attacks are ineffective because each identity requires computational work. In PoS, each identity requires staked capital. In pure voting systems without identity costs, Sybil attacks can subvert consensus.

**Mitigations**:
- PoW: Each identity costs computational resources
- PoS: Each identity requires bonded stake, slashable on misbehavior
- Proof of Humanity: Social identity verification (Worldcoin, Proof of Humanity)
- Reputation systems: Peer scoring, stake-weighted voting

### Long-Range Attacks

Specific to PoS, a long-range attack involves an adversary who controlled significant stake at some past point creating an alternative chain from that point forward. Since the adversary genuinely controlled those keys historically, slashing cannot penalize them for "misbehavior" that occurred under their control.

**Mitigations**:
- **Weak subjectivity**: New nodes must obtain a recent checkpoint from a trusted source
- **Forward-secure signatures**: Keys evolve over time; old keys cannot sign new blocks
- **Finality gadgets**: Once a checkpoint is finalized, it cannot be reverted regardless of historical stake

## Interview Questions

### Q1: Explain the DAO hack and how it was prevented.

The 2016 DAO hack exploited a reentrancy vulnerability in the `splitDAO()` function. The attacker recursively called `withdraw()` before the balance was updated, draining ~$60M in ETH. It was stopped by a hard fork (creating Ethereum Classic) that modified the contract's state at a specific block. This is the most famous example of why the checks-effects-interactions pattern is critical.

### Q2: How would you secure a cross-chain bridge?

Defense in depth: (1) Use a large, geographically distributed validator set with high slashing penalties; (2) Implement rate limits and daily transfer caps; (3) Add timelocks and upgrade guards; (4) Use ZK proofs for message verification when possible; (5) Implement emergency pause functionality via multi-sig; (6) Conduct formal verification of the bridge contracts; (7) Monitor for anomalous withdrawal patterns.

### Q3: Why are flash loans not a vulnerability themselves?

Flash loans are a neutral tool — they enable atomic, uncollateralized lending. The vulnerability is in protocols that rely on spot prices or don't account for atomic price manipulation. Flash loans have legitimate uses: arbitrage (improving market efficiency), self-liquidation (avoiding penalties), and collateral swapping. The security issue is in the *consumer* contracts, not the flash loan mechanism.

## Related Topics

- [Ethereum Internals](./ethereum-internals.md) — MEV, PBS, rollup architecture
- [Consensus Mechanisms](./consensus-mechanisms.md) — Slashing, validator security, BFT safety
- [Web Security](../security/web-security.md) — General web security patterns
- [Cryptography](../cryptography/README.md) — Digital signatures, hash functions, ZK proofs
