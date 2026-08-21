# Chainlink Oracle Network

## Overview

Smart contracts cannot, by themselves, read off-chain state. The EVM is a deterministic state machine: any node that replays a block must arrive at the same result, which precludes fetching from `https://api.coingecko.com/...` at execution time. The contract would get a different answer each time it was re-executed by a different node, and consensus breaks down.

An oracle bridges this gap. A naive oracle — a single trusted server that posts prices on-chain — merely relocates the trust: it is now a centralized chokepoint that can be hacked, bribed, or compelled by a regulator. Chainlink's design philosophy is that the oracle itself should be a *decentralized network* with its own consensus, cryptographic provenance, and slashing economics. The contract should not trust any single node; it should trust the median of dozens of nodes and the cryptographic proof that threshold signatures were collected.

This page covers the five core Chainlink primitives: the Off-Chain Reporting protocol (OCR2) that produces a single aggregated value on-chain per round; the median aggregation model; the price-feed consumer interface; Verifiable Random Functions (VRF) for on-chain randomness; the Cross-Chain Interoperability Protocol (CCIP); and the Automation (formerly Keeper) network.

## Off-Chain Reporting (OCR2)

### Why OCR exists

Pre-OCR oracle designs had each node submit its own observation on-chain. For a DON of N=31 nodes, that was 31 transactions per round, each paying base gas — a 31x gas cost compared to a single price update. Worse, an attacker watching the mempool could see the median outcome before it was finalized and front-run it.

OCR (2020) and OCR2 (2022) collapse N submissions into one. The aggregation happens off-chain in a P2P protocol; only the *final report* — together with a threshold signature over it — is broadcast on-chain.

### The OCR protocol

A DON consists of N = 3f + 1 oracle nodes, tolerating up to f Byzantine (malicious) nodes. Each round:

```
1. Each node observes the target value (e.g., ETH/USD from exchanges).
2. Each node signs its observation:  sig_i = Sign(sk_i, H(epoch, round, obs_i))
3. Nodes gossip observations via libp2p.
4. Once a node has at least 2f+1 observations, it computes the
   median and assembles a report:
     report = (obs_1, obs_2, ..., obs_n | median | config | ...)
5. A "leader" node is elected round-robin; the leader collects
   signatures from 2f+1 distinct nodes (a quorum) on the report.
6. The designated "transmitter" sends a single transaction to the
   on-chain contract containing:
     (report, signatures[2f+1])
7. The on-chain contract:
     - verifies 2f+1 distinct signatures against the configured oracle set
     - checks each signer's observation is in the report
     - extracts the median as the new "answer"
     - emits NewRound(roundId, answer, ...)
```

The on-chain verification is the crucial part. Here is the core of the contract (simplified from `OffchainAggregator.sol`):

```solidity
function transmit(
    bytes memory report,
    bytes32[] rs, bytes32[] ss, uint8[] vs
) external {
    // Decode the report: observations + observers bitmap + median + juels
    (bytes32 observers, int192[] observations, bytes32 rawReportContext) =
        abi.decode(report, (bytes32, int192[], bytes32));

    require(observations.length == config_.n, "wrong number of observations");

    // Verify that we have at least f+1 signatures from distinct observers
    // who are in the observers bitmap.
    require(rs.length == config_.n, "wrong number of signatures");

    // Hash the report context and observers for replay protection
    bytes32 h = keccak256(abi.encodePacked(rawReportContext, observers, observations));

    // Recover each signer and check it matches the configured oracle set
    address[] memory signers = new address[](config_.n);
    for (uint i = 0; i < config_.n; i++) {
        signers[i] = ecrecover(h, vs[i], rs[i], ss[i]);
        require(s_isSigner[signers[i]], "not authorized signer");
    }

    // Compute median of observations that came from valid signers
    int192 median = _median(observations);

    // Record the new round and update the latest answer
    s_latestRoundId = s_latestRoundId + 1;
    s_latestAnswer = median;
    emit NewRound(s_latestRoundId, median, block.timestamp);
}
```

The key invariant: any quorum of `2f+1` honest signers forces the contract to accept the median of their observations. An attacker controlling `f` or fewer nodes cannot make the contract accept a value that wasn't the median of at least `f+1` honest observations.

### OCR2 improvements over OCR1

OCR2 introduced several changes — most importantly:

- **P2P network re-architecture**: libp2p instead of a custom transport; same nodes can serve multiple feeds.
- **Multi-feed support**: one DON can produce many reports (e.g., ETH/USD, BTC/USD, LINK/USD).
- **Mercury-style streaming**: off-chain clients (and now on-chain via a streaming protocol) can pull reports.
- **Config-driven signer sets**: signer sets can be rotated without redeploying the aggregator.
- **BLS support (in some deployments)**: aggregate signature verification reduces on-chain cost further.

## Median Aggregation

The aggregation rule is **median**, not mean. Median is robust to outliers: if one of N nodes is compromised and submits `1e18` for an asset worth `1000`, the median moves by at most one rank. For N=31 (the typical Chainlink price-feed DON), an attacker controlling `f=10` nodes can shift the median by at most `ceil((N - f) / 2) - 1 = 10` ranks — i.e., they can make the median equal to the 11th-highest honest observation, but no further.

The median is computed off-chain over the `2f+1` observations in the report; the on-chain contract recomputes it from the same observations (which were signed). This is a **commit-reveal-with-proofs** pattern: each node commits to its observation via signature; the contract verifies the median over the committed observations.

Why median over mean?

- A single compromised node submitting `1e18` would shift a *mean* of 31 honest values around `1000` to roughly `(1000 * 30 + 1e18) / 31 ≈ 3.2e16`. The mean is unusable.
- The *median* of those same 31 values is unchanged (rank-16 of the sorted list still sits near 1000).
- For multi-source aggregation across exchanges (Binance, Coinbase, Kraken, etc.), median is the standard choice because exchange outages produce "phantom" prices that median discards.

Variants: volume-weighted median (each observation weighted by reported volume), trimmed mean (drop top k and bottom k, then mean), and **mean of medians** (median per exchange, then mean across exchanges). Chainlink's feeds use a configurable per-feed aggregation in the off-chain `reporting plugin`, not a fixed rule.

## Price Feeds Consumer Interface

The on-chain consumer interface is `AggregatorV3Interface`:

```solidity
interface AggregatorV3Interface {
    function decimals() external view returns (uint8);
    function description() external view returns (string memory);
    function version() external view returns (uint256);
    function latestRoundData()
        external view returns (
            uint80 roundId,
            int256 answer,       // price * 1e8 for USD pairs, 1e18 for ETH pairs
            uint256 startedAt,
            uint256 updatedAt,
            uint80 answeredInRound
        );
    function getRoundData(uint80 _roundId)
        external view returns (
            uint80 roundId,
            int256 answer,
            uint256 startedAt,
            uint256 updatedAt,
            uint80 answeredInRound
        );
}
```

A typical consumer — say, an Aave reserve contract — wraps this with staleness and deviation checks:

```solidity
function getAssetPrice(address asset) public view returns (uint256) {
    AggregatorData storage ad = _aggregators[asset];
    (, int256 rawPrice, , uint256 updatedAt, ) =
        IChainlinkAggregator(ad.source).latestRoundData();

    // 1. Sanity: price must be positive.
    require(rawPrice > 0, "CL: negative price");

    // 2. Staleness: must have updated within the heartbeat.
    require(block.timestamp - updatedAt <= ad.heartbeat, "CL: stale");

    // 3. Deviation: shouldn't move more than X% in one round.
    // (Implemented by comparing with the previous round.)

    return uint256(rawPrice) * (10 ** (ad.decimals - IChainlinkAggregator(ad.source).decimals()));
}
```

Feeds are configured with **heartbeats** (e.g., 3600 seconds for ETH/USD mainnet) and **deviation thresholds** (e.g., 0.5%). The DON transmits a new report whenever either threshold is crossed. A consumer that ignores staleness is exposed to using yesterday's price during a market crash — exactly the failure mode that caused several liquidation spirals.

## Verifiable Random Function (VRF)

Randomness on a deterministic chain is hard. The standard naive approach — `blockhash(block.number - 1) as the seed` — is manipulable: a miner/validator can choose to include or omit transactions to bias the resulting hash. Even after The Merge, a validator can grind by withholding an attestation.

Chainlink VRF v2 uses an **Elliptic-Curve Verifiable Random Function (ECVRF)** based on secp256k1. The output is provably generated by the holder of a specific secret key from a specific seed — neither party (user nor oracle) can bias the result.

The protocol:

```
1. Consumer calls:  requestId = COORDINATOR.requestRandomWords(
    keyHash,           // gas-limited key hash identifying the oracle node
    subscriptionId,    // pre-funded subscription
    requestConfirmations,  // confirmations to wait before generating
    callbackGasLimit,
    numWords           // up to 500 random uint256s per request
)

2. The request is logged. After `requestConfirmations` blocks, the
   VRF oracle:
   a. Computes a deterministic seed:
        finalSeed = keccak256(blockhash(block.number - requestConfirmations) . requestId)
   b. Generates (randomness, proof) = VRF_prove(sk, finalSeed)
   c. Returns the result by calling the consumer's callback:
        rawFulfillRandomWords(requestId, randomWords)

3. The coordinator verifies the proof on-chain using the oracle's
   registered public key. If the proof fails, the callback is not
   invoked.
```

The verification is the cryptographic core. The ECVRF prove/verify algorithm is:

```
Prove(sk, alpha):
    // alpha = H(seed)  (encoded as a curve point)
    // k = nonce
    g = generator of curve
    Y = sk * g                   // public key
    H = hash_to_curve(alpha)
    k = nonce(sk, alpha)
    U = k * g
    V = k * H
    c = hash(Y, H, g, U, V, alpha)
    s = k - c * sk  mod n
    return (gamma = sk * H, c, s)   // "proof"

Verify(pk, alpha, proof):
    // Recompute c from public inputs and the proof, then check:
    U = s*g + c*Y
    V = s*H + c*gamma
    c' = hash(Y, H, g, U, V, alpha)
    require(c == c', "VRF verification failed")
    // Output:
    output = hash(gamma)  // deterministic random value
```

The consumer is guaranteed: (a) the random output is the correct one for `(sk, finalSeed)`, and (b) the seed was derived from a blockhash the user could not have known at request time, combined with a per-request nonce. Neither party can bias the result.

Common pitfalls: forgetting `requestConfirmations >= 3` (reorgs can cause the seed to change), and accepting randomness from a contract that hasn't implemented `fulfillRandomWords` correctly (the callback must be `onlyCoordinator` to prevent spoofing).

## Cross-Chain Interoperability Protocol (CCIP)

CCIP is Chainlink's generic cross-chain messaging protocol. It is explicitly *not* a bridge in the Wormhole/LayerZero sense — the design centers on a separate **Risk Management Network (RMN)** that validates every cross-chain message.

```
[ SOURCE CHAIN ]                              [ DEST CHAIN ]
                                                  |
 Router                                            |
   |                                               |
 OnRamp                                          OffRamp
   |                                              ^
   |  -- message -->                            commit-then-execute
   |                                              ^
   |                                              |
   v                                              |
 Committing DON  ---  MerkleRoot  ----->  Risk Management Network (RMN)
                                              |
                                              v
                                          validates root
                                              |
                                              v
                                          OffRamp executes messages
```

Components:

- **Router**: chain-specific entry contract; users call `ccipSend(destinationChainSelector, message)`.
- **OnRamp (source)**: validates the message, locks/burns tokens via the source token pool, and emits a `MessageSent` event.
- **Committing DON**: an OCR2-style DON that listens to `MessageSent` events across all OnRamps on the source chain and periodically commits a Merkle root of pending messages onto the source chain.
- **Risk Management Network**: a *separate* DON that independently recomputes the Merkle root and votes to bless it. The RMN is the safety check — even if the committing DON is compromised, the RMN must independently attest.
- **OffRamp (dest)**: after the RMN blesses the root, executes the corresponding messages on the destination chain by calling destination token pools (mint/unlock) and receiver contracts.

Token transfers go through **TokenPools** that implement either a burn-and-mint model (for native CCIP-enabled tokens) or a lock-and-mint model (for wrapped variants). A `rates` contract enforces per-message limits (max tokens per chain pair) and dynamic fees.

CCIP's central design claim is that **two independent DONs** (committing + RMN) must both attest to a Merkle root before messages execute. This is in contrast to LayerZero (DVN + oracle, configurable by the app) and Wormhole (guardian set of 19, single signature). The trade-off: CCIP is slower (a few minutes of finality) but eliminates single-network catastrophic failures (the Wormhole February 2022 hack of $325M exploited a signature forgery; CCIP's two-DON structure would require both to be compromised simultaneously).

## Automation (formerly Keepers)

Chainlink Automation is a service for triggering smart contract functions when off-chain conditions hold. The pattern is:

```solidity
interface AutomationCompatible {
    function checkUpkeep(bytes calldata checkData)
        external view returns (bool upkeepNeeded, bytes memory performData);

    function performUpkeep(bytes calldata performData) external;
}
```

A user registers a contract as an "upkeep" with a `checkData` blob and funds a prepaid LINK balance. Automation nodes poll `checkUpkeep` off-chain (using an Ethereum RPC and `eth_call` simulation) — when the function returns `upkeepNeeded=true`, the node submits a transaction calling `performUpkeep(performData)`. Gas is paid from the upkeep's prepaid balance via a `registry` contract that mediates LINK reimbursement.

Two trigger modes:

1. **Custom logic trigger**: nodes call `checkUpkeep` every block; the contract decides when to act (e.g., "harvest when accumulated rewards > 1 ETH").
2. **Log trigger**: nodes watch for specific log events (matching a topic mask); when matched, the log is included in `performData`. Useful for limit-order execution: "if a Swap event of type X fires, call rebalance()".

The registry contract keeps a Merkle root of all upkeeps; nodes verify they're acting on a registered upkeep. A keeper that calls `performUpkeep` without a priori `checkUpkeep=true` result gets reverted and pays its own gas — keeping the system incentive-compatible.

Common failures:
- `checkUpkeep` reverting on chain reorgs (the off-chain simulation sees a block that doesn't land).
- Gas-price spikes making the reimbursement insufficient; the keeper either skips the upkeep or frontruns it.
- Misuse of `block.number` / `block.timestamp` inside `checkUpkeep` causing non-determinism — the spec recommends simulating at the latest block, so these are fine, but the contract should avoid using values that depend on the executing block.

## Failure Modes and Defense

Chainlink-specific attacks worth knowing for interviews:

- **Stale-feed exploit**: during the March 2020 crash and the November 2022 FTX collapse, several feeds briefly went stale because nodes' upstream sources (Binance, FTX) degraded. Protocols that consumed `latestRoundData` without checking `updatedAt` accepted stale prices for minutes. Hard lesson: always bound `block.timestamp - updatedAt`.
- **Liquidity attack on the source**: even an honest DON can be misled if its sources are thin. The Synthetix sUSD exploit (June 2020) wasn't a Chainlink failure — it was a manipulation of the Uniswap sUSD/ETH pool that was being read directly by the Synthetix oracle. The fix: don't read spot AMM prices; use Chainlink or TWAPs.
- **VRF collision attack**: if two consumers request randomness using the same seed (because the seed depends only on `blockhash`), they get the same number. The VRF contract includes a per-request nonce derived from the consumer's address and a counter, defeating this.
- **OCR DON takeover**: if the signer set can be rotated by a malicious admin key, the whole DON can be replaced. Chainlink's mainnet feeds use **multi-sig + timelocked** admin contracts for this reason; consumers should also register the feed's `proposedAggregator` updates and observe the multi-sig actions.

## References

- Chainlink Whitepaper 2.0 — https://chain.link/whitepaper/whitepaper-v2.pdf
- Chainlink Documentation — https://docs.chain.link/
- Off-Chain Reporting (OCR2) specification — https://docs.chain.link/chainlink-nodes/oracle-application#off-chain-reporting-ocr
- libocr source code (OCR2 protocol implementation) — https://github.com/smartcontractkit/libocr
- Chainlink VRF v2 documentation — https://docs.chain.link/vrf/v2/introduction
- Chainlink CCIP documentation — https://docs.chain.link/ccip
- Chainlink Automation documentation — https://docs.chain.link/chainlink-automation
- AggregatorV3Interface source — https://github.com/smartcontractkit/chainlink/blob/master/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol
