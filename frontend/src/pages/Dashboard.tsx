
import { useAsync } from '../hooks/useAsync';
import { getPlots, getAlerts, getSeries } from '../services/api';
import { MapPin, UserRound } from 'lucide-react';
import { Load, Gauge } from '../components/ui';
import Trend from '../components/Trend';
import { T, A } from '../utils/units';
import type { Farm, Units } from '../types';
import { useEffect, useState } from 'react';

// ==========================================
// FARM PROFILE LOCATION
// ==========================================

const PROFILE_KEY = 'prithvix.profile.v1';

function getSavedFarmLocation(): string {

    try {

        const profile = JSON.parse(
            localStorage.getItem(PROFILE_KEY) || '{}'
        );

        return (
            profile.farmLocation?.trim() ||
            profile.farmName?.trim() ||
            ''
        );

    } catch {

        return '';

    }
}


// ==========================================
// DASHBOARD COMPONENT
// ==========================================

export default function Dashboard({
    farm,
    units,
    onSetupFarm
}: {
    farm: Farm;
    units: Units;
    onSetupFarm: () => void;
}) {

    // ======================================
    // LOCATION STATE
    // ======================================

    const [farmLocation, setFarmLocation] = useState(
        () => getSavedFarmLocation()
    );

    // Listen for Farmer Hub profile changes

    useEffect(() => {

        const updateLocation = () => {

            setFarmLocation(getSavedFarmLocation());

        };

        window.addEventListener(
            'prithvix-profile-updated',
            updateLocation
        );

        return () => {

            window.removeEventListener(
                'prithvix-profile-updated',
                updateLocation
            );

        };

    }, []);


    // Location displayed on Dashboard

    const displayedLocation =
        farmLocation ||
        (farm.key === 'custom' ? farm.location : '') ||
        '';


    // ======================================
    // FETCH DASHBOARD DATA
    // ======================================

    const pl = useAsync(
        () => getPlots(farm),
        [farm]
    );

    const al = useAsync(
        () => getAlerts(farm),
        [farm]
    );

    const se = useAsync(
        () => getSeries(farm),
        [farm]
    );


    // ======================================
    // DASHBOARD UI
    // ======================================

    return (
        <>

            {/* WELCOME BANNER */}

            <div className="welcome-banner">

                <div className="welcome-content">

                    <div className="location-status">

                        <MapPin size={16} />

                        <span>
                            {displayedLocation
                                ? `Location: ${displayedLocation}`
                                : 'Location: Not Configured'}
                        </span>

                    </div>


                    <h1>Welcome to PrithviX</h1>

                    <p>
                        Complete your farm profile to unlock live satellite
                        intelligence answering what is happening on your
                        land and what to do next.
                    </p>

                </div>


                <button
                    className="setup-farm-btn"
                    onClick={onSetupFarm}
                >

                    <UserRound size={19} />

                    Setup Farm Profile

                </button>

            </div>




            {/* RECOMMENDED ACTIONS AND CONDITIONS */}

            <h1>What to do today</h1>


            <div className="cols" style={{ marginTop: 10 }}>


                {/* RECOMMENDED ACTIONS */}

                <div className="panel">

                    <h2>Recommended actions</h2>

                    <Load s={al}>

                        {a => a
                            .filter(x => x.s !== 'n')
                            .map(x => (

                                <div
                                    key={x.t}
                                    className={'act ' + x.s}
                                >

                                    <b>{x.a}</b>

                                    <small>
                                        {x.t} · Plot {x.p}
                                    </small>

                                </div>

                            ))}

                    </Load>

                </div>



                {/* FARM CONDITIONS */}

                <div className="panel">

                    <Load s={pl}>

                        {plots => {

                            const p = plots[0];

                            if (!p) {
                                return <p>No plot data available.</p>;
                            }

                            return (

                                <>

                                    <h2>
                                        Conditions ({p.name})
                                    </h2>


                                    <Gauge
                                        l="Soil moisture"
                                        v={p.moist ?? 0}
                                        t={p.moist != null ? `${Math.round(p.moist * 100)}%` : '--'}
                                        src="SMAP"
                                    />


                                    <Gauge
                                        l="Vegetation"
                                        v={p.ndvi ?? 0}
                                        t={p.ndvi != null ? `NDVI ${p.ndvi}` : '--'}
                                        src="Landsat"
                                    />


                                    <Gauge
                                        l="Water available"
                                        v={(p.moist ?? 0) * 2}
                                        t={p.moist == null ? '--' : p.moist < .2 ? 'Low' : 'Adequate'}
                                        src="GPM / POWER"
                                    />


                                    <div className="gauge">

                                        <span>Surface temp</span>

                                        <b>
                                            {p.lst != null ? T(p.lst, units) : '--'}
                                        </b>

                                        <span className="src">
                                            ECOSTRESS
                                        </span>

                                    </div>

                                </>

                            );

                        }}

                    </Load>

                </div>

            </div>



            {/* PLOTS TABLE */}

            <div className="panel">

                <h2>Plots</h2>

                <Load s={pl}>

                    {plots => (

                        <div className="scroll">

                            <table>

                                <thead>

                                    <tr>
                                        <th>Plot</th>
                                        <th>Area</th>
                                        <th>Crop</th>
                                        <th>Moisture</th>
                                        <th>NDVI</th>
                                        <th>Status</th>
                                    </tr>

                                </thead>


                                <tbody>

                                    {plots.map(x => (

                                        <tr key={x.id}>

                                            <td>{x.name}</td>

                                            <td>
                                                {A(x.ha, units)}
                                            </td>

                                            <td>{x.crop}</td>

                                            <td>
                                                {x.moist != null ? `${Math.round(x.moist * 100)}%` : '--'}
                                            </td>

                                            <td>{x.ndvi ?? '--'}</td>

                                            <td>
                                                {x.status || '--'}
                                            </td>

                                        </tr>

                                    ))}

                                </tbody>

                            </table>

                        </div>

                    )}

                </Load>

            </div>



            {/* SATELLITE DATA COVERAGE */}

            <p className="src">

                Coverage: SMAP is coarse (about 9 km) with a revisit
                of 2 to 3 days. ECOSTRESS passes are irregular and may
                skip a location. Landsat repeats every 16 days and is
                cloud-limited. Gaps will be shown as gaps.

            </p>

        </>
    );

}
