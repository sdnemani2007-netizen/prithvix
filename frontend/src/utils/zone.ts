import type { Zone } from '../types';

// Latitude-only climate zone estimate used when the backend has no stored zone.
export const zoneFor = (lat: number): Zone =>
    Math.abs(lat) < 23.5 ? 'trop' : Math.abs(lat) < 40 ? 'humid' : 'temp';

export const ZONE_NAMES: Record<string, string> = {
    trop: 'Tropical',
    humid: 'Humid subtropical',
    med: 'Mediterranean',
    temp: 'Temperate'
};
