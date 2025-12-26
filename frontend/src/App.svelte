<script>
  import { onDestroy, onMount } from 'svelte';

  const DEFAULT_API_BASE = (import.meta.env.VITE_API_BASE ?? 'http://localhost:8000').replace(/\/$/, '');

  let apiBaseInput = DEFAULT_API_BASE;
  let apiBase = DEFAULT_API_BASE;

  let healthStatus = 'checking';
  let healthMessage = 'Looking for the API...';
  let capabilities = [];
  let apiVersion = '';
  let capabilitiesError = '';

  let trimByTime = {
    startLocal: '',
    endLocal: '',
    gpxFile: null,
    status: 'idle',
    error: '',
    downloadUrl: '',
    filename: '',
    message: ''
  };

  let trimByVideo = {
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
    resolution: '1920x1080',
    status: 'idle',
    error: '',
    downloadUrl: '',
    filename: '',
    message: ''
  };

  const resolutionPresets = ['1920x1080', '1280x720', '1024x768', '1024x1024'];

  onMount(() => {
    refreshApiStatus();
  });

  onDestroy(() => {
    [trimByTime, trimByVideo, mapAnimation].forEach((state) => {
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

  async function refreshApiStatus() {
    healthStatus = 'checking';
    healthMessage = 'Checking availability...';
    capabilitiesError = '';

    try {
      const healthResponse = await fetch(`${apiBase}/api/v1/health`);
      if (!healthResponse.ok) {
        throw new Error(`Health request failed (${healthResponse.status})`);
      }
      const body = await healthResponse.json();
      healthStatus = body?.status === 'ok' ? 'ready' : 'warning';
      healthMessage = body?.service ? `Online: ${body.service}` : 'Health endpoint responded';
    } catch (error) {
      healthStatus = 'error';
      healthMessage = parseError(error, 'Could not reach the API');
      capabilities = [];
      apiVersion = '';
      return;
    }

    try {
      const capsResponse = await fetch(`${apiBase}/api/v1/capabilities`);
      if (!capsResponse.ok) {
        throw new Error(`Capabilities request failed (${capsResponse.status})`);
      }
      const body = await capsResponse.json();
      capabilities = body?.endpoints ?? [];
      apiVersion = body?.version ?? '';
    } catch (error) {
      capabilities = [];
      apiVersion = '';
      capabilitiesError = parseError(error, 'Could not load capabilities');
    }
  }

  function applyApiBase() {
    apiBase = apiBaseInput.trim().replace(/\/$/, '');
    refreshApiStatus();
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

  async function submitTrimByTime() {
    if (trimByTime.downloadUrl) {
      URL.revokeObjectURL(trimByTime.downloadUrl);
    }
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
    }
  }

  async function submitTrimByVideo() {
    if (trimByVideo.downloadUrl) {
      URL.revokeObjectURL(trimByVideo.downloadUrl);
    }
    trimByVideo = {
      ...trimByVideo,
      status: 'loading',
      error: '',
      message: '',
      downloadUrl: '',
      filename: ''
    };

    try {
      if (!trimByVideo.gpxFile || !trimByVideo.videoFile) {
        throw new Error('Upload both the GPX track and the matching video.');
      }

      const formData = new FormData();
      formData.append('gpx_file', trimByVideo.gpxFile);
      formData.append('video_file', trimByVideo.videoFile);

      const { blob, filename } = await requestFile('/api/v1/gpx/trim-by-video', formData, 'trimmed.gpx');
      const downloadUrl = URL.createObjectURL(blob);
      trimByVideo = {
        ...trimByVideo,
        status: 'success',
        downloadUrl,
        filename,
        message: `Trimmed ${trimByVideo.gpxFile.name} using ${trimByVideo.videoFile.name}.`
      };
    } catch (error) {
      trimByVideo = { ...trimByVideo, status: 'error', error: parseError(error) };
    }
  }

  async function submitMapAnimation() {
    if (mapAnimation.downloadUrl) {
      URL.revokeObjectURL(mapAnimation.downloadUrl);
    }
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
      if (!mapAnimation.durationSeconds || mapAnimation.durationSeconds <= 0) {
        throw new Error('Duration must be greater than zero.');
      }
      if (!mapAnimation.resolution) {
        throw new Error('Pick a resolution for the export.');
      }

      const formData = new FormData();
      formData.append('gpx_file', mapAnimation.gpxFile);
      formData.append('duration_seconds', String(mapAnimation.durationSeconds));
      formData.append('resolution', mapAnimation.resolution);

      const { blob, filename } = await requestFile('/api/v1/gpx/map-animate', formData, 'route.mp4');
      const downloadUrl = URL.createObjectURL(blob);
      mapAnimation = {
        ...mapAnimation,
        status: 'success',
        downloadUrl,
        filename,
        message: `Rendered ${filename} (${mapAnimation.resolution}, ${mapAnimation.durationSeconds}s).`
      };
    } catch (error) {
      mapAnimation = { ...mapAnimation, status: 'error', error: parseError(error) };
    }
  }

  function statusTone(state) {
    if (state === 'success' || state === 'ready') return 'positive';
    if (state === 'loading') return 'info';
    if (state === 'warning') return 'warning';
    if (state === 'error') return 'danger';
    return 'muted';
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
    <div class="hero__copy">
      <p class="pill">GPX Helper</p>
      <h1>Run the GPX Helper API from the browser.</h1>
      <p class="lede">
        Upload a GPX track, pair it with video metadata, and export trimmed tracks or map animations without leaving the
        page.
      </p>
      <div class="status-bar">
        <span class={`chip ${statusTone(healthStatus)}`}>Health: {healthMessage}</span>
        {#if apiVersion}
          <span class="chip muted">API {apiVersion}</span>
        {/if}
        <span class="chip muted">Base: {apiBase}</span>
      </div>
    </div>

    <form class="api-card" on:submit|preventDefault={applyApiBase}>
      <div class="api-card__header">
        <p class="eyebrow">API connection</p>
        <button class="ghost" type="button" on:click={refreshApiStatus}>Refresh</button>
      </div>
      <label for="api-base">API base URL</label>
      <div class="input-row">
        <input
          id="api-base"
          name="api-base"
          type="url"
          placeholder="http://localhost:8000"
          bind:value={apiBaseInput}
          required
        />
        <button type="submit">Connect</button>
      </div>
      <p class="hint">Defaults to the local FastAPI server at http://localhost:8000.</p>
      <div class="api-status">
        <span class={`chip ${statusTone(healthStatus)}`}>{healthMessage}</span>
        {#if capabilitiesError}
          <p class="error" role="alert">{capabilitiesError}</p>
        {/if}
      </div>
    </form>
  </header>

  <main class="content">
    <section class="panel">
      <div class="panel__header">
        <div>
          <p class="eyebrow">Endpoints</p>
          <h2>Available API routes</h2>
        </div>
        <button class="ghost" type="button" on:click={refreshApiStatus}>Re-check</button>
      </div>
      {#if capabilities.length}
        <ul class="endpoint-list">
          {#each capabilities as endpoint}
            <li>{endpoint}</li>
          {/each}
        </ul>
      {:else}
        <p class="muted-text">Capabilities load after the API responds.</p>
      {/if}
    </section>

    <section class="tool-grid">
      <article class="tool-card">
        <div class="panel__header">
          <div>
            <p class="eyebrow">Trim by timestamps</p>
            <h3>Trim GPX by time window</h3>
            <p class="muted-text">Send your GPX file with start and end times to crop the track.</p>
          </div>
          <span class={`chip ${statusTone(trimByTime.status)}`}>
            {trimByTime.status === 'idle'
              ? 'Waiting'
              : trimByTime.status === 'loading'
                ? 'Processing...'
                : trimByTime.status === 'success'
                  ? 'Done'
                  : 'Needs attention'}
          </span>
        </div>

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
            Start time
            <input type="datetime-local" bind:value={trimByTime.startLocal} required />
          </label>
          <label>
            End time
            <input type="datetime-local" bind:value={trimByTime.endLocal} required />
          </label>
          <div class="form-actions">
            <button type="submit">Trim track</button>
            <p class="hint">Times are converted to UTC before sending to the API.</p>
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

      <article class="tool-card">
        <div class="panel__header">
          <div>
            <p class="eyebrow">Video-assisted trim</p>
            <h3>Trim GPX using video</h3>
            <p class="muted-text">Upload the GPX and companion video to crop the track to the clip duration.</p>
          </div>
          <span class={`chip ${statusTone(trimByVideo.status)}`}>
            {trimByVideo.status === 'idle'
              ? 'Waiting'
              : trimByVideo.status === 'loading'
                ? 'Processing...'
                : trimByVideo.status === 'success'
                  ? 'Done'
                  : 'Needs attention'}
          </span>
        </div>

        <form class="form-grid" on:submit|preventDefault={submitTrimByVideo}>
          <label>
            GPX file
            <input
              type="file"
              accept=".gpx,application/gpx+xml"
              on:change={(event) =>
                (trimByVideo = { ...trimByVideo, gpxFile: event.target.files?.[0] ?? null })}
              required
            />
          </label>
          <label>
            Video file
            <input
              type="file"
              accept="video/*"
              on:change={(event) =>
                (trimByVideo = { ...trimByVideo, videoFile: event.target.files?.[0] ?? null })}
              required
            />
          </label>
          <div class="form-actions">
            <button type="submit">Trim with video</button>
            <p class="hint">Uses metadata if available, otherwise falls back to file timestamps.</p>
          </div>
        </form>
        {#if trimByVideo.error}
          <p class="error" role="alert">{trimByVideo.error}</p>
        {/if}
        {#if trimByVideo.message}
          <p class="success" aria-live="polite">{trimByVideo.message}</p>
        {/if}
        {#if trimByVideo.downloadUrl}
          <a class="download" href={trimByVideo.downloadUrl} download={trimByVideo.filename}>Download {trimByVideo.filename}</a>
        {/if}
      </article>
    </section>

    <section class="tool-card wide">
      <div class="panel__header">
        <div>
          <p class="eyebrow">Route animation</p>
          <h3>Render map animation</h3>
          <p class="muted-text">Send your GPX to the API to render an MP4 route animation.</p>
        </div>
        <span class={`chip ${statusTone(mapAnimation.status)}`}>
          {mapAnimation.status === 'idle'
            ? 'Waiting'
            : mapAnimation.status === 'loading'
              ? 'Processing...'
              : mapAnimation.status === 'success'
                ? 'Done'
                : 'Needs attention'}
        </span>
      </div>

      <form class="form-grid" on:submit|preventDefault={submitMapAnimation}>
        <label>
          GPX file
          <input
            type="file"
            accept=".gpx,application/gpx+xml"
            on:change={(event) =>
              (mapAnimation = { ...mapAnimation, gpxFile: event.target.files?.[0] ?? null })}
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
        <label>
          Resolution
          <select bind:value={mapAnimation.resolution}>
            {#each resolutionPresets as preset}
              <option value={preset}>{preset}</option>
            {/each}
          </select>
        </label>
        <div class="form-actions">
          <button type="submit">Render animation</button>
          <p class="hint">The backend renders a 30 fps MP4 for the selected resolution.</p>
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
      <p>GPX + video workflows, now directly wired to the FastAPI backend.</p>
    </div>
    <a class="ghost" href="https://github.com/OpenAI-Tools/GPX_helper" target="_blank" rel="noreferrer">
      View the repository
    </a>
  </footer>
</div>
