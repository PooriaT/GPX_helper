<script>
  import FileField from './FileField.svelte';

  export let mapAnimation;
  export let isBusy;
  export let mapTileOptions;
  export let currentMapTileOption;
  export let currentMapTilePreview;

  export let onSubmit;
  export let onGpxChange;
</script>

<section class="tool-card wide">
  <header class="section-header">
    <h2>Render animation</h2>
    <p class="muted-text">Upload a GPX track and tune the route video output.</p>
  </header>

  <form class="form-grid" on:submit|preventDefault={onSubmit}>
    <div class="form-section">
      <FileField
        label="GPX file"
        accept=".gpx,application/gpx+xml"
        fileName={mapAnimation.gpxFile?.name ?? ''}
        onChange={onGpxChange}
        required
      />
    </div>
    <div class="animation-inline-fields">
      <label class="compact-field">
        Duration (seconds)
        <input type="number" min="1" step="1" bind:value={mapAnimation.durationSeconds} placeholder="45" required />
      </label>
      <label class="compact-field">
        Frames per second (fps)
        <input type="number" min="1" step="1" bind:value={mapAnimation.fps} placeholder="30" required />
      </label>
    </div>
    <div class="options-row">
      <div class="options-group">
        <p class="options-title">Output size</p>
        <div class="options-stack">
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
            {#if currentMapTilePreview}
              <img src={currentMapTilePreview} alt={`${currentMapTileOption.label} map tile preview`} loading="lazy" />
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
