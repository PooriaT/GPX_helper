export const DEFAULT_API_BASE = (import.meta.env.VITE_API_BASE ?? 'http://localhost:8000').replace(/\/$/, '');

export const MAP_TILE_OPTIONS = [
  { value: '', label: 'Backend default (MAP_TILE_URL_TEMPLATE)' },
  { value: 'osm', label: 'OpenStreetMap (Standard)' },
  { value: 'cyclosm', label: 'CyclOSM' },
  { value: 'opentopomap', label: 'OpenTopoMap (Topo)' }
];

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
