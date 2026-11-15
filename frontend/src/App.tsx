import { useEffect, useState } from 'react';
import {
    LayoutDashboard,
    MapPin,
    CloudSun,
    Sprout,
    Repeat,
    Bell,
    User,
    Bot
} from 'lucide-react';

import type { Farm, Units } from './types';
import { fetchFarms, updateBackendFarm } from './services/api';

import PrithviXAI from './pages/PrithviXAI';
import Dashboard from './pages/Dashboard';
import MyFarm from './pages/MyFarm';
import SoilClimate from './pages/SoilClimate';
import Crops from './pages/Crops';
import Rotation from './pages/Rotation';
import Alerts from './pages/Alerts';
import FarmerHub from './pages/FarmerHub';

const NAV = [
    ['dash', 'Dashboard', LayoutDashboard],
    ['farm', 'My Farm', MapPin],
    ['soil', 'Soil & Climate', CloudSun],
    ['crops', 'Crop Recommendations', Sprout],
    ['rot', 'Crop Rotation', Repeat],
    ['alerts', 'Alerts & Advice', Bell],
    ['ai', 'PrithviX AI', Bot],
    ['hub', 'Farmer Hub', User]
] as const;

const ACTIVE_FARM_KEY = 'prithvix.activeFarm';
const PROFILE_KEY = 'prithvix.profile.v1';

function profileFromFarm(f: Farm) {
    return {
        farmerName: f.farmer_name || '',
        farmName: f.name,
        farmLocation: f.location || '',
        farmArea: String(f.area || ''),
        areaUnit: f.area_unit || 'Acres',
        currentCrop: f.current_crop || '',
        soilType: f.soil_type || 'Unknown',
        waterSource: f.water_source || 'Unknown',
        irrigation: f.irrigation_method || 'Unknown',
        primaryGoal: f.primary_goal || 'Increase Crop Yield & Quality',
        id: f.id
    };
}

export default function App() {
    const [page, setPage] = useState('dash');
    const [farms, setFarms] = useState<Farm[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState('');
    const [key, setKey] = useState<string>(() => {
        return localStorage.getItem(ACTIVE_FARM_KEY) || '';
    });

    const [units, setUnits] = useState<Units>('m');
    const [profile, setProfile] = useState(() => {
        try {
            return JSON.parse(localStorage.getItem('prithvix.profile.v1') || '{}');
        } catch {
            return {};
        }
    });

    // 1. On mount: the backend database is the single source of truth for farms
    useEffect(() => {
        fetchFarms().then(backendFarms => {
            setFarms(backendFarms);
            if (backendFarms.length > 0) {
                const saved = localStorage.getItem(ACTIVE_FARM_KEY) || '';
                const active = backendFarms.find(f => f.key === saved || f.id === saved) ?? backendFarms[0];
                setKey(active.key);
                const p = profileFromFarm(active);
                setProfile(p);
                localStorage.setItem(PROFILE_KEY, JSON.stringify(p));
            } else {
                // Nothing stored on the server: start from a clean state
                setKey('');
                setProfile({});
                localStorage.removeItem(PROFILE_KEY);
                localStorage.removeItem(ACTIVE_FARM_KEY);
            }
            setLoadError('');
        }).catch(err => {
            console.warn('Backend fetch failed on start:', err);
            setLoadError(err instanceof Error ? err.message : 'Cannot reach the PrithviX backend.');
        }).finally(() => setLoading(false));
    }, []);

    // 2. (farm list is no longer cached locally)

    // 3. Remember selected farm
    useEffect(() => {
        if (key) localStorage.setItem(ACTIVE_FARM_KEY, key);
    }, [key]);

    // 4. Synchronize profile updates from FarmerHub
    useEffect(() => {
        const updateProfile = (event: Event) => {
            try {
                const savedProfile = JSON.parse(
                    localStorage.getItem('prithvix.profile.v1') || '{}'
                );
                setProfile(savedProfile);

                const customEvt = event as CustomEvent<Farm>;
                if (customEvt.detail && customEvt.detail.key) {
                    const newFarm = customEvt.detail;
                    setFarms(current => {
                        const filtered = current.filter(f => f.key !== newFarm.key && f.id !== newFarm.id);
                        return [newFarm, ...filtered];
                    });
                    setKey(newFarm.key);
                } else {
                    fetchFarms().then(bf => setFarms(bf)).catch(() => {});
                }
            } catch {
                setProfile({});
            }
        };

        window.addEventListener('prithvix-profile-updated', updateProfile);
        return () => window.removeEventListener('prithvix-profile-updated', updateProfile);
    }, []);

    const farm: Farm | undefined = farms.find(f => f.key === key || f.id === key) ?? farms[0];

    // Called when user selects a location on the map in My Farm
    const locate = (
        lat: number,
        lng: number,
        locationName?: string
    ) => {
        if (!farm?.id) return;
        const selectedLocation = locationName || 'Custom location';

        updateBackendFarm(farm.id, {
            location: selectedLocation,
            latitude: lat,
            longitude: lng
        }).then(updated => {
            setFarms(current => current.map(f => f.id === updated.id ? updated : f));
        }).catch(err => console.warn('Could not update backend coordinates:', err));

        try {
            const savedProfile = JSON.parse(
                localStorage.getItem('prithvix.profile.v1') || '{}'
            );
            const updatedProfile = {
                ...savedProfile,
                farmLocation: selectedLocation
            };
            localStorage.setItem('prithvix.profile.v1', JSON.stringify(updatedProfile));
            setProfile(updatedProfile);
            window.dispatchEvent(new Event('prithvix-profile-updated'));
        } catch (error) {
            console.error('Could not update farm location:', error);
        }
    };

    return (
        <div className="app">
            <nav>
                <div className="logo">
                    <img
                        src="/prithviX-logo.png"
                        alt="PrithviX Logo"
                        className="brand-logo"
                    />
                    <span>PrithviX</span>
                </div>

                {NAV.map(([id, label, Icon]) => (
                    <button
                        key={id}
                        className={id === page ? 'on' : ''}
                        onClick={() => setPage(id)}
                    >
                        <Icon size={16} />
                        {label}
                    </button>
                ))}

                {/* Active Farm Profile Card: Shown ONLY when farm profile is configured */}
                {profile.farmLocation?.trim() && (
                    <div className="active-farm-card">
                        <div className="active-farm-header">
                            <span>Active Farm Profile</span>
                            <span className="active-farm-dot"></span>
                        </div>

                        <h4>{profile.farmLocation}</h4>

                        <p>
                            {profile.farmArea || ''}
                            {profile.farmArea && profile.areaUnit
                                ? ` ${profile.areaUnit}`
                                : ''}
                            {profile.currentCrop
                                ? ` • ${profile.currentCrop}`
                                : ''}
                        </p>
                    </div>
                )}
            </nav>

            <main>
                <header>
                    <select
                        value={farm?.key ?? ''}
                        onChange={e => setKey(e.target.value)}
                        aria-label="Select farm"
                    >
                        {farms.map(f => (
                            <option key={f.key} value={f.key}>
                                {f.name}
                            </option>
                        ))}
                    </select>

                    <select
                        style={{ marginLeft: 'auto' }}
                        value={units}
                        onChange={e => setUnits(e.target.value as Units)}
                        aria-label="Measurement units"
                    >
                        <option value="m">Metric</option>
                        <option value="i">Imperial</option>
                    </select>
                </header>

                <div className="pg">
                    {loading && <p className="src">Loading your farms…</p>}
                    {!loading && loadError && (
                        <div className="act c">
                            <b>Could not reach the PrithviX backend</b>
                            <small>{loadError} Start the backend and reload this page.</small>
                        </div>
                    )}
                    {!loading && !loadError && !farm && (
                        <p className="src">No farm yet. Enter your farm details below to get started.</p>
                    )}
                    {farm && page === 'dash' && (
                        <Dashboard
                            farm={farm}
                            units={units}
                            onSetupFarm={() => setPage('hub')}
                        />
                    )}

                    {farm && page === 'farm' && (
                        <MyFarm
                            farm={farm}
                            units={units}
                            onLocate={locate}
                        />
                    )}

                    {farm && page === 'soil' && (
                        <SoilClimate farm={farm} units={units} />
                    )}

                    {farm && page === 'crops' && (
                        <Crops farm={farm} />
                    )}

                    {farm && page === 'rot' && (
                        <Rotation farm={farm} />
                    )}

                    {farm && page === 'alerts' && (
                        <Alerts farm={farm} />
                    )}

                    {farm && page === 'ai' && (
                        <PrithviXAI farm={farm} />
                    )}

                    {!loading && !loadError && (page === 'hub' || !farm) && (
                        <FarmerHub farm={farm} />
                    )}
                </div>
            </main>
        </div>
    );
}
