export const DEFAULT_API_BASE = (import.meta.env.VITE_API_BASE ?? 'http://localhost:8000').replace(/\/$/, '');

// Local fallback for when /api/v1/capabilities is unavailable.
export const MAP_TILE_OPTIONS = [
  {
    value: 'osm',
    label: 'OpenStreetMap (Standard)',
    previewUrl: 'https://tile.openstreetmap.org/12/654/1582.png',
    attribution: 'OpenStreetMap contributors'
  },
  {
    value: 'cyclosm',
    label: 'CyclOSM',
    previewUrl: 'https://a.tile-cyclosm.openstreetmap.fr/cyclosm/12/654/1582.png',
    attribution: 'CyclOSM and OpenStreetMap contributors'
  },
  {
    value: 'opentopomap',
    label: 'OpenTopoMap (Topo)',
    previewUrl: 'https://a.tile.opentopomap.org/12/654/1582.png',
    attribution: 'OpenTopoMap and OpenStreetMap contributors'
  },
  {
    value: 'esri_world_imagery',
    label: 'Satellite (Esri World Imagery)',
    previewUrl: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/12/1582/654',
    attribution: 'Esri, Vantor, Earthstar Geographics, and the GIS User Community'
  }
];

export function normalizeMapTileOptions(mapLayers) {
  if (!Array.isArray(mapLayers)) return [];
  return mapLayers
    .map((layer) => {
      const value = typeof layer?.value === 'string' ? layer.value : layer?.key;
      const label = layer?.label;
      const hasValidValue = typeof value === 'string' && (value === '' || value.trim());
      if (!hasValidValue || typeof label !== 'string' || !label.trim()) return null;
      return {
        value,
        label,
        previewUrl: typeof layer.preview_url === 'string' ? layer.preview_url : layer.previewUrl,
        attribution: typeof layer.attribution === 'string' ? layer.attribution : undefined
      };
    })
    .filter(Boolean);
}

export const TELEMETRY_TYPE_OPTIONS = [
  { value: 'elevation_value', label: 'Elevation value' },
  { value: 'speed', label: 'Speed' },
  { value: 'heart_rate', label: 'Heart rate' },
  { value: 'elevation_graph', label: 'Elevation graph' }
];

export const TASKS = [
  { id: 'trim', href: '#/trim', label: 'Trim GPX', description: 'Cut a track by timestamps or split it around recorded videos.' },
  { id: 'animation', href: '#/animation', label: 'Create route animation', description: 'Render a map-based MP4 animation from a GPX route.' },
  { id: 'telemetry', href: '#/telemetry', label: 'Generate telemetry video', description: 'Render telemetry overlays with speed, elevation, or graph data.' }
];

export const PAGES = [
  { id: 'trim', href: '#/trim', label: 'Trim GPX' },
  { id: 'animation', href: '#/animation', label: 'Route animation' },
  { id: 'telemetry', href: '#/telemetry', label: 'Telemetry video' },
  { id: 'about', href: '#/about', label: 'About' }
];

export const PAGE_DESCRIPTIONS = {
  trim: 'Trim tracks by exact times or split them from video metadata.',
  animation: 'Render a clean MP4 route animation from a GPX track.',
  telemetry: 'Create telemetry-only videos for overlays and compositing.',
  about: 'A quick overview of the tools available in GPX Helper.'
};
