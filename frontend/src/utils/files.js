export function readFileText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error || new Error('Unable to read file.'));
    reader.readAsText(file);
  });
}

export function loadVideoDuration(file) {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    video.preload = 'metadata';
    const objectUrl = URL.createObjectURL(file);
    const cleanup = () => {
      URL.revokeObjectURL(objectUrl);
    };
    video.onloadedmetadata = () => {
      cleanup();
      if (Number.isFinite(video.duration)) {
        resolve(video.duration);
      } else {
        reject(new Error('Unable to read video duration.'));
      }
    };
    video.onerror = () => {
      cleanup();
      reject(new Error('Unable to read video metadata.'));
    };
    video.src = objectUrl;
  });
}
