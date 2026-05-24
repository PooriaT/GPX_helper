export function buildTrimByTimeFormData(gpxFile, startIso, endIso) {
  const formData = new FormData();
  formData.append('gpx_file', gpxFile);
  formData.append('start_time', startIso);
  formData.append('end_time', endIso);
  return formData;
}

export function buildTrimByVideosFormData(gpxFile, clips) {
  const formData = new FormData();
  formData.append('gpx_file', gpxFile);
  formData.append(
    'clips_json',
    JSON.stringify(clips.map((clip) => ({ start_time: clip.startIso, end_time: clip.endIso, duration_seconds: clip.durationSeconds })))
  );
  return formData;
}

export function buildMapAnimationFormData(mapAnimation, resolutionLabel) {
  const formData = new FormData();
  formData.append('gpx_file', mapAnimation.gpxFile);
  formData.append('duration_seconds', String(mapAnimation.durationSeconds));
  formData.append('fps', String(mapAnimation.fps));
  formData.append('resolution', resolutionLabel);
  formData.append('marker_style', mapAnimation.markerStyle || 'default');
  formData.append('marker_color', mapAnimation.markerColor);
  formData.append('trail_color', mapAnimation.trailColor);
  formData.append('full_trail_color', mapAnimation.fullTrailColor);
  formData.append('full_trail_opacity', String(mapAnimation.fullTrailOpacity));
  formData.append('marker_size', String(mapAnimation.markerSize));
  formData.append('line_width', String(mapAnimation.lineWidth));
  formData.append('line_opacity', String(mapAnimation.lineOpacity));
  if (mapAnimation.tileType) formData.append('tile_type', mapAnimation.tileType);
  return formData;
}

export function buildBatchMapAnimationFormData(batchState, sharedMapAnimationSettings, resolutionLabel) {
  const formData = new FormData();
  batchState.gpxFiles.forEach((gpxFile) => {
    formData.append('gpx_files', gpxFile);
  });
  formData.append(
    'jobs_json',
    JSON.stringify(
      batchState.pairs.map((pair, index) => {
        const job = {
          gpx_file_index: index,
          duration_seconds: Number(pair.durationSeconds)
        };
        const outputName = pair.outputName?.trim();
        if (outputName) job.output_name = outputName;
        return job;
      })
    )
  );
  formData.append('fps', String(sharedMapAnimationSettings.fps));
  formData.append('resolution', resolutionLabel);
  formData.append('marker_style', sharedMapAnimationSettings.markerStyle || 'default');
  formData.append('marker_color', sharedMapAnimationSettings.markerColor);
  formData.append('trail_color', sharedMapAnimationSettings.trailColor);
  formData.append('full_trail_color', sharedMapAnimationSettings.fullTrailColor);
  formData.append('full_trail_opacity', String(sharedMapAnimationSettings.fullTrailOpacity));
  formData.append('marker_size', String(sharedMapAnimationSettings.markerSize));
  formData.append('line_width', String(sharedMapAnimationSettings.lineWidth));
  formData.append('line_opacity', String(sharedMapAnimationSettings.lineOpacity));
  if (sharedMapAnimationSettings.tileType) formData.append('tile_type', sharedMapAnimationSettings.tileType);
  return formData;
}

export function buildTelemetryFormData(telemetryVideo, resolutionLabel, backgroundColor) {
  const formData = new FormData();
  formData.append('gpx_file', telemetryVideo.gpxFile);
  formData.append('duration_seconds', String(telemetryVideo.durationSeconds));
  formData.append('fps', String(telemetryVideo.fps));
  formData.append('resolution', resolutionLabel);
  formData.append('telemetry_type', telemetryVideo.telemetryType);
  formData.append('background_color', backgroundColor);
  return formData;
}

export function resolveTelemetryBackgroundColor(telemetryVideo) {
  const backgroundMode = telemetryVideo.backgroundMode ?? 'transparent';
  return backgroundMode === 'transparent' ? 'transparent' : telemetryVideo.backgroundColor?.trim() || '#000000';
}
