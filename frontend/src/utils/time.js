function padToTwo(value) {
  return String(value).padStart(2, '0');
}

export function formatDurationLabel(totalSeconds) {
  if (!Number.isFinite(totalSeconds) || totalSeconds <= 0) {
    return '0s';
  }

  const roundedSeconds = Math.round(totalSeconds);
  const hours = Math.floor(roundedSeconds / 3600);
  const minutes = Math.floor((roundedSeconds % 3600) / 60);
  const seconds = roundedSeconds % 60;
  const parts = [];

  if (hours) parts.push(`${hours}h`);
  if (minutes) parts.push(`${minutes}m`);
  if (seconds || !parts.length) parts.push(`${seconds}s`);

  return parts.join(' ');
}

export function toLocalDateTimeValue(date) {
  return (
    [date.getFullYear(), padToTwo(date.getMonth() + 1), padToTwo(date.getDate())].join('-') +
    'T' +
    [padToTwo(date.getHours()), padToTwo(date.getMinutes()), padToTwo(date.getSeconds())].join(':')
  );
}

export function formatUtcLabel(value) {
  return value.toISOString().replace('.000Z', 'Z');
}

export function toIsoString(localValue, label) {
  if (!localValue) {
    throw new Error(`${label} is required.`);
  }
  const parsed = new Date(localValue);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error(`Use a valid ${label.toLowerCase()}.`);
  }
  return parsed.toISOString();
}
