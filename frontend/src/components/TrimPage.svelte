<script>
  import FileField from './FileField.svelte';
  import TaskContainer from './TaskContainer.svelte';

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

  let selectedMode = 'time';
</script>

<TaskContainer
  title="Trim GPX"
  description="Choose one trim mode, provide the required inputs, review the selection, then export the result."
>
  <div class="mode-selector" aria-label="Trim mode">
    <button type="button" class:mode-active={selectedMode === 'time'} on:click={() => (selectedMode = 'time')}>
      Trim by time
    </button>
    <button type="button" class:mode-active={selectedMode === 'videos'} on:click={() => (selectedMode = 'videos')}>
      Split by videos
    </button>
  </div>

  <section hidden={selectedMode !== 'time'} aria-hidden={selectedMode !== 'time'}>
    <form class="form-grid" on:submit|preventDefault={onSubmitTrimByTime}>
      <section class="step-section">
        <div class="step-heading">
          <span class="step-number">1</span>
          <div>
            <h3>Upload GPX</h3>
            <p class="muted-text">This is the track that will be trimmed.</p>
          </div>
        </div>
        <FileField
          label="GPX file"
          accept=".gpx,application/gpx+xml"
          fileName={trimByTime.gpxFile?.name ?? ''}
          onChange={onTrimByTimeGpxChange}
          required
        />
      </section>

      <section class="step-section">
        <div class="step-heading">
          <span class="step-number">2</span>
          <div>
            <h3>Provide timestamps</h3>
            <p class="muted-text">Enter the trim range directly or load it from optional video metadata.</p>
          </div>
        </div>
        <div class="form-section">
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
      </section>

      <section class="step-section review-section">
        <div class="step-heading">
          <span class="step-number">3</span>
          <div>
            <h3>Review inputs</h3>
            <p class="muted-text">Confirm the source track and trim range before exporting.</p>
          </div>
        </div>
        <dl class="review-list">
          <div>
            <dt>GPX file</dt>
            <dd>{trimByTime.gpxFile?.name ?? 'Required'}</dd>
          </div>
          <div>
            <dt>Time range</dt>
            <dd>{trimByTime.startLocal || 'Start required'} to {trimByTime.endLocal || 'end required'}</dd>
          </div>
          <div>
            <dt>Video metadata</dt>
            <dd>{trimByTime.videoFile?.name ?? 'Not selected'}</dd>
          </div>
        </dl>
      </section>

      <section class="step-section action-step">
        <div class="step-heading">
          <span class="step-number">4</span>
          <div>
            <h3>Execute action</h3>
            <p class="muted-text">Create one GPX file for the selected time range.</p>
          </div>
        </div>
        <div class="form-actions">
          <button class="primary-action" type="submit" disabled={isBusy}>Trim track</button>
        </div>
      </section>
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
  </section>

  <section hidden={selectedMode !== 'videos'} aria-hidden={selectedMode !== 'videos'}>
    <form class="form-grid" on:submit|preventDefault={onSubmitTrimByVideos}>
      <section class="step-section">
        <div class="step-heading">
          <span class="step-number">1</span>
          <div>
            <h3>Upload GPX</h3>
            <p class="muted-text">This track will be split into video-aligned GPX segments.</p>
          </div>
        </div>
        <FileField
          label="GPX file"
          accept=".gpx,application/gpx+xml"
          fileName={trimByVideos.gpxFile?.name ?? ''}
          onChange={onTrimByVideosGpxChange}
          required
        />
      </section>

      <section class="step-section">
        <div class="step-heading">
          <span class="step-number">2</span>
          <div>
            <h3>Add videos</h3>
            <p class="muted-text">Each video creates one GPX segment using its metadata timestamps.</p>
          </div>
        </div>
        <div class="form-section">
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
      </section>

      <section class="step-section review-section">
        <div class="step-heading">
          <span class="step-number">3</span>
          <div>
            <h3>Review clips</h3>
            <p class="muted-text">Check the generated clip list before creating the ZIP.</p>
          </div>
        </div>
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
      </section>

      <section class="step-section action-step">
        <div class="step-heading">
          <span class="step-number">4</span>
          <div>
            <h3>Execute action</h3>
            <p class="muted-text">Download one ZIP containing all trimmed GPX segments.</p>
          </div>
        </div>
        <div class="form-actions">
          <button class="primary-action" type="submit" disabled={isBusy || trimByVideos.isPreparing}>Create ZIP</button>
        </div>
      </section>
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
  </section>
</TaskContainer>
