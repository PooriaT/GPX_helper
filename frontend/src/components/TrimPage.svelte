<script>
  import FileField from './FileField.svelte';

  export let trimByTime;
  export let trimByVideos;
  export let isBusy;
  export let formatDurationLabel;
  export let onSubmitTrimByTime;
  export let onSubmitTrimByVideos;
  export let onTrimByTimeGpxChange;
  export let onTrimByTimeVideoChange;
  export let onTrimByVideosGpxChange;
  export let onTrimByVideosVideoChange;
</script>

<section class="workflow-grid">
  <article class="tool-card workflow-card">
    <header class="section-header">
      <h2>Trim by time</h2>
      <p class="muted-text">Select a GPX file and define the time range.</p>
    </header>

    <form class="form-grid" on:submit|preventDefault={onSubmitTrimByTime}>
      <div class="form-section">
        <FileField
          label="GPX file"
          accept=".gpx,application/gpx+xml"
          fileName={trimByTime.gpxFile?.name ?? ''}
          onChange={onTrimByTimeGpxChange}
          required
        />
        <FileField
          label="Optional video file"
          accept="video/*"
          fileName={trimByTime.videoFile?.name ?? ''}
          placeholder="Optional metadata source"
          onChange={onTrimByTimeVideoChange}
        />
      </div>
      <div class="form-section form-section-inline">
        <label>
          Start time
          <input type="datetime-local" step="1" bind:value={trimByTime.startLocal} required />
        </label>
        <label>
          End time
          <input type="datetime-local" step="1" bind:value={trimByTime.endLocal} required />
        </label>
      </div>
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
      <p class="muted-text">Create one trimmed GPX segment for each video file.</p>
    </header>

    <form class="form-grid" on:submit|preventDefault={onSubmitTrimByVideos}>
      <div class="form-section">
        <FileField
          label="GPX file"
          accept=".gpx,application/gpx+xml"
          fileName={trimByVideos.gpxFile?.name ?? ''}
          onChange={onTrimByVideosGpxChange}
          required
        />
        <FileField
          label="Video files"
          accept="video/*"
          multiple
          fileName={trimByVideos.videoFiles.length ? `${trimByVideos.videoFiles.length} video files selected` : ''}
          placeholder="Select videos to split by"
          onChange={onTrimByVideosVideoChange}
          required
        />
      </div>
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
