<script>
  export let title;
  export let description;
</script>

<section class="tool-card task-container wide">
  <header class="section-header task-header">
    <p class="eyebrow">Selected task</p>
    <h2>{title}</h2>
    <p class="muted-text">{description}</p>
  </header>
  <div class="task-flow">
    <slot />
  </div>
</section>
