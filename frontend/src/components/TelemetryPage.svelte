<script>
  export let telemetryVideo;
  export let isBusy;
  export let telemetryTypeOptions;

  export let onSubmit;
  export let onGpxChange;
</script>

<section class="tool-card wide">
  <header class="section-header">
    <h2>Render telemetry video</h2>
    <p class="muted-text">
      Export a telemetry-only MP4 from the GPX track for compositing over another clip.
    </p>
  </header>

  <form class="form-grid" on:submit|preventDefault={onSubmit}>
    <label>
      GPX file
      <input type="file" accept=".gpx,application/gpx+xml" on:change={onGpxChange} required />
    </label>
    <div class="animation-inline-fields">
      <label class="compact-field">
        Duration (seconds)
        <input type="number" min="1" step="1" bind:value={telemetryVideo.durationSeconds} placeholder="4" required />
      </label>
      <label class="compact-field">
        Frames per second (fps)
        <input type="number" min="1" step="1" bind:value={telemetryVideo.fps} placeholder="30" required />
      </label>
    </div>
    <div class="options-row">
      <div class="options-group">
        <p class="options-title">Output size</p>
        <div class="options-stack">
          <label>
            Resolution width (px)
            <input type="number" min="1" step="1" bind:value={telemetryVideo.resolutionWidth} placeholder="1024" required />
          </label>
          <label>
            Resolution height (px)
            <input type="number" min="1" step="1" bind:value={telemetryVideo.resolutionHeight} placeholder="1024" required />
          </label>
        </div>
      </div>
      <div class="options-group">
        <p class="options-title">Telemetry</p>
        <div class="options-stack">
          <label>
            Telemetry video type
            <select bind:value={telemetryVideo.telemetryType}>
              {#each telemetryTypeOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>
          <label>
            Background color
            <input type="text" bind:value={telemetryVideo.backgroundColor} placeholder="transparent" list="background-color-presets" />
            <datalist id="background-color-presets">
              <option value="transparent"></option>
              <option value="#000000"></option>
              <option value="#ffffff"></option>
            </datalist>
          </label>
          <p class="hint">
            Default is <code>transparent</code>. Standard MP4 exports are usually opaque, so many players will display transparent regions as black.
          </p>
        </div>
      </div>
    </div>
    <div class="form-actions">
      <button type="submit" disabled={isBusy}>Render telemetry video</button>
    </div>
  </form>
  {#if telemetryVideo.error}
    <p class="error" role="alert">{telemetryVideo.error}</p>
  {/if}
  {#if telemetryVideo.message}
    <p class="success" aria-live="polite">{telemetryVideo.message}</p>
  {/if}
  {#if telemetryVideo.downloadUrl}
    <a class="download" href={telemetryVideo.downloadUrl} download={telemetryVideo.filename}>
      Download {telemetryVideo.filename}
    </a>
  {/if}
</section>
