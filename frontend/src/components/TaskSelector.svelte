<script>
  export let tasks = [];
  export let selectedTask = '';
</script>

<section class="task-selector" aria-labelledby="task-selector-title">
  <div class="task-selector-header">
    <p class="eyebrow">Task selection</p>
    <h2 id="task-selector-title">Choose what you want to do</h2>
  </div>
  <div class="task-options">
    {#each tasks as task}
      <a
        class="task-option"
        class:task-option-active={selectedTask === task.id}
        href={task.href}
        aria-current={selectedTask === task.id ? 'step' : undefined}
      >
        <span class="task-option-title">{task.label}</span>
        <span class="task-option-description">{task.description}</span>
      </a>
    {/each}
  </div>
</section>
