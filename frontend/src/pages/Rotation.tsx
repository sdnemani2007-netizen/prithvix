import { useState, useEffect } from 'react';
import { useAsync } from '../hooks/useAsync';
import { getRotation } from '../services/api';
import { Load } from '../components/ui';
import type { Farm } from '../types';

const cls = (c: string) =>
    /Chick|Soy|Pulse|Pea|Bean|Lentil|Cowpea/i.test(c)
        ? 'leg'
        : /Ground|Canola|Sunflower|Mustard/i.test(c)
        ? 'oil'
        : 'cer';

export default function Rotation({ farm }: { farm: Farm }) {
    const r = useAsync(() => getRotation(farm), [farm]);
    const [sel, setSel] = useState<string>('');

    return (
        <>
                <div className="info-note" style={{ background: '#eef6ec', borderColor: '#bcd8b6', color: '#2a5a22' }}>
                    Agro-ecological rotation schedules designed to disrupt pest reservoirs and balance soil nutrients.
                </div>
            <h1>Crop rotation · {farm.name}</h1>
            <Load s={r}>
                {plans => {
                    const keys = Object.keys(plans);
                    const activeKey = sel && plans[sel] ? sel : (keys[0] || 'Current plan');
                    const p = plans[activeKey];
                    if (!p) return <p>No rotation plan available.</p>;

                    return (
                        <>
                            <div className="chips">
                                {keys.map(k => (
                                    <button
                                        key={k}
                                        className={k === activeKey ? 'on' : ''}
                                        onClick={() => setSel(k)}
                                    >
                                        {k}
                                    </button>
                                ))}
                            </div>
                            <div className="panel">
                                <div className="tl">
                                    <div className="h" />
                                    {[1, 2, 3, 4].map(i => (
                                        <div key={i} className="h">Season {i}</div>
                                    ))}
                                    {(['A', 'B'] as const).map(id => [
                                        <div key={id} className="h">Plot {id}</div>,
                                        ...(p[id] || []).map((c, i) => (
                                            <div key={id + i} className={cls(c)}>
                                                {c}
                                            </div>
                                        ))
                                    ])}
                                </div>
                                <p><b>{activeKey}:</b> {p.note}</p>
                                <p className="src">Green: legume/pulse · Dark: cereal · Gold: oilseed</p>
                            </div>
                        </>
                    );
                }}
            </Load>
        </>
    );
}
