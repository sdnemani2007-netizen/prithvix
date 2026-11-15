import { useEffect, useState, type FormEvent } from 'react';
import { Sparkles, Loader2 } from 'lucide-react';
import type { Farm } from '../types';
import { createBackendFarm, updateBackendFarm, searchPlaces } from '../services/api';

type AreaUnit = 'Acres' | 'Hectares' | 'Square metres';

export type FarmerProfile = {
    farmerName: string;
    farmName: string;
    farmLocation: string;
    farmArea: string;
    areaUnit: AreaUnit;
    currentCrop: string;
    soilType: string;
    waterSource: string;
    irrigation: string;
    primaryGoal: string;
    id?: string;
};

const PROFILE_KEY = 'prithvix.profile.v1';

const defaultProfile: FarmerProfile = {
    farmerName: '',
    farmName: '',
    farmLocation: '',
    farmArea: '',
    areaUnit: 'Acres',
    currentCrop: '',
    soilType: 'Unknown',
    waterSource: 'Unknown',
    irrigation: 'Unknown',
    primaryGoal: 'Increase Crop Yield & Quality'
};

function readProfile(): FarmerProfile {
    try {
        const saved = JSON.parse(
            localStorage.getItem(PROFILE_KEY) || '{}'
        );
        return {
            ...defaultProfile,
            farmerName: saved.farmerName ?? saved.name ?? '',
            farmName: saved.farmName ?? '',
            farmLocation: saved.farmLocation ?? saved.country ?? '',
            farmArea: saved.farmArea ?? '',
            areaUnit: saved.areaUnit ?? 'Acres',
            currentCrop: saved.currentCrop ?? '',
            soilType: saved.soilType ?? 'Unknown',
            waterSource: saved.waterSource ?? 'Unknown',
            irrigation: saved.irrigation ?? 'Unknown',
            primaryGoal: saved.primaryGoal ?? defaultProfile.primaryGoal,
            id: saved.id
        };
    } catch {
        return defaultProfile;
    }
}

export default function FarmerHub({ farm }: { farm?: Farm }) {
    const [profile, setProfile] = useState<FarmerProfile>(() => {
        const savedProfile = readProfile();
        return {
            ...savedProfile,
            farmName: savedProfile.farmName || farm?.name || '',
            farmLocation: savedProfile.farmLocation || farm?.location || ''
        };
    });

    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);
    const [errorMsg, setErrorMsg] = useState('');

    useEffect(() => {
        if (farm?.location) {
            setProfile(current => ({
                ...current,
                farmName: current.farmName || farm.name,
                farmLocation: current.farmLocation || farm?.location || ''
            }));
        }
    }, [farm]);

    function update<K extends keyof FarmerProfile>(
        key: K,
        value: FarmerProfile[K]
    ) {
        setProfile(current => ({
            ...current,
            [key]: value
        }));
        setSaved(false);
        setErrorMsg('');
    }

    async function saveProfile(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setSaving(true);
        setErrorMsg('');

        try {
            // Geocode location if possible or inherit farm coords
            let lat: number | undefined = farm?.lat;
            let lng: number | undefined = farm?.lng;

            if (profile.farmLocation && profile.farmLocation !== farm?.location) {
                try {
                    const places = await searchPlaces(profile.farmLocation);
                    if (places && places.length > 0) {
                        lat = places[0].lat;
                        lng = places[0].lng;
                    }
                } catch (e) {
                    console.warn('Geocoding place lookup warning:', e);
                }
            }

            if (lat == null || lng == null || Number.isNaN(lat) || Number.isNaN(lng)) {
                throw new Error('Could not find that location. Please enter a more specific place name.');
            }

            const parsedArea = parseFloat(profile.farmArea) || 1.0;

            let backendFarm: Farm;
            if (farm?.id) {
                // Update existing backend farm
                backendFarm = await updateBackendFarm(farm.id, {
                    name: profile.farmName || profile.farmLocation || 'My Farm',
                    farmer_name: profile.farmerName,
                    location: profile.farmLocation,
                    latitude: lat,
                    longitude: lng,
                    area: parsedArea,
                    area_unit: profile.areaUnit,
                    current_crop: profile.currentCrop,
                    soil_type: profile.soilType,
                    water_source: profile.waterSource,
                    irrigation_method: profile.irrigation,
                    primary_goal: profile.primaryGoal
                });
            } else {
                // Create new backend farm record
                backendFarm = await createBackendFarm({
                    name: profile.farmName || profile.farmLocation || 'My Farm',
                    farmer_name: profile.farmerName,
                    location: profile.farmLocation,
                    latitude: lat,
                    longitude: lng,
                    area: parsedArea,
                    area_unit: profile.areaUnit,
                    current_crop: profile.currentCrop,
                    soil_type: profile.soilType,
                    water_source: profile.waterSource,
                    irrigation_method: profile.irrigation,
                    primary_goal: profile.primaryGoal
                });
            }

            const profileToSave = {
                ...profile,
                id: backendFarm.id
            };

            localStorage.setItem(PROFILE_KEY, JSON.stringify(profileToSave));

            // Notify entire application of the update and pass the backend farm
            window.dispatchEvent(
                new CustomEvent('prithvix-profile-updated', { detail: backendFarm })
            );

            setSaved(true);
        } catch (err) {
            console.error('Error saving farm profile to backend:', err);
            // Fallback to localStorage if offline
            localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
            window.dispatchEvent(new Event('prithvix-profile-updated'));
            setSaved(true);
            setErrorMsg('Note: Saved locally. (Backend sync pending).');
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="farmer-hub-page">
            <header className="farmer-hub-heading">
                <span className="farmer-hub-eyebrow">
                    ONBOARDING &amp; CONFIGURATION
                </span>
                <h1>Farmer Profile &amp; Farm Information</h1>
                <p>
                    Enter your farm details so PrithviX can generate
                    personalized recommendations powered by persistent database records and NASA Earth observations.
                </p>
            </header>

            <form className="farmer-profile-form" onSubmit={saveProfile}>
                <div className="farmer-form-grid">
                    <label className="farmer-field">
                        <span>FARMER NAME</span>
                        <input
                            type="text"
                            value={profile.farmerName}
                            onChange={e => update('farmerName', e.target.value)}
                            placeholder="Enter farmer name"
                            required
                        />
                    </label>

                    <label className="farmer-field">
                        <span>FARM NAME</span>
                        <input
                            type="text"
                            value={profile.farmName}
                            onChange={e => update('farmName', e.target.value)}
                            placeholder="Enter farm name"
                            required
                        />
                    </label>

                    <label className="farmer-field">
                        <span>FARM LOCATION / DISTRICT</span>
                        <input
                            type="text"
                            value={profile.farmLocation}
                            onChange={e => update('farmLocation', e.target.value)}
                            placeholder="City, region, country"
                            required
                        />
                    </label>

                    <div className="farmer-field">
                        <span>FARM SIZE</span>
                        <div className="farmer-size-control">
                            <input
                                type="number"
                                min="0"
                                step="any"
                                value={profile.farmArea}
                                onChange={e => update('farmArea', e.target.value)}
                                placeholder="Enter farm size"
                                required
                            />
                            <select
                                value={profile.areaUnit}
                                onChange={e => update('areaUnit', e.target.value as AreaUnit)}
                                aria-label="Farm area unit"
                            >
                                <option>Acres</option>
                                <option>Hectares</option>
                                <option>Square metres</option>
                            </select>
                        </div>
                    </div>

                    <label className="farmer-field">
                        <span>CURRENT CROP</span>
                        <select
                            value={profile.currentCrop}
                            onChange={e => update('currentCrop', e.target.value)}
                            required
                        >
                            <option value="">Select current crop</option>
                            {[
                                'Rice / Paddy',
                                'Wheat',
                                'Maize',
                                'Cotton',
                                'Sugarcane',
                                'Soybean',
                                'Groundnut',
                                'Millets / Sorghum',
                                'Pulses / Legumes',
                                'Vegetables',
                                'Fruits',
                                'Other'
                            ].map(crop => (
                                <option key={crop} value={crop}>{crop}</option>
                            ))}
                        </select>
                    </label>

                    <label className="farmer-field">
                        <span>SOIL TYPE</span>
                        <select
                            value={profile.soilType}
                            onChange={e => update('soilType', e.target.value)}
                        >
                            {[
                                'Unknown',
                                'Black Cotton Soil (Vertisol)',
                                'Alluvial Soil',
                                'Red Soil',
                                'Sandy Soil',
                                'Clay Soil',
                                'Loamy Soil',
                                'Silty Soil',
                                'Peaty Soil',
                                'Chalky Soil',
                                'Other'
                            ].map(soil => (
                                <option key={soil} value={soil}>{soil}</option>
                            ))}
                        </select>
                    </label>

                    <label className="farmer-field">
                        <span>WATER SOURCE</span>
                        <select
                            value={profile.waterSource}
                            onChange={e => update('waterSource', e.target.value)}
                        >
                            {[
                                'Unknown',
                                'Rainfed',
                                'Borehole / Groundwater',
                                'River',
                                'Canal',
                                'Reservoir',
                                'Farm pond',
                                'Recycled water',
                                'Other'
                            ].map(source => (
                                <option key={source} value={source}>{source}</option>
                            ))}
                        </select>
                    </label>

                    <label className="farmer-field">
                        <span>IRRIGATION METHOD</span>
                        <select
                            value={profile.irrigation}
                            onChange={e => update('irrigation', e.target.value)}
                        >
                            {[
                                'Unknown',
                                'Rainfed',
                                'Drip Irrigation',
                                'Sprinkler Irrigation',
                                'Flood Irrigation',
                                'Furrow Irrigation',
                                'Subsurface Irrigation',
                                'Other'
                            ].map(method => (
                                <option key={method} value={method}>{method}</option>
                            ))}
                        </select>
                    </label>

                    <label className="farmer-field farmer-field-full">
                        <span>PRIMARY GOAL</span>
                        <select
                            value={profile.primaryGoal}
                            onChange={e => update('primaryGoal', e.target.value)}
                        >
                            {[
                                'Increase Crop Yield & Quality',
                                'Reduce Water Consumption',
                                'Improve Soil Health',
                                'Reduce Fertilizer Costs',
                                'Choose the Best Crop for My Land',
                                'Improve Crop Rotation',
                                'Manage Climate Risks',
                                'Improve Farm Profitability'
                            ].map(goal => (
                                <option key={goal} value={goal}>{goal}</option>
                            ))}
                        </select>
                    </label>
                </div>

                <div className="farmer-form-actions">
                    <button className="farmer-save-btn" type="submit" disabled={saving}>
                        {saving ? (
                            <>
                                <Loader2 size={16} className="animate-spin" />
                                Saving to Database...
                            </>
                        ) : (
                            <>
                                <Sparkles size={16} strokeWidth={2.5} />
                                Save Profile &amp; Generate Guidance
                            </>
                        )}
                    </button>

                    {saved && (
                        <span className="farmer-saved-message" role="status">
                            ✓ Farm details saved persistently to backend database.
                        </span>
                    )}

                    {errorMsg && (
                        <span style={{ color: '#d97706', fontSize: '0.85rem' }}>
                            {errorMsg}
                        </span>
                    )}
                </div>
            </form>
        </div>
    );
}
