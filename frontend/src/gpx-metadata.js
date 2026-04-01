function parseXml(text) {
  if (typeof text !== 'string' || !text.trim()) {
    return null;
  }

  const document = new DOMParser().parseFromString(text, 'application/xml');
  if (document.querySelector('parsererror')) {
    return null;
  }

  return document;
}

function parseTrackPointTimestamps(document) {
  if (!document) {
    return [];
  }

  return Array.from(document.getElementsByTagNameNS('*', 'trkpt'))
    .map((trackPoint) => trackPoint.getElementsByTagNameNS('*', 'time').item(0)?.textContent?.trim())
    .filter(Boolean)
    .map((value) => new Date(value))
    .filter((timestamp) => !Number.isNaN(timestamp.getTime()));
}

export function parseGpxTimeRangeFromText(text) {
  const timestamps = parseTrackPointTimestamps(parseXml(text));

  if (!timestamps.length) {
    return null;
  }

  return {
    start: timestamps[0],
    end: timestamps[timestamps.length - 1]
  };
}

export function parseGpxDurationFromText(text) {
  const timeRange = parseGpxTimeRangeFromText(text);
  if (!timeRange) {
    return null;
  }

  const diffMs = timeRange.end.getTime() - timeRange.start.getTime();
  if (diffMs <= 0) {
    return null;
  }

  return Math.max(1, Math.round(diffMs / 1000));
}
