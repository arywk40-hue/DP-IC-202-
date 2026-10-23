"""Transactional, hash-linked audit events and domain-separated Merkle proofs.

Local integrity is not blockchain verification. Preserve independent receipts to
detect a privileged operator rewriting or truncating the whole local journal.
"""
from contextlib import closing
import hashlib
import json
import sqlite3


def canonical(value):
    """INDRA JSON v1: sorted UTF-8 keys, compact encoding, finite numbers only."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def initialize(db):
    db.execute("""CREATE TABLE IF NOT EXISTS audit_events (
        sequence INTEGER PRIMARY KEY, event_hash TEXT UNIQUE NOT NULL,
        body TEXT NOT NULL)""")


def append(db, kind, payload):
    """Append inside the caller's write transaction; rollback follows its owner."""
    initialize(db)
    row = db.execute("SELECT sequence,event_hash FROM audit_events ORDER BY sequence DESC LIMIT 1").fetchone()
    seq, previous = (row[0] + 1, row[1]) if row else (1, "0" * 64)
    body = dict(schema="indra_audit_json_v1", sequence=seq, previous=previous,
                kind=kind, payload=payload)
    h = digest(body)
    db.execute("INSERT INTO audit_events VALUES (?,?,?)", (seq, h, canonical(body).decode()))
    return h


def read_verified(path):
    """Verify a consistent read-only snapshot; raise on mutation/gaps/reordering."""
    from pathlib import Path
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)) as db:
        rows = db.execute("SELECT sequence,event_hash,body FROM audit_events ORDER BY sequence").fetchall()
    events, previous = [], "0" * 64
    for expected, (seq, h, raw) in enumerate(rows, 1):
        body = json.loads(raw)
        if (seq != expected or body.get("sequence") != seq or
                body.get("previous") != previous or digest(body) != h):
            raise ValueError("Audit integrity mismatch at sequence " + str(seq))
        events.append(dict(hash=h, event=body))
        previous = h
    return events


def merkle_root(hashes):
    """SHA-256(0x00 || event hash) leaves, 0x01 branches; duplicate odd tail."""
    if not hashes:
        raise ValueError("Cannot anchor an empty batch")
    level = [hashlib.sha256(b"\x00" + bytes.fromhex(h)).digest() for h in hashes]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [hashlib.sha256(b"\x01" + level[i] + level[i+1]).digest()
                 for i in range(0, len(level), 2)]
    return level[0].hex()


def batch(path):
    events = read_verified(path)
    manifest = dict(schema="indra_batch_v1", first=1, last=len(events),
                    count=len(events), root=merkle_root([e["hash"] for e in events]))
    return dict(manifest=manifest, batch_id=digest(manifest), events=events,
                status="LOCAL_ONLY")
