<script>
  import FileField from './FileField.svelte';
  import TaskContainer from './TaskContainer.svelte';

  export let mapAnimation;
  export let isBusy;
  export let mapTileOptions;

  export let onSubmit;
  export let onGpxChange;

  $: selectedMapTileOption = mapTileOptions.find((option) => option.value === mapAnimation.tileType) ?? mapTileOptions[0];
  $: selectedMapTilePreview = selectedMapTileOption?.previewUrl ?? null;
</script>

<TaskContainer
  title="Create route animation"
  description="Upload a GPX track, confirm the timing, adjust optional render settings, then create the MP4."
>
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

    <details class="advanced-settings">
      <summary>Advanced settings</summary>
      <div class="advanced-content">
        <div class="options-row">
          <div class="options-group">
            <p class="options-title">Output size</p>
            <div class="options-stack">
              <label>
                Frames per second (fps)
                <input type="number" min="1" step="1" bind:value={mapAnimation.fps} placeholder="30" required />
              </label>
              <label>
                Resolution width (px)
                <input type="number" min="1" step="1" bind:value={mapAnimation.resolutionWidth} placeholder="1024" required />
              </label>
              <label>
                Resolution height (px)
                <input type="number" min="1" step="1" bind:value={mapAnimation.resolutionHeight} placeholder="1024" required />
              </label>
            </div>
          </div>
          <div class="options-group">
            <p class="options-title">Map tiles</p>
            <div class="options-stack">
              <figure class="tile-preview">
                {#if selectedMapTilePreview}
                  {#key selectedMapTilePreview}
                    <img src={selectedMapTilePreview} alt={`${selectedMapTileOption.label} map tile preview`} loading="lazy" />
                  {/key}
                {:else}
                  <figcaption>No preview available.</figcaption>
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
                <input class="color-picker" type="color" bind:value={mapAnimation.markerColor} style={`--picker-color: ${mapAnimation.markerColor};`} />
                <span class="color-value">{mapAnimation.markerColor}</span>
              </div>
            </label>
            <label>
              Marker size (px)
              <input type="number" min="1" step="0.5" bind:value={mapAnimation.markerSize} placeholder="6" />
            </label>
            <label>
              Animated trail color
              <div class="color-control">
                <input class="color-picker" type="color" bind:value={mapAnimation.trailColor} style={`--picker-color: ${mapAnimation.trailColor};`} />
                <span class="color-value">{mapAnimation.trailColor}</span>
              </div>
            </label>
            <label>
              Full trail color
              <div class="color-control">
                <input class="color-picker" type="color" bind:value={mapAnimation.fullTrailColor} style={`--picker-color: ${mapAnimation.fullTrailColor};`} />
                <span class="color-value">{mapAnimation.fullTrailColor}</span>
              </div>
            </label>
            <label>
              Full trail opacity
              <input type="number" min="0" max="1" step="0.05" bind:value={mapAnimation.fullTrailOpacity} placeholder="0.8" />
            </label>
            <label>
              Line width (px)
              <input type="number" min="0.5" step="0.1" bind:value={mapAnimation.lineWidth} placeholder="2.5" />
            </label>
            <label>
              Animated line opacity
              <input type="number" min="0" max="1" step="0.05" bind:value={mapAnimation.lineOpacity} placeholder="1" />
            </label>
          </div>
        </div>
      </div>
    </details>

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
</TaskContainer>
