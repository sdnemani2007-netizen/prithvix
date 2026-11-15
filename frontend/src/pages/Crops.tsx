import { useAsync } from '../hooks/useAsync';
import { getCrops } from '../services/api';
import { Load } from '../components/ui';
import { ZONE_NAMES } from '../utils/zone';
import type { Farm } from '../types';

export default function Crops({ farm }: { farm: Farm }) {
    const c = useAsync(() => getCrops(farm), [farm]);
    const zoneName = ZONE_NAMES[farm.z] || 'Unclassified';

    return (
        <>
                <div className="info-note" style={{ background: '#eef6ec', borderColor: '#bcd8b6', color: '#2a5a22' }}>
                    Recommendations calculated from farm profile, soil characteristics, and NASA agroclimatology.
                </div>
            <h1>Crop recommendations · {farm.name}</h1>
            <p className="src">
                Climate zone: {zoneName}.
                Scoring incorporates soil type, water source, and satellite meteorological demand.
            </p>
            <div className="panel">
                <Load s={c}>
                    {list => (
                        <div className="scroll">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Crop</th>
                                        <th>Suitability</th>
                                        <th>Water need</th>
                                        <th>Why</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {list.map(x => (
                                        <tr key={x.n}>
                                            <td><b>{x.n}</b></td>
                                            <td>
                                                <div className="bar" style={{ width: 120 }}>
                                                    <i style={{ width: `${x.sc}%` }} />
                                                </div>
                                                {x.sc}
                                            </td>
                                            <td>{x.w}</td>
                                            <td>
                                                {x.why}
                                                {x.supporting_observations && x.supporting_observations.length > 0 && (
                                                    <div style={{ fontSize: '0.8rem', color: '#4a6042', marginTop: 4 }}>
                                                        {x.supporting_observations.slice(0, 2).join(' • ')}
                                                    </div>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </Load>
            </div>
        </>
    );
}
