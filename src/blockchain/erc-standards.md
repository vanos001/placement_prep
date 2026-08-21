# ERC Token Standards

## Overview

Ethereum Request for Comments (ERC) standards define the public interface contracts must implement to be recognised as a particular kind of token. The interfaces are deliberately minimal — a function signature, an event, a transfer semantic — so that any compliant contract can be dropped into a wallet, marketplace, DEX, or governance system without bespoke integration. This page covers the four primary token standards (ERC-20, ERC-721, ERC-1155, ERC-4626), the permit extension (EIP-2612), and the practical differences that matter when picking one.

## ERC-20: Fungible Tokens

[EIP-20](https://eips.ethereum.org/EIPS/eip-20), finalised in 2017, defines the fungible token interface. Every ERC-20 token has the same nine methods and two events:

```solidity
interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function allowance(address owner, address spender) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function name() external view returns (string memory);            // optional
    function symbol() external view returns (string memory);          // optional
    function decimals() external view returns (uint8);                // optional
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}
```

Key semantics:

- **`transfer(to, amount)`**: moves balance from `msg.sender` to `to`. Must emit `Transfer`. Reverts on insufficient balance or (post-2019) when `to` is the zero address.
- **`approve(spender, amount)`**: grants `spender` an allowance of `amount` from `msg.sender`. Must emit `Approval`.
- **`transferFrom(from, to, amount)`**: spender calls this; the contract checks `allowance[from][spender] >= amount`, decrements the allowance, moves the tokens.

### Two long-standing footguns

1. **Approval front-running (the "infinite approval" problem)**: if you approve Alice for 100, then later approve her for 50, the second tx is in the mempool. Alice sees it, front-runs with `transferFrom` for 100, and the second approval then sets her to 50 — she's withdrawn 150 total. The fix in practice is the `permit` extension (see below) or `increaseAllowance`/`decreaseAllowance` instead of absolute `approve`. Many production contracts (Compound's cToken, Uniswap's LP token) make this worse by allowing `type(uint256).max` as a "no-allowance-check" sentinel.

2. **`transfer` to a contract that doesn't support ERC-20**: the recipient contract has no `onERC20Received` callback (ERC-20 has none, unlike ERC-721's `onERC721Received`). Tokens sent to a contract with no `transfer` handler are locked permanently — the 2017 Parity wallet incident locked 513k ETH; similar accidents on token contracts happen weekly. Mitigation: use `SafeERC20.transfer` which checks the return data for the bool and reverts if missing.

The total supply of USDC, USDT, DAI — the three largest stablecoins — are all ERC-20. The standard survives because the interface is minimal and contract composability wins over feature richness.

## EIP-2612: Permit Extension

[EIP-2612](https://eips.ethereum.org/EIPS/eip-2612) adds a `permit` method to ERC-20. Instead of `approve` (which requires an on-chain transaction from the user, costing ~50k gas), the user signs an EIP-712 typed-data message off-chain. The spender submits the signature + the message in a single `permit` call, which writes the allowance on the user's behalf:

```solidity
function permit(
    address owner,
    address spender,
    uint256 value,
    uint256 deadline,
    uint8 v,
    bytes32 r,
    bytes32 s
) external;
```

The signed payload is `keccak256("\x19\x01" ++ domainSeparator ++ hashStruct(Permit))` where `Permit` is `permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)`. The contract tracks `nonces[owner]` to prevent replay.

Gas savings: the user pays zero gas for the approval (signature is off-chain). The spender folds the `permit` and the `transferFrom` into one transaction. The pattern is universal for ERC-20 vaults, DAI (PERMIT-type-1), and most L2 native tokens.

A related extension, [EIP-3009](https://eips.ethereum.org/EIPS/eip-3009) (`TransferWithAuthorization`), lets the spender pull tokens with a signed message without writing to the allowance mapping — saving one `SSTORE`. Used by USDC since v2.

## ERC-721: Non-Fungible Tokens

[EIP-721](https://eips.ethereum.org/EIPS/eip-721) introduces NFTs. Each token is unique and identified by a `uint256 tokenId`:

```solidity
interface IERC721 {
    function balanceOf(address owner) external view returns (uint256);
    function ownerOf(uint256 tokenId) external view returns (address);
    function safeTransferFrom(address from, address to, uint256 tokenId, bytes calldata data) external;
    function transferFrom(address from, address to, uint256 tokenId) external;
    function approve(address to, uint256 tokenId) external;
    function getApproved(uint256 tokenId) external view returns (address);
    function setApprovalForAll(address operator, bool approved) external;
    function isApprovedForAll(address owner, address operator) external view returns (bool);
    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event Approval(address indexed owner, address indexed approved, uint256 indexed tokenId);
    event ApprovalForAll(address indexed owner, address indexed operator, bool approved);
}
```

Notable differences vs. ERC-20:

- **`ownerOf`**: lookups are by `tokenId`, not by `(owner, token)` pair. The standard does *not* specify how owner is stored — most implementations use `mapping(uint256 => address) _owners`.
- **`safeTransferFrom`**: after the transfer, calls `IERC721Receiver(to).onERC721Received(...)` and reverts if the recipient returns the wrong magic value. This prevents accidentally sending to contracts that don't understand NFTs.
- **`setApprovalForAll`**: per-operator, per-collection allowance. The standard does not define per-token approval beyond the legacy `approve(tokenId)` which is for a single token at a time.
- **`supportsInterface`** (ERC-165): the contract returns `true` for `0x80ac58cd` (the ERC-721 interface id) so consumers can detect support without trying a call.

### Metadata extension

EIP-721 also defines `IERC721Metadata`: `name()`, `symbol()`, `tokenURI(uint256 tokenId) returns (string)`. The URI convention is JSON with `name`, `description`, `image`, `attributes`. Marketplaces (OpenSea, Blur, Magic Eden) fetch this off-chain — the contract itself stores nothing but the URI template (e.g. `https://api.example.com/metadata/{id}.json`). The art/data is off-chain; the contract only commits to where to find it.

This is the weakest link in NFT design: the contract guarantees token ownership but not metadata. If the off-chain server returns different JSON tomorrow, the "asset" changes. Immutable's fix is to store the metadata IPFS hash on-chain; the more general fix is to render fully on-chain (Autoglyphs, ChainRunners, Nouns).

### Enumeration

ERC-721's optional `IERC721Enumerable` exposes `totalSupply()` and `tokenOfOwnerByIndex(owner, index)`. OpenSea uses this to list a wallet's collection. The naive implementation (`uint256[] _allTokens` plus `mapping(uint256 => uint256) _allTokensIndex`) costs O(1) at the price of `SSTORE` on every mint and burn. Most contracts skip this and rely on The Graph for enumeration — gas-protocol trade-off.

## ERC-1155: Multi-Token

[EIP-1155](https://eips.ethereum.org/EIPS/eip-1155) is a *multi-token* standard: a single contract manages many token types, both fungible and non-fungible. Each token type has a `uint256 tokenId`, and balances are stored in `mapping(address => mapping(uint256 => uint256))`. This collapses a game's item catalogue (1000 swords, 500 shields, 1 of each legendary) into one contract rather than 1500 separate ERC-20 and ERC-721 deployments.

```solidity
interface IERC1155 {
    function balanceOf(address account, uint256 id) external view returns (uint256);
    function balanceOfBatch(address[] calldata accounts, uint256[] calldata ids)
        external view returns (uint256[] memory);
    function safeBatchTransferFrom(address from, address to, uint256[] calldata ids,
        uint256[] calldata amounts, bytes calldata data) external;
    event TransferSingle(address indexed operator, address indexed from,
        address indexed to, uint256 id, uint256 value);
    event TransferBatch(address indexed operator, address indexed from,
        address indexed to, uint256[] ids, uint256[] values);
    // ... mint / burn events
}
```

Differences vs. ERC-721:

- **Batch transfers**: `safeBatchTransferFrom` takes arrays — one transaction can move a basket of items. Saves gas because the calldata overhead is amortised and the loop touches the same storage slot.
- **No separate approval per token**: only `setApprovalForAll(operator, approved)` — a single bool per operator. The standard does not have `approve(tokenId)` because per-token approval is meaningless when each token type may have a billion identical copies.
- **URI templates**: `uri(uint256 id) returns (string)` returns a template — typically `https://api.example.com/item/{id}.json` and clients substitute the hex-encoded `id`.
- **Fungible + non-fungible in one**: a token with supply 1 is effectively an NFT; a token with supply 10⁹ is effectively a fungible token. The same contract can hold both.

ERC-1155 dominates game item contracts (Enjin, Gods Unchived, Immutable) and was used by OpenSea's shared storefront (the so-called "shared" 1155 contract that hosts ~95% of OpenSea's secondary listings).

## ERC-4626: Tokenized Vault

[EIP-4626](https://eips.ethereum.org/EIPS/eip-4626), finalised in 2022, standardises yield-bearing vaults. The vault holds an underlying ERC-20 (the "asset"); users deposit assets and receive ERC-20 shares whose value grows with the vault's yield. The standard wraps both the deposit / withdraw flow and the accounting, so any vault can plug into any front-end or aggregator.

```solidity
interface IERC4626 is IERC20 {
    function asset() external view returns (address);
    function totalAssets() external view returns (uint256);
    function convertToShares(uint256 assets) external view returns (uint256);
    function convertToAssets(uint256 shares) external view returns (uint256);
    function deposit(uint256 assets, address receiver) external returns (uint256);
    function withdraw(uint256 assets, address receiver, address owner) external returns (uint256);
    function redeem(uint256 shares, address receiver, address owner) external returns (uint256);
    function maxDeposit(address receiver) external view returns (uint256);
    function previewDeposit(uint256 assets) external view returns (uint256);
    // ... + withdraw / redeem / mint / withdraw variants
    event Deposit(address indexed sender, address indexed owner, uint256 assets, uint256 shares);
    event Withdraw(address indexed sender, address indexed receiver, address indexed owner, uint256 assets, uint256 shares);
}
```

The standard is a *strong* extension of ERC-20: shares are themselves an ERC-20, so a vault can be deposited into another vault (Yearn did this with yvTokens inside yvTokens), the share token can be AMM'd, etc. The four core operations (`deposit`, `withdraw`, `mint`, `redeem`) come with `preview`/`max` companions so integrators can quote without reverting.

### The first-depositor attack

Without protection, an attacker can manipulate `totalAssets` to make share prices unfavourable for later depositors:

1. Vault is empty. Attacker deposits 1 wei of asset, gets 1 share.
2. Attacker donates `2^128 - 1` of asset directly via `asset.transfer(vault, huge)`. `totalAssets()` now reads as huge.
3. Next depositor deposits 100k assets. The vault computes `shares = 100k * 1 / (huge)` ≈ 0 — depositor gets 0 shares for 100k of value, attacker steals it on withdraw.

OpenZeppelin's [ERC4626 implementation](https://docs.openzeppelin.com/contracts/4.x/erc4626) introduces *virtual assets and shares*: the vault pretends it has `10 ** decimals_offset` virtual assets and shares at deployment, so the initial share price is well-defined and the donation attack requires an economically-unreasonable donation. The offset scales with the underlying token's decimals — for a USDC (6-decimals) vault, the offset is 1e12; for a WETH (18-decimals) vault, the offset is 0.

### Inflation and deflation attacks

A related concern is the *deflationary token* underlying — if `asset.transferFrom` charges a 1% fee on transfer, the vault gets less than it accounts for. The standard does not require this; production vaults that wrap fee-on-transfer tokens typically override `_deposit` and `_withdraw` to use actual balances rather than the requested amounts. The Yearn V3 vault and the Morpho vaults handle this explicitly.

## Comparison

```
+---------------+----------+----------+----------+----------+
| Standard      | ERC-20   | ERC-721  | ERC-1155 | ERC-4626 |
+---------------+----------+----------+----------+----------+
| Token model   | fungible | unique   | both     | shares   |
| Identifiers   | account  | tokenId  | (acct,id)| share    |
| Storage       | (a)->u   | id->a    | (a,id)->u| (a)->u   |
| Transfer      | simple   | single   | batch    | mint/burn|
| Receiver cb   | none     | yes      | yes      | n/a      |
| Approval      | allowance| per-id   | per-acct | ERC-20   |
| Standard size | 9 fn     | 11 fn    | 6 fn     | 21 fn    |
| Use case      | money    | art      | games    | vaults   |
| Examples      | USDC     | Crypto-  | Gods     | Yearn v3 |
|               | DAI      | Punks    | Unchained| Morpho   |
+---------------+----------+----------+----------+----------+
```

When to pick which:

- **ERC-20**: money, governance tokens, voting shares. If every unit is interchangeable, ERC-20.
- **ERC-721**: one-of-one collectibles, ENS domains, real-estate titles, identity tokens. The "this is *that* token" property matters.
- **ERC-1155**: games with many item types; collections where shared metadata is more efficient than per-token contracts; semi-fungible items (e.g. season-pass tiers). Batch transfers are a real cost win.
- **ERC-4626**: any vault that holds an asset and issues shares. If you find yourself writing `deposit()`, `withdraw()`, `totalAssets()`, you should implement ERC-4626 instead — it gets you free composability with Yearn, Morpho, Zerolend, and every aggregator.

## Common Gotchas

- **Reentrancy on `transfer`**: ERC-20's `transfer` to a contract can reenter via its fallback. ERC-721's `safeTransferFrom` explicitly invokes the receiver hook. Apply `nonReentrant` to *all* mutating functions that touch shares or balances — not just `withdraw`.
- **Solidity `transfer` vs. token `transfer`**: `address(this).transfer(x)` is the 2300-gas EVM primitive; `IERC20(token).transfer(to, x)` is a high-level call that forwards gas. The former is being deprecated; the latter is what tokens mean.
- **`decimals()` is optional**: don't assume `18` (USDC is 6). Hardcoding decimals breaks integrations. Always read it dynamically.
- **Token pauses**: USDT has a `pause` flag — when paused, `transfer` reverts silently with no return value. `SafeERC20` handles this by reverting on a missing bool return.
- **Rebasing tokens**: `balanceOf` of a rebasing token (stETH, aToken) changes over time. The vault's accounting breaks if it assumes balances are constant between deposit and withdraw.
- **Frontrunning the mint**: NFT mints can be sandwiched by reading the public mempool and outbidding gas. Mitigation: Merkle-tree allowlists and off-chain signatures.

## Interview Questions

### Q1: Why does ERC-20 lack a "transfer-and-call" function while ERC-721 and ERC-1155 have one?

ERC-20 was finalised in 2017, predating the composability lessons of the next few years. By the time ERC-721 and ERC-1155 were designed, the pattern of "if you send tokens to a contract, call a hook so the recipient knows" was well established. [EIP-1363](https://eips.ethereum.org/EIPS/eip-1363) retrofits this onto ERC-20 (`transferAndCall`), but adoption is patchy. The lesson: a missing callback is a security vulnerability in practice (locked tokens), so newer standards learn from older mistakes.

### Q2: What's the difference between ERC-721 and ERC-1155 for a game with 1000 unique items and 1M fungible gold tokens?

ERC-721 would require 1000 contract deployments (or one contract with 1000 unique tokenIds, but then the gold token can't be modelled as ERC-721). ERC-1155 handles both in one contract: the 1000 items are tokenIds with supply 1, the gold is one tokenId with supply 1M. Transfers are batched, gas is amortised, the contract surface is half the size. For games, ERC-1155 is almost always right; for art collections (Bored Apes, CryptoPunks) ERC-721 is the convention.

### Q3: How does `permit` save gas, and what does it cost in trust model?

Without `permit`, the user submits an `approve` transaction (~50k gas: one `SSTORE` plus 21k base). With `permit`, the user signs off-chain (free), the spender folds the `permit` call into the transaction that does the work — one extra `SLOAD` + `SSTORE` plus `ecrecover` (3k gas). Trust model: the signature is a one-time credential; the user signs exactly what they authorised, so there's no extra trust.

### Q4: Explain the first-depositor attack on an ERC-4626 vault.

The vault is empty. Attacker mints 1 share for 1 asset, then donates a huge amount of asset directly via `asset.transfer(vault, huge)`. `totalAssets()` reports `huge + 1`. The next user deposits 100k assets; the vault computes `shares_mint = 100k * 1 / (huge + 1)` ≈ 0. The depositor gets 0 shares for 100k of assets; the attacker then redeems their single share for the entire vault balance. OpenZeppelin's `ERC4626` adds a *virtual* offset so the donation must exceed that virtual baseline — economically unfeasible.

## References

- [EIP-20: ERC-20 token standard](https://eips.ethereum.org/EIPS/eip-20)
- [EIP-721: ERC-721 non-fungible token standard](https://eips.ethereum.org/EIPS/eip-721)
- [EIP-1155: multi-token standard](https://eips.ethereum.org/EIPS/eip-1155)
- [EIP-4626: tokenized vault standard](https://eips.ethereum.org/EIPS/eip-4626)
- [EIP-2612: permit extension for ERC-20](https://eips.ethereum.org/EIPS/eip-2612)
- [EIP-165: standard interface detection](https://eips.ethereum.org/EIPS/eip-165)
- [EIP-1363: payable token with callbacks](https://eips.ethereum.org/EIPS/eip-1363)
- [EIP-3009: transfer with authorisation (ERC-20 extension)](https://eips.ethereum.org/EIPS/eip-3009)
- [OpenZeppelin ERC-4626 implementation](https://docs.openzeppelin.com/contracts/4.x/erc4626)

## Related Topics

- [Solidity](./solidity.md) — Contract structure, modifiers, ABI encoding
- [EVM Internals](./evm-internals.md) — Storage layout, gas, opcodes used in token transfers
- [Smart Contract Security](./smart-contract-security.md) — Reentrancy, overflow, access control on token contracts
- [Ethereum Internals](./ethereum-internals.md) — Gas model that drives ERC costs, EIP-1559
