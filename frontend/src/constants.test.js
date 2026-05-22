import { normalizeMapTileOptions } from './constants';

describe('normalizeMapTileOptions', () => {
  it('maps capabilities map layer metadata into select options with previews', () => {
    expect(
      normalizeMapTileOptions([
        { key: '', value: '', label: 'Backend default (MAP_TILE_URL_TEMPLATE)' },
        {
          key: 'osm',
          value: 'osm',
          label: 'OpenStreetMap (Standard)',
          preview_url: 'https://example.test/osm-preview.png',
          attribution: 'OpenStreetMap contributors'
        }
      ])
    ).toEqual([
      { value: '', label: 'Backend default (MAP_TILE_URL_TEMPLATE)', previewUrl: undefined, attribution: undefined },
      {
        value: 'osm',
        label: 'OpenStreetMap (Standard)',
        previewUrl: 'https://example.test/osm-preview.png',
        attribution: 'OpenStreetMap contributors'
      }
    ]);
  });

  it('ignores malformed map layer entries', () => {
    expect(normalizeMapTileOptions([null, { key: 'osm' }, { label: 'Missing value' }])).toEqual([]);
  });
});
