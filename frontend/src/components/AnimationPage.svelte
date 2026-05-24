<script>
  import BatchAnimationPanel from './BatchAnimationPanel.svelte';
  import FileField from './FileField.svelte';
  import MapAnimationSettings from './MapAnimationSettings.svelte';
  import TaskContainer from './TaskContainer.svelte';

  export let mapAnimation;
  export let mapAnimationBatch;
  export let isBusy;
  export let mapTileOptions;

  export let onSubmit;
  export let onBatchSubmit;
  export let onGpxChange;
  export let onBatchGpxFilesChange;
  export let onBatchPairDurationChange;
  export let onBatchPairOutputNameChange;

  let selectedMode = 'single';
</script>

<TaskContainer
  title="Create route animation"
  description="Upload a GPX track, confirm the timing, adjust optional render settings, then create the MP4."
>
  <div class="mode-selector" aria-label="Route animation mode">
    <button type="button" class:mode-active={selectedMode === 'single'} on:click={() => (selectedMode = 'single')}>
      Single GPX
    </button>
    <button type="button" class:mode-active={selectedMode === 'batch'} on:click={() => (selectedMode = 'batch')}>
      Batch GPX files
    </button>
  </div>

  {#if selectedMode === 'single'}
    <form class="form-grid" on:submit|preventDefault={onSubmit}>
    <section class="step-section">
      <div class="step-heading">
        <span class="step-number">1</span>
        <div>
          <h3>Upload GPX</h3>
          <p class="muted-text">The route animation is generated from this track.</p>
        </div>
      </div>
      <FileField
        label="GPX file"
        accept=".gpx,application/gpx+xml"
        fileName={mapAnimation.gpxFile?.name ?? ''}
        onChange={onGpxChange}
        required
      />
    </section>

    <section class="step-section">
      <div class="step-heading">
        <span class="step-number">2</span>
        <div>
          <h3>Confirm timing</h3>
          <p class="muted-text">Use the detected duration or enter the intended video length.</p>
        </div>
      </div>
      <div class="animation-inline-fields">
        <label class="compact-field">
          Duration (seconds)
          <input type="number" min="1" step="1" bind:value={mapAnimation.durationSeconds} placeholder="45" required />
        </label>
      </div>
    </section>

    <section class="step-section">
      <div class="step-heading">
        <span class="step-number">3</span>
        <div>
          <h3>Review inputs</h3>
          <p class="muted-text">Confirm the source file and current render target.</p>
        </div>
      </div>
      <dl class="review-list">
        <div>
          <dt>GPX file</dt>
          <dd>{mapAnimation.gpxFile?.name ?? 'Required'}</dd>
        </div>
        <div>
          <dt>Duration</dt>
          <dd>{mapAnimation.durationSeconds || 'Required'} seconds</dd>
        </div>
        <div>
          <dt>Output</dt>
          <dd>{mapAnimation.resolutionWidth}x{mapAnimation.resolutionHeight} at {mapAnimation.fps} fps</dd>
        </div>
      </dl>
    </section>

    <MapAnimationSettings {mapAnimation} {mapTileOptions} />

    <section class="step-section action-step">
      <div class="step-heading">
        <span class="step-number">4</span>
        <div>
          <h3>Execute action</h3>
          <p class="muted-text">Render the route animation as an MP4.</p>
        </div>
      </div>
      <div class="form-actions">
        <button class="primary-action" type="submit" disabled={isBusy}>Render animation</button>
      </div>
    </section>
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
  {/if}

  {#if selectedMode === 'batch'}
    <BatchAnimationPanel
      {mapAnimationBatch}
      {mapAnimation}
      {isBusy}
      {mapTileOptions}
      onSubmit={onBatchSubmit}
      onGpxFilesChange={onBatchGpxFilesChange}
      onPairDurationChange={onBatchPairDurationChange}
      onPairOutputNameChange={onBatchPairOutputNameChange}
    />
  {/if}
</TaskContainer>
