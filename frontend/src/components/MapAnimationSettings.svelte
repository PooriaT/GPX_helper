<script>
  export let mapAnimation;
  export let mapTileOptions;

  $: selectedMapTileOption = mapTileOptions.find((option) => option.value === mapAnimation.tileType) ?? mapTileOptions[0];
  $: selectedMapTilePreview = selectedMapTileOption?.previewUrl ?? null;
</script>

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
          Marker style
          <select bind:value={mapAnimation.markerStyle}>
            <option value="default">Default marker</option>
            <option value="bike">Bike</option>
            <option value="runner">Runner</option>
          </select>
        </label>
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
