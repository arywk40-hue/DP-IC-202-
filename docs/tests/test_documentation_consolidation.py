"""Documentation moves preserve evidence and leave two active Markdown files."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def test_original_bytes_and_model_document_checksums_preserved():
    migration = json.loads((ROOT/'docs/documentation_consolidation.json').read_text())
    source = ROOT/migration['original_archive']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == migration['archive_sha256']
    handbook = (ROOT/migration['destination']).read_text()
    with zipfile.ZipFile(source) as archive:
        for path in archive.namelist():
            assert path.endswith('.md') and not (ROOT/path).exists()
            assert f'id="{migration["sources"][path]}"' in handbook
        for name in ['ml/configs/committed_exports_v1.json','docs/plans/PROTECTED_PATHS.json']:
            manifest=json.loads((ROOT/name).read_text())
            for original, digest in manifest['documentation_migration']['original_files'].items():
                assert hashlib.sha256(archive.read(original)).hexdigest()==digest


def test_only_two_active_markdown_files_and_internal_section_links_resolve():
    paths=subprocess.check_output(['git','ls-files','*.md'],cwd=ROOT,text=True).splitlines()
    moves=json.loads((ROOT/'docs/repository_reorganization.json').read_text())['tracked_file_moves']
    active={moves.get(p,p) for p in paths if (ROOT/moves.get(p,p)).is_file()}
    assert active == {'README.md','docs/EVERYTHING.md'}
    text=(ROOT/'docs/EVERYTHING.md').read_text()
    ids=set(re.findall(r'<a id="([^"]+)"',text))
    refs=re.findall(r'\]\(#(source-[a-f0-9]+)\)',text)
    assert set(refs) <= ids
