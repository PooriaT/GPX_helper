import { parseGpxDurationFromText, parseGpxTimeRangeFromText } from '../gpx-metadata';
import { loadEmbeddedVideoStart } from '../video-metadata';
import { readFileText, loadVideoDuration } from './files';
import { formatUtcLabel, toLocalDateTimeValue } from './time';

export async function deriveVideoTimes(file) {
  const [durationSeconds, start] = await Promise.all([loadVideoDuration(file), loadEmbeddedVideoStart(file)]);
  const end = new Date(start.getTime() + durationSeconds * 1000);
  return { durationSeconds, start, end };
}

export async function buildVideoClip(file, index) {
  const { durationSeconds, start, end } = await deriveVideoTimes(file);
  return {
    id: `${file.name}-${file.size}-${index}`,
    name: file.name,
    durationSeconds,
    startIso: start.toISOString(),
    endIso: end.toISOString(),
    startLocal: toLocalDateTimeValue(start),
    endLocal: toLocalDateTimeValue(end)
  };
}

export async function buildMapAnimationBatchPair(gpxFile, videoFile, index) {
  const durationSeconds = await loadVideoDuration(videoFile);
  const gpxBaseName = gpxFile?.name?.replace(/\.[^./\\]+$/, '') || `route-${index + 1}`;
  return {
    gpxFile,
    videoFile,
    durationSeconds: Math.max(1, Math.round(durationSeconds)),
    outputName: gpxBaseName
  };
}

export async function parseGpxDuration(file) {
  if (!file) return null;
  const text = await readFileText(file);
  return parseGpxDurationFromText(text);
}

export async function parseGpxTimeRange(file) {
  if (!file) return null;
  const text = await readFileText(file);
  return parseGpxTimeRangeFromText(text);
}

function buildVideoRangeError(label, start, end, gpxRange) {
  return `${label} spans ${formatUtcLabel(start)} to ${formatUtcLabel(end)}, but the GPX track only covers ${formatUtcLabel(gpxRange.start)} to ${formatUtcLabel(gpxRange.end)}.`;
}

export async function ensureRangeFitsGpx(label, start, end, gpxFile) {
  if (!gpxFile) return;
  const gpxRange = await parseGpxTimeRange(gpxFile);
  if (!gpxRange) throw new Error('The GPX file does not contain readable timestamps.');
  if (start < gpxRange.start || end > gpxRange.end) throw new Error(buildVideoRangeError(label, start, end, gpxRange));
}

export async function ensureVideosFitGpx(clips, gpxFile) {
  if (!clips.length || !gpxFile) return;
  const gpxRange = await parseGpxTimeRange(gpxFile);
  if (!gpxRange) throw new Error('The GPX file does not contain readable timestamps.');

  const mismatchedClip = clips.find((clip) => {
    const start = new Date(clip.startIso);
    const end = new Date(clip.endIso);
    return start < gpxRange.start || end > gpxRange.end;
  });

  if (mismatchedClip) {
    throw new Error(
      buildVideoRangeError(
        `Video "${mismatchedClip.name}"`,
        new Date(mismatchedClip.startIso),
        new Date(mismatchedClip.endIso),
        gpxRange
      )
    );
  }
}
