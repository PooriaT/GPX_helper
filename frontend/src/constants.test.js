import { normalizeMapTileOptions } from './constants';

describe('normalizeMapTileOptions', () => {
  it('maps capabilities map layer metadata into select options with previews', () => {
    expect(
      normalizeMapTileOptions([
        { key: '', value: '', label: 'Backend default (MAP_TILE_URL_TEMPLATE)' },
        {
          key: 'esri_world_imagery',
          value: 'esri_world_imagery',
          label: 'Satellite (Esri World Imagery)',
          preview_url: 'https://example.test/esri-preview.png',
          attribution: 'Esri, Vantor, Earthstar Geographics, and the GIS User Community'
        }
      ])
    ).toEqual([
      { value: '', label: 'Backend default (MAP_TILE_URL_TEMPLATE)', previewUrl: undefined, attribution: undefined },
      {
        value: 'esri_world_imagery',
        label: 'Satellite (Esri World Imagery)',
        previewUrl: 'https://example.test/esri-preview.png',
        attribution: 'Esri, Vantor, Earthstar Geographics, and the GIS User Community'
      }
    ]);
  });

  it('ignores malformed map layer entries', () => {
    expect(normalizeMapTileOptions([null, { key: 'osm' }, { label: 'Missing value' }])).toEqual([]);
  });
});
