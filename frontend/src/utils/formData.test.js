import { buildMapAnimationFormData, buildTelemetryFormData, resolveTelemetryBackgroundColor } from './formData';

describe('map animation form data', () => {
  function buildMapAnimation(overrides = {}) {
    return {
      gpxFile: new File(['gpx'], 'track.gpx', { type: 'application/gpx+xml' }),
      durationSeconds: 10,
      fps: 30,
      markerColor: '#0ea5e9',
      trailColor: '#0ea5e9',
      fullTrailColor: '#111827',
      fullTrailOpacity: 0.8,
      markerSize: 6,
      lineWidth: 2.5,
      lineOpacity: 1,
      tileType: 'osm',
      ...overrides
    };
  }

  it('includes the selected marker style in animation requests', () => {
    const formData = buildMapAnimationFormData(buildMapAnimation({ markerStyle: 'runner' }), '640x640');

    expect(formData.get('marker_style')).toBe('runner');
  });

  it('defaults missing marker style in animation requests', () => {
    const formData = buildMapAnimationFormData(buildMapAnimation(), '640x640');

    expect(formData.get('marker_style')).toBe('default');
  });
});

describe('telemetry form data', () => {
  it('resolves transparent as the default telemetry background', () => {
    expect(resolveTelemetryBackgroundColor({})).toBe('transparent');
    expect(resolveTelemetryBackgroundColor({ backgroundMode: 'transparent', backgroundColor: '#112233' })).toBe('transparent');
  });

  it('includes transparent background in telemetry requests', () => {
    const formData = buildTelemetryFormData(
      {
        gpxFile: new File(['gpx'], 'track.gpx', { type: 'application/gpx+xml' }),
        durationSeconds: 10,
        fps: 30,
        telemetryType: 'elevation_value'
      },
      '640x640',
      resolveTelemetryBackgroundColor({ backgroundMode: 'transparent', backgroundColor: '#112233' })
    );

    expect(formData.get('background_color')).toBe('transparent');
  });

  it('includes custom background color in telemetry requests', () => {
    const formData = buildTelemetryFormData(
      {
        gpxFile: new File(['gpx'], 'track.gpx', { type: 'application/gpx+xml' }),
        durationSeconds: 10,
        fps: 30,
        telemetryType: 'elevation_value'
      },
      '640x640',
      resolveTelemetryBackgroundColor({ backgroundMode: 'custom', backgroundColor: ' #112233 ' })
    );

    expect(formData.get('background_color')).toBe('#112233');
  });
});
