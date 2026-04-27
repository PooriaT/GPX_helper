<script>
  import FileField from './FileField.svelte';
  import TaskContainer from './TaskContainer.svelte';

  export let telemetryVideo;
  export let isBusy;
  export let telemetryTypeOptions;

  export let onSubmit;
  export let onGpxChange;

  $: backgroundMode =
    telemetryVideo.backgroundMode ?? (telemetryVideo.backgroundColor?.trim().toLowerCase() === 'transparent' ? 'transparent' : 'custom');
  $: colorPickerValue = /^#[0-9a-f]{6}$/i.test(telemetryVideo.backgroundColor ?? '') ? telemetryVideo.backgroundColor : '#000000';

  function selectBackgroundMode(mode) {
    telemetryVideo.backgroundMode = mode;
    if (mode === 'custom' && (!telemetryVideo.backgroundColor || telemetryVideo.backgroundColor.trim().toLowerCase() === 'transparent')) {
      telemetryVideo.backgroundColor = '#000000';
    }
  }

  function handleColorPicker(event) {
    telemetryVideo.backgroundColor = event.currentTarget.value;
  }
</script>

<TaskContainer
  title="Generate telemetry video"
  description="Upload a GPX track, select the telemetry overlay, review the export settings, then render the overlay."
>
  <form class="form-grid" on:submit|preventDefault={onSubmit}>
    <section class="step-section">
      <div class="step-heading">
        <span class="step-number">1</span>
        <div>
          <h3>Upload GPX</h3>
          <p class="muted-text">Telemetry is generated from the data in this track.</p>
        </div>
      </div>
      <FileField
        label="GPX file"
        accept=".gpx,application/gpx+xml"
        fileName={telemetryVideo.gpxFile?.name ?? ''}
        onChange={onGpxChange}
        required
      />
    </section>

    <section class="step-section">
      <div class="step-heading">
        <span class="step-number">2</span>
        <div>
          <h3>Select telemetry</h3>
          <p class="muted-text">Choose the overlay content and confirm the video duration.</p>
        </div>
      </div>
      <div class="options-row">
        <label>
          Telemetry video type
          <select bind:value={telemetryVideo.telemetryType}>
            {#each telemetryTypeOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>
        <label>
          Duration (seconds)
          <input type="number" min="1" step="1" bind:value={telemetryVideo.durationSeconds} placeholder="4" required />
        </label>
      </div>
    </section>

    <section class="step-section">
      <div class="step-heading">
        <span class="step-number">3</span>
        <div>
          <h3>Review inputs</h3>
          <p class="muted-text">Confirm the source file and current export target.</p>
        </div>
      </div>
      <dl class="review-list">
        <div>
          <dt>GPX file</dt>
          <dd>{telemetryVideo.gpxFile?.name ?? 'Required'}</dd>
        </div>
        <div>
          <dt>Telemetry type</dt>
          <dd>{telemetryTypeOptions.find((option) => option.value === telemetryVideo.telemetryType)?.label ?? telemetryVideo.telemetryType}</dd>
        </div>
        <div>
          <dt>Output</dt>
          <dd>{telemetryVideo.resolutionWidth}x{telemetryVideo.resolutionHeight} at {telemetryVideo.fps} fps</dd>
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
                <input type="number" min="1" step="1" bind:value={telemetryVideo.fps} placeholder="30" required />
              </label>
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
            <p class="options-title">Compositing</p>
            <div class="options-stack">
              <div>
                <span class="field-label">Background mode</span>
                <div class="mode-selector background-mode-selector" role="group" aria-label="Background mode">
                  <button
                    type="button"
                    class:mode-active={backgroundMode === 'transparent'}
                    aria-pressed={backgroundMode === 'transparent'}
                    on:click={() => selectBackgroundMode('transparent')}
                  >
                    Transparent
                  </button>
                  <button
                    type="button"
                    class:mode-active={backgroundMode === 'custom'}
                    aria-pressed={backgroundMode === 'custom'}
                    on:click={() => selectBackgroundMode('custom')}
                  >
                    Custom color
                  </button>
                </div>
              </div>
              {#if backgroundMode === 'custom'}
                <div class="options-stack">
                  <span class="field-label">Custom background color</span>
                  <div class="color-control">
                    <input
                      class="color-picker"
                      type="color"
                      value={colorPickerValue}
                      on:input={handleColorPicker}
                      style={`--picker-color: ${colorPickerValue}`}
                      aria-label="Pick custom background color"
                    />
                    <span class="color-value">{telemetryVideo.backgroundColor}</span>
                  </div>
                  <label>
                    Color value
                    <input type="text" bind:value={telemetryVideo.backgroundColor} placeholder="#000000" list="background-color-presets" />
                  </label>
                  <datalist id="background-color-presets">
                    <option value="#000000"></option>
                    <option value="#ffffff"></option>
                    <option value="red"></option>
                  </datalist>
                </div>
              {/if}
              <p class="hint">
                Transparent background is recommended for compositing over cycling, running, or activity footage.
              </p>
            </div>
          </div>
        </div>
      </div>
    </details>

    <section class="step-section action-step">
      <div class="step-heading">
        <span class="step-number">4</span>
        <div>
          <h3>Execute action</h3>
          <p class="muted-text">Render telemetry overlay.</p>
        </div>
      </div>
      <div class="form-actions">
        <button class="primary-action" type="submit" disabled={isBusy}>Render telemetry video</button>
      </div>
    </section>
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
</TaskContainer>
