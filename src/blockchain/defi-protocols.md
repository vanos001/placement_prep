# DeFi Protocol Architectures

## Overview

Decentralized finance (DeFi) replaces traditional financial intermediaries with on-chain smart contracts. A Uniswap pool substitutes for a specialist market maker; a Compound market substitutes for a bank's treasury desk; an Aave flash loan substitutes for an intraday prime-broker credit line. Each primitive composes with the others because settlement is atomic, balances are public, and any contract can call any other contract.

This page covers the four load-bearing primitives — automated market makers (AMMs), over-collateralized lending, yield farming incentives, and liquidations — and the oracle dependency that links all of them to off-chain price reality. It closes with a comparison to traditional finance (TradFi) market microstructure.

## Automated Market Makers

### The Constant-Product Invariant (Uniswap V2)

Uniswap V2 replaces a limit-order book with a single reserve pair `(x, y)` constrained by `x · y = k`. A trader who adds `Δx` of token X must remove `Δy` of token Y such that `(x + Δx)(y - Δy) = k` (ignoring fees). Solving for the output:

```
Δy = y · Δx / (x + Δx)
```

With a 0.30% fee in V2, the effective input is `Δx' = Δx · 997/1000`, giving:

```
Δy = (y · Δx') / (x + Δx')
```

The marginal price `dy/dx = y/x` drifts as the pool is consumed. A large trade relative to pool depth produces slippage bounded by `(Δx / x)`. Liquidity provision is permissionless: anyone calls `addLiquidity()` and receives LP tokens representing a pro-rata claim on `(x, y)`.

The V2 contract is roughly 700 lines of Solidity. The core swap is:

```solidity
function swap(uint amount0Out, uint amount1Out, address to, bytes calldata data) external lock {
    require(amount0Out > 0 || amount1Out > 0, 'IIA');
    (uint112 _reserve0, uint112 _reserve1,) = getReserves();
    require(amount0Out < _reserve0 && amount1Out < _reserve1, 'IL');

    uint balance0;
    uint balance1;
    { // scope for token{0,1} transfers
        address _token0 = token0;
        address _token1 = token1;
        if (amount0Out > 0) _safeTransfer(_token0, to, amount0Out);
        if (amount1Out > 0) _safeTransfer(_token1, to, amount1Out);
        if (data.length > 0) IUniswapCallee(to).uniswapV2Call(msg.sender, amount0Out, amount1Out, data);
        balance0 = IERC20(_token0).balanceOf(address(this));
        balance1 = IERC20(_token1).balanceOf(address(this));
    }
    // invariant check: (balance0 * reserve1 == balance1 * reserve0) must hold post-swap
    uint balance0Adjusted = balance0.mul(1000).sub(amount0In.mul(3));
    uint balance1Adjusted = balance1.mul(1000).sub(amount1In.mul(3));
    require(balance0Adjusted.mul(balance1Adjusted) >= uint(_reserve0).mul(_reserve1).mul(1000000), 'K');
}
```

The `K` check enforces the invariant *after* the swap. The `sub(amountIn.mul(3))` clause applies the 0.3% fee by reducing the effective input balance before the constant-product test.

### Concentrated Liquidity (Uniswap V3)

V2's inefficiency: liquidity is spread uniformly over `[0, ∞)`, so almost all of it sits idle if the price stays in a tight range. Uniswap V3 lets LPs choose a price range `[Pa, Pb]` and provide liquidity only inside it. The pool tracks liquidity as a piecewise-constant function `L(P)` over a discretized tick grid (ticks every `1.0001^i` for integer `i`, giving 0.01% granularity).

The V3 math replaces `x · y = k` with the concentrated-liquidity relation:

```
L = sqrt(x · y)            (reserve geometry at price P = sqrt(Pa · Pb) for active range)
x = L · (1/sqrt(P) - 1/sqrt(Pb))
y = L · (sqrt(P) - sqrt(Pa))
```

`L` is invariant for a single position while the price stays in `[Pa, Pb]`. When the price crosses a tick boundary, the pool either uses up one reserve (virtual) and flips to the other side, or accumulates fees into the position. LP positions are NFTs (ERC-721) because each position is non-fungible: distinct ranges, distinct fee tiers, distinct `Pa`/`Pb`.

V3 supports three fee tiers per pair (typically 0.05%, 0.30%, 1.00%) so LPs can self-select into volatility bands. Stablecoin/stablecoin pairs concentrate in the 0.05% pool with ranges like `[0.999, 1.001]`, achieving capital efficiency 100–400x higher than V2 for the same depth.

> **Interview angle**: "Why does V3 LP earn more risk?" Because concentrated liquidity isomorphic to a short straddle — the LP is short volatility. If price moves outside `[Pa, Pb]`, the position becomes 100% one asset and accrues no fees until price returns. Impermanent loss is amplified relative to V2.

### TWAP oracles built on AMMs

Uniswap V2 also exports a price oracle via `priceCumulative0/1` accumulators updated each block:

```solidity
require(_blockTimestamp != blockTimestamp, "UniswapV2: FORBIDDEN");
uint32 timeElapsed = blockTimestamp - blockTimestampLast;
price0CumulativeLast += uint(UQ112x112.encode(_reserve1).uqdiv(_reserve0)) * timeElapsed;
price1CumulativeLast += uint(UQ112x112.encode(_reserve0).uqdiv(_reserve1)) * timeElapsed;
```

The time-weighted average price (TWAP) over `T` seconds is `Δaccumulator / T`. TWAP over a long window (≥30 minutes) is manipulation-resistant: an attacker must hold the pool's spot price off-market for the full window, which is unprofitable when the rest of the market is arbitraging back to fair value. Many lending protocols consume TWAPs as a backstop to their primary Chainlink feed.

## Over-Collateralized Lending

### Compound v2: the cToken model

Compound v2 wraps each collateral asset into an interest-bearing ERC-20 called a **cToken** (e.g., `cUSDC`). Supplying USDC mints cUSDC at an exchange rate that appreciates over time:

```
exchangeRate = (totalUnderlying + totalReserves) / totalCTokenSupply
```

The borrow rate and supply rate derive from a per-block utilization `U = borrows / (cash + borrows)`. The interest rate curve is piecewise linear with a kink at `U = 0.8`:

```
borrowRate = baseRate + U            · multiplier         (U ≤ U_optimal)
borrowRate = baseRate + U_optimal   · multiplier + (U - U_optimal) · kink     (U > U_optimal)
supplyRate = borrowRate · U · (1 - reserveFactor)
```

Above the kink, the rate explodes — discouraging further borrows and rewarding suppliers who add liquidity. This is the on-chain equivalent of a central bank's standing facility.

### Aave v3: the aToken + stable rate model

Aave's variant mints **aTokens** (`aUSDC`) that are *1:1* with the underlying and accrue interest via `scaledBalanceOf = balance / liquidityIndex`. The `liquidityIndex` is updated each time the reserve's utilization changes.

Aave adds two non-Compound primitives:

- **Stable-rate borrows**: a borrower locks in a rate for the life of the position (subject to rebalancing on large utilization shocks). Useful for borrowers hedging rate volatility.
- **Flash loans**: atomic, fee-charged, uncollateralized loans that must be repaid in the same transaction. Aave earned 0.09% per flash loan (now 0.05%). This is impossible in TradFi — it relies on transaction atomicity.

```solidity
function flashLoanSimple(
    address receiverAddress,
    address asset,
    uint256 amount,
    bytes calldata params,
    uint16 referralCode
) external override {
    uint256 totalSupply = _reserves[asset].totalSupply();
    uint256 availableLiquidity = IERC20(asset).balanceOf(address(this));
    require(availableLiquidity >= amount, "L");

    // Calculate and store the premium
    uint256 premium = _calculatePremium(amount, totalSupply);
    _reserves[asset].accrueToTreasury(premium);

    // Transfer the funds
    IERC20(asset).transfer(receiverAddress, amount);

    // Execute the receiver's callback
    IFlashLoanSimpleReceiver(receiverAddress).executeOperation(
        asset, amount, premium, msg.sender, params
    );

    // Verify repayment
    uint256 balanceAfter = IERC20(asset).balanceOf(address(this));
    require(balanceAfter >= availableLiquidity + premium, "BP");
}
```

Flash loans have become the load-bearing primitive for arbitrage, liquidations, refinancing, and self-liquidation of MakerDAO vaults.

## Yield Farming

Yield farming is the practice of staking or locking LP tokens (or other DeFi receipts) to earn protocol incentives — typically a governance token minted by the protocol itself. The mechanism is simple: rewards are emitted per second and split pro-rata among stakers.

```solidity
function stake(uint256 amount) external nonReentrant updateReward(msg.sender) {
    require(amount > 0, "Cannot stake 0");
    _totalSupply = _totalSupply.add(amount);
    _balances[msg.sender] = _balances[msg.sender].add(amount);
    stakingToken.safeTransferFrom(msg.sender, address(this), amount);
    emit Staked(msg.sender, amount);
}

modifier updateReward(address account) {
    rewardPerTokenStored = rewardPerToken();
    lastUpdateTime = lastTimeRewardApplicable();
    if (account != address(0)) {
        rewards[account] = earned(account);
        userRewardPerTokenPaid[account] = rewardPerTokenStored;
    }
    _;
}

function rewardPerToken() public view returns (uint256) {
    if (_totalSupply == 0) return rewardPerTokenStored;
    return rewardPerTokenStored.add(
        lastTimeRewardApplicable().sub(lastUpdateTime).mul(rewardRate).mul(1e18).div(_totalSupply)
    );
}
```

The SushiSwap vampire attack on Uniswap (Aug 2020) is the canonical case: SUSHI was minted to users who staked Uniswap LP tokens, then the underlying liquidity was migrated to Sushi's own pools. This demonstrated that yield farming can be used to bootstrap liquidity by directly attacking an incumbent's TVL.

The economic critique: yield farming rewards are often denominated in a protocol's own token, whose value depends on the protocol's success, which depends on the liquidity the farming incentivizes. This is a reflexive loop — valuable while momentum persists, but it collapses to zero if the token price falls below the operational cost of providing the liquidity.

## The Liquidation Mechanism

Lending protocols enforce solvency via liquidation. Each account has a **health factor** `H = (collateral_value · liquidationThreshold) / debt_value`. When `H < 1`, the position is liquidatable.

A liquidator repays part of the debt and receives collateral plus a **bonus** (e.g., 5–10%) as compensation for gas, slippage, and risk. Compound v2 lets any caller liquidate up to 50% of the borrowed position; Aave v3 uses `closeFactor = 1` (full liquidation) when `H < liquidationThreshold` (close factor e-mode), and `closeFactor = 0.5` otherwise.

```
Liquidator pays:    debt_to_repay = min(position_debt * closeFactor, ...)
Liquidator gets:    collateral_seized = debt_to_repay / oracle_price * (1 + liquidation_bonus)
Position debt:      -= debt_to_repay
Position collateral: -= collateral_seized
```

The challenge for liquidators is three-fold:

1. **Gas auctions**: liquidations are competitive; the highest gas-price transaction wins. Ethereum's MEV-Boost and private RPCs (Flashbots Protect) are now the de facto routing layer.
2. **Slippage on the swap-back**: seized collateral must be sold into another asset, often via the very AMMs whose price is also feeding the lending market.
3. **Oracle lag**: a fast-moving market can leave a position *underwater* (collateral value < debt value) before liquidation lands. The protocol absorbs the loss via its safety module (Aave) or via auction-based debt markets (MakerDAO's flop auctions).

MakerDAO's liquidation model is auction-based rather than instantaneous:

- **Flop auction** — sells MKR governance tokens to mint Dai and recapitalize bad debt.
- **Flip auction** — sells seized collateral (e.g., ETH) for Dai at a descending-price Dutch auction, settling the debt.

The March 2020 Black Thursday event exposed a failure mode: zero-bid auctions for collateral when gas prices spiked, leaving MakerDAO undercollateralized by ~$6M. The protocol responded with chainlink price floors, auction coalescing, and higher minimum bid increments.

## Oracle Dependency

Every lending protocol depends on a price oracle to compute `collateral_value` and `debt_value`. The dominant choice is Chainlink's decentralized price feeds, which aggregate off-chain prices from multiple node operators and post them on-chain via the **Off-Chain Reporting (OCR)** protocol.

A typical Chainlink feed exposes:

```solidity
function latestRoundData()
    external view returns (
        uint80 roundId,
        int256 answer,    // price * 1e8
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
```

Aave v3's ` getPriceAssetPrice(asset)` call typically reads:

```solidity
function _getPrice(address asset) internal view returns (uint256) {
    AggregatorInterface feed = _assets[asset].priceFeed;
    require(feed != address(0), "PF");
    int256 price = feed.latestAnswer();
    require(price > 0, "IP");
    return uint256(price);
}
```

Two design considerations matter:

1. **Stale data**: feeds only update when price moves more than `deviationThreshold` or after `heartbeatSeconds`. A bug or network split can leave the on-chain answer stale. Aave wraps each call in a staleness check (`updatedAt` must be within bounds).
2. **Manipulation**: reading the AMM's *spot* price is unsafe — an attacker can use a flash loan to push the spot price within a single transaction, then borrow against the inflated collateral. Synthetix's sUSD exploit (Jun 2020) was a flash-loan-driven oracle manipulation that cost ~$1B in synthetic-asset inflation. The fix is to use TWAPs or Chainlink's volume/liquidity-weighted aggregated price.

The fair-market price is computed off-chain by oracle nodes pulling from at least 5–7 sources (e.g., Binance, Coinbase, Kraken, Uniswap TWAP), taking the median, signing the report, and pushing it on-chain. Median (not mean) is chosen because it is robust to outliers — one bad source cannot drag the answer far.

## Comparison to Traditional Finance

| Dimension | Traditional Finance | DeFi |
|-----------|--------------------|------|
| **Counterparty risk** | Bilateral credit, ISDA agreements, CCP intermediation | Trust-minimized; risk reduced to smart contract + oracle |
| **Margin call** | Real-time monitoring, broker-initiated, 1–3 day settlement | Atomic on-chain liquidation, 12-second block cadence |
| **Interest rate discovery** | LIBOR/SOFR, brokered repo | Per-block utilization curve, per-asset markets |
| **Credit underwriting** | KYC, FICO, income verification | Zero. Risk is priced purely via collateralization ratio |
| **Settlement finality** | T+1 (US equities), T+2 (FX) | Atomic (single transaction) or near-atomic (single block) |
| **Regulation** | SEC, CFTC, banking charters | Permissionless; legal status still in flux |
| **Market making** | Specialists, HFT firms on order books | Passive AMMs, concentrated-liquidity LPs |
| **Transparency** | OTC markets opaque, L2/L3 hidden | Every reserve, every position is publicly readable |
| **Liquidation** | Broker liquidation, prime-broker risk transfer | Public, anyone can call `liquidate()` |
| **Systemic risk** | Counterparty cascades (Lehman 2008) | Oracle + composability cascades (Celsius, FTX, UST 2022) |

The key structural differences: DeFi replaces bilateral credit risk with smart-contract risk and oracle risk; replaces broker intermediation with permissionless market-making; and replaces regulatory protection with open-source audits and bug bounties. The composability primitive — any contract calling any other — has no TradFi analog because TradFi settlement is bilateral and legally encumbered, while EVM settlement is atomic.

The trade-offs are clear: DeFi's atomicity enables flash loans, instant liquidations, and composability, but the same atomicity is what makes oracle manipulation a single-transaction exploit. Permissionless market-making eliminates gatekeeping but creates symmetric attacks (sandwich, just-in-time liquidity). Yield farming bootstraps liquidity but is reflexive and unstable. The protocols are best understood not as TradFi replacements but as a different point in the design space — one that optimizes for composability and verifiability at the cost of capital efficiency for low-volatility use cases.

## References

- Uniswap V3 Core whitepaper — https://uniswap.org/whitepaper-v3.pdf
- Uniswap V2 Core whitepaper — https://uniswap.org/whitepaper.pdf
- Compound V2 whitepaper — https://compound.finance/documents/Compound.Whitepaper.pdf
- Aave V3 technical paper — https://github.com/aave/aave-v3-core/blob/master/techpaper/Aave_V3_Technical_Paper.pdf
- MakerDAO MIPs and auction documentation — https://docs.makerdao.com/
- Chainlink Price Feeds documentation — https://docs.chain.link/data-feeds/price-feeds
- Uniswap V3 Core source — https://github.com/Uniswap/v3-core
- Synthetix sUSD incident postmortem — https://blog.synthetix.io/issue-report/
