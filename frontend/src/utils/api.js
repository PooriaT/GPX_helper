export function extractFilename(headerValue, fallback) {
  if (!headerValue) return fallback;
  const match = headerValue.match(/filename\*?=(?:UTF-8''|\"?)([^\";]+)/i);
  if (match?.[1]) {
    const raw = match[1].trim().replace(/\"/g, '');
    try {
      return decodeURIComponent(raw);
    } catch (error) {
      return raw;
    }
  }
  return fallback;
}

export function deriveMp4Filename(file, fallback) {
  const name = file?.name;
  if (!name) return fallback;
  const base = name.replace(/\.[^./\\]+$/, '');
  if (!base) return fallback;
  return `${base}.mp4`;
}

export function parseError(error, fallback = 'Request failed') {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export function cloneFormData(formData) {
  const copy = new FormData();
  formData.forEach((value, key) => copy.append(key, value));
  return copy;
}

export async function requestFile(apiBase, path, formData, fallbackFilename) {
  const response = await fetch(`${apiBase}${path}`, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    let detail;
    try {
      detail = await response.json();
    } catch (error) {
      detail = null;
    }
    throw new Error(detail?.detail || `Request failed (${response.status})`);
  }

  const blob = await response.blob();
  const filename = extractFilename(response.headers.get('content-disposition'), fallbackFilename);
  return { blob, filename };
}

export async function requestEta(apiBase, path, formData) {
  const response = await fetch(`${apiBase}${path}`, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    let detail;
    try {
      detail = await response.json();
    } catch (error) {
      detail = null;
    }
    throw new Error(detail?.detail || `Unable to fetch ETA (${response.status})`);
  }

  const payload = await response.json();
  if (typeof payload?.estimated_seconds !== 'number') {
    throw new Error('Invalid ETA response from server.');
  }
  return payload.estimated_seconds;
}

export async function requestCapabilities(apiBase) {
  const response = await globalThis.fetch(`${apiBase}/api/v1/capabilities`);
  if (!response.ok) {
    throw new Error(`Unable to fetch capabilities (${response.status})`);
  }
  return response.json();
}
