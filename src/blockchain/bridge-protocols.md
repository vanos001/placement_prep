# Cross-Chain Bridge Protocols

## Overview

A blockchain bridge moves assets or messages between two chains that do not share a consensus. Because the source chain has no way to natively "send" a transaction to a destination chain, every bridge is fundamentally a *protocol for replacing a real asset transfer with an escrow* — a small set of signers (or a small set of proofs) that attest to events on the source chain so that the destination chain can release a corresponding asset.

This page covers the four dominant bridge architectures, each with a different security assumption: the **trusted bridge** (multisig custodian, e.g., Wormhole's original design), the **trustless bridge** (light-client verification, e.g., IBC), the **liquidity pool model** (Lock-Mint-Burn-Release, e.g., Across, Stargate), and the **wrapped token model** (BTC on Ethereum). We then dissect three of the largest bridge hacks — Ronin (March 2022, $624M), Wormhole (February 2022, $326M), and Nomad (August 2022, $190M) — to show how each architecture's failure mode maps to its security assumption.

The honest framing: **bridges are the most-attacked corner of crypto infrastructure**. Chainalysis estimated that through 2022, bridges accounted for ~69% of all stolen funds in crypto — $2.5B+ across 13 incidents. Understanding why is the point of this page.

## The Trusted Bridge (Multisig Custodian)

The simplest bridge design: a set of N custodians jointly control a multisig wallet on the destination chain. When they see a deposit on the source chain, they sign a release transaction. The trust assumption is "*at least* `m` of `n` custodians are honest."

```
                  Trusted (Multisig) Bridge

   User (Source chain A)                  Custodians (n signers)            Destination chain B
   ----------------------                ----------------------            --------------------
       deposit X of asset                 watch source A                   multisig address
       into bridge escrow                 -> see deposit confirmed         on chain B holds
                                            (k blocks)                     minted equivalent
                                          -> sign release message
                                       --------------------------------> verify m-of-n sigs
                                                                          -> release X (minted)
                                                                          to user

   Trust assumption: at least m of n custodians are honest AND non-colluding.
   If n-m+1 collude, they can mint unbacked funds on chain B.
   If custodians go offline, redemptions are frozen.
```

Concrete parameters from production systems:

- **Wormhole (original, pre-hack)**: 19 validator custodians, 13-of-19 signatures required to authorise a mint on Solana.
- **Ronin (pre-hack)**: 9 validators, 5-of-9 multisig (lowered from the original 9-of-9 in November 2021 to reduce gas costs).
- **Multichain (pre-shutdown)**: 8-of-11 threshold on a Secp256k1 multi-party computation (MPC) wallet.

The security of this model has two distinct failure surfaces:

1. **Key compromise**: an attacker who steals `n - m + 1` private keys can mint arbitrary tokens on the destination chain, with no backing assets on the source. The Ronin hack was this exact pattern: the attacker stole 5 of 9 validator keys (presumably via social engineering of the validator operators) and minted 173,600 ETH and 25.5M USDC on the Ronin chain.
2. **Quorum manipulation**: the multisig parameters can be changed off-chain by the bridge operators; users have no recourse. The Wormhole hack exploited this through a different vector (signature verification bypass) but the same root cause: the multisig was the single point of failure.

> **Interview Angle**: "Why don't bridges just use more signers?" They do — Wormhole moved to a 19-of-19 Guardian set after the hack, and LayerZero uses 1-of-1 with DVN (decentralised verifier network) signers. The trade-off is **operational complexity**: every signer must coordinate, the gas cost of m-of-n verification scales with `n`, and rotating a single signer requires a full multi-party key refresh ceremony. Adding signers helps against key compromise but not against collusion among the signers.

## The Trustless Bridge (Light Client Verification)

The trustless bridge replaces human custodians with **cryptographic verification**: the destination chain runs a *light client* of the source chain as a smart contract. Anyone can post a header chain proof from chain A to a verifier contract on chain B, and once a header is finalised, Merkle proofs against it can unlock arbitrary messages.

```
              Trustless (Light Client) Bridge

   Relayer (anyone)                          Source chain A                 Destination chain B
   ---------------                          --------------                 --------------------
       watches chain A,                                          Light-client smart contract
       collects finalised                                         verifies each header's PoW/PoS
       block headers                                             -> stores header chain on-chain

   posts header H_n + chain proof                            -> verify PoW (or validator sigs
       (for PoW: work below target,                             in the case of PoS chains)
        difficulty transitions,                                  -> store H_n in contract
        previous-header linkage)

   user wants to prove event in tx T on chain A
       T is in block H_k
       Merkle proof: T is in block H_k's merkle root
       (intermediate hashes)
   posts: (T, H_k, Merkle path) ---------------->  chain B verifies
                                                      header H_k exists in light client
                                                      Merkle path is valid for H_k's root
                                                      -> release funds on chain B
```

The two reference implementations are:

- **IBC (Inter-Blockchain Communication)**: the Cosmos SDK's cross-chain protocol. Uses a *light client* of each chain on the other, and a *relayer* (permissionless) to ferry packets. The trust assumption reduces to "the destination chain correctly finalised the source chain's light client" — i.e., to the source chain's consensus itself. IBC is used by 90+ Cosmos SDK chains and is the dominant trustless bridge for the Cosmos ecosystem.
- **Bitcoin-Ethereum bridges (e.g., tBTC v2)**: a light client of Bitcoin in an Ethereum contract that verifies Bitcoin's PoW headers. The contract implements the Bitcoin consensus rules (work, difficulty adjustment, chain selection). Anyone can submit headers; the contract tracks the longest-work chain.

The trustless bridge eliminates the multisig trust assumption but introduces two new constraints:

1. **Contract complexity**: the light client contract must implement the source chain's full header validation rules. A single bug here can let an attacker submit a *fake* header (this is exactly what the Wormhole hack did, but for Solana rather than Bitcoin — the wormhole verifier was tricked into accepting a forged signature).
2. **Finality latency**: light clients only accept headers that are *final* on the source chain. For PoW chains, this means waiting ~6 confirmations (Bitcoin) or more if reorg risk is high. For BFT chains with instant finality (Cosmos), this is one block.

## The Liquidity Pool Model (Lock-Mint-Burn-Release)

The most common *practical* bridge design today is the liquidity pool bridge. The user locks assets on the source chain, the destination chain releases equivalent assets from a pre-funded pool. The pool is replenished by arbitrageurs and fees; the bridge operators never need to sign per-transaction.

```
           Liquidity Pool Bridge (Across / Stargate / Hop)

   User (chain A)              Bridge contracts             Liquidity Providers (LPs)
   ----------                  -----------------            ------------------------
                              Chain A: escrow             LP_1 deposits 100 USDC
                                  + pool track             into chain B pool
                                  + watcher oracle         LP_2 deposits 100 USDC
                                                           into chain A pool

   1. User locks 100 USDC      Chain A escrow
      on chain A              + verifies finality (using a watcher
                                  network or oracle like UMA/Optimistic
                                  oracle)
                              2. User receives 99.5 USDC on chain B
                                 from LP-funded pool (0.5% fee
                                 covers LP risk + relayer cost)
                              3. Pool imbalance: chain A pool has +100,
                                 chain B pool has -100
                              4. Slow rebalance: a relayer moves the
                                 chain A USDC back to chain B
                                 (via the canonical bridge,
                                 or via another path), restoring balance.

   Trust assumption: (a) the watcher network does not falsely attest
   to a deposit, (b) the LPs do not pull all liquidity simultaneously
   (race condition with user deposits).
```

The two important sub-designs are:

- **Lock-Mint**: user locks asset on source, gets wrapped mint on destination. The wrapped asset's supply is constrained by the locked reserves. Canonical example: USDC bridges to L2s.
- **Burn-Mint**: user burns asset on source, gets asset minted on destination. Used when the same token natively exists on both chains (e.g., USDC native on Ethereum and on Avalanche). The Circle-issued "USDC native" replaces old bridged-USD patterns because the burn-mint flow avoids bridge-risk on the asset itself.

The **Across Protocol** (developed by UMA/Risk Labs) uses an optimistic oracle: relayers post the deposit and a 2-hour optimistically-verified window opens. If no one disputes the deposit within the window, the LP-side pool releases funds. Disputes go to the UMA optimistic oracle (token-holder vote on what happened).

The **Stargate** bridge (LayerZero's flagship liquidity layer) uses a different mechanism — a *delta-based fee* that dynamically prices bridge usage based on pool imbalance. If you bridge against a heavily-imbalanced pool, your fee is higher, which creates arbitrage incentive for LPs to rebalance.

## The Wrapped Token Model

Wrapped tokens are a special case of the lock-mint model where the wrapped asset becomes the *de-facto* native representation of the source asset on the destination chain.

```
                Wrapped Token Model (e.g., WBTC, cbBTC)

   BTC holder          BTC custodian              Ethereum                WBTC holder
   ---------           -------------              --------                -----------
   1. Locks N BTC      multisig wallet            mint N WBTC to user    uses WBTC
      in custody       (BitGo for WBTC,           (ERC-20 token)         in DeFi
      multisig         Coinbase for cbBTC,
                        Kraken for cbBTC)
   2. BTC is held      while WBTC supply > 0
      in custody
   3. To redeem:      user burns N WBTC on      Ethereum, custodian
                        releases N BTC on
                        Bitcoin to user

   Centralisation: WBTC is 100% backed by BTC held by BitGo (with
   a 1-of-1 + cold storage + custodian key rotation model).
   cbBTC is held by Coinbase, with on-chain-of-coinbase accounting.
```

Wrapped tokens are essentially custodial products with an ERC-20 wrapper. Their security reduces to the security of the underlying custodian's key management. WBTC's market cap (~$10B at peak) makes it the single largest custodial bridge in crypto by TVL; the **cbBTC** (Coinbase's BTC-on-Base) launched in 2024 has quickly captured share on L2s because it's regulatory-friendly.

> **Interview Angle**: "Why do bridges have so many hacks relative to L1s and L2s?" Three structural reasons. (1) Bridges are the **narrowest neck** in crypto: a single bug in the verifier contract compromises every asset that has ever been bridged, regardless of the security of the source or destination chain. (2) Bridges have **asymmetric risk**: the code path for legitimate messages is exercised thousands of times per day, but the code path for malicious messages is exercised only by attackers — there's no normalisation. (3) Bridges accumulate **treasury**: bridges naturally become the largest single holders of asset X on chain Y (because of lock-mint), making them a target comparable to an exchange but with weaker operational security.

## Security Trade-offs: Three Hacks in Detail

### The Ronin Bridge Hack — March 23, 2022 ($624M)

**Architecture**: trusted (multisig) bridge with 9 validators, 5-of-9 threshold.

**Root cause**: The attacker obtained 5 of 9 validator private keys. The most likely vector (per the Sky Mavis post-mortem) was social engineering: the Ronin team had been using a custom RPC node for transaction approval, and the attacker had been preparing since November 2021 by convincing a Ronin engineer to run a fake job-interview PDF that contained malware. The malware compromised the engineer's machine, which had access to the validator keys.

**The exploit**: once the attacker had 5 keys, they signed a single transaction withdrawing 173,600 ETH and 25.5M USDC from the Ronin bridge contract. The bridge's withdrawal process had been auto-approving transactions with 5-of-9 signatures since a gas-optimisation change in November 2021. The team discovered the hack **six days later**, when a user reported being unable to withdraw 5,000 ETH.

**Lessons**: (a) a multisig is only as secure as the *weakest* signer's operational security; (b) gas-optimisations that lower the threshold are dangerous; (c) a 5-of-9 with social engineering ≈ a 1-of-1 with social engineering.

### The Wormhole Hack — February 2, 2022 ($326M)

**Architecture**: trusted (multisig) bridge between Solana and Ethereum, with a Solana program that verified Ethereum signatures from a 19-validator "Guardian" set.

**Root cause**: a signature verification bug in the Solana program. The Wormhole program expected that signatures from the Guardian set were produced via the Solana `secp256k1` instruction (Sysvar `instructions`), which is a system-level signature verifier. The program failed to check that the signature was actually present in the `instructions` sysvar — it just checked that *some* signature had been verified in the current transaction. An attacker could forge a message claiming to be from the Guardian set, include a *different* valid signature (for any message), and the Wormhole program would accept it.

**The exploit**: the attacker called the Wormhole program on Solana with a fake "Guardian signature" claiming that 120,000 ETH had been locked on the Ethereum side. The program minted 120,000 Wormhole-wETH on Solana. The attacker then sold it for native assets on Solana.

**Lessons**: (a) signature verification is the single most security-critical path in a bridge contract — bugs here are catastrophic; (b) using language-level verifiers (Solana's `secp256k1` sysvar) is convenient but introduces an attack surface (the bridge must check the sysvar correctly, not just call the verifier); (c) the bug was *known* in the Wormhole codebase since at least January 2022, but the patch had not been deployed to mainnet at the time of the hack.

### The Nomad Bridge Hack — August 1, 2022 ($190M)

**Architecture**: a *trustless* bridge with an on-chain light client that tracked Merkle roots of messages from the source chains. Anyone could update the root by providing a Merkle path proof.

**Root cause**: a recent code change to the `replica` contract initialised the trusted Merkle root to `0x00...00` (32 zero bytes) during a routine upgrade. The contract's update function had a check `require(acceptableRoot(root))` where `acceptableRoot` returned true for the zero-hash during the initialisation window. The contract also failed to check that the *path elements* in the Merkle proof were non-zero — and since the trusted root was zero, every message hashed with zero siblings was a "valid proof" against the zero root.

**The exploit**: this is the most spectacular bridge hack because the bug turned *every* user into a potential attacker. Once one person found the exploit, the transaction calldata became a template that anyone could copy with their own recipient address. Hundreds of unrelated wallets participated — the hack was the most "decentralised" hack in crypto history. The total loss was ~$190M, but more than 900 addresses received funds.

**Lessons**: (a) initialise values matter — a "default zero" Merkle root is a catastrophic default; (b) upgrades are the most dangerous moment in a bridge's life — the Nomad hack happened immediately after a routine update; (c) a "trustless" bridge is not necessarily safer than a "trusted" bridge — the security assumption shifts from "the multisig is honest" to "the verifier contract is correct," and the latter is a moving target as upgrades happen.

## The Generalised Bridge Framework (LayerZero V2)

LayerZero V2 (2024) introduced a framework that explicitly separates the three components a bridge needs:

```
                       LayerZero V2 architecture

   Source chain A                    Destination chain B
   ----------------                  -----------------------
   OApp (origin application)         OApp (destination application)
       |                                 ^
       v                                 |
   Endpoint (LayerZero)              Endpoint (LayerZero)
       |                                 ^
       |                                 |
       |   message + proof of message     |
       |   (signed by DVNs)               |
       +---------------------------------->+

   DVN = Decentralised Verifier Network
       (e.g., 1-of-N oracle like Chainlink, LayerZero Labs, Google Cloud)
       configurable per-application

   Executor (optional): forwards message to destination OApp
       once DVNs have verified

   Security model: the OApp picks its DVN set. A high-value
   app can require 3-of-5 DVNs (e.g., Chainlink + LayerZero
   Labs + LayerZero DVN + CCIP + a custom DVN). A low-value
   app can require 1-of-1.

   Failure mode: if DVNs disagree, the Endpoint refuses to
   deliver the message, and the OApp defines the fallback
   (replay elsewhere, manual recovery, etc.).
```

The key insight is that *different applications need different bridge-security assumptions*. A $100 NFT cross-chain mint can tolerate 1-of-1 DVNs; a $1B treasury transfer should require 3-of-5 with specific named DVNs. LayerZero V2's contribution is making this *configurable per-application*, rather than forcing every user of a bridge into the same trust assumption.

## Comparison and Recommendations

```
                       Trusted         Trustless       Liquidity Pool   Wrapped Token
                       ----------     -----------     --------------   -------------
   Trust assumption     m-of-n          L1 consensus    oracle + LPs    custodian
                       custodians      of source       honesty         key management
   Latency              minutes         ~10 min         minutes          minutes
                       (multisig)      (light client
                                        finality)
   Per-asset backing    full            full            proportional    full
   Recovery             social recovery hard fork the   hard fork both  social recovery
                       (if possible)   destination     chains           (custodian
   Censorship           possible        not possible    possible         possible
                       by majority                      by oracle
   Audit complexity     low             very high       medium           low
                       (count sigs)    (full L1 rules) (oracle + LP)    (count sigs)
   Failure case study  Ronin, Wormhole Nomad           (no major hacks cbBTC / WBTC
                                       (Aug 2022)       to date)         (no major
                                                                          hacks to date)
```

Practical guidance from the LI.FI and Chainalysis reports:

- For **small transfers** (sub-$10k), liquidity-pool bridges (Across, Stargate) are dominant — fast, cheap, and well-capitalised.
- For **treasury transfers** (sub-$10M), use a trustless bridge if available (IBC between Cosmos chains, or a verified light-client path), otherwise use the *canonical* bridge of the destination chain (e.g., the OP Stack canonical bridge for Base → Ethereum).
- For **wrapped-token holdings**, treat the wrapped asset as a *custodial claim*, not as the underlying asset. A DeFi position collateralised by WBTC has an additional counterparty (BitGo) versus one collateralised by native ETH.
- For **cross-chain L2 → L1 withdrawals**, prefer the canonical rollup bridge (7-day challenge window on OP Stack / Arbitrum) over any third-party bridge — the third-party bridge introduces additional trust assumptions for the *same* withdrawal delay.

## Interview Questions

### Q1: Why are bridges the most-hacked infrastructure in crypto?

Three structural reasons. (1) Bridges are the *narrowest neck* — a single bug compromises every bridged asset regardless of source/destination chain security. (2) Bridges have asymmetric code paths — the malicious-message path is exercised only by attackers, never by legitimate traffic. (3) Bridges accumulate treasuries — they become the largest single holders of asset X on chain Y, making them a target comparable to an exchange but with weaker operational security (no cold storage, no withdrawal limits, often multisigs held by externally-controlled keys).

### Q2: How does a liquidity pool bridge handle the case where the pool is empty?

Two mechanisms. (1) **Slippage**: the user's quote is computed against the available pool balance; if the pool has only $50 of an asset the user wants $100 of, the bridge refuses (or the user accepts 50% fill). (2) **Rebalancing**: relayers continuously move funds from over-filled pools to under-filled pools using the canonical bridge (slow path) or alternate routes (faster). Some bridges (Across) include a "slow relayer" mechanic where users can opt to wait for a slow path that's cheaper than the immediate-fill path.

### Q3: Compare the Ronin and Nomad hacks at the protocol level.

Ronin was a *trust failure* — the multisig model held because the contract worked as specified; the keys were stolen. The fix is operational (better key custody, more signers, hardware signing). Nomad was a *correctness failure* — the contract itself was buggy after a routine upgrade, and the multisig (had there been one) would have signed exactly the same fraudulent messages because the contract verified them. The fix is engineering (formal verification of upgrade paths, two-phase commit on initialised values, simulation of every code change before deployment). The two failure modes are orthogonal: a bridge can be operationally secure but code-insecure (Nomad), or code-secure but operationally insecure (Ronin). Robust bridges must defend against both.

## References

- LI.FI Docs — "Bridge architecture overview": https://docs.li.fi/smart-contract-api/bridge-protocols
- LayerZero V2 Documentation: https://docs.layerzero.network/v2
- Wormhole Documentation: https://docs.wormhole.com/
- Chainalysis — "Crypto Crime: Bridges and the $2B Stolen in 2022": https://www.chainalysis.com/blog/212-crypto-crime-report-2022-bridge-hacks/
- Nomad Bridge Post-Mortem (August 2022): https://nomadxyz.notion.site/nomadxyz/Nomad-Bridge-Incident-Resource-Center-93b3fe1bb1c14b1a9d1c2b61e9524d03
- Wormhole Post-Mortem (February 2022): https://wormhole.com/wormhole-incident-report.pdf
- Ronin Network Post-Mortem (March 2022): https://roninblockchain.substack.com/p/community-alert-ronin-validators
- IBC Specification (Cosmos): https://github.com/cosmos/ibc

## Related Topics

- [Ethereum Internals](./ethereum-internals.md) — L1 contracts that bridges call into
- [Optimistic Rollups](./optimistic-rollups.md) — canonical L2 bridges (the OP Stack OptimismPortal)
- [ZK Rollups](./zk-rollups.md) — ZK-based light clients as bridge verifiers
- [Blockchain Security](./blockchain-security.md) — broader smart-contract attack surface
