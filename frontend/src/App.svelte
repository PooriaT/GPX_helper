<script>
  const stats = [
    { label: 'Video-aware trimming', value: 'Use EXIF to match GPX start & end' },
    { label: 'Map animation ready', value: 'Tile-aligned Web Mercator export' },
    { label: 'Reliable fallbacks', value: 'Uses file mtime when metadata is missing' }
  ];

  const highlights = [
    {
      eyebrow: 'gpx_splitter.py',
      title: 'Sync video and GPS effortlessly',
      copy: 'Read creation and duration metadata, trim the track to what the camera actually captured, and export a clean GPX clip.'
    },
    {
      eyebrow: 'map_animator.py',
      title: 'Render motion with context',
      copy: 'Convert coordinates to EPSG:3857, fetch OpenStreetMap tiles automatically, and draw a smooth progress line over your route.'
    },
    {
      eyebrow: 'Confidence baked in',
      title: 'Clear feedback while you work',
      copy: 'Warnings when timestamps are missing, strong defaults for UTC data, and a simple workflow you can reuse for every ride or hike.'
    }
  ];

  const workflow = [
    {
      number: '01',
      title: 'Import your footage + GPX',
      copy: 'Drop a GoPro (or other camera) MP4 along with the matching GPX track. EXIF metadata guides the crop so your overlay lines up.'
    },
    {
      number: '02',
      title: 'Crop to the exact clip',
      copy: 'Run gpx_splitter.py to trim the track to the video start/end. Keep the default output or choose a custom destination path.'
    },
    {
      number: '03',
      title: 'Animate or export',
      copy: 'Feed the cropped GPX to map_animator.py to render a basemap animation with ffmpeg, or hand it to your overlay tool of choice.'
    }
  ];

  const capabilityCards = [
    {
      eyebrow: 'Ready to run',
      title: 'Install the essentials',
      copy: 'Use exiftool for metadata, ffmpeg for exports, and Python packages like gpxpy, matplotlib, and contextily for maps.',
      chips: ['exiftool', 'ffmpeg', 'gpxpy', 'matplotlib', 'contextily']
    },
    {
      eyebrow: 'Data you can trust',
      title: 'Timezone-aware processing',
      copy: 'UTC timestamps keep everything aligned. Missing timestamps trigger explicit warnings so you can fix files before exporting.',
      chips: ['UTC-first', 'Warnings when missing', 'Fallbacks logged']
    },
    {
      eyebrow: 'Output options',
      title: 'Share-ready results',
      copy: 'Write cropped GPX files for overlays or render MP4 map animations sized for your project, from social posts to 4K exports.',
      chips: ['GPX crops', '1920x1080 defaults', 'Custom durations']
    }
  ];

  const callouts = [
    {
      title: 'Fast iteration',
      copy: 'Keep your tooling local and repeatable. Swap in new clips without rebuilding the whole workflow.'
    },
    {
      title: 'Clean visual layer',
      copy: 'Use the map animation as a hero visual, B-roll, or lower-third element—no extra post-processing required.'
    },
    {
      title: 'Works offline',
      copy: 'Once tiles are cached, you can iterate without a connection and keep exports reproducible.'
    }
  ];
</script>

<svelte:head>
  <meta name="description" content="Landing page for GPX Helper, the toolkit that syncs GoPro video with GPX tracks and renders map animations." />
</svelte:head>

<main class="page">
  <section class="hero">
    <div>
      <div class="hero__badge">GPX Helper · Svelte landing</div>
      <h1 class="hero__title">Sync footage, trim GPX tracks, and render map animations with clarity.</h1>
      <p class="hero__copy">
        A lightweight surface for the GPX_helper toolkit—built to spotlight the Python utilities that align camera
        footage with GPS data and export ready-to-share visuals.
      </p>

      <div class="hero__actions">
        <a class="btn primary" href="#workflow">See the workflow</a>
        <a
          class="btn secondary"
          href="https://github.com/OpenAI-Tools/GPX_helper"
          target="_blank"
          rel="noreferrer"
        >
          View CLI docs
        </a>
      </div>

      <div class="hero__stats">
        {#each stats as stat}
          <div class="stat-card">
            <div class="stat-card__label">{stat.label}</div>
            <div class="stat-card__value">{stat.value}</div>
          </div>
        {/each}
      </div>
    </div>

    <div class="hero__visual">
      <div class="visual-row">
        <div class="visual-card">
          <h4>gpx_splitter.py</h4>
          <p>Read EXIF metadata, trim the track to match the clip, and export a new GPX with precise timestamps.</p>
        </div>
        <div class="visual-card">
          <h4>map_animator.py</h4>
          <p>Convert to Web Mercator, fetch OSM tiles, and render a smooth MP4 route animation with ffmpeg.</p>
        </div>
      </div>
      <div class="visual-card">
        <h4>Workflow preview</h4>
        <p>
          Import your video and GPX, crop confidently, then animate. The toolkit keeps things tidy with warnings and
          helpful defaults.
        </p>
      </div>
    </div>
  </section>

  <div class="section-title" id="workflow">
    <h2>Your end-to-end path</h2>
    <p>Three steps to aligned overlays and map-ready exports.</p>
  </div>
  <div class="panel timeline">
    {#each workflow as step}
      <div class="timeline-step">
        <div class="bubble">{step.number}</div>
        <div>
          <h4>{step.title}</h4>
          <p>{step.copy}</p>
        </div>
      </div>
    {/each}
  </div>

  <div class="section-title">
    <h2>What&apos;s inside</h2>
    <p>Tooling details so you know exactly how the landing connects to the Python scripts.</p>
  </div>
  <div class="card-grid">
    {#each highlights as item}
      <div class="card">
        <small>{item.eyebrow}</small>
        <h3>{item.title}</h3>
        <p>{item.copy}</p>
      </div>
    {/each}
  </div>

  <div class="section-title">
    <h2>Capabilities at a glance</h2>
    <p>Dependencies, safeguards, and export targets in one place.</p>
  </div>
  <div class="card-grid">
    {#each capabilityCards as card}
      <div class="card">
        <small>{card.eyebrow}</small>
        <h3>{card.title}</h3>
        <p>{card.copy}</p>
        <div class="chip-row">
          {#each card.chips as chip}
            <span class="chip">{chip}</span>
          {/each}
        </div>
      </div>
    {/each}
  </div>

  <div class="section-title">
    <h2>Why this matters</h2>
    <p>Designed to stay fast, visual, and predictable.</p>
  </div>
  <div class="callouts">
    {#each callouts as callout}
      <div class="panel callout">
        <h3>{callout.title}</h3>
        <p>{callout.copy}</p>
      </div>
    {/each}
  </div>

  <div class="gradient-border footer-cta">
    <div class="panel footer-cta">
      <h3>Ready to build your overlay?</h3>
      <p>
        Use the landing page as your launchpad: crop GPX to your footage, animate routes, and keep your next ride or hike
        perfectly in sync.
      </p>
      <div class="hero__actions" style="justify-content: center">
        <a class="btn primary" href="https://github.com/OpenAI-Tools/GPX_helper" target="_blank" rel="noreferrer">
          Open the toolkit
        </a>
        <a class="btn secondary" href="#workflow">Review the steps</a>
      </div>
    </div>
  </div>
</main>
