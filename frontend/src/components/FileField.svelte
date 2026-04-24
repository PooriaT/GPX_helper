<script>
  export let label;
  export let accept = '';
  export let multiple = false;
  export let required = false;
  export let fileName = '';
  export let placeholder = 'No file selected';
  export let onChange;
</script>

<label class="file-field">
  <span class="field-label">{label}</span>
  <span class="file-control" aria-hidden="true">
    <span class="file-control-action">{multiple ? 'Choose files' : 'Choose file'}</span>
    <span class:file-placeholder={!fileName} class="file-control-name">{fileName || placeholder}</span>
  </span>
  <input
    class="file-input-native"
    type="file"
    aria-label={label}
    {accept}
    {multiple}
    {required}
    on:change={onChange}
  />
</label>
