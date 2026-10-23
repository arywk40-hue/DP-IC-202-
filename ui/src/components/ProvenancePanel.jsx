import React, { useEffect, useState } from 'react';
import { getProvenance } from '../api/client';

export default function ProvenancePanel() {
  const [proof, setProof] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    let active = true;
    const refresh = async () => {
      try {
        const result = await getProvenance();
        if (active) { setProof(result); setError(null); }
      } catch { if (active) { setProof(null); setError('Audit evidence unavailable.'); } }
    };
    refresh();
    const timer = setInterval(refresh, 30000);
    return () => { active = false; clearInterval(timer); };
  }, []);
  return <section className="system-intro" aria-label="Data audit trail">
    <h2>Data audit trail</h2>
    {error ? <p role="status">{error}</p> : proof ? <>
      <p>{proof.count} recorded events · Local audit trail</p>
      <p>Records can be exported for signature and content verification. No external blockchain confirmation is connected to this dashboard.</p>
      <details><summary>Batch fingerprint</summary><code style={{overflowWrap:'anywhere'}}>{proof.batch_id}</code></details>
    </> : <p>Checking audit records…</p>}
  </section>;
}
