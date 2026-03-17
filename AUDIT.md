# Axelar CGP Solidity -- Security Audit Report

**Repository:** `Kushmanmb/axelar-cgp-silly-files`  
**Audit Version:** 1.0.0  
**Date:** 2026-03-17  
**Scope:** All production Solidity contracts in `contracts/` (excluding `contracts/test/`)  
**Compiler Range Tested:** Solidity `0.8.9` (pinned) and `^0.8.0` (floating)  
**Auditors:** 0xCon Automated + Manual Review  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Scope](#2-scope)
3. [Findings Overview](#3-findings-overview)
4. [Critical Findings](#4-critical-findings)
5. [High Findings](#5-high-findings)
6. [Medium Findings](#6-medium-findings)
7. [Low Findings](#7-low-findings)
8. [Informational Findings](#8-informational-findings)
9. [Secrets & Sensitive Data Scan](#9-secrets--sensitive-data-scan)
10. [Dependency Vulnerability Scan](#10-dependency-vulnerability-scan)
11. [Recommendations Summary](#11-recommendations-summary)
12. [Disclaimer](#12-disclaimer)

---

## 1. Executive Summary

This report documents the findings of a full security audit of the Axelar Cross-chain Gateway Protocol (CGP) Solidity smart contracts. The audit covered access control, reentrancy, signature verification, proxy patterns, ERC-20 correctness, deposit service security, and dependency vulnerabilities.

**Total findings: 16**

| Severity     | Count |
|-------------|-------|
| Critical     | 0     |
| High         | 3     |
| Medium       | 4     |
| Low          | 5     |
| Informational| 4     |

**No hardcoded secrets or private keys were found in the repository.**

---

## 2. Scope

### In-Scope Contracts

| Contract | Path |
|----------|------|
| AxelarGateway | `contracts/AxelarGateway.sol` |
| AxelarGatewayProxy | `contracts/AxelarGatewayProxy.sol` |
| AxelarAuthWeighted | `contracts/auth/AxelarAuthWeighted.sol` |
| BurnableMintableCappedERC20 | `contracts/BurnableMintableCappedERC20.sol` |
| MintableCappedERC20 | `contracts/MintableCappedERC20.sol` |
| ERC20 | `contracts/ERC20.sol` |
| ERC20Permit | `contracts/ERC20Permit.sol` |
| ECDSA | `contracts/ECDSA.sol` |
| EternalStorage | `contracts/EternalStorage.sol` |
| Ownable | `contracts/Ownable.sol` |
| TokenDeployer | `contracts/TokenDeployer.sol` |
| DepositHandler | `contracts/DepositHandler.sol` |
| AxelarDepositService | `contracts/deposit-service/AxelarDepositService.sol` |
| AxelarDepositServiceProxy | `contracts/deposit-service/AxelarDepositServiceProxy.sol` |
| DepositReceiver | `contracts/deposit-service/DepositReceiver.sol` |
| DepositServiceBase | `contracts/deposit-service/DepositServiceBase.sol` |
| ReceiverImplementation | `contracts/deposit-service/ReceiverImplementation.sol` |
| AxelarGasService | `contracts/gas-service/AxelarGasService.sol` |
| AxelarGasServiceProxy | `contracts/gas-service/AxelarGasServiceProxy.sol` |
| Proxy | `contracts/util/Proxy.sol` |

### Out-of-Scope

- `contracts/test/` -- test helpers/mocks
- `node_modules/` -- third-party dependencies
- Off-chain infrastructure, validators, and relayers

---

## 3. Findings Overview

| ID | Title | Severity | Contract | Status |
|----|-------|----------|----------|--------|
| H-01 | `ecrecover` return value not checked for zero address in `ERC20Permit` | High | ERC20Permit | Open |
| H-02 | `tokenAddress` zero-check occurs after it is used in `receiveAndSendToken` | High | ReceiverImplementation | Open |
| H-03 | `AxelarGasService` constructor does not validate `gasCollector` address | High | AxelarGasService | Open |
| M-01 | `selfdestruct` usage deprecated in Cancun; contracts rely on it for cleanup | Medium | DepositHandler, DepositReceiver | Open |
| M-02 | Floating pragma `^0.8.0` in production contracts | Medium | Multiple | Open |
| M-03 | `AxelarDepositService.refundToken` public storage creates cross-function re-entrancy surface | Medium | AxelarDepositService | Open |
| M-04 | `Proxy.init` sets owner to zero if `newOwner` is zero address -- permanent lock | Medium | Proxy | Open |
| L-01 | `ECDSA.recover` does not guard against the zero-address signer | Low | ECDSA | Acknowledged |
| L-02 | `TokenDeployer.deployToken` is unprotected -- anyone can deploy tokens | Low | TokenDeployer | Acknowledged |
| L-03 | `EternalStorage` getter/setter functions are all `public` | Low | EternalStorage | Acknowledged |
| L-04 | Missing two-step ownership transfer in `Ownable` | Low | Ownable | Open |
| L-05 | `AxelarAuthWeighted.validateProof` epoch window only 16 -- aggressive key rotation risk | Low | AxelarAuthWeighted | Acknowledged |
| I-01 | Inconsistent Solidity version pinning across codebase | Info | Multiple | Open |
| I-02 | `DepositHandler` uses `noReenter` but not `ReentrancyGuard` pattern | Info | DepositHandler | Acknowledged |
| I-03 | `MintableCappedERC20` cap check happens after `_mint` | Info | MintableCappedERC20 | Acknowledged |
| I-04 | 69 npm dev-dependency vulnerabilities (35 low, 13 medium, 17 high, 4 critical) | Info | package.json | Open |

---

## 4. Critical Findings

*No critical severity findings were identified.*

---

## 5. High Findings

### H-01 -- `ecrecover` Return Not Checked for Zero Address in `ERC20Permit`

**Severity:** High  
**Contract:** `contracts/ERC20Permit.sol`  
**Lines:** 57-59  

**Description:**  
The `permit()` function calls the built-in `ecrecover` opcode and stores the result in `recoveredAddress`. If the signature is invalid in certain ways (e.g., `v` is neither 27 nor 28 after the explicit checks), `ecrecover` returns `address(0)`. The subsequent check `if (recoveredAddress != issuer)` would pass if the caller sets `issuer = address(0)`, allowing anyone to grant an unlimited approval from the zero address. While the downstream `_approve` call would revert on a zero-address owner, this remains a latent correctness issue and deviates from the EIP-2612 reference implementation which explicitly checks `recoveredAddress != address(0)`.

**Vulnerable Code:**
```solidity
address recoveredAddress = ecrecover(digest, v, r, s);
if (recoveredAddress != issuer) revert InvalidSignature();
```

**Recommendation:**  
Add an explicit zero-address check immediately after `ecrecover`:
```solidity
address recoveredAddress = ecrecover(digest, v, r, s);
if (recoveredAddress == address(0) || recoveredAddress != issuer) revert InvalidSignature();
```

---

### H-02 -- `tokenAddress` Zero-Check After Use in `receiveAndSendToken`

**Severity:** High  
**Contract:** `contracts/deposit-service/ReceiverImplementation.sol`  
**Lines:** 28-40  

**Description:**  
In `receiveAndSendToken`, the `tokenAddress` is fetched from the gateway and immediately used in `IERC20(tokenAddress).balanceOf(address(this))` on line 38. The validation `if (tokenAddress == address(0)) revert InvalidSymbol()` only occurs on line 40, **after** the external call. If `tokenAddress` is zero (invalid symbol), the `balanceOf` call on address `0x0` will either revert with an unexpected error or succeed silently, producing misleading behaviour before the intended guard fires.

**Vulnerable Code:**
```solidity
address tokenAddress = IAxelarGateway(gateway).tokenAddresses(symbol);
// ...
uint256 amount = IERC20(tokenAddress).balanceOf(address(this));  // line 38 -- used here

if (tokenAddress == address(0)) revert InvalidSymbol();          // line 40 -- guarded too late
```

**Recommendation:**  
Move the zero-address check immediately after fetching `tokenAddress`, before any use:
```solidity
address tokenAddress = IAxelarGateway(gateway).tokenAddresses(symbol);
if (tokenAddress == address(0)) revert InvalidSymbol();

uint256 amount = IERC20(tokenAddress).balanceOf(address(this));
if (amount == 0) revert NothingDeposited();
```

---

### H-03 -- `AxelarGasService` Constructor Does Not Validate `gasCollector`

**Severity:** High  
**Contract:** `contracts/gas-service/AxelarGasService.sol`  
**Lines:** 29-31  

**Description:**  
The constructor accepts a `gasCollector_` parameter and stores it as an `immutable` variable without checking it is non-zero. Because the variable is `immutable`, it cannot be changed after deployment. If a zero address is passed by mistake, the `onlyCollector` modifier will permanently allow only `address(0)` to collect fees, effectively bricking fee collection for the lifetime of the contract.

**Vulnerable Code:**
```solidity
constructor(address gasCollector_) {
    gasCollector = gasCollector_;  // no zero-address guard
}
```

**Recommendation:**
```solidity
constructor(address gasCollector_) {
    if (gasCollector_ == address(0)) revert InvalidAddress();
    gasCollector = gasCollector_;
}
```

---

## 6. Medium Findings

### M-01 -- `selfdestruct` Deprecated; Reliance on Post-Cancun State Clearing

**Severity:** Medium  
**Contracts:** `contracts/DepositHandler.sol` (line 29), `contracts/deposit-service/DepositReceiver.sol` (line 25)  

**Description:**  
Both `DepositHandler.destroy()` and `DepositReceiver` constructor use `selfdestruct`. EIP-6780 (activated in Cancun/Dencun, March 2024) changed `selfdestruct` semantics: the opcode no longer clears contract storage or code, and only transfers ETH when called in the same transaction as contract creation. The hardhat config already targets `cancun`. The `DepositHandler` pattern relies on `destroy()` being called in the same transaction as `new DepositHandler{salt:...}()` -- this still works with EIP-6780 for ETH transfer, but storage is no longer cleared. Future code changes that rely on storage being wiped would be silently broken.

**Recommendation:**  
Migrate to a pattern that does not depend on storage clearing via `selfdestruct`. Consider using `CREATE2`-based singleton deployment with state resets, or document explicitly that no contract state is written before `destroy()` is called.

---

### M-02 -- Floating Pragma `^0.8.0` in Production Contracts

**Severity:** Medium  
**Contracts:** `AxelarGateway.sol`, `TokenDeployer.sol`, `AxelarAuthWeighted.sol`, `AxelarDepositService.sol`, `DepositReceiver.sol`, `DepositServiceBase.sol`, `ReceiverImplementation.sol`, `AxelarGasService.sol`  

**Description:**  
Production contracts use `pragma solidity ^0.8.0;` which allows compilation with any `0.8.x` release up to (but not including) `0.9.0`. Minor compiler releases have historically introduced breaking changes and new optimisations that alter bytecode. Pinning to a specific version ensures deterministic, auditable deployments.

**Recommendation:**  
Pin all production contracts to the same specific version used by the other contracts (`0.8.9` or the latest audited release). For example:
```solidity
pragma solidity 0.8.9;
```

---

### M-03 -- `refundToken` Public Storage Creates Re-Entrancy Surface

**Severity:** Medium  
**Contract:** `contracts/deposit-service/AxelarDepositService.sol`  
**Lines:** 24, 154-169  

**Description:**  
`refundToken` is a `public` state variable that is written immediately before deploying a `DepositReceiver` and reset to zero only after the loop completes. During the loop, an external contract (via `DepositReceiver -> delegatecall -> ReceiverImplementation`) can re-enter `AxelarDepositService` and read `refundToken` in an inconsistent state. While Slither annotates these as "reentrancy-benign", the pattern relies on the EVM single-call atomicity guarantee -- any future refactoring that introduces external calls outside the constructor lifecycle would silently introduce a re-entrancy bug.

**Recommendation:**  
Use the checks-effects-interactions pattern: compute all refund state before any external calls, or use a local variable passed through the call chain instead of relying on public storage.

---

### M-04 -- `Proxy.init` Can Permanently Lock Ownership to `address(0)`

**Severity:** Medium  
**Contract:** `contracts/util/Proxy.sol`  
**Lines:** 27-51  

**Description:**  
The `init()` function accepts a `newOwner` parameter and stores it directly with `sstore(_OWNER_SLOT, newOwner)` with no zero-address check. If `newOwner` is accidentally set to `address(0)`, the proxy owner becomes the zero address permanently (since there is no upgrade path once initialized). This would make it impossible to ever call privileged `onlyOwner` functions through the proxy.

**Recommendation:**
```solidity
if (newOwner == address(0)) revert InvalidOwner();
```

---

## 7. Low Findings

### L-01 -- `ECDSA.recover` Does Not Guard Against Zero-Address Signer

**Severity:** Low  
**Contract:** `contracts/ECDSA.sol`  
**Lines:** 62-63  

**Description:**  
While invalid `v`/`s` values are rejected before calling `ecrecover`, the function does not check whether the recovered address is `address(0)`. This is consistent with OpenZeppelin's older implementation, but newer best practices (OpenZeppelin ? 4.x) add this explicit check. The impact is low since `AxelarAuthWeighted` would fail to find a matching operator, but callers of this library should be aware of the omission.

**Recommendation:**  
Add `if (signer == address(0)) revert InvalidSignature();` after the `ecrecover` call.

---

### L-02 -- `TokenDeployer.deployToken` Is Unprotected

**Severity:** Low  
**Contract:** `contracts/TokenDeployer.sol`  

**Description:**  
`TokenDeployer.deployToken` is `external` with no access control modifier. In production the only caller should be `AxelarGateway` (via `delegatecall`), so the `TokenDeployer` is never directly called. However, any EOA or contract can call `deployToken` directly and waste gas deploying tokens. This is low impact (gas waste only) but is a code quality issue.

**Recommendation:**  
Add a comment documenting that this function is only safe to call via `delegatecall` from `AxelarGateway`, or restrict direct calls with an access check.

---

### L-03 -- `EternalStorage` Getter Functions Are All `public`

**Severity:** Low  
**Contract:** `contracts/EternalStorage.sol`  

**Description:**  
All getter functions (`getUint`, `getString`, `getAddress`, etc.) are `public`, meaning any contract or EOA can read any storage slot by knowing the key. While storage in Ethereum is already publicly readable at the EVM level, the `public` modifier exposes these as part of the ABI, which can aid attackers in enumeration. For sensitive keys (governance address, implementation address), this is low impact since they are also `immutable` constants, but it is a principle-of-least-privilege violation.

**Recommendation:**  
Consider making getters `internal` where they are only needed within the contract hierarchy, and exposing named, typed view functions for the values that should be publicly readable.

---

### L-04 -- Missing Two-Step Ownership Transfer in `Ownable`

**Severity:** Low  
**Contract:** `contracts/Ownable.sol`  

**Description:**  
`transferOwnership` performs a single-step ownership transfer -- the new owner is set immediately without requiring the new address to accept. A typo in the new owner address would permanently lock out legitimate ownership. This is a well-known issue documented in OpenZeppelin's `Ownable2Step`.

**Recommendation:**  
Implement a two-step pattern: `proposeOwnership(address)` stores a pending owner, and the new owner must call `acceptOwnership()` to complete the transfer.

---

### L-05 -- `AxelarAuthWeighted` Key Retention Window Is Only 16 Epochs

**Severity:** Low  
**Contract:** `contracts/auth/AxelarAuthWeighted.sol`  
**Lines:** 15, 37-38  

**Description:**  
`OLD_KEY_RETENTION = 16` means only the last 16 operator sets are considered valid for signing. If the Axelar network performs rapid key rotations (e.g., during an incident), old in-flight transactions signed with epoch `N` will be rejected if epoch advances to `N + 16` before they are processed.

**Recommendation:**  
Document the maximum safe block-time window for key retention, and consider parameterising `OLD_KEY_RETENTION` via governance to allow adjustment without a full upgrade.

---

## 8. Informational Findings

### I-01 -- Inconsistent Solidity Version Pinning

**Severity:** Informational  
**Description:**  
Some contracts use `pragma solidity 0.8.9;` (pinned) while others use `pragma solidity ^0.8.0;` (floating). Consistent pinning across the entire codebase reduces the risk of divergent behaviour in different deployment environments.

---

### I-02 -- `DepositHandler.noReenter` Uses Custom Re-Entrancy Guard

**Severity:** Informational  
**Description:**  
`DepositHandler` implements its own re-entrancy guard (`IS_LOCKED`/`IS_NOT_LOCKED` pattern) rather than inheriting from a battle-tested implementation such as OpenZeppelin's `ReentrancyGuard`. The implementation is functionally equivalent, but custom guards are harder to audit and maintain.

---

### I-03 -- `MintableCappedERC20.mint` Cap Check After `_mint`

**Severity:** Informational  
**Contract:** `contracts/MintableCappedERC20.sol`  
**Description:**  
The `totalSupply > capacity` check fires after `_mint` has already updated state. While the function reverts on overflow (returning state to pre-mint), this is a deviation from the Checks-Effects-Interactions pattern and could cause confusion during code review.

**Recommendation:**  
Pre-compute whether the mint would exceed the cap before calling `_mint`:
```solidity
if (capacity > 0 && totalSupply + amount > capacity) revert CapExceeded();
_mint(account, amount);
```

---

### I-04 -- 69 npm Dev-Dependency Vulnerabilities

**Severity:** Informational  
**Description:**  
`npm audit` reports 69 vulnerabilities in dev dependencies (35 low, 13 moderate, 17 high, 4 critical). The critical ones include:
- `cipher-base` -- missing type checks enabling hash rewind (`GHSA-cpq7-6gpm-g9rc`)
- `form-data` -- unsafe random boundary (`GHSA-fjxv-7rqg-78g4`)
- `pbkdf2` -- uninitialized memory for non-standard algorithms (`GHSA-h7cp-r72f-jxh6`, `GHSA-v62p-rq8g-8h59`)
- `sha.js` -- missing type checks enabling hash rewind (`GHSA-95m3-7q98-8xr5`)

All are in **dev dependencies** used only by the test harness (Hardhat, coverage tools). They do not affect deployed contract code. However, they could affect CI environments or scripts that process untrusted input.

**Recommendation:**  
Run `npm audit fix` to resolve automatable issues. Evaluate `npm audit fix --force` for breaking-change upgrades in a test branch.

---

## 9. Secrets & Sensitive Data Scan

A full grep scan of the repository (excluding `node_modules/`) for common patterns (private keys, mnemonics, API keys, `.env` files) returned **no findings**. Specifically:

- No 64-hex-character strings consistent with private keys outside of keccak256 hash constants
- No mnemonic phrases
- No `PRIVATE_KEY`, `SECRET`, `API_KEY`, `PASSWORD` assignments in source files
- No `.env` files committed
- The `funding.json` file contains only a public project ID (`0x4db69fb5...`), not a secret

---

## 10. Dependency Vulnerability Scan

**Tool:** `npm audit`  
**Scan Date:** 2026-03-17  

| Severity | Count | Notes |
|----------|-------|-------|
| Critical | 4     | Dev dependencies only -- `cipher-base`, `form-data`, `pbkdf2`, `sha.js` |
| High     | 17    | Dev dependencies only -- `axios`, `base-x`, `ws`, `undici`, etc. |
| Moderate | 13    | Dev dependencies only |
| Low      | 35    | Dev dependencies only |
| **Total**| **69**| **No production contract impact** |

All vulnerabilities are in packages used exclusively by the development/testing toolchain (Hardhat, eslint, coverage). The compiled Solidity bytecode deployed on-chain is not affected.

---

## 11. Recommendations Summary

| Priority | Action |
|----------|--------|
| High | Add `recoveredAddress == address(0)` check in `ERC20Permit.permit` |
| High | Move `tokenAddress` zero-check before `balanceOf` call in `ReceiverImplementation` |
| High | Add `address(0)` guard in `AxelarGasService` constructor |
| Medium | Migrate away from `selfdestruct` in `DepositHandler` and `DepositReceiver` |
| Medium | Pin all production pragma versions to `0.8.9` |
| Medium | Add `address(0)` guard for `newOwner` in `Proxy.init` |
| Low | Implement two-step ownership transfer in `Ownable` |
| Low | Document `TokenDeployer.deployToken` delegatecall-only intent |
| Informational | Run `npm audit fix` to address dev dependency vulnerabilities |

---

## 12. Disclaimer

This report is provided "as is" and does not constitute a warranty or guarantee of the security of the smart contracts. The audit was performed against the state of the repository at the commit referenced above. Any subsequent changes to the codebase may introduce new vulnerabilities not covered by this report. This report should not be taken as an endorsement of the security or correctness of the contracts.
