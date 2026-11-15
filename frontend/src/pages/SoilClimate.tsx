import { useAsync } from '../hooks/useAsync';
import { getSeries } from '../services/api';
import { Load } from '../components/ui';
import Trend from '../components/Trend';
import { R, Tn } from '../utils/units';
import type { Farm, Units } from '../types';

export default function SoilClimate({ farm, units }: { farm: Farm; units: Units }) {
    const se = useAsync(() => getSeries(farm), [farm]);

    return (
        <>
                <div className="info-note" style={{ background: '#eef6ec', borderColor: '#bcd8b6', color: '#2a5a22' }}>
                    Historical NASA Earth observation trends aggregated for {farm.name} ({farm.location}).
                </div>
            <h1>Soil &amp; climate · {farm.name}</h1>
            <p className="src">
                Multi-sensor satellite monitoring: SMAP (soil moisture), Landsat/ECOSTRESS (surface temperature), GPM/POWER (precipitation), and Landsat/MODIS (vegetation index).
            </p>
            <Load s={se}>
                {s => (
                    <div className="cols" style={{ marginTop: 10 }}>
                        <div className="panel">
                            <h2>Soil moisture</h2>
                            <Trend labels={s.periods} data={s.moist.map(v => v == null ? null : Math.round(v * 100))} unit="%" />
                            <small className="src">Source: NASA SMAP L4 (9 km assimilation)</small>
                        </div>
                        <div className="panel">
                            <h2>Land surface temperature</h2>
                            <Trend labels={s.periods} data={s.lst.map(v => v == null ? null : Tn(v, units))} unit={units === 'm' ? ' °C' : ' °F'} color="#9A7B3A" />
                            <small className="src">Source: Landsat 8/9 ST_B10 / NASA POWER</small>
                        </div>
                        <div className="panel">
                            <h2>Rainfall per month</h2>
                            <Trend labels={s.periods} data={s.rain.map(v => v == null ? null : R(v, units))} unit={units === 'm' ? ' mm' : ' in'} bar color="#3C6E8F" />
                            <small className="src">Source: NASA GPM IMERG V07 / NASA POWER</small>
                        </div>
                        <div className="panel">
                            <h2>Vegetation (NDVI)</h2>
                            <Trend labels={s.periods} data={s.ndvi} color="#1F3D2B" />
                            <small className="src">Source: Landsat 8/9 Level 2 / MODIS MOD13Q1</small>
                        </div>
                    </div>
                )}
            </Load>
        </>
    );
}
