export type Zone = 'trop' | 'humid' | 'med' | 'temp';
export type Units = 'm' | 'i';

export interface Farm {
    id?: string;
    key: string;
    name: string;
    farmer_name?: string;
    location?: string;
    lat: number;
    lng: number;
    area?: number;
    area_unit?: string;
    current_crop?: string;
    soil_type?: string;
    water_source?: string;
    irrigation_method?: string;
    primary_goal?: string;
    tz: string;
    z: string;
    pl?: number[][];
    boundary_geojson?: any;
}

export interface Plot {
    id: string;
    name: string;
    ha: number;
    crop: string;
    moist: number | null;
    lst: number | null;
    ndvi: number | null;
    status?: string;
}

export interface Crop {
    n: string;
    sc: number;
    w: string;
    why: string;
    supporting_observations?: string[];
    limitations?: string[];
    confidence?: string;
}

export interface Alert {
    s: 'c' | 'w' | 'i' | 'n';
    t: string;
    p: string;
    d: string;
    x: string;
    a: string;
    source?: string;
}

export interface Plan {
    A: string[];
    B: string[];
    note: string;
}

export interface Series {
    periods?: string[];
    moist: (number | null)[];
    rain: (number | null)[];
    lst: (number | null)[];
    ndvi: (number | null)[];
    sources?: Record<string, string>;
}

export interface DashboardData {
    farm_id: string;
    farm_name: string;
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
    plots: Plot[];
    conditions: {
        soil_moisture?: number;
        soil_moisture_str: string;
        vegetation_ndvi?: number;
        vegetation_ndvi_str: string;
        water_available?: number;
        water_available_status: string;
        surface_temp_c?: number;
        surface_temp_str: string;
        observation_dates: Record<string, string>;
        sources: Record<string, string>;
    };
    recommended_actions: Alert[];
    datasets_status: Record<string, string>;
    caveats: string;
}

export interface FarmerProfile {
    farmerName: string;
    farmName: string;
    farmLocation: string;
    farmArea: string;
    areaUnit: 'Acres' | 'Hectares' | 'Square metres';
    currentCrop: string;
    soilType: string;
    waterSource: string;
    irrigation: string;
    primaryGoal: string;
    latitude?: number;
    longitude?: number;
    id?: string;
}
