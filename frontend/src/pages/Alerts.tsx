import { useState } from 'react';
import { useAsync } from '../hooks/useAsync';
import { getAlerts } from '../services/api';
import { Load } from '../components/ui';
import type { Farm } from '../types';

const F: [string, string][] = [
    ['all', 'All'],
    ['c', 'Critical'],
    ['w', 'Warning'],
    ['i', 'Info'],
    ['n', 'Normal']
];

export default function Alerts({ farm }: { farm: Farm }) {
    const al = useAsync(() => getAlerts(farm), [farm]);
    const [f, setF] = useState('all');

    return (
        <>
            <h1>Alerts &amp; advice · {farm.name}</h1>
            <p className="src">
                Continuous satellite telemetry screening for moisture stress, anomalous precipitation, and thermal shocks.
            </p>
            <div className="chips" style={{ marginTop: 10 }}>
                {F.map(([k, l]) => (
                    <button
                        key={k}
                        className={k === f ? 'on' : ''}
                        onClick={() => setF(k)}
                    >
                        {l}
                    </button>
                ))}
            </div>
            <Load s={al}>
                {list => {
                    const v = list.filter(a => f === 'all' || a.s === f);
                    return v.length ? (
                        v.map(a => (
                            <div key={a.t + a.d} className={'act ' + a.s} style={{ marginBottom: 12 }}>
                                <b>{a.t}: {a.x}</b>
                                <div style={{ marginTop: 4 }}>{a.a}</div>
                                <small style={{ display: 'block', marginTop: 4, color: '#666' }}>
                                    {a.d} · Sector {a.p} {a.source ? `· Feed: ${a.source}` : ''}
                                </small>
                            </div>
                        ))
                    ) : (
                        <p className="src">No alerts in this category.</p>
                    );
                }}
            </Load>
        </>
    );
}
