<script>
  import { onDestroy, onMount } from 'svelte';
  import AnimationPage from './components/AnimationPage.svelte';
  import AboutPage from './components/AboutPage.svelte';
  import LoadingBanner from './components/LoadingBanner.svelte';
  import TaskSelector from './components/TaskSelector.svelte';
  import TelemetryPage from './components/TelemetryPage.svelte';
  import TrimPage from './components/TrimPage.svelte';
  import { parseGpxDurationFromText, parseGpxTimeRangeFromText } from './gpx-metadata';
  import { loadEmbeddedVideoStart } from './video-metadata';
  import { cloneFormData, deriveMp4Filename, parseError, requestEta, requestFile } from './utils/api';
  import { readFileText, loadVideoDuration } from './utils/files';
  import { formatDurationLabel, formatUtcLabel, toIsoString, toLocalDateTimeValue } from './utils/time';

  const DEFAULT_API_BASE = (import.meta.env.VITE_API_BASE ?? 'http://localhost:8000').replace(/\/$/, '');
  let apiBase = DEFAULT_API_BASE;

  let trimByTime = { startLocal: '', endLocal: '', gpxFile: null, videoFile: null, status: 'idle', error: '', downloadUrl: '', filename: '', message: '' };
  let trimByVideos = { gpxFile: null, videoFiles: [], clips: [], totalDurationSeconds: 0, isPreparing: false, status: 'idle', error: '', downloadUrl: '', filename: '', message: '' };
  let mapAnimation = { gpxFile: null, durationSeconds: 45, fps: 30, resolutionWidth: 1024, resolutionHeight: 1024, tileType: '', markerColor: '#0ea5e9', trailColor: '#0ea5e9', fullTrailColor: '#111827', fullTrailOpacity: 0.8, markerSize: 6, lineWidth: 2.5, lineOpacity: 1, status: 'idle', error: '', downloadUrl: '', filename: '', message: '' };
  let telemetryVideo = { gpxFile: null, durationSeconds: 4, fps: 30, resolutionWidth: 1024, resolutionHeight: 1024, telemetryType: 'elevation_value', backgroundColor: 'transparent', status: 'idle', error: '', downloadUrl: '', filename: '', message: '' };

  const mapTileOptions = [
    { value: '', label: 'Backend default (configured tile provider)' },
    { value: 'osm', label: 'OpenStreetMap (Standard)' },
    { value: 'cyclosm', label: 'CyclOSM' },
    { value: 'opentopomap', label: 'OpenTopoMap (Topo)' }
  ];
  const telemetryTypeOptions = [
    { value: 'elevation_value', label: 'Elevation value' },
    { value: 'speed', label: 'Speed' },
    { value: 'heart_rate', label: 'Heart rate' },
    { value: 'elevation_graph', label: 'Elevation graph' }
  ];
  const tasks = [
    { id: 'trim', href: '#/trim', label: 'Trim GPX', description: 'Cut a track by timestamps or split it around recorded videos.' },
    { id: 'animation', href: '#/animation', label: 'Create route animation', description: 'Render a map-based MP4 animation from a GPX route.' },
    { id: 'telemetry', href: '#/telemetry', label: 'Generate telemetry video', description: 'Export an MP4 overlay with speed, elevation, or graph data.' }
  ];
  const pages = [
    { id: 'trim', href: '#/trim', label: 'Trim GPX' },
    { id: 'animation', href: '#/animation', label: 'Route animation' },
    { id: 'telemetry', href: '#/telemetry', label: 'Telemetry video' },
    { id: 'about', href: '#/about', label: 'About' }
  ];
  const pageDescriptions = {
    trim: 'Trim tracks by exact times or split them from video metadata.',
    animation: 'Render a clean MP4 route animation from a GPX track.',
    telemetry: 'Create telemetry-only videos for overlays and compositing.',
    about: 'A quick overview of the tools available in GPX Helper.'
  };
  const defaultPage = pages[0].id;

  let activeRequestLabel = '';
  let estimatedSeconds = null;
  let trimByVideosSelectionId = 0;
  let currentPage = defaultPage;

  $: isBusy = [trimByTime, trimByVideos, mapAnimation, telemetryVideo].some((state) => state.status === 'loading');
  $: activePage = pages.find((page) => page.id === currentPage) ?? pages[0];
  $: activePageDescription = pageDescriptions[currentPage] ?? pageDescriptions[defaultPage];
  $: selectedTask = tasks.some((task) => task.id === currentPage) ? currentPage : '';

  function normalizeHash(hash) {
    const route = hash.replace(/^#\/?/, '').split(/[?#]/)[0].toLowerCase();
    return pages.some((page) => page.id === route) ? route : defaultPage;
  }

  function syncPageFromHash(replace = false) {
    if (typeof window === 'undefined') return;
    const nextPage = normalizeHash(window.location.hash);
    currentPage = nextPage;
    const normalizedHash = `#/${nextPage}`;
    if (window.location.hash !== normalizedHash) {
      if (replace) window.history.replaceState(null, '', normalizedHash);
      else window.location.hash = normalizedHash;
    }
  }

  onMount(() => {
    syncPageFromHash(true);
  });

  onDestroy(() => {
    [trimByTime, trimByVideos, mapAnimation, telemetryVideo].forEach((state) => {
      if (state.downloadUrl) URL.revokeObjectURL(state.downloadUrl);
    });
  });

  function startRequest(label) {
    activeRequestLabel = label;
    estimatedSeconds = null;
  }

  function finishRequest() {
    activeRequestLabel = '';
    estimatedSeconds = null;
  }

  async function deriveVideoTimes(file) {
    const [durationSeconds, start] = await Promise.all([loadVideoDuration(file), loadEmbeddedVideoStart(file)]);
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

  function buildVideoRangeError(label, start, end, gpxRange) {
    return `${label} spans ${formatUtcLabel(start)} to ${formatUtcLabel(end)}, but the GPX track only covers ${formatUtcLabel(gpxRange.start)} to ${formatUtcLabel(gpxRange.end)}.`;
  }

  async function ensureRangeFitsGpx(label, start, end, gpxFile) {
    if (!gpxFile) return;
    const gpxRange = await parseGpxTimeRange(gpxFile);
    if (!gpxRange) throw new Error('The GPX file does not contain readable timestamps.');
    if (start < gpxRange.start || end > gpxRange.end) throw new Error(buildVideoRangeError(label, start, end, gpxRange));
  }

  async function ensureVideosFitGpx(clips, gpxFile) {
    if (!clips.length || !gpxFile) return;
    const gpxRange = await parseGpxTimeRange(gpxFile);
    if (!gpxRange) throw new Error('The GPX file does not contain readable timestamps.');

    const mismatchedClip = clips.find((clip) => {
      const start = new Date(clip.startIso);
      const end = new Date(clip.endIso);
      return start < gpxRange.start || end > gpxRange.end;
    });

    if (mismatchedClip) {
      throw new Error(buildVideoRangeError(`Video "${mismatchedClip.name}"`, new Date(mismatchedClip.startIso), new Date(mismatchedClip.endIso), gpxRange));
    }
  }

  async function submitTrimByTime() {
    if (trimByTime.downloadUrl) URL.revokeObjectURL(trimByTime.downloadUrl);
    startRequest('Trimming GPX by time...');
    trimByTime = { ...trimByTime, status: 'loading', error: '', message: '', downloadUrl: '', filename: '' };

    try {
      if (!trimByTime.gpxFile) throw new Error('Upload a GPX track to trim.');
      const startIso = toIsoString(trimByTime.startLocal, 'Start time');
      const endIso = toIsoString(trimByTime.endLocal, 'End time');
      const startDate = new Date(startIso);
      const endDate = new Date(endIso);
      if (startDate >= endDate) throw new Error('Start time must be before end time.');
      await ensureRangeFitsGpx('Selected trim range', startDate, endDate, trimByTime.gpxFile);

      const formData = new FormData();
      formData.append('gpx_file', trimByTime.gpxFile);
      formData.append('start_time', startIso);
      formData.append('end_time', endIso);

      const { blob, filename } = await requestFile(apiBase, '/api/v1/gpx/trim-by-time', formData, 'trimmed.gpx');
      const downloadUrl = URL.createObjectURL(blob);
      trimByTime = { ...trimByTime, status: 'success', downloadUrl, filename, message: `Trimmed ${trimByTime.gpxFile.name} between ${startIso} and ${endIso}.` };
    } catch (error) {
      trimByTime = { ...trimByTime, status: 'error', error: parseError(error) };
    } finally {
      finishRequest();
    }
  }

  async function submitTrimByVideos() {
    if (trimByVideos.downloadUrl) URL.revokeObjectURL(trimByVideos.downloadUrl);
    startRequest('Trimming GPX by multiple videos...');
    trimByVideos = { ...trimByVideos, isPreparing: false, status: 'loading', error: '', message: '', downloadUrl: '', filename: '' };

    try {
      if (!trimByVideos.gpxFile) throw new Error('Upload a GPX track to trim.');
      if (!trimByVideos.clips.length) throw new Error('Add at least one video file.');
      await ensureVideosFitGpx(trimByVideos.clips, trimByVideos.gpxFile);

      const formData = new FormData();
      formData.append('gpx_file', trimByVideos.gpxFile);
      formData.append('clips_json', JSON.stringify(trimByVideos.clips.map((clip) => ({ start_time: clip.startIso, end_time: clip.endIso, duration_seconds: clip.durationSeconds }))));

      const { blob, filename } = await requestFile(apiBase, '/api/v1/gpx/trim-by-videos', formData, 'trimmed-gpx-files.zip');
      const downloadUrl = URL.createObjectURL(blob);
      trimByVideos = { ...trimByVideos, status: 'success', downloadUrl, filename, message: `Prepared ${trimByVideos.clips.length} trimmed GPX files from ${trimByVideos.videoFiles.length} videos.` };
    } catch (error) {
      trimByVideos = { ...trimByVideos, status: 'error', error: parseError(error) };
    } finally {
      finishRequest();
    }
  }

  async function submitMapAnimation() {
    if (mapAnimation.downloadUrl) URL.revokeObjectURL(mapAnimation.downloadUrl);
    startRequest('Rendering map animation...');
    mapAnimation = { ...mapAnimation, status: 'loading', error: '', message: '', downloadUrl: '', filename: '' };

    try {
      if (!mapAnimation.gpxFile) throw new Error('Upload a GPX track to animate.');
      if (!mapAnimation.durationSeconds) {
        const parsedDuration = await parseGpxDuration(mapAnimation.gpxFile);
        if (parsedDuration) mapAnimation = { ...mapAnimation, durationSeconds: parsedDuration };
      }
      if (!mapAnimation.durationSeconds || mapAnimation.durationSeconds <= 0) throw new Error('Duration must be greater than zero.');
      if (!mapAnimation.fps || mapAnimation.fps <= 0) throw new Error('Frames per second must be greater than zero.');
      if (!mapAnimation.resolutionWidth || !mapAnimation.resolutionHeight) throw new Error('Enter a resolution for the export.');
      if (mapAnimation.resolutionWidth <= 0 || mapAnimation.resolutionHeight <= 0) throw new Error('Resolution must be greater than zero.');
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
      if (mapAnimation.tileType) formData.append('tile_type', mapAnimation.tileType);

      requestEta(apiBase, '/api/v1/gpx/map-animate/estimate', cloneFormData(formData)).then((eta) => {
        estimatedSeconds = eta;
      }).catch(() => {
        estimatedSeconds = null;
      });

      const fallbackName = deriveMp4Filename(mapAnimation.gpxFile, 'route.mp4');
      const { blob, filename } = await requestFile(apiBase, '/api/v1/gpx/map-animate', formData, fallbackName);
      const downloadUrl = URL.createObjectURL(blob);
      mapAnimation = { ...mapAnimation, status: 'success', downloadUrl, filename, message: `Rendered ${filename} (${resolutionLabel}, ${mapAnimation.durationSeconds}s).` };
    } catch (error) {
      mapAnimation = { ...mapAnimation, status: 'error', error: parseError(error) };
    } finally {
      finishRequest();
    }
  }

  async function submitTelemetryVideo() {
    if (telemetryVideo.downloadUrl) URL.revokeObjectURL(telemetryVideo.downloadUrl);
    startRequest('Rendering telemetry video...');
    telemetryVideo = { ...telemetryVideo, status: 'loading', error: '', message: '', downloadUrl: '', filename: '' };

    try {
      if (!telemetryVideo.gpxFile) throw new Error('Upload a GPX track to render.');
      if (!telemetryVideo.durationSeconds) {
        const parsedDuration = await parseGpxDuration(telemetryVideo.gpxFile);
        if (parsedDuration) telemetryVideo = { ...telemetryVideo, durationSeconds: parsedDuration };
      }
      if (!telemetryVideo.durationSeconds || telemetryVideo.durationSeconds <= 0) throw new Error('Duration must be greater than zero.');
      if (!telemetryVideo.fps || telemetryVideo.fps <= 0) throw new Error('Frames per second must be greater than zero.');
      if (!telemetryVideo.resolutionWidth || !telemetryVideo.resolutionHeight) throw new Error('Enter a resolution for the export.');
      if (telemetryVideo.resolutionWidth <= 0 || telemetryVideo.resolutionHeight <= 0) throw new Error('Resolution must be greater than zero.');
      const resolutionLabel = `${telemetryVideo.resolutionWidth}x${telemetryVideo.resolutionHeight}`;
      const backgroundColor = telemetryVideo.backgroundColor?.trim() || 'transparent';

      const formData = new FormData();
      formData.append('gpx_file', telemetryVideo.gpxFile);
      formData.append('duration_seconds', String(telemetryVideo.durationSeconds));
      formData.append('fps', String(telemetryVideo.fps));
      formData.append('resolution', resolutionLabel);
      formData.append('telemetry_type', telemetryVideo.telemetryType);
      formData.append('background_color', backgroundColor);

      requestEta(apiBase, '/api/v1/gpx/telemetry-video/estimate', cloneFormData(formData)).then((eta) => {
        estimatedSeconds = eta;
      }).catch(() => {
        estimatedSeconds = null;
      });

      const fallbackName = deriveMp4Filename(telemetryVideo.gpxFile, 'telemetry.mp4');
      const { blob, filename } = await requestFile(apiBase, '/api/v1/gpx/telemetry-video', formData, fallbackName);
      const downloadUrl = URL.createObjectURL(blob);
      telemetryVideo = { ...telemetryVideo, status: 'success', downloadUrl, filename, backgroundColor, message: `Rendered ${filename} (${resolutionLabel}, ${telemetryVideo.durationSeconds}s).` };
    } catch (error) {
      telemetryVideo = { ...telemetryVideo, status: 'error', error: parseError(error) };
    } finally {
      finishRequest();
    }
  }

  function handleTrimByTimeGpxChange(event) {
    trimByTime = { ...trimByTime, gpxFile: event.target.files?.[0] ?? null };
  }

  async function handleTrimByTimeVideoChange(event) {
    const file = event.target.files?.[0] ?? null;
    trimByTime = { ...trimByTime, videoFile: file };
    if (!file) return;
    try {
      const { start, end } = await deriveVideoTimes(file);
      trimByTime = { ...trimByTime, videoFile: file, startLocal: toLocalDateTimeValue(start), endLocal: toLocalDateTimeValue(end), error: '' };
    } catch (error) {
      trimByTime = { ...trimByTime, error: parseError(error, 'Unable to read video metadata.') };
    }
  }

  function handleTrimByVideosGpxChange(event) {
    trimByVideos = { ...trimByVideos, gpxFile: event.target.files?.[0] ?? null, error: '' };
  }

  async function handleTrimByVideosVideoChange(event) {
    const selectionId = ++trimByVideosSelectionId;
    const files = Array.from(event.target.files ?? []);
    trimByVideos = { ...trimByVideos, videoFiles: files, clips: [], totalDurationSeconds: 0, isPreparing: files.length > 0, error: '', message: '', status: 'idle' };
    if (!files.length) return;

    try {
      const clips = await Promise.all(files.map((file, index) => buildVideoClip(file, index)));
      if (selectionId !== trimByVideosSelectionId) return;
      const totalDurationSeconds = clips.reduce((sum, clip) => sum + clip.durationSeconds, 0);
      trimByVideos = { ...trimByVideos, videoFiles: files, clips, totalDurationSeconds, isPreparing: false, status: 'idle', error: '' };
    } catch (error) {
      if (selectionId !== trimByVideosSelectionId) return;
      trimByVideos = { ...trimByVideos, videoFiles: files, clips: [], totalDurationSeconds: 0, isPreparing: false, status: 'idle', error: parseError(error, 'Unable to read video metadata.') };
    }
  }

  async function handleMapAnimationGpxChange(event) {
    const file = event.target.files?.[0] ?? null;
    let durationSeconds = mapAnimation.durationSeconds;
    if (file) {
      const parsedDuration = await parseGpxDuration(file);
      if (parsedDuration) durationSeconds = parsedDuration;
    }
    mapAnimation = { ...mapAnimation, gpxFile: file, durationSeconds };
  }

  async function handleTelemetryGpxChange(event) {
    const file = event.target.files?.[0] ?? null;
    let durationSeconds = 4;
    if (file) {
      const parsedDuration = await parseGpxDuration(file);
      if (parsedDuration) durationSeconds = parsedDuration;
    }
    telemetryVideo = { ...telemetryVideo, gpxFile: file, durationSeconds, error: '', message: '', status: 'idle' };
  }
</script>

<svelte:window on:hashchange={() => syncPageFromHash()} />

<svelte:head>
  <title>{activePage.label} · GPX Helper</title>
  <meta name="description" content="Run the GPX Helper API from the browser to trim GPX files or render route animations." />
</svelte:head>

<div class="app-shell">
  <header class="app-header">
    <div class="brand-block"><p class="brand-mark">GPX Helper</p></div>
    <div class="header-links">
      <a class="secondary-link contributor-link" href="https://www.youtube.com/@EclipseValley" target="_blank" rel="noreferrer">
        <svg aria-hidden="true" viewBox="0 0 24 24" class="youtube-icon"><path fill="currentColor" d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.4 3.5 12 3.5 12 3.5s-7.4 0-9.4.6A3 3 0 0 0 .5 6.2 31.4 31.4 0 0 0 0 12a31.4 31.4 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c2 .6 9.4.6 9.4.6s7.4 0 9.4-.6a3 3 0 0 0 2.1-2.1A31.4 31.4 0 0 0 24 12a31.4 31.4 0 0 0-.5-5.8ZM9.6 15.6V8.4l6.2 3.6-6.2 3.6Z" /></svg>
        <span>EclipseValley</span>
      </a>
      <a class="secondary-link github-link" href="https://github.com/pooriat/GPX_helper" target="_blank" rel="noreferrer">
        <svg aria-hidden="true" viewBox="0 0 16 16" class="github-icon"><path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8a8 8 0 0 0 5.47 7.59c.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.2 1.87.86 2.33.66.07-.52.28-.86.51-1.06-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.01.08-2.1 0 0 .67-.21 2.2.82a7.62 7.62 0 0 1 2 0c1.53-1.04 2.2-.82 2.2-.82.44 1.09.16 1.9.08 2.1.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.19 0 .21.15.46.55.38A8 8 0 0 0 16 8c0-4.42-3.58-8-8-8z" /></svg>
        <span>GitHub</span>
      </a>
    </div>
  </header>

  <section class="workspace-bar">
    <div class="workspace-title">
      <h1>What do you want to do?</h1>
      <p class="muted-text">Select a task first. The workspace below then shows only the inputs and action for that flow.</p>
    </div>
    <nav class="workspace-tabs" aria-label="Main menu">
      {#each pages as page}
        <a href={page.href} class:workspace-tab-active={currentPage === page.id} aria-current={currentPage === page.id ? 'page' : undefined}>{page.label}</a>
      {/each}
    </nav>
  </section>

  <TaskSelector {tasks} {selectedTask} />

  {#if isBusy}
    <LoadingBanner {activeRequestLabel} {estimatedSeconds} />
  {/if}

  <main class="content">
    <div class="page-transition">
      {#if currentPage === 'trim'}
        <TrimPage
          {trimByTime}
          {trimByVideos}
          {isBusy}
          {formatDurationLabel}
          onSubmitTrimByTime={submitTrimByTime}
          onSubmitTrimByVideos={submitTrimByVideos}
          onTrimByTimeGpxChange={handleTrimByTimeGpxChange}
          onTrimByTimeVideoChange={handleTrimByTimeVideoChange}
          onTrimByVideosGpxChange={handleTrimByVideosGpxChange}
          onTrimByVideosVideoChange={handleTrimByVideosVideoChange}
        />
      {:else if currentPage === 'animation'}
        <AnimationPage
          {mapAnimation}
          {isBusy}
          {mapTileOptions}
          onSubmit={submitMapAnimation}
          onGpxChange={handleMapAnimationGpxChange}
        />
      {:else if currentPage === 'telemetry'}
        <TelemetryPage
          {telemetryVideo}
          {isBusy}
          {telemetryTypeOptions}
          onSubmit={submitTelemetryVideo}
          onGpxChange={handleTelemetryGpxChange}
        />
      {:else}
        <AboutPage />
      {/if}
    </div>
  </main>
</div>
