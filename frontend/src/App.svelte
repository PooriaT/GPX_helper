<script>
  import { onDestroy } from 'svelte';

  const DEFAULT_API_BASE = (import.meta.env.VITE_API_BASE ?? 'http://localhost:8000').replace(/\/$/, '');

  let apiBase = DEFAULT_API_BASE;

  let trimByTime = {
    startLocal: '',
    endLocal: '',
    gpxFile: null,
    videoFile: null,
    status: 'idle',
    error: '',
    downloadUrl: '',
    filename: '',
    message: ''
  };

  let mapAnimation = {
    gpxFile: null,
    durationSeconds: 45,
    resolutionWidth: 1024,
    resolutionHeight: 1024,
    tileType: '',
    markerColor: '#0ea5e9',
    trailColor: '#0ea5e9',
    fullTrailColor: '#111827',
    fullTrailOpacity: 0.8,
    markerSize: 6,
    lineWidth: 2.5,
    lineOpacity: 1,
    status: 'idle',
    error: '',
    downloadUrl: '',
    filename: '',
    message: ''
  };

  const mapTileOptions = [
    { value: '', label: 'Server default' },
    { value: 'osm', label: 'OpenStreetMap (Standard)' },
    { value: 'cyclosm', label: 'CyclOSM' },
    { value: 'opentopomap', label: 'OpenTopoMap (Topo)' }
  ];

  let activeRequestLabel = '';
  let estimatedSeconds = null;
  const currentYear = new Date().getFullYear();

  $: isBusy = [trimByTime, mapAnimation].some((state) => state.status === 'loading');

  onDestroy(() => {
    [trimByTime, mapAnimation].forEach((state) => {
      if (state.downloadUrl) {
        URL.revokeObjectURL(state.downloadUrl);
      }
    });
  });

  function extractFilename(headerValue, fallback) {
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

  function toIsoString(localValue, label) {
    if (!localValue) {
      throw new Error(`${label} is required.`);
    }
    const parsed = new Date(localValue);
    if (Number.isNaN(parsed.getTime())) {
      throw new Error(`Use a valid ${label.toLowerCase()}.`);
    }
    return parsed.toISOString();
  }

  function parseError(error, fallback = 'Request failed') {
    if (error instanceof Error && error.message) {
      return error.message;
    }
    return fallback;
  }

  function cloneFormData(formData) {
    const copy = new FormData();
    formData.forEach((value, key) => copy.append(key, value));
    return copy;
  }

  function startRequest(label) {
    activeRequestLabel = label;
    estimatedSeconds = null;
  }

  function finishRequest() {
    activeRequestLabel = '';
    estimatedSeconds = null;
  }

  function readFileText(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error || new Error('Unable to read file.'));
      reader.readAsText(file);
    });
  }

  function padToTwo(value) {
    return String(value).padStart(2, '0');
  }

  function toLocalDateTimeValue(date) {
    return [
      date.getFullYear(),
      padToTwo(date.getMonth() + 1),
      padToTwo(date.getDate())
    ].join('-') +
      'T' +
      [
        padToTwo(date.getHours()),
        padToTwo(date.getMinutes()),
        padToTwo(date.getSeconds())
      ].join(':');
  }

  function loadVideoDuration(file) {
    return new Promise((resolve, reject) => {
      const video = document.createElement('video');
      video.preload = 'metadata';
      const objectUrl = URL.createObjectURL(file);
      const cleanup = () => {
        URL.revokeObjectURL(objectUrl);
      };
      video.onloadedmetadata = () => {
        cleanup();
        if (Number.isFinite(video.duration)) {
          resolve(video.duration);
        } else {
          reject(new Error('Unable to read video duration.'));
        }
      };
      video.onerror = () => {
        cleanup();
        reject(new Error('Unable to read video metadata.'));
      };
      video.src = objectUrl;
    });
  }

  async function deriveVideoTimes(file) {
    const durationSeconds = await loadVideoDuration(file);
    // File timestamp marks the clip start; compute the end using the duration.
    const start = new Date(file.lastModified);
    const end = new Date(start.getTime() + durationSeconds * 1000);
    return { durationSeconds, start, end };
  }

  async function parseGpxDuration(file) {
    if (!file) return null;
    const text = await readFileText(file);
    if (typeof text !== 'string') return null;

    const timeMatches = [...text.matchAll(/<time>([^<]+)<\/time>/g)];
    const timestamps = timeMatches
      .map((match) => new Date(match[1]))
      .filter((timestamp) => !Number.isNaN(timestamp.getTime()));

    if (timestamps.length < 2) return null;
    const first = timestamps[0];
    const last = timestamps[timestamps.length - 1];
    const diffMs = last.getTime() - first.getTime();
    if (diffMs <= 0) return null;

    return Math.max(1, Math.round(diffMs / 1000));
  }

  async function requestFile(path, formData, fallbackFilename) {
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

  async function requestEta(path, formData) {
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

  async function submitTrimByTime() {
    if (trimByTime.downloadUrl) {
      URL.revokeObjectURL(trimByTime.downloadUrl);
    }
    startRequest('Trimming GPX by time...');
    trimByTime = {
      ...trimByTime,
      status: 'loading',
      error: '',
      message: '',
      downloadUrl: '',
      filename: ''
    };

    try {
      if (!trimByTime.gpxFile) {
        throw new Error('Upload a GPX track to trim.');
      }
      const startIso = toIsoString(trimByTime.startLocal, 'Start time');
      const endIso = toIsoString(trimByTime.endLocal, 'End time');
      if (new Date(startIso) >= new Date(endIso)) {
        throw new Error('Start time must be before end time.');
      }

      const formData = new FormData();
      formData.append('gpx_file', trimByTime.gpxFile);
      formData.append('start_time', startIso);
      formData.append('end_time', endIso);

      const { blob, filename } = await requestFile('/api/v1/gpx/trim-by-time', formData, 'trimmed.gpx');
      const downloadUrl = URL.createObjectURL(blob);
      trimByTime = {
        ...trimByTime,
        status: 'success',
        downloadUrl,
        filename,
        message: `Trimmed ${trimByTime.gpxFile.name} between ${startIso} and ${endIso}.`
      };
    } catch (error) {
      trimByTime = { ...trimByTime, status: 'error', error: parseError(error) };
    } finally {
      finishRequest();
    }
  }

  async function submitMapAnimation() {
    if (mapAnimation.downloadUrl) {
      URL.revokeObjectURL(mapAnimation.downloadUrl);
    }
    startRequest('Rendering map animation...');
    mapAnimation = {
      ...mapAnimation,
      status: 'loading',
      error: '',
      message: '',
      downloadUrl: '',
      filename: ''
    };

    try {
      if (!mapAnimation.gpxFile) {
        throw new Error('Upload a GPX track to animate.');
      }
      if (!mapAnimation.durationSeconds) {
        const parsedDuration = await parseGpxDuration(mapAnimation.gpxFile);
        if (parsedDuration) {
          mapAnimation = { ...mapAnimation, durationSeconds: parsedDuration };
        }
      }
      if (!mapAnimation.durationSeconds || mapAnimation.durationSeconds <= 0) {
        throw new Error('Duration must be greater than zero.');
      }
      if (!mapAnimation.resolutionWidth || !mapAnimation.resolutionHeight) {
        throw new Error('Enter a resolution for the export.');
      }
      if (mapAnimation.resolutionWidth <= 0 || mapAnimation.resolutionHeight <= 0) {
        throw new Error('Resolution must be greater than zero.');
      }
      const resolutionLabel = `${mapAnimation.resolutionWidth}x${mapAnimation.resolutionHeight}`;

      const formData = new FormData();
      formData.append('gpx_file', mapAnimation.gpxFile);
      formData.append('duration_seconds', String(mapAnimation.durationSeconds));
      formData.append('resolution', resolutionLabel);
      formData.append('marker_color', mapAnimation.markerColor);
      formData.append('trail_color', mapAnimation.trailColor);
      formData.append('full_trail_color', mapAnimation.fullTrailColor);
      formData.append('full_trail_opacity', String(mapAnimation.fullTrailOpacity));
      formData.append('marker_size', String(mapAnimation.markerSize));
      formData.append('line_width', String(mapAnimation.lineWidth));
      formData.append('line_opacity', String(mapAnimation.lineOpacity));
      if (mapAnimation.tileType) {
        formData.append('tile_type', mapAnimation.tileType);
      }

      requestEta('/api/v1/gpx/map-animate/estimate', cloneFormData(formData))
        .then((eta) => {
          estimatedSeconds = eta;
        })
        .catch(() => {
          estimatedSeconds = null;
        });

      const { blob, filename } = await requestFile('/api/v1/gpx/map-animate', formData, 'route.mp4');
      const downloadUrl = URL.createObjectURL(blob);
      mapAnimation = {
        ...mapAnimation,
        status: 'success',
        downloadUrl,
        filename,
        message: `Rendered ${filename} (${resolutionLabel}, ${mapAnimation.durationSeconds}s).`
      };
    } catch (error) {
      mapAnimation = { ...mapAnimation, status: 'error', error: parseError(error) };
    } finally {
      finishRequest();
    }
  }

</script>

<svelte:head>
  <meta
    name="description"
    content="Run the GPX Helper API from the browser to trim GPX files or render route animations."
  />
</svelte:head>

<div class="page-shell">
  <header class="hero">
    <h1>GPX Helper</h1>
    <p class="lede">
      Trim GPX tracks, sync them to video timestamps, and render map animations directly in your browser.
    </p>
  </header>

  {#if isBusy}
    <div class="loading-banner" role="status" aria-live="polite">
      <div class="spinner" aria-hidden="true"></div>
      <div class="loading-copy">
        <p class="loading-title">{activeRequestLabel || 'Working on your request...'}</p>
        <p class="muted-text">
          {#if estimatedSeconds}
            Estimated wait: ~{Math.max(1, Math.round(estimatedSeconds))} seconds.
          {:else}
            Preparing your request. Buttons stay disabled until it finishes.
          {/if}
        </p>
      </div>
    </div>
  {/if}

  <main class="content">
    <section class="tool-grid">
      <article class="tool-card">
        <header class="section-header">
          <p class="section-label">Trim by timestamps</p>
          <h2>Trim GPX by time window</h2>
          <p class="muted-text">Send your GPX file with start and end times to crop the track.</p>
        </header>

        <form class="form-grid" on:submit|preventDefault={submitTrimByTime}>
          <label>
            GPX file
            <input
              type="file"
              accept=".gpx,application/gpx+xml"
              on:change={(event) =>
                (trimByTime = { ...trimByTime, gpxFile: event.target.files?.[0] ?? null })}
              required
            />
          </label>
          <label>
            Optional video file
            <input
              type="file"
              accept="video/*"
              on:change={async (event) => {
                const file = event.target.files?.[0] ?? null;
                trimByTime = { ...trimByTime, videoFile: file };
                if (!file) return;
                try {
                  const { start, end } = await deriveVideoTimes(file);
                  trimByTime = {
                    ...trimByTime,
                    videoFile: file,
                    startLocal: toLocalDateTimeValue(start),
                    endLocal: toLocalDateTimeValue(end),
                    error: ''
                  };
                } catch (error) {
                  trimByTime = { ...trimByTime, error: parseError(error, 'Unable to read video metadata.') };
                }
              }}
            />
          </label>
          <label>
            Start time
            <input type="datetime-local" step="1" bind:value={trimByTime.startLocal} required />
          </label>
          <label>
            End time
            <input type="datetime-local" step="1" bind:value={trimByTime.endLocal} required />
          </label>
          <div class="form-actions">
            <button type="submit" disabled={isBusy}>Trim track</button>
            <p class="hint">
              Add a video to auto-fill the start time from the file timestamp and the end time as start plus duration.
              Times are converted to UTC before sending to the API.
            </p>
          </div>
        </form>
        {#if trimByTime.error}
          <p class="error" role="alert">{trimByTime.error}</p>
        {/if}
        {#if trimByTime.message}
          <p class="success" aria-live="polite">{trimByTime.message}</p>
        {/if}
        {#if trimByTime.downloadUrl}
          <a class="download" href={trimByTime.downloadUrl} download={trimByTime.filename}>Download {trimByTime.filename}</a>
        {/if}
      </article>
    </section>

    <section class="tool-card wide">
      <header class="section-header">
        <p class="section-label">Route animation</p>
        <h2>Render map animation</h2>
        <p class="muted-text">Send your GPX to the API to render an MP4 route animation.</p>
      </header>

      <form class="form-grid" on:submit|preventDefault={submitMapAnimation}>
        <label>
          GPX file
          <input
            type="file"
            accept=".gpx,application/gpx+xml"
            on:change={async (event) => {
              const file = event.target.files?.[0] ?? null;
              let durationSeconds = mapAnimation.durationSeconds;
              if (file) {
                const parsedDuration = await parseGpxDuration(file);
                if (parsedDuration) {
                  durationSeconds = parsedDuration;
                }
              }
              mapAnimation = { ...mapAnimation, gpxFile: file, durationSeconds };
            }}
            required
          />
        </label>
        <label>
          Duration (seconds)
          <input
            type="number"
            min="1"
            step="1"
            bind:value={mapAnimation.durationSeconds}
            placeholder="45"
            required
          />
        </label>
        <div class="options-group">
          <p class="options-title">Output size</p>
          <div class="options-grid">
            <label>
              Resolution width (px)
              <input
                type="number"
                min="1"
                step="1"
                bind:value={mapAnimation.resolutionWidth}
                placeholder="1024"
                required
              />
            </label>
            <label>
              Resolution height (px)
              <input
                type="number"
                min="1"
                step="1"
                bind:value={mapAnimation.resolutionHeight}
                placeholder="1024"
                required
              />
            </label>
          </div>
        </div>
        <div class="options-group">
          <p class="options-title">Map tiles</p>
          <div class="options-grid">
            <label>
              Tile style
              <select bind:value={mapAnimation.tileType}>
                {#each mapTileOptions as option}
                  <option value={option.value}>{option.label}</option>
                {/each}
              </select>
            </label>
          </div>
        </div>
        <div class="options-group">
          <p class="options-title">Style options</p>
          <div class="options-grid">
            <label>
              Marker color
              <input type="color" bind:value={mapAnimation.markerColor} />
            </label>
            <label>
              Marker size (px)
              <input
                type="number"
                min="1"
                step="0.5"
                bind:value={mapAnimation.markerSize}
                placeholder="6"
              />
            </label>
            <label>
              Animated trail color
              <input type="color" bind:value={mapAnimation.trailColor} />
            </label>
            <label>
              Full trail color
              <input type="color" bind:value={mapAnimation.fullTrailColor} />
            </label>
            <label>
              Full trail opacity
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                bind:value={mapAnimation.fullTrailOpacity}
                placeholder="0.8"
              />
            </label>
            <label>
              Line width (px)
              <input
                type="number"
                min="0.5"
                step="0.1"
                bind:value={mapAnimation.lineWidth}
                placeholder="2.5"
              />
            </label>
            <label>
              Animated line opacity
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                bind:value={mapAnimation.lineOpacity}
                placeholder="1"
              />
            </label>
          </div>
        </div>
        <div class="form-actions">
          <button type="submit" disabled={isBusy}>Render animation</button>
          <p class="hint">Duration auto-fills from the GPX timestamps when available.</p>
        </div>
      </form>
      {#if mapAnimation.error}
        <p class="error" role="alert">{mapAnimation.error}</p>
      {/if}
      {#if mapAnimation.message}
        <p class="success" aria-live="polite">{mapAnimation.message}</p>
      {/if}
      {#if mapAnimation.downloadUrl}
        <a class="download" href={mapAnimation.downloadUrl} download={mapAnimation.filename}>Download {mapAnimation.filename}</a>
      {/if}
    </section>
  </main>

  <footer class="site-footer">
    <div>
      <strong>GPX Helper</strong>
      <p>Copyleft {currentYear} · Built for streamlined GPX and video workflows.</p>
    </div>
    <a class="ghost github-link" href="https://github.com/pooriat/GPX_helper" target="_blank" rel="noreferrer">
      <svg aria-hidden="true" viewBox="0 0 16 16" class="github-icon">
        <path
          fill="currentColor"
          d="M8 0C3.58 0 0 3.58 0 8a8 8 0 005.47 7.59c.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.2 1.87.86 2.33.66.07-.52.28-.86.51-1.06-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.01.08-2.1 0 0 .67-.21 2.2.82a7.62 7.62 0 012 0c1.53-1.04 2.2-.82 2.2-.82.44 1.09.16 1.9.08 2.1.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.19 0 .21.15.46.55.38A8 8 0 0016 8c0-4.42-3.58-8-8-8z"
        />
      </svg>
      <span>GitHub</span>
    </a>
  </footer>
</div>
