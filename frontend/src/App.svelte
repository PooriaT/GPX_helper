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
      if (!mapAnimation.durationSeconds) {
        const parsedDuration = await parseGpxDuration(mapAnimation.gpxFile);
        if (parsedDuration) {
          mapAnimation = { ...mapAnimation, durationSeconds: parsedDuration };
        }
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

</script>

<svelte:head>
  <meta
    name="description"
    content="Run the GPX Helper API from the browser to trim GPX files or render route animations."
  />
</svelte:head>

<div class="page-shell">
  <header class="hero">
    <h1>Run the GPX Helper API from the browser.</h1>
    <p class="lede">
      Upload a GPX track, pair it with video metadata, and export trimmed tracks or map animations without leaving the
      page.
    </p>
  </header>

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
                  const duration = await loadVideoDuration(file);
                  const end = new Date(file.lastModified);
                  const start = new Date(end.getTime() - duration * 1000);
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
            <input type="datetime-local" bind:value={trimByTime.startLocal} required />
          </label>
          <label>
            End time
            <input type="datetime-local" bind:value={trimByTime.endLocal} required />
          </label>
          <div class="form-actions">
            <button type="submit">Trim track</button>
            <p class="hint">
              Add a video to auto-fill the end time from the file timestamp and the start time as end minus duration.
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

      <article class="tool-card">
        <header class="section-header">
          <p class="section-label">Video-assisted trim</p>
          <h2>Trim GPX using video</h2>
          <p class="muted-text">Upload the GPX and companion video to crop the track to the clip duration.</p>
        </header>

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
      <p>GPX + video workflows, now directly wired to the FastAPI backend.</p>
    </div>
    <a class="ghost" href="https://github.com/OpenAI-Tools/GPX_helper" target="_blank" rel="noreferrer">
      View the repository
    </a>
  </footer>
</div>
