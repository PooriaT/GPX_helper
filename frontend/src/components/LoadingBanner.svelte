<script>
  export let activeRequestLabel = '';
  export let estimatedSeconds = null;
</script>

<div class="loading-banner" role="status" aria-live="polite">
  <div class="spinner" aria-hidden="true"></div>
  <div class="loading-copy">
    <p class="loading-title">{activeRequestLabel || 'Working on your request...'}</p>
    <p class="muted-text">
      {#if estimatedSeconds}
        Estimated wait: ~{Math.max(1, Math.round(estimatedSeconds))} seconds.
      {:else}
        Preparing request.
      {/if}
    </p>
  </div>
</div>
