"""Anchor signed batches to an explicitly configured local EVM RPC.

Requires an unlocked local development account. Refuses remote RPCs. Run with
--once for one batch, or omit it for a retrying 60-second gateway worker.
"""
import argparse
import json
import logging
from pathlib import Path
import sys
import time
from urllib.parse import urlparse
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from contracts.scripts.provenance import export, verify


def anchor(w3, contract, sender, proof):
    """Idempotently anchor a batch, then read its committed root back."""
    bid = bytes.fromhex(proof['batch_id'])
    root = bytes.fromhex(proof['manifest']['root'])
    existing = contract.functions.roots(bid).call()
    tx = None
    if existing == bytes(32):
        tx = w3.eth.wait_for_transaction_receipt(
            contract.functions.anchor(bid, root).transact({'from': sender}), timeout=120)
        if tx.status != 1:
            raise ValueError('Anchor transaction failed')
    if contract.functions.roots(bid).call() != root:
        raise ValueError('On-chain root mismatch')
    return dict(status='LOCAL_EVM_ROOT_MATCH', batch_id=proof['batch_id'],
                root=proof['manifest']['root'], chain_id=w3.eth.chain_id,
                contract=contract.address,
                transaction=tx.transactionHash.hex() if tx else None,
                independently_witnessed=False)


def main():
    from web3 import Web3
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rpc', default='http://127.0.0.1:8545')
    p.add_argument('--contract')
    p.add_argument('--deploy', action='store_true', help='Deploy once to the local RPC before anchoring')
    p.add_argument('--account', required=True)
    p.add_argument('--db', type=Path, required=True)
    p.add_argument('--key', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--once', action='store_true')
    args = p.parse_args()
    parsed = urlparse(args.rpc)
    if parsed.scheme != 'http' or parsed.hostname not in {'localhost', '127.0.0.1', '::1'}:
        p.error('Only explicit loopback development RPC is supported')
    if bool(args.contract) == bool(args.deploy):
        p.error('Choose exactly one of --contract or --deploy')
    artifact = json.loads((Path(__file__).resolve().parents[2]/'contracts/build/IndraAnchor.json').read_text())
    w3 = Web3(Web3.HTTPProvider(args.rpc, request_kwargs={'timeout': 10}))
    if args.deploy:
        factory = w3.eth.contract(abi=artifact['abi'], bytecode=artifact['bin'])
        deployed = w3.eth.wait_for_transaction_receipt(factory.constructor().transact({'from':args.account}), timeout=120)
        if deployed.status != 1:
            raise ValueError('Contract deployment failed')
        args.contract = deployed.contractAddress
        print(json.dumps(dict(deployed_contract=args.contract, chain_id=w3.eth.chain_id)), flush=True)
    contract = w3.eth.contract(address=Web3.to_checksum_address(args.contract), abi=artifact['abi'])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            proof = export(args.db, args.output_dir/'latest.json', args.key)
            verify(proof, proof['public_key'])
            result = anchor(w3, contract, args.account, proof)
            # One persistent signed proof per batch; latest may change on next poll.
            (args.output_dir/(proof['batch_id']+'.json')).write_text(json.dumps(dict(proof=proof, receipt=result), indent=2)+'\n')
            print(json.dumps(result), flush=True)
        except Exception:
            logging.exception('Anchoring failed; audit journal retained for retry')
            if args.once:
                raise
        if args.once:
            return
        time.sleep(60)


if __name__ == '__main__':
    main()
