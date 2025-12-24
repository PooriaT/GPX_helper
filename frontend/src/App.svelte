<svelte:head>
  <meta
    name="description"
    content="GPX Helper simplifies syncing GPX tracks with video footage and preparing map-ready exports."
  />
</svelte:head>

<main class="page">
  <section class="hero">
    <div class="hero__badge">GPX Helper</div>
    <h1>Make GPX + video sync simple.</h1>
    <p class="hero__copy">
      A focused landing page for the GPX_helper toolkit. Trim tracks to footage, prep map-ready exports, and keep your
      workflow predictable.
    </p>
    <div class="hero__actions">
      <a class="btn primary" href="https://github.com/OpenAI-Tools/GPX_helper" target="_blank" rel="noreferrer">
        View the toolkit
      </a>
      <a class="btn secondary" href="#steps">How it works</a>
    </div>
  </section>

  <section class="panel" id="steps">
    <h2>Three quick steps</h2>
    <ol class="steps">
      <li>
        <strong>Import footage + GPX.</strong>
        <span>Point the scripts at your video file and matching track.</span>
      </li>
      <li>
        <strong>Trim with confidence.</strong>
        <span>Use metadata to crop the GPX to the real clip window.</span>
      </li>
      <li>
        <strong>Export for maps.</strong>
        <span>Generate a clean GPX or an animation-ready route.</span>
      </li>
    </ol>
  </section>

  <section class="panel highlights">
    <div>
      <h3>What you get</h3>
      <p>Lightweight scripts and clear defaults so you can iterate fast.</p>
    </div>
    <ul>
      <li>EXIF-backed trim for video alignment.</li>
      <li>Web Mercator export for map animation workflows.</li>
      <li>Warnings and fallbacks when timestamps are missing.</li>
    </ul>
  </section>

  <section class="footer-cta">
    <h3>Backend coming next</h3>
    <p>For now, this stays frontend-only. We can hook it up once the backend is ready.</p>
    <a class="btn primary" href="https://github.com/OpenAI-Tools/GPX_helper" target="_blank" rel="noreferrer">
      Read the docs
    </a>
  </section>
</main>
