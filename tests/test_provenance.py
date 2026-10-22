"""Mutation, transaction, restart, signed evidence and real local EVM checks."""
import copy
import json
import sqlite3
import pytest
from ml.provenance import append, batch, read_verified
from scripts.provenance import export, verify, evm_test


def journal(path):
    with sqlite3.connect(path) as db:
        for i in range(3):
            append(db, 'TEST', {'value': i})
    db.close()


def test_mutation_and_rollback(tmp_path):
    path = tmp_path/'audit.sqlite'
    journal(path)
    assert batch(path)['manifest']['count'] == 3
    with pytest.raises(RuntimeError):
        with sqlite3.connect(path) as db:
            append(db, 'ROLLBACK', {})
            raise RuntimeError()
    assert len(read_verified(path)) == 3
    with sqlite3.connect(path) as db:
        db.execute("UPDATE audit_events SET body='{}' WHERE sequence=2")
    with pytest.raises(ValueError, match='mismatch'):
        read_verified(path)


def test_signature_and_truncated_export(tmp_path):
    pytest.importorskip('cryptography')
    path = tmp_path/'audit.sqlite'
    journal(path)
    proof = export(path, tmp_path/'proof.json', tmp_path/'key')
    assert verify(proof, proof['public_key'])
    with pytest.raises(ValueError, match='Untrusted'):
        verify(proof, 'ff'*32)
    altered = copy.deepcopy(proof)
    altered['events'].pop()
    with pytest.raises(ValueError):
        verify(altered, proof['public_key'])
    altered = copy.deepcopy(proof)
    altered['events'][0]['event']['payload']['value'] = 100
    with pytest.raises(ValueError):
        verify(altered, proof['public_key'])


def test_evm_contract(tmp_path):
    pytest.importorskip('web3')
    from pathlib import Path
    if not Path('contracts/build/IndraAnchor.json').exists():
        pytest.skip('Run scripts/compile_anchor.py first')
    path = tmp_path/'audit.sqlite'
    journal(path)
    result = evm_test(batch(path))
    assert result['root_matches'] and result['duplicate_rejected'] and result['unauthorized_rejected']


def test_worker_retries_existing_commitment(tmp_path):
    pytest.importorskip('web3')
    from pathlib import Path
    from web3 import Web3, EthereumTesterProvider
    from scripts.anchor_worker import anchor
    artifact_path = Path('contracts/build/IndraAnchor.json')
    if not artifact_path.exists():
        pytest.skip('Compile contract first')
    artifact = json.loads(artifact_path.read_text())
    w3 = Web3(EthereumTesterProvider())
    owner = w3.eth.accounts[0]
    factory = w3.eth.contract(abi=artifact['abi'], bytecode=artifact['bin'])
    receipt = w3.eth.wait_for_transaction_receipt(factory.constructor().transact({'from':owner}))
    contract = w3.eth.contract(address=receipt.contractAddress, abi=artifact['abi'])
    path = tmp_path/'audit.sqlite'
    journal(path)
    proof = batch(path)
    assert anchor(w3,contract,owner,proof)['transaction']
    assert anchor(w3,contract,owner,proof)['transaction'] is None
