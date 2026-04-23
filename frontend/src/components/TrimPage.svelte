<script>
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
    </header>

    <form class="form-grid" on:submit|preventDefault={onSubmitTrimByTime}>
      <label>
        GPX file
        <input type="file" accept=".gpx,application/gpx+xml" on:change={onTrimByTimeGpxChange} required />
      </label>
      <label>
        Optional video file
        <input type="file" accept="video/*" on:change={onTrimByTimeVideoChange} />
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

    <form class="form-grid" on:submit|preventDefault={onSubmitTrimByVideos}>
      <label>
        GPX file
        <input type="file" accept=".gpx,application/gpx+xml" on:change={onTrimByVideosGpxChange} required />
      </label>
      <label>
        Video files
        <input type="file" accept="video/*" multiple on:change={onTrimByVideosVideoChange} required />
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
