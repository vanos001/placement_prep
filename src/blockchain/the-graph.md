# The Graph Protocol

## Overview

A blockchain's data layer is intentionally hostile to queries. The Ethereum state trie is a key-value store addressed by 32-byte slots; historical block data is a flat list of `(block_hash, transactions[], logs[])`. "Give me all ERC-20 transfers to address X in the last 30 days" requires scanning ~215,000 blocks and parsing every `Transfer` event log. Every client that needs this for a wallet UI, a DeFi dashboard, or an analytics page re-implements the same scan.

The Graph's answer is *decentralized indexing*: developers define a **subgraph** — a manifest that declares which contract events to listen to and how to transform them into typed entities in a Postgres-backed store. Indexers run the Graph Node software, ingest blocks, run AssemblyScript handlers against the events, and serve the resulting store via a GraphQL API. Consumers pay query fees in GRT. The economic layer distributes those fees to indexers and the curators who signaled on the subgraph's importance.

This page covers the subgraph format (manifest + GraphQL schema + mapping handlers), the indexer/curator/delegator role split, GRT token economics, the query market, and a comparison with traditional indexing (Elasticsearch, hosted RPC services).

## The Subgraph

A subgraph is a directory containing three files: `subgraph.yaml` (manifest), `schema.graphql` (types), and `mapping.ts` (AssemblyScript handlers). It is compiled with `graph-cli` into a `.wasm` blob plus a manifest blob and deployed to a Graph Node.

### The Manifest (`subgraph.yaml`)

```yaml
specVersion: 1.0.0
schema:
  file: ./schema.graphql
dataSources:
  - kind: ethereum
    name: UniswapV3Pool
    network: mainnet
    source:
      address: "0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8"
      abi: Pool
      startBlock: 12500000
    mapping:
      kind: wasm/assemblyscript
      apiVersion: 1.0.0
      language: wasm/assemblyscript
      entities:
        - Swap
        - Pool
        - Token
      abis:
        - name: Pool
          file: ./abis/Pool.json
        - name: ERC20
          file: ./abis/ERC20.json
      eventHandlers:
        - event: Swap(index_prefix sender,index_prefix recipient,int256 amount0,int256 amount1,uint160 sqrtPriceX96,uint128 liquidity,int24 tick)
          handler: handleSwap
        - event: Mint(address sender,address owner,int24 tickLower,int24 tickUpper,uint128 amount,uint256 amount0,uint256 amount1)
          handler: handleMint
      callHandlers:
        - function: swap(address,bool,int256,uint160,bytes)
          handler: handleSwapCall
      blockHandlers:
        - handler: handleBlock
templates:
  - name: Pair
    kind: ethereum
    network: mainnet
    source:
      abi: Pair
    mapping:
      kind: wasm/assemblyscript
      apiVersion: 1.0.3
      language: wasm/assemblyscript
      file: ./mapping.ts
      entities: [Pair]
      abis:
        - name: Pair
          file: ./abis/Pair.json
      eventHandlers:
        - event: PairCreated(index_prefix token0,index_prefix token1,address pair,uint256)
          handler: handlePairCreated
```

Three concepts are worth unpacking:

1. **Static data sources**: address-bounded sources with an ABI. Handlers only fire when the matching event is emitted *by that specific address*. This filters the global event stream to only relevant logs.
2. **Templates (dynamic data sources)**: factory contracts create new instances at runtime; the subgraph can't enumerate them upfront. A template lets the handler call `Pair.create(addr)` at indexing time, registering a new dynamic data source. The Graph Node then attaches the same handlers to the new address from its deployment block onward.
3. **Call handlers** and **block handlers**: optional sources that fire on function-call traces or every block. Call handlers are more expensive (need full trace data) and should be used only when no event captures the relevant state change.

### The GraphQL Schema

```graphql
type Swap @entity(immutable: true) {
  id: Bytes!
  pool: Pool!
  sender: Bytes!
  recipient: Bytes!
  amount0: BigInt!
  amount1: BigInt!
  sqrtPriceX96: BigInt!
  tick: Int!
  timestamp: BigInt!
  transaction: Transaction!
}

type Pool @entity {
  id: Bytes!
  token0: Token!
  token1: Token!
  feeTier: Int!
  liquidity: BigInt!
  sqrtPrice: BigInt!
  tick: Int!
  swaps: [Swap!]! @derivedFrom(field: "pool")
}

type Token @entity {
  id: Bytes!
  symbol: String!
  name: String!
  decimals: Int!
}

type Transaction @entity(immutable: true) {
  id: Bytes!
  timestamp: BigInt!
  blockNumber: BigInt!
  swaps: [Swap!]! @derivedFrom(field: "transaction")
}
```

Annotations:

- `@entity(immutable: true)` — write-once record, never updated. The Graph Node stores these in a separate append-only table, optimizing writes for high-volume event streams.
- `@derivedFrom(field: ...)` — virtual field; no on-disk storage, derived by a reverse-lookup join.
- Types: `Bytes`, `BigInt`, `Int`, `BigDecimal`, `String`, `Boolean` — the schema deliberately avoids floating-point to keep indexing deterministic across machines.

### The Mapping Handlers

The mapping language is AssemblyScript, a strict subset of TypeScript that compiles to WASM. Each handler receives a strongly-typed event object:

```typescript
import { Swap, Mint } from "../generated/Pool/Pool";
import { Swap as SwapEntity, Pool as PoolEntity } from "../generated/schema";
import { BigDecimal } from "@graphprotocol/graph-ts";

export function handleSwap(event: Swap): void {
  // 1. Load or create the Pool entity
  let pool = PoolEntity.load(event.address);
  if (pool == null) {
    pool = new PoolEntity(event.address);
    pool.liquidity = event.params.liquidity;
    pool.sqrtPrice = event.params.sqrtPriceX96;
    pool.tick = event.params.tick;
  }

  // 2. Update mutable state from the new swap
  pool.sqrtPrice = event.params.sqrtPriceX96;
  pool.tick = event.params.tick;
  pool.liquidity = event.params.liquidity;
  pool.save();

  // 3. Create an immutable Swap record
  let swap = new SwapEntity(event.transaction.hash.concatI32(event.logIndex));
  swap.pool = pool.id;
  swap.sender = event.params.sender;
  swap.recipient = event.params.recipient;
  swap.amount0 = event.params.amount0;
  swap.amount1 = event.params.amount1;
  swap.sqrtPriceX96 = event.params.sqrtPriceX96;
  swap.tick = event.params.tick;
  swap.timestamp = event.block.timestamp;
  swap.transaction = event.transaction.hash;
  swap.save();
}
```

The handler's invariants:

- It runs deterministically — same block on any indexer must produce the same database state.
- WASM is sandboxed; it cannot make HTTP calls or read the filesystem.
- Time/memory are bounded by the Graph Node host (the handler must complete within a per-block gas-like limit; otherwise it's flagged as failed).

### Substreams: the streaming successor

In 2023, The Graph introduced **Substreams**, a streaming-first alternative to the event-handler model. A Substream is a Rust module that consumes a stream of block data, runs in parallel across block ranges, and writes to a sink (Postgres, GraphQL, file). The model is map-reduce style:

```rust
#[substreams::handlers::map]
fn map_swaps(block: Block) -> Result<Swaps, substreams::errors::Error> {
    let mut swaps = Swaps::default();
    for trx in block.transactions() {
        for log in trx.logs() {
            if log.address == UNISWAP_V3_FACTORY {
                if let Some(decoded) = decode_swap(log) {
                    swaps.items.push(decoded);
                }
            }
        }
    }
    Ok(swaps)
}

#[substreams::handlers::store]
fn store_volume(swaps: Swaps, store: StoreAddBigInt) {
    for swap in swaps.items {
        store.add(swap.block_number, &swap.amount_usd);
    }
}
```

Substreams address the long-tail problem: re-indexing an entire chain from block 0 to 18M with sequential per-event handlers can take days. Substreams run handlers in parallel across block ranges (1000-block chunks), enabling ~50x faster cold-sync times. The output is fed to the same Postgres/GraphQL sink, so consumer-facing queries are unchanged.

## Roles: Indexer, Curator, Delegator

### Indexer

An indexer runs a Graph Node (Rust), stakes a minimum amount of GRT (currently 100,000 GRT), and registers on the Arbitrum L2 contracts. The indexer allocates its **stake** across subgraphs it chooses to index. Allocating signals both capability ("I'm indexing this") and economic commitment ("I have skin in the game if I serve wrong answers"). Allocations are time-bounded; an indexer must close an allocation to claim rewards.

```solidity
function allocate(
    bytes32 _subgraphDeploymentID,
    uint256 _amount,
    uint256 _metadata,
    bytes32 _prevAllocationID
) external returns (bytes32) {
    require(_amount > 0, "amount must be > 0");
    Indexer storage indexer = indexers[msg.sender];
    require(indexer.stakedAmount >= _amount + indexer.allocationCurrent, "stake too low");

    // Create allocation, mark as active, emit event for syncing.
    Allocation storage a = allocations[allocationID];
    a.indexer = msg.sender;
    a.subgraphDeploymentID = _subgraphDeploymentID;
    a.tokens = _amount;
    a.createdAt = block.timestamp;
    a.allocationType = AllocationType.Active;

    emit AllocationCreated(msg.sender, allocationID, _subgraphDeploymentID, _amount);
    return allocationID;
}
```

Indexers earn three revenue streams:

1. **Query fees**: from consumers paying per query (or per-byte of response).
2. **Indexing rewards**: protocol-inflation emissions distributed pro-rata to allocated stake.
3. **Delegation rewards**: a share of delegator stake's earnings.

Slashing applies if an indexer serves provably-wrong data (proven by a **dispute** mechanism; see Query Market below).

### Curator

A curator signals on a subgraph by staking GRT into the bonding curve for that subgraph's curation signal. The bonding curve is a Bancor-style `P(signal) = reserveRatio * supply` curve — buying signal mints signal tokens, selling burns them. The signal weight of a subgraph determines the share of indexing rewards allocated to its indexers (a soft reputation signal).

The economic game: a curator profits if the subgraph's query fees grow (so indexing rewards to the subgraph grow) after their signal. Bonding-curve slippage ensures that earlier curators get a cheaper price per signal unit, rewarding early identification of valuable subgraphs.

The risk: curation GRT is locked in a bonding curve with slippage on exit. A curator that signals on a subgraph which never attracts query traffic cannot recover their stake without accepting a slippage loss.

### Delegator

A delegator delegates GRT to a specific indexer (not to a subgraph). The delegation earns a share of that indexer's rewards; the indexer takes a `indexerRewardCut` (typically 10–50%) and the rest is split pro-rata to delegators based on their delegated amount, after a `queryFeeCut` on query fees.

The Delegator's risk: if the indexer is slashed, the delegated stake is also slashed. Delegators must choose indexers based on operational reliability (uptime, sync status, response latency).

```
Indexer rewards split (illustrative):
  Indexing rewards (inflation):
    - indexer share = delegationPool * indexerRewardCut%
    - delegator share = (delegationPool * (100 - indexerRewardCut)%) proportional to delegated amount

  Query fees:
    - indexer's earned portion
    - delegator's portion = earned * (100 - queryFeeCut)% proportional to delegation
    - rest burned (token-deflationary)
```

## GRT Token Economics

GRT is an ERC-20 token on Ethereum with a bridge to Arbitrum (where the protocol contracts live). Key parameters:

- **Total supply**: 10 billion GRT at genesis (2020). Issuance schedule: ~3% annual via indexing rewards.
- **Initial distribution**: 34% to community (including Edge Dapp, grants, ecosystem); 23% to team and early backers (4-yr vest); 17% to early backers; 11% to Edge (foundation); 8% grant program; remaining to validators/supply.
- **Burning**: query fees paid on the network are partially burned; specifically, the protocol burns the indexer's share of query fees if they choose the "burn" path instead of withdrawing.

Token velocity is governed by the protocol's reward/penalty rates:

- **Indexing reward rate** (~3% APY on allocated stake, paid in newly minted GRT).
- **Delegation fee**: delegation into an indexer costs a fixed `delegationTax` (0.5% of delegated amount, burned).
- **Unbonding period**: 28 days for curators; 28 days for delegators — locks prevent flash-bank-runs and force commitment.
- **Slashable**: disputes proved against an indexer cause proportional slashing (10% of stake + allocation in current spec, configurable).

The token's purpose is **economic security of the indexing layer**. Without it, any peer could serve wrong data and there would be no cost; with it, wrong data costs stake. This is the same pattern as Chainlink's staked DONs and Chainlink's CCIP Risk Management Network.

## The Query Market

A consumer query flow (on the decentralized network):

```
Consumer
   |
   | 1. POST GraphQL query + payment (signed) to Gateway URL
   v
Gateway (router)
   |
   | 2. Resolve which indexers are allocated to this subgraph
   |    Pick the lowest-cost indexer by attested availability.
   v
Indexer (Graph Node)
   |
   | 3. Run GraphQL query against local Postgres store.
   |    Return response + signed receipt.
   v
Gateway
   |
   | 4. Verify receipt signature, relay response to consumer.
   | 5. Submit payment attestation on-chain (Arbitrum) to settle.
   v
Cost & Settlement contracts
   |
   | 6. Indexer gets paid in GRT; portion burned per queryFeeCut.
```

The **dispute** mechanism (the trust-minimization layer):

```
Consumer notices an indexer's response differs from canonical state.
Consumer submits a dispute with:
  - the query
  - the indexer's signed receipt (response hash)
  - a canonical answer (re-derived from the chain)
If the dispute contract finds the indexer wrong:  slash + reward to consumer.
If the dispute is invalid:  consumer loses their dispute bond.
```

Disputes are typically resolved by Fishermen — independent actors watching for inconsistent responses. The economic question for them: expected reward must exceed the gas cost of submitting a dispute + the opportunity cost of the dispute bond. In practice, disputes are rare (the protocol has had a handful of substantive disputes per year) because indexing is deterministic — a properly-synced indexer cannot produce a wrong answer; the only failure modes are bugs in the WASM runtime or Postgres state divergence.

## Comparison to Traditional Indexing

| Dimension | Elasticsearch / OpenSearch | Alchemy / Infura (hosted RPC + indexing) | The Graph (decentralized) |
|-----------|---------------------------|------------------------------------------|---------------------------|
| **Source** | Any (push from your services) | EVM RPC + custom indexer | EVM logs + ABI |
| **Schema** | Dynamic mappings (JSON) | Custom per-dapp | GraphQL schema + WASM mappings |
| **Query language** | Lucene, ES\|QL, Kibana | REST/JSON-RPC | GraphQL |
| **Writes** | Synchronous; client pushes | Via your off-chain indexer | Async from chain events |
| **Pricing** | Per-node compute + storage | Per-call metered | Per-query fee in GRT |
| **Replication** | Self-managed primary/replica | AWS-multi-AZ | Decentralized parallel indexers |
| **Failure mode** | Index is wrong → your ops team fixes it | Provider outage → no SLA fallback | Indexer sync lag → switch to another indexer |
| **Trust model** | Trust the cluster | Trust the provider | Trust the indexer + (optionally) verify via dispute |
| **Cold sync** | Re-build from upstream; hours-days | n/a (provider pre-indexes) | Hours-days on mainnet (Substreams reduces ~50x) |
| **Liquidity / migration** | Vendor lock-in on Lucene mappings | Migration to own indexer is feasible | Subgraphs are portable; manifest is open |

The structural comparison: Elasticsearch is a *general-purpose* indexed-search engine that you operate against any data source. The Graph is a *domain-specific* indexer for EVM chains, with a declarative manifest that defines what to index and how to transform it. Alchemy and Infura offer hosted RPC and ad-hoc indexing APIs, but those are centralized — you trust the provider.

The Graph's distinctive claim is *decentralized, verifiable* indexing. In principle, a consumer can query multiple indexers and reconcile; in practice, the GraphQL gateway does this transparently. The trade-off: query latency on the decentralized network (~200–500 ms for typical GraphQL queries) is higher than a single Elasticsearch shard (~10–50 ms) because of the routing, signing, and payment layers.

For enterprise-scale analytics (millions of queries per day, complex aggregations, dashboards), the practical pattern is hybrid: use The Graph for the canonical, auditable on-chain view (e.g., "all transfers of token X in real time"), then ETL that into Snowflake / BigQuery / Elasticsearch for ad-hoc analytics. The Graph becomes the source of truth that downstream BI trusts.

## Failure Modes and Pitfalls

- **Handler non-determinism**: AssemblyScript can read floating-point opcodes that vary across WASM runtimes. The Graph Node deliberately pins the runtime version; subgraphs that depend on timing or random behavior can fail to sync consistently across indexers.
- **Reorg handling**: on a chain reorg, the Graph Node must roll back the affected handlers' effects and re-run them with the canonical chain. Handlers that perform `store.load()` + side-effect (e.g., a counter that increments on each event) require careful idempotency; non-idempotent handlers can corrupt the store on reorgs.
- **State bloat**: a high-volume subgraph (Uniswap V3 mainnet) produces hundreds of millions of entities; the Postgres store can reach TB-scale. Indexers must provision storage accordingly.
- **Stale allocations**: an indexer can allocate to a subgraph and earn rewards without syncing — until a dispute surfaces that the indexer serves no data. The protocol addresses this by requiring the indexer to produce "POI" (Proof of Indexing) attestations periodically; a missing POI within a window slashes the allocation.

## References

- The Graph documentation — https://thegraph.com/docs/
- Subgraph manifest specification — https://thegraph.com/docs/en/developing/creating-a-subgraph/
- Graph Protocol specification (technical paper) — https://github.com/graphprotocol/graphprotocol-docs
- GraphQL schema reference for subgraphs — https://thegraph.com/docs/en/developing/defining-a-subgraph/
- AssemblyScript API reference (`@graphprotocol/graph-ts`) — https://thegraph.com/docs/en/developing/assemblyscript-api/
- Substreams documentation — https://thegraph.com/docs/en/substreams/
- GRT token economics — https://thegraph.com/docs/en/about/the-graph-token/
- The Graph contracts (Arbitrum) — https://github.com/graphprotocol/contracts
- Proof of Indexing specification — https://thegraph.com/blog/proof-of-indexing
