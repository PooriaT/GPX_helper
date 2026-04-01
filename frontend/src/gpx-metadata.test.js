import { describe, expect, it } from 'vitest';

import { parseGpxDurationFromText, parseGpxTimeRangeFromText } from './gpx-metadata';

describe('gpx-metadata', () => {
  it('derives duration from track point timestamps instead of metadata time', () => {
    const gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1">
  <metadata>
    <time>2026-03-28T15:45:38.000Z</time>
  </metadata>
  <trk>
    <trkseg>
      <trkpt lat="49.0" lon="-123.0">
        <time>2026-03-28T15:57:28.000Z</time>
      </trkpt>
      <trkpt lat="49.1" lon="-123.1">
        <time>2026-03-28T16:07:28.000Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>`;

    expect(parseGpxDurationFromText(gpx)).toBe(600);
  });

  it('returns the track point time range', () => {
    const gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="49.0" lon="-123.0">
        <time>2026-03-28T15:57:28.000Z</time>
      </trkpt>
      <trkpt lat="49.1" lon="-123.1">
        <time>2026-03-28T16:07:28.000Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>`;

    expect(parseGpxTimeRangeFromText(gpx)).toEqual({
      start: new Date('2026-03-28T15:57:28.000Z'),
      end: new Date('2026-03-28T16:07:28.000Z')
    });
  });

  it('returns null when no valid track point timestamps exist', () => {
    const gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1">
  <metadata>
    <time>2026-03-28T15:45:38.000Z</time>
  </metadata>
</gpx>`;

    expect(parseGpxDurationFromText(gpx)).toBeNull();
    expect(parseGpxTimeRangeFromText(gpx)).toBeNull();
  });
});
