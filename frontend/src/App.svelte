<script>
  import { onDestroy, onMount } from 'svelte';
  import { parseGpxDurationFromText, parseGpxTimeRangeFromText } from './gpx-metadata';
  import { loadEmbeddedVideoStart } from './video-metadata';

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

  let trimByVideos = {
    gpxFile: null,
    videoFiles: [],
    clips: [],
    totalDurationSeconds: 0,
    isPreparing: false,
    status: 'idle',
    error: '',
    downloadUrl: '',
    filename: '',
    message: ''
  };

  let mapAnimation = {
    gpxFile: null,
    durationSeconds: 45,
    fps: 30,
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

  const mapTilePreviewUrls = {
    osm: 'https://tile.openstreetmap.org/12/654/1582.png',
    cyclosm: 'https://a.tile-cyclosm.openstreetmap.fr/cyclosm/12/654/1582.png',
    opentopomap: 'https://a.tile.opentopomap.org/12/654/1582.png'
  };

  const pages = [
    { id: 'trim', href: '#/trim', label: 'Trim GPX' },
    { id: 'animation', href: '#/animation', label: 'Route animation' },
    { id: 'about', href: '#/about', label: 'About' }
  ];
  const defaultPage = pages[0].id;

  let activeRequestLabel = '';
  let estimatedSeconds = null;
  let trimByVideosSelectionId = 0;
  let currentPage = defaultPage;

  $: isBusy = [trimByTime, trimByVideos, mapAnimation].some((state) => state.status === 'loading');
  $: currentMapTileOption =
    mapTileOptions.find((option) => option.value === mapAnimation.tileType) ?? mapTileOptions[0];
  $: currentMapTilePreview = mapTilePreviewUrls[mapAnimation.tileType] ?? null;
  $: activePage = pages.find((page) => page.id === currentPage) ?? pages[0];

  function normalizeHash(hash) {
    const route = hash.replace(/^#\/?/, '').split(/[?#]/)[0].toLowerCase();
    return pages.some((page) => page.id === route) ? route : defaultPage;
  }

  function syncPageFromHash(replace = false) {
    if (typeof window === 'undefined') {
      return;
    }

    const nextPage = normalizeHash(window.location.hash);
    currentPage = nextPage;

    const normalizedHash = `#/${nextPage}`;
    if (window.location.hash !== normalizedHash) {
      if (replace) {
        window.history.replaceState(null, '', normalizedHash);
      } else {
        window.location.hash = normalizedHash;
      }
    }
  }

  onMount(() => {
    syncPageFromHash(true);
  });

  onDestroy(() => {
    [trimByTime, trimByVideos, mapAnimation].forEach((state) => {
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

  function deriveMp4Filename(file, fallback) {
    const name = file?.name;
    if (!name) return fallback;
    const base = name.replace(/\.[^./\\]+$/, '');
    if (!base) return fallback;
    return `${base}.mp4`;
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

  function formatDurationLabel(totalSeconds) {
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
    const [durationSeconds, start] = await Promise.all([
      loadVideoDuration(file),
      loadEmbeddedVideoStart(file)
    ]);
    const end = new Date(start.getTime() + durationSeconds * 1000);
    return { durationSeconds, start, end };
  }

  async function buildVideoClip(file, index) {
    const { durationSeconds, start, end } = await deriveVideoTimes(file);
    return {
      id: `${file.name}-${file.size}-${index}`,
      name: file.name,
      durationSeconds,
      startIso: start.toISOString(),
      endIso: end.toISOString(),
      startLocal: toLocalDateTimeValue(start),
      endLocal: toLocalDateTimeValue(end)
    };
  }

  async function parseGpxDuration(file) {
    if (!file) return null;
    const text = await readFileText(file);
    return parseGpxDurationFromText(text);
  }

  async function parseGpxTimeRange(file) {
    if (!file) return null;
    const text = await readFileText(file);
    return parseGpxTimeRangeFromText(text);
  }

  function formatUtcLabel(value) {
    return value.toISOString().replace('.000Z', 'Z');
  }

  function buildVideoRangeError(label, start, end, gpxRange) {
    return `${label} spans ${formatUtcLabel(start)} to ${formatUtcLabel(end)}, but the GPX track only covers ${formatUtcLabel(gpxRange.start)} to ${formatUtcLabel(gpxRange.end)}.`;
  }

  async function ensureRangeFitsGpx(label, start, end, gpxFile) {
    if (!gpxFile) {
      return;
    }

    const gpxRange = await parseGpxTimeRange(gpxFile);
    if (!gpxRange) {
      throw new Error('The GPX file does not contain readable timestamps.');
    }

    if (start < gpxRange.start || end > gpxRange.end) {
      throw new Error(buildVideoRangeError(label, start, end, gpxRange));
    }
  }

  async function ensureVideoFitsGpx(videoFile, gpxFile) {
    if (!videoFile || !gpxFile) {
      return;
    }

    const videoRange = await deriveVideoTimes(videoFile);
    await ensureRangeFitsGpx(`Video "${videoFile.name}"`, videoRange.start, videoRange.end, gpxFile);
  }

  async function ensureVideosFitGpx(clips, gpxFile) {
    if (!clips.length || !gpxFile) {
      return;
    }

    const gpxRange = await parseGpxTimeRange(gpxFile);
    if (!gpxRange) {
      throw new Error('The GPX file does not contain readable timestamps.');
    }

    const mismatchedClip = clips.find((clip) => {
      const start = new Date(clip.startIso);
      const end = new Date(clip.endIso);
      return start < gpxRange.start || end > gpxRange.end;
    });

    if (mismatchedClip) {
      throw new Error(
        buildVideoRangeError(
          `Video "${mismatchedClip.name}"`,
          new Date(mismatchedClip.startIso),
          new Date(mismatchedClip.endIso),
          gpxRange
        )
      );
    }
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
      const startDate = new Date(startIso);
      const endDate = new Date(endIso);
      if (startDate >= endDate) {
        throw new Error('Start time must be before end time.');
      }
      await ensureRangeFitsGpx('Selected trim range', startDate, endDate, trimByTime.gpxFile);

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

  async function submitTrimByVideos() {
    if (trimByVideos.downloadUrl) {
      URL.revokeObjectURL(trimByVideos.downloadUrl);
    }
    startRequest('Trimming GPX by multiple videos...');
    trimByVideos = {
      ...trimByVideos,
      isPreparing: false,
      status: 'loading',
      error: '',
      message: '',
      downloadUrl: '',
      filename: ''
    };

    try {
      if (!trimByVideos.gpxFile) {
        throw new Error('Upload a GPX track to trim.');
      }
      if (!trimByVideos.clips.length) {
        throw new Error('Add at least one video file.');
      }
      await ensureVideosFitGpx(trimByVideos.clips, trimByVideos.gpxFile);

      const formData = new FormData();
      formData.append('gpx_file', trimByVideos.gpxFile);
      formData.append(
        'clips_json',
        JSON.stringify(
          trimByVideos.clips.map((clip) => ({
            start_time: clip.startIso,
            end_time: clip.endIso,
            duration_seconds: clip.durationSeconds
          }))
        )
      );

      const { blob, filename } = await requestFile(
        '/api/v1/gpx/trim-by-videos',
        formData,
        'trimmed-gpx-files.zip'
      );
      const downloadUrl = URL.createObjectURL(blob);
      trimByVideos = {
        ...trimByVideos,
        status: 'success',
        downloadUrl,
        filename,
        message: `Prepared ${trimByVideos.clips.length} trimmed GPX files from ${trimByVideos.videoFiles.length} videos.`
      };
    } catch (error) {
      trimByVideos = { ...trimByVideos, status: 'error', error: parseError(error) };
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
      if (!mapAnimation.fps || mapAnimation.fps <= 0) {
        throw new Error('Frames per second must be greater than zero.');
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
      formData.append('fps', String(mapAnimation.fps));
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

      const fallbackName = deriveMp4Filename(mapAnimation.gpxFile, 'route.mp4');
      const { blob, filename } = await requestFile('/api/v1/gpx/map-animate', formData, fallbackName);
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

<svelte:window on:hashchange={() => syncPageFromHash()} />

<svelte:head>
  <title>{activePage.label} · GPX Helper</title>
  <meta
    name="description"
    content="Run the GPX Helper API from the browser to trim GPX files or render route animations."
  />
</svelte:head>

<div class="app-shell">
  <header class="app-header">
    <div class="brand-block">
      <p class="brand-mark">GPX Helper</p>
    </div>
    <div class="header-links">
      <a class="secondary-link contributor-link" href="https://www.youtube.com/@EclipseValley" target="_blank" rel="noreferrer">
        <svg aria-hidden="true" viewBox="0 0 24 24" class="youtube-icon">
          <path
            fill="currentColor"
            d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.4 3.5 12 3.5 12 3.5s-7.4 0-9.4.6A3 3 0 0 0 .5 6.2 31.4 31.4 0 0 0 0 12a31.4 31.4 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c2 .6 9.4.6 9.4.6s7.4 0 9.4-.6a3 3 0 0 0 2.1-2.1A31.4 31.4 0 0 0 24 12a31.4 31.4 0 0 0-.5-5.8ZM9.6 15.6V8.4l6.2 3.6-6.2 3.6Z"
          />
        </svg>
        <span>EclipseValley</span>
      </a>
      <a class="secondary-link github-link" href="https://github.com/pooriat/GPX_helper" target="_blank" rel="noreferrer">
        <svg aria-hidden="true" viewBox="0 0 16 16" class="github-icon">
          <path
            fill="currentColor"
            d="M8 0C3.58 0 0 3.58 0 8a8 8 0 0 0 5.47 7.59c.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.2 1.87.86 2.33.66.07-.52.28-.86.51-1.06-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.01.08-2.1 0 0 .67-.21 2.2.82a7.62 7.62 0 0 1 2 0c1.53-1.04 2.2-.82 2.2-.82.44 1.09.16 1.9.08 2.1.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.19 0 .21.15.46.55.38A8 8 0 0 0 16 8c0-4.42-3.58-8-8-8z"
          />
        </svg>
        <span>GitHub</span>
      </a>
    </div>
  </header>

  <section class="workspace-bar">
    <h1>{activePage.label}</h1>
    <nav class="workspace-tabs" aria-label="Main menu">
      {#each pages as page}
        <a
          href={page.href}
          class:workspace-tab-active={currentPage === page.id}
          aria-current={currentPage === page.id ? 'page' : undefined}
        >
          {page.label}
        </a>
      {/each}
    </nav>
  </section>

  {#if isBusy}
    <div class="loading-banner" role="status" aria-live="polite">
      <div class="spinner" aria-hidden="true"></div>
      <div class="loading-copy">
        <p class="loading-title">{activeRequestLabel || 'Working on your request...'}</p>
        <p class="muted-text">
          {#if estimatedSeconds}
            Estimated wait: ~{Math.max(1, Math.round(estimatedSeconds))} seconds.
          {:else}
            Preparing request.
          {/if}
        </p>
      </div>
    </div>
  {/if}

  <main class="content">
    {#if currentPage === 'trim'}
      <section class="workflow-grid">
        <article class="tool-card workflow-card">
          <header class="section-header">
            <h2>Trim by time</h2>
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
                    trimByTime = {
                      ...trimByTime,
                      error: parseError(error, 'Unable to read video metadata.')
                    };
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
            </div>
          </form>
          {#if trimByTime.error}
            <p class="error" role="alert">{trimByTime.error}</p>
          {/if}
          {#if trimByTime.message}
            <p class="success" aria-live="polite">{trimByTime.message}</p>
          {/if}
          {#if trimByTime.downloadUrl}
            <a class="download" href={trimByTime.downloadUrl} download={trimByTime.filename}>
              Download {trimByTime.filename}
            </a>
          {/if}
        </article>

        <article class="tool-card workflow-card workflow-card-emphasis">
          <header class="section-header">
            <h2>Split by videos</h2>
          </header>

          <form class="form-grid" on:submit|preventDefault={submitTrimByVideos}>
            <label>
              GPX file
              <input
                type="file"
                accept=".gpx,application/gpx+xml"
                on:change={(event) =>
                  (trimByVideos = {
                    ...trimByVideos,
                    gpxFile: event.target.files?.[0] ?? null,
                    error: ''
                  })}
                required
              />
            </label>
            <label>
              Video files
              <input
                type="file"
                accept="video/*"
                multiple
                on:change={async (event) => {
                  const selectionId = ++trimByVideosSelectionId;
                  const files = Array.from(event.target.files ?? []);

                  trimByVideos = {
                    ...trimByVideos,
                    videoFiles: files,
                    clips: [],
                    totalDurationSeconds: 0,
                    isPreparing: files.length > 0,
                    error: '',
                    message: '',
                    status: 'idle'
                  };

                  if (!files.length) {
                    return;
                  }

                  try {
                    const clips = await Promise.all(files.map((file, index) => buildVideoClip(file, index)));
                    if (selectionId !== trimByVideosSelectionId) {
                      return;
                    }

                    const totalDurationSeconds = clips.reduce((sum, clip) => sum + clip.durationSeconds, 0);
                    trimByVideos = {
                      ...trimByVideos,
                      videoFiles: files,
                      clips,
                      totalDurationSeconds,
                      isPreparing: false,
                      status: 'idle',
                      error: ''
                    };
                  } catch (error) {
                    if (selectionId !== trimByVideosSelectionId) {
                      return;
                    }
                    trimByVideos = {
                      ...trimByVideos,
                      videoFiles: files,
                      clips: [],
                      totalDurationSeconds: 0,
                      isPreparing: false,
                      status: 'idle',
                      error: parseError(error, 'Unable to read video metadata.')
                    };
                  }
                }}
                required
              />
            </label>
            <div class="options-group">
              <p class="options-title">Clips</p>
              {#if trimByVideos.clips.length}
                <p class="hint">{trimByVideos.clips.length} clips · {formatDurationLabel(trimByVideos.totalDurationSeconds)}</p>
                <div class="clip-list" aria-live="polite">
                  {#each trimByVideos.clips as clip, index (clip.id)}
                    <div class="clip-item">
                      <p class="clip-title">{index + 1}.gpx</p>
                      <p class="clip-meta">{clip.name}</p>
                      <p class="clip-meta">
                        {clip.startLocal} to {clip.endLocal} · {formatDurationLabel(clip.durationSeconds)}
                      </p>
                    </div>
                  {/each}
                </div>
              {:else if trimByVideos.isPreparing}
                <p class="hint">Reading video metadata.</p>
              {:else}
                <p class="hint">No videos selected.</p>
              {/if}
            </div>
            <div class="form-actions">
              <button type="submit" disabled={isBusy || trimByVideos.isPreparing}>Create ZIP</button>
            </div>
          </form>
          {#if trimByVideos.error}
            <p class="error" role="alert">{trimByVideos.error}</p>
          {/if}
          {#if trimByVideos.message}
            <p class="success" aria-live="polite">{trimByVideos.message}</p>
          {/if}
          {#if trimByVideos.downloadUrl}
            <a class="download" href={trimByVideos.downloadUrl} download={trimByVideos.filename}>
              Download {trimByVideos.filename}
            </a>
          {/if}
        </article>
      </section>
    {:else if currentPage === 'animation'}
      <section class="tool-card wide">
        <header class="section-header">
          <h2>Render animation</h2>
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
          <div class="animation-inline-fields">
            <label class="compact-field">
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
            <label class="compact-field">
              Frames per second (fps)
              <input
                type="number"
                min="1"
                step="1"
                bind:value={mapAnimation.fps}
                placeholder="30"
                required
              />
            </label>
          </div>
          <div class="options-row">
            <div class="options-group">
              <p class="options-title">Output size</p>
              <div class="options-stack">
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
              <div class="options-stack">
                <figure class="tile-preview">
                  {#if currentMapTilePreview}
                    <img
                      src={currentMapTilePreview}
                      alt={`${currentMapTileOption.label} map tile preview`}
                      loading="lazy"
                    />
                    <figcaption>{currentMapTileOption.label}</figcaption>
                  {:else}
                    <figcaption>{currentMapTileOption.label}. No preview available.</figcaption>
                  {/if}
                </figure>
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
          </div>
          <div class="options-group">
            <p class="options-title">Style options</p>
            <div class="options-grid">
              <label>
                Marker color
                <div class="color-control">
                  <input
                    class="color-picker"
                    type="color"
                    bind:value={mapAnimation.markerColor}
                    style={`--picker-color: ${mapAnimation.markerColor};`}
                  />
                  <span class="color-value">{mapAnimation.markerColor}</span>
                </div>
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
                <div class="color-control">
                  <input
                    class="color-picker"
                    type="color"
                    bind:value={mapAnimation.trailColor}
                    style={`--picker-color: ${mapAnimation.trailColor};`}
                  />
                  <span class="color-value">{mapAnimation.trailColor}</span>
                </div>
              </label>
              <label>
                Full trail color
                <div class="color-control">
                  <input
                    class="color-picker"
                    type="color"
                    bind:value={mapAnimation.fullTrailColor}
                    style={`--picker-color: ${mapAnimation.fullTrailColor};`}
                  />
                  <span class="color-value">{mapAnimation.fullTrailColor}</span>
                </div>
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
          </div>
        </form>
        {#if mapAnimation.error}
          <p class="error" role="alert">{mapAnimation.error}</p>
        {/if}
        {#if mapAnimation.message}
          <p class="success" aria-live="polite">{mapAnimation.message}</p>
        {/if}
        {#if mapAnimation.downloadUrl}
          <a class="download" href={mapAnimation.downloadUrl} download={mapAnimation.filename}>
            Download {mapAnimation.filename}
          </a>
        {/if}
      </section>
    {:else}
      <section class="about-grid">
        <article class="tool-card about-card">
          <header class="section-header">
            <h2>What this app does</h2>
          </header>
          <p class="muted-text">
            GPX Helper trims GPX tracks and renders route videos from the same browser UI.
          </p>
        </article>

        <article class="tool-card about-card">
          <header class="section-header">
            <h2>Trim GPX</h2>
          </header>
          <ul class="about-list">
            <li><strong>Trim by time:</strong> export one GPX file from a start and end time.</li>
            <li><strong>Split by videos:</strong> create one GPX segment per video and download them as a ZIP.</li>
            <li><strong>Optional video metadata:</strong> can fill clip times automatically when available.</li>
          </ul>
        </article>

        <article class="tool-card about-card">
          <header class="section-header">
            <h2>Route animation</h2>
          </header>
          <ul class="about-list">
            <li>Render the GPX route as an MP4.</li>
            <li>Adjust duration, frame rate, size, tiles, and route styling.</li>
            <li>Use it when you need a clean route preview or shareable map video.</li>
          </ul>
        </article>
      </section>
    {/if}
  </main>
</div>
