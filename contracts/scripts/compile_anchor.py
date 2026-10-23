"""Compile pinned Solidity source; explicitly run once before EVM tests."""
import json
import os
from pathlib import Path
import solcx
ROOT = Path(__file__).resolve().parents[2]
cache = ROOT/'contracts/.cache/solc'
cache.mkdir(parents=True, exist_ok=True)
os.environ['SOLCX_BINARY_PATH'] = str(cache)
solcx.install_solc('0.8.24', solcx_binary_path=cache)
solcx.set_solc_version('0.8.24', solcx_binary_path=cache)
result = solcx.compile_source((ROOT/'contracts/IndraAnchor.sol').read_text(),
                             output_values=['abi', 'bin'])
artifact = result['<stdin>:IndraAnchor']
artifact['compiler'] = '0.8.24'
import hashlib
artifact['source_sha256'] = hashlib.sha256((ROOT/'contracts/IndraAnchor.sol').read_bytes()).hexdigest()
(ROOT/'contracts/build').mkdir(exist_ok=True)
(ROOT/'contracts/build/IndraAnchor.json').write_text(json.dumps(artifact, indent=2)+'\n')
