import { buildTelemetryFormData, resolveTelemetryBackgroundColor } from './formData';

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
