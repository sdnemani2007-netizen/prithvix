// PrithviX Integrated API Service
// Connects React Frontend to FastAPI Python Backend (NASA Earth Observation Services)

import type { Farm, Plot, Crop, Alert, Plan, Series, DashboardData, FarmerProfile } from '../types';
import { zoneFor } from '../utils/zone';

const RAW_BASE = import.meta.env.VITE_API_URL as string | undefined;
export const BASE = (RAW_BASE || 'http://127.0.0.1:8000').replace(/\/+$/, '');

// Shared GET helper: throws an Error carrying the backend's `detail` message.
async function apiGet<T>(path: string): Promise<T> {
    let res: Response;
    try {
        res = await fetch(`${BASE}${path}`, { headers: { Accept: 'application/json' } });
    } catch {
        throw new Error('Cannot reach the PrithviX backend. Make sure it is running.');
    }
    if (!res.ok) {
        let detail = `Server returned HTTP ${res.status}`;
        try {
            const j = await res.json();
            if (j?.detail) detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail);
        } catch { /* non-JSON body */ }
        throw new Error(detail);
    }
    return res.json() as Promise<T>;
}

// Map backend Farm record to frontend Farm model
export function mapBackendFarmToFrontend(bf: any): Farm {
    const key = String(bf.id);
    const lat = Number(bf.latitude);
    const lng = Number(bf.longitude);
    const z = bf.climate_zone || zoneFor(lat);

    return {
        id: bf.id,
        key: key,
        name: bf.name || 'My Farm',
        farmer_name: bf.farmer_name,
        location: bf.location || bf.name || '',
        lat,
        lng,
        area: bf.area,
        area_unit: bf.area_unit || 'Acres',
        current_crop: bf.current_crop,
        soil_type: bf.soil_type,
        water_source: bf.water_source,
        irrigation_method: bf.irrigation_method,
        primary_goal: bf.primary_goal,
        tz: bf.timezone || 'Asia/Kolkata',
        z: z,
        boundary_geojson: bf.boundary_geojson
    };
}

// ---------------------------------------------------------------------------
// FARMS API
// ---------------------------------------------------------------------------

export async function fetchFarms(): Promise<Farm[]> {
    const data = await apiGet<any[]>('/api/farms');
    return Array.isArray(data) ? data.map(mapBackendFarmToFrontend) : [];
}

export async function createBackendFarm(payload: {
    name: string;
    farmer_name?: string;
    location: string;
    latitude: number;
    longitude: number;
    area?: number;
    area_unit?: string;
    current_crop?: string;
    soil_type?: string;
    water_source?: string;
    irrigation_method?: string;
    primary_goal?: string;
    timezone?: string;
    climate_zone?: string;
    boundary_geojson?: any;
}): Promise<Farm> {
    const res = await fetch(`${BASE}/api/farms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(payload)
    });
    if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`Failed to create farm: ${res.status} ${errorText}`);
    }
    const data = await res.json();
    return mapBackendFarmToFrontend(data);
}

export async function updateBackendFarm(farmId: string, payload: Partial<{
    name: string;
    farmer_name: string;
    location: string;
    latitude: number;
    longitude: number;
    area: number;
    area_unit: string;
    current_crop: string;
    soil_type: string;
    water_source: string;
    irrigation_method: string;
    primary_goal: string;
    timezone: string;
    climate_zone: string;
    boundary_geojson: any;
}>): Promise<Farm> {
    const res = await fetch(`${BASE}/api/farms/${farmId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(payload)
    });
    if (!res.ok) {
        throw new Error(`Failed to update farm: ${res.status}`);
    }
    const data = await res.json();
    return mapBackendFarmToFrontend(data);
}

export async function deleteBackendFarm(farmId: string): Promise<void> {
    const res = await fetch(`${BASE}/api/farms/${farmId}`, {
        method: 'DELETE'
    });
    if (!res.ok && res.status !== 404) {
        throw new Error(`Failed to delete farm: ${res.status}`);
    }
}

// ---------------------------------------------------------------------------
// DASHBOARD, PLOTS, CROPS, ROTATION, SERIES, ALERTS (all real backend data)
// ---------------------------------------------------------------------------

function requireId(f: Farm): string {
    if (!f.id) throw new Error('This farm has not been saved yet.');
    return f.id;
}

export async function getDashboardData(farmId: string): Promise<DashboardData> {
    return apiGet<DashboardData>(`/api/dashboard/${farmId}`);
}

export const getPlots = async (f: Farm): Promise<Plot[]> => {
    const dash = await getDashboardData(requireId(f));
    return Array.isArray(dash.plots) ? dash.plots : [];
};

export const getCrops = async (f: Farm): Promise<Crop[]> => {
    const data = await apiGet<{ recommendations: Crop[] }>(`/api/crops/recommendations/${requireId(f)}`);
    return data.recommendations || [];
};

export const getRotation = async (f: Farm): Promise<Record<string, Plan>> => {
    const data = await apiGet<{ plans: Record<string, Plan> }>(`/api/crops/rotation/${requireId(f)}`);
    return data.plans || {};
};

export const getSeries = async (f: Farm): Promise<Series> => {
    const data = await apiGet<Series>(`/api/satellite/${requireId(f)}/timeseries?months=12`);
    return {
        periods: data.periods,
        moist: data.moist,
        rain: data.rain,
        lst: data.lst,
        ndvi: data.ndvi,
        sources: data.sources
    };
};

export async function getAlerts(f: Farm): Promise<Alert[]> {
    return apiGet<Alert[]>(`/api/alerts/${requireId(f)}`);
}

// ---------------------------------------------------------------------------
// GEOCODING SEARCH
// ---------------------------------------------------------------------------

export interface Place {
    name: string;
    lat: number;
    lng: number;
}

export async function searchPlaces(q: string): Promise<Place[]> {
    const r = await fetch(
        `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=6&accept-language=en&q=${encodeURIComponent(q)}`
    );
    if (!r.ok) {
        throw new Error('Search failed (' + r.status + ')');
    }
    const j = await r.json() as {
        display_name: string;
        lat: string;
        lon: string;
    }[];
    return j.map(p => ({
        name: p.display_name,
        lat: +p.lat,
        lng: +p.lon
    }));
}

// ---------------------------------------------------------------------------
// PRITHVIX AI ASSISTANT
// ---------------------------------------------------------------------------

export interface PrithviXAIRequest {
    message: string;
    farm?: {
        name: string;
        location?: string;
        latitude: number;
        longitude: number;
        timezone: string;
        zone: string;
        currentCrop: string;
        soilType: string;
        waterSource: string;
        irrigation: string;
        farmArea: string;
        areaUnit: string;
        primaryGoal: string;
    };
    farm_id?: string;
}

export interface PrithviXAIResponse {
    reply: string;
    grounded_on?: any;
    provider?: string;
}

export async function askPrithviX(payload: PrithviXAIRequest): Promise<PrithviXAIResponse> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 120000);
    let response: Response;
    try {
        response = await fetch(`${BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            body: JSON.stringify(payload),
            signal: controller.signal
        });
    } catch (err: any) {
        throw new Error(
            err?.name === 'AbortError'
                ? 'The PrithviXAI request timed out. Please try again.'
                : 'Unable to connect to the PrithviXAI server.'
        );
    } finally {
        clearTimeout(timer);
    }
    if (!response.ok) {
        let detail = `Server returned HTTP ${response.status}`;
        try {
            const j = await response.json();
            if (j?.detail) detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail);
        } catch { /* ignore */ }
        throw new Error(detail);
    }
    return await response.json() as PrithviXAIResponse;
}
