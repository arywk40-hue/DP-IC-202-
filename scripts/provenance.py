"""Export signed audit evidence or exercise the anchor contract on a local EVM."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ml.provenance import batch, canonical, digest, merkle_root


def export(db, output, key_path):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if not key_path.exists():
        key = Ed25519PrivateKey.generate().private_bytes_raw()
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(key)
    key = Ed25519PrivateKey.from_private_bytes(key_path.read_bytes())
    proof = batch(db)
    proof['public_key'] = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    proof['signature'] = key.sign(canonical(proof['manifest'])).hex()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2) + '\n')
    return proof


def verify(proof, trusted_key):
    """Verify against an externally pinned signer, not an embedded trust claim."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    if proof['public_key'] != trusted_key:
        raise ValueError('Untrusted signer')
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(trusted_key)).verify(
        bytes.fromhex(proof['signature']), canonical(proof['manifest']))
    events = proof['events']
    previous = '0' * 64
    for seq, item in enumerate(events, 1):
        body = item['event']
        if (body['sequence'] != seq or body['previous'] != previous or
                digest(body) != item['hash']):
            raise ValueError('Event mismatch')
        previous = item['hash']
    expected = dict(schema='indra_batch_v1', first=1, last=len(events),
                    count=len(events), root=merkle_root([e['hash'] for e in events]))
    if expected != proof['manifest'] or digest(expected) != proof['batch_id']:
        raise ValueError('Manifest mismatch')
    return True


def evm_test(proof):
    """Deploy actual Solidity bytecode on ephemeral PyEVM; no production claims."""
    from web3 import Web3, EthereumTesterProvider
    from eth_tester.exceptions import TransactionFailed
    artifact = json.loads((Path(__file__).resolve().parents[1] / 'contracts/build/IndraAnchor.json').read_text())
    w3 = Web3(EthereumTesterProvider())
    owner, other = w3.eth.accounts[:2]
    factory = w3.eth.contract(abi=artifact['abi'], bytecode=artifact['bin'])
    deployment = w3.eth.wait_for_transaction_receipt(factory.constructor().transact({'from': owner}))
    contract = w3.eth.contract(address=deployment.contractAddress, abi=artifact['abi'])
    bid, root = bytes.fromhex(proof['batch_id']), bytes.fromhex(proof['manifest']['root'])
    receipt = w3.eth.wait_for_transaction_receipt(contract.functions.anchor(bid, root).transact({'from': owner}))
    assert receipt.status == 1 and contract.functions.roots(bid).call() == root
    for who, ident in [(owner, bid), (other, b'\x01' * 32)]:
        try:
            contract.functions.anchor(ident, root).transact({'from': who})
        except TransactionFailed:
            continue
        raise AssertionError('Duplicate/unauthorized anchor accepted')
    return dict(network='EPHEMERAL_LOCAL_PYEVM', chain_id=w3.eth.chain_id,
                contract=contract.address, transaction=receipt.transactionHash.hex(),
                gas_used=receipt.gasUsed, root_matches=True,
                duplicate_rejected=True, unauthorized_rejected=True,
                independently_witnessed=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    e = sub.add_parser('export')
    e.add_argument('--db', type=Path, required=True)
    e.add_argument('--output', type=Path, required=True)
    e.add_argument('--key', type=Path, required=True)
    v = sub.add_parser('verify')
    v.add_argument('--proof', type=Path, required=True)
    v.add_argument('--trusted-key', required=True)
    t = sub.add_parser('evm-test')
    t.add_argument('--proof', type=Path, required=True)
    t.add_argument('--trusted-key', required=True)
    args = p.parse_args()
    if args.command == 'export':
        proof = export(args.db, args.output, args.key)
        print(json.dumps(dict(status='LOCAL_ONLY', public_key=proof['public_key'], batch_id=proof['batch_id'])))
    else:
        proof = json.loads(args.proof.read_text())
        verify(proof, args.trusted_key)
        print(json.dumps(evm_test(proof) if args.command == 'evm-test' else dict(status='SIGNATURE_AND_CONTENT_VERIFIED', on_chain_verified=False)))


if __name__ == '__main__':
    main()
