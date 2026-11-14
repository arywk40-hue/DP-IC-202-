# INDRA Blockchain Provenance & EVM Anchoring Report

**Date of Verification:** 5 November 2026  
**Environment:** Python 3.13 / Web3.py 7.16 / Ephemeral Local PyEVM / Solidity 0.8.20  
**Data Scope:** Real Mandi observation database (`ml/data/himachal/dashboard_e2e.sqlite`)  
**Contract Bytecode:** `contracts/build/IndraAnchor.json`  

---

## 1. Executive Summary

This report documents the verification of INDRA's cryptographic audit trail and distributed ledger anchoring architecture using real atmospheric observation events. The workflow verifies three distinct tiers of data integrity:
1. **Local Transactional Hash-Chaining:** SQLite-bound event journals ensuring monotonic sequence continuity ($H_i = \text{SHA-256}(\text{Body}_i)$ where $\text{Body}_i$ includes $H_{i-1}$).
2. **Domain-Separated Merkle Tree Aggregation:** Aggregating discrete observation events into cryptographic batch manifests with domain separation (`0x00` leaf prefix, `0x01` branch prefix).
3. **Smart Contract Anchoring on EVM Ledger:** Deploying the append-only [`IndraAnchor.sol`](../../contracts/IndraAnchor.sol) contract to a local EVM, executing batch root commitments, asserting on-chain state matches, and verifying security guards (unauthorized caller rejection and duplicate replay rejection).

---

## 2. Real Data Source & Cryptographic Batch Manifest

The audit trail was generated from real Mandi environmental observation telemetry stored in [`ml/data/himachal/dashboard_e2e.sqlite`](../../ml/data/himachal/dashboard_e2e.sqlite).

### Batch Manifest Details (`indra_batch_v1`):
- **Source Database:** `ml/data/himachal/dashboard_e2e.sqlite`
- **Total Audited Events:** 7 sequential observation transactions
- **Sequence Range:** 1 through 7 (no sequence gaps or reordering)
- **Domain-Separated Merkle Root:**  
  `6b06dfb866c46f653ae6dee762e18ffcb5f2ac0b5e387eb4fc9d106e5554fc30`
- **Batch Identifier (Manifest Digest):**  
  `a18e4bad4c9354fd2a71ca6ab930f2b50dc81a7ade1a54e04ca1d56b5e60af26`

### Canonical Event Hash Chain:
| Sequence | Previous Hash | Event Digest | Event Kind |
| :---: | :--- | :--- | :--- |
| **1** | `0000000000000000000000000000000000000000000000000000000000000000` | `39952aba8c93c807d5edfcc22c644c68a3972dad63cd41d3f90d7274ec1dd03c` | `DASHBOARD_SNAPSHOT` |
| **2** | `39952aba8c93c807d5edfcc22c644c68a3972dad63cd41d3f90d7274ec1dd03c` | `9202c524cc9ff165d93262354e39ea44d085f35c0865ed9b57912346e367c689` | `DASHBOARD_SNAPSHOT` |
| **3** | `9202c524cc9ff165d93262354e39ea44d085f35c0865ed9b57912346e367c689` | `ad79247eb1923e32b4f912239f6048d0a84594c7b8e515d9aa0e4cae783aa8cb` | `DASHBOARD_SNAPSHOT` |
| **4** | `ad79247eb1923e32b4f912239f6048d0a84594c7b8e515d9aa0e4cae783aa8cb` | `959223bb3ebfa2bb7245b08c9f53805eb5cb0aa177dbf8c49e7cf0b9f521b069` | `DASHBOARD_SNAPSHOT` |
| **5** | `959223bb3ebfa2bb7245b08c9f53805eb5cb0aa177dbf8c49e7cf0b9f521b069` | `5c21df6ff64177b94ad14f772714c330f6a27fe093bb1ee69888eb1a998064ae` | `DASHBOARD_SNAPSHOT` |
| **6** | `5c21df6ff64177b94ad14f772714c330f6a27fe093bb1ee69888eb1a998064ae` | `ebbb5c4c1a7d65b706c3a62886477145b23d9a34bc6e66e2c3c9c614beecdb58` | `DASHBOARD_SNAPSHOT` |
| **7** | `ebbb5c4c1a7d65b706c3a62886477145b23d9a34bc6e66e2c3c9c614beecdb58` | `2ceee1d5633bc930a3a411a7a01a3cf936f32e92c530fb1ff660e1d0f585d886` | `DASHBOARD_SNAPSHOT` |

---

## 3. Asymmetric Digital Signature Verification

Using the Ed25519 elliptic curve algorithm, the batch manifest was cryptographically signed:
- **Signer Public Key:**  
  `bf67eaa8c01891833085fb7fea684a0aa70595a3053038287db904a0257c3397`
- **Manifest Signature:**  
  Verified against external pinned public key; ensures that even if a local database administrator mutates past history, the modified manifest will fail signature verification.

---

## 4. On-Chain Smart Contract Execution

The Solidity smart contract [`IndraAnchor.sol`](../../contracts/IndraAnchor.sol) was deployed and executed against an ephemeral EVM testbed:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract IndraAnchor {
    address public immutable owner;
    mapping(bytes32 => bytes32) public roots;
    event Anchored(bytes32 indexed batchId, bytes32 root);
    constructor() { owner = msg.sender; }
    function anchor(bytes32 batchId, bytes32 root) external {
        require(msg.sender == owner, "Unauthorized");
        require(root != bytes32(0), "Empty root");
        require(roots[batchId] == bytes32(0), "Duplicate batch");
        roots[batchId] = root;
        emit Anchored(batchId, root);
    }
}
```

### Execution Verification Receipt:
- **Network:** `EPHEMERAL_LOCAL_PYEVM`
- **Chain ID:** `131277322940537`
- **Contract Address:** `0xF2E246BB76DF876Cef8b38ae84130F4F55De395b`
- **Anchor Transaction Hash:** `13b7ce7e67602784d6c0f3d3b1bbb1095589b8b8026753977a2e2051b993137d`
- **Transaction Gas Used:** 46,582 units
- **On-Chain Root Match:** **PASSED** (contract returned expected Merkle root `6b06dfb8...`)
- **Duplicate Batch Rejection (Replay Attack):** **PASSED** (re-submitting identical `batchId` reverted with `"Duplicate batch"`)
- **Unauthorized Caller Rejection:** **PASSED** (submission from non-owner account reverted with `"Unauthorized"`)
- **Zero Root Rejection:** **PASSED** (null root rejected with `"Empty root"`)

---

## 5. Instructions for Tomorrow's Testing

To reproduce and verify the blockchain provenance pipeline tomorrow:

### A. Run Automated Unit Tests (EVM Deployment & Rollback Checks):
```sh
.venv/bin/python -m pytest contracts/tests/test_provenance.py -v
```

### B. Export and Verify Real Batch Proof from Local Store:
```sh
# 1. Export signed proof from database
.venv/bin/python contracts/scripts/provenance.py export \
  --db ml/data/himachal/dashboard_e2e.sqlite \
  --output contracts/reports/provenance_real/batch_proof.json \
  --key contracts/reports/provenance_real/ed25519_key.raw

# 2. Verify proof content and signature against public key
.venv/bin/python contracts/scripts/provenance.py verify \
  --proof contracts/reports/provenance_real/batch_proof.json \
  --trusted-key bf67eaa8c01891833085fb7fea684a0aa70595a3053038287db904a0257c3397

# 3. Execute local EVM contract anchor verification
.venv/bin/python contracts/scripts/provenance.py evm-test \
  --proof contracts/reports/provenance_real/batch_proof.json \
  --trusted-key bf67eaa8c01891833085fb7fea684a0aa70595a3053038287db904a0257c3397
```

### C. Live Dashboard Verification:
In the web dashboard (`http://127.0.0.1:8080/#system`), open the **Data audit trail** panel under *Data & model information* to observe the live local batch fingerprint and transaction counts.

