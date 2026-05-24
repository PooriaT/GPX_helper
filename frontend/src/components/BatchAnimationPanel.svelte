<script>
  import FileField from './FileField.svelte';
  import MapAnimationSettings from './MapAnimationSettings.svelte';

  export let mapAnimationBatch;
  export let mapAnimation;
  export let isBusy;
  export let mapTileOptions;

  export let onSubmit;
  export let onGpxFilesChange;
  export let onVideoFilesChange;
  export let onPairDurationChange;
  export let onPairOutputNameChange;

  $: hasFiles = mapAnimationBatch.gpxFiles.length > 0 || mapAnimationBatch.videoFiles.length > 0;
  $: hasCountMismatch = mapAnimationBatch.gpxFiles.length > 0 && mapAnimationBatch.videoFiles.length > 0 && mapAnimationBatch.gpxFiles.length !== mapAnimationBatch.videoFiles.length;
  $: countMessage = hasCountMismatch
    ? `${mapAnimationBatch.gpxFiles.length} GPX files and ${mapAnimationBatch.videoFiles.length} video files selected. Add or remove files so the counts match.`
    : '';
</script>

<form class="form-grid" on:submit|preventDefault={onSubmit}>
  <section class="step-section">
    <div class="step-heading">
      <span class="step-number">1</span>
      <div>
        <h3>Upload GPX files</h3>
        <p class="muted-text">Files are paired by selection order.</p>
      </div>
    </div>
    <FileField
      label="GPX files"
      accept=".gpx,application/gpx+xml"
      multiple
      fileName={mapAnimationBatch.gpxFiles.length ? `${mapAnimationBatch.gpxFiles.length} GPX files selected` : ''}
      placeholder="Select GPX files"
      onChange={onGpxFilesChange}
      required
    />
  </section>

  <section class="step-section">
    <div class="step-heading">
      <span class="step-number">2</span>
      <div>
        <h3>Upload videos</h3>
        <p class="muted-text">Videos stay in the browser and are used only to detect duration.</p>
      </div>
    </div>
    <FileField
      label="Video files"
      accept="video/*"
      multiple
      fileName={mapAnimationBatch.videoFiles.length ? `${mapAnimationBatch.videoFiles.length} video files selected` : ''}
      placeholder="Select videos for duration detection"
      onChange={onVideoFilesChange}
      required
    />
  </section>

  <section class="step-section review-section">
    <div class="step-heading">
      <span class="step-number">3</span>
      <div>
        <h3>Review GPX/video pairs</h3>
        <p class="muted-text">Each row becomes one animation in the ZIP, and durations can be adjusted before rendering.</p>
      </div>
    </div>

    {#if countMessage}
      <p class="error" role="alert">{countMessage}</p>
    {/if}

    {#if mapAnimationBatch.isPreparing}
      <p class="hint">Reading video durations.</p>
    {:else if mapAnimationBatch.pairs.length}
      <div class="pair-table-wrap">
        <table class="pair-table">
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">GPX</th>
              <th scope="col">Video</th>
              <th scope="col">Duration</th>
              <th scope="col">Output name</th>
            </tr>
          </thead>
          <tbody>
            {#each mapAnimationBatch.pairs as pair, index}
              <tr>
                <td>{index + 1}</td>
                <td>{pair.gpxFile?.name ?? 'Missing GPX'}</td>
                <td>{pair.videoFile?.name ?? 'Missing video'}</td>
                <td>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={pair.durationSeconds}
                    aria-label={`Duration for pair ${index + 1}`}
                    on:input={(event) => onPairDurationChange(index, event.currentTarget.value)}
                    required
                  />
                </td>
                <td>
                  <input
                    type="text"
                    value={pair.outputName}
                    aria-label={`Output name for pair ${index + 1}`}
                    placeholder="route"
                    on:input={(event) => onPairOutputNameChange(index, event.currentTarget.value)}
                  />
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else if hasFiles}
      <p class="hint">Select matching GPX and video files to create pairs.</p>
    {:else}
      <p class="hint">No pairs selected.</p>
    {/if}
  </section>

  <MapAnimationSettings {mapAnimation} {mapTileOptions} />

  <section class="step-section action-step">
    <div class="step-heading">
      <span class="step-number">4</span>
      <div>
        <h3>Execute action</h3>
        <p class="muted-text">Render all route animations into one ZIP file.</p>
      </div>
    </div>
    <div class="form-actions">
      <button class="primary-action" type="submit" disabled={isBusy || mapAnimationBatch.isPreparing}>Render batch ZIP</button>
    </div>
    <p class="muted-text">Batch renders are all-or-nothing: if one pair fails, no ZIP is created.</p>
  </section>
</form>

{#if mapAnimationBatch.error}
  <p class="error" role="alert">{mapAnimationBatch.error}</p>
{/if}
{#if mapAnimationBatch.message}
  <p class="success" aria-live="polite">{mapAnimationBatch.message}</p>
{/if}
{#if mapAnimationBatch.downloadUrl}
  <a class="download" href={mapAnimationBatch.downloadUrl} download={mapAnimationBatch.filename}>
    Download {mapAnimationBatch.filename}
  </a>
{/if}
