import { describe, expect, it } from 'vitest';

import { loadEmbeddedVideoStart } from './video-metadata';

const QUICKTIME_EPOCH_OFFSET_MS = Date.UTC(1904, 0, 1);

function concatArrays(...arrays) {
  const totalLength = arrays.reduce((sum, array) => sum + array.length, 0);
  const combined = new Uint8Array(totalLength);
  let offset = 0;

  arrays.forEach((array) => {
    combined.set(array, offset);
    offset += array.length;
  });

  return combined;
}

function encodeType(type) {
  return Uint8Array.from(type.split('').map((character) => character.charCodeAt(0)));
}

function makeBox(type, payload) {
  const box = new Uint8Array(8 + payload.length);
  const view = new DataView(box.buffer);
  view.setUint32(0, box.length);
  box.set(encodeType(type), 4);
  box.set(payload, 8);
  return box;
}

function makeHeaderPayload(date, version = 0) {
  const creationTimeSeconds = Math.floor((date.getTime() - QUICKTIME_EPOCH_OFFSET_MS) / 1000);

  if (version === 1) {
    const payload = new Uint8Array(32);
    const view = new DataView(payload.buffer);
    payload[0] = 1;
    view.setBigUint64(4, BigInt(creationTimeSeconds));
    view.setBigUint64(12, BigInt(creationTimeSeconds));
    view.setUint32(20, 1000);
    view.setBigUint64(24, 2000n);
    return payload;
  }

  const payload = new Uint8Array(20);
  const view = new DataView(payload.buffer);
  view.setUint32(4, creationTimeSeconds);
  view.setUint32(8, creationTimeSeconds);
  view.setUint32(12, 1000);
  view.setUint32(16, 2000);
  return payload;
}

function makeHdlrPayload(handlerType) {
  const payload = new Uint8Array(24);
  payload.set(encodeType(handlerType), 8);
  return payload;
}

function makeShortHdlrPayload(length = 8) {
  return new Uint8Array(length);
}

function makeInvalidBox(prefix = 'vide') {
  return encodeType(prefix.padEnd(8, '\0').slice(0, 8));
}

function makeTrack({ handlerType = 'vide', mediaDate = null, version = 0 } = {}) {
  const mdiaChildren = [makeBox('hdlr', makeHdlrPayload(handlerType))];

  if (mediaDate !== null) {
    mdiaChildren.unshift(makeBox('mdhd', makeHeaderPayload(mediaDate, version)));
  }

  return makeBox('trak', makeBox('mdia', concatArrays(...mdiaChildren)));
}

function makeUnsetMdhd(version = 0) {
  return makeBox('mdhd', makeHeaderPayload(new Date(QUICKTIME_EPOCH_OFFSET_MS), version));
}

function makeVideoFile({ movieDate, tracks = [], version = 0 }) {
  const ftypPayload = new Uint8Array(8);
  const fileBytes = concatArrays(
    makeBox('ftyp', ftypPayload),
    makeBox('moov', concatArrays(makeBox('mvhd', makeHeaderPayload(movieDate, version)), ...tracks))
  );

  return new File([fileBytes], 'GX010001.MP4', { type: 'video/mp4' });
}

describe('loadEmbeddedVideoStart', () => {
  it('reads a QuickTime creation time from the mvhd box', async () => {
    const expected = new Date('2025-11-29T18:42:49.000Z');

    await expect(loadEmbeddedVideoStart(makeVideoFile({ movieDate: expected }))).resolves.toEqual(expected);
  });

  it('supports version 1 mvhd creation times', async () => {
    const expected = new Date('2026-01-02T03:04:05.000Z');

    await expect(loadEmbeddedVideoStart(makeVideoFile({ movieDate: expected, version: 1 }))).resolves.toEqual(expected);
  });

  it('prefers the video-track mdhd media creation time when available', async () => {
    const movieDate = new Date('2026-01-02T03:04:05.000Z');
    const mediaDate = new Date('2026-01-02T03:05:15.000Z');

    const file = makeVideoFile({
      movieDate,
      tracks: [makeTrack({ mediaDate })]
    });

    await expect(loadEmbeddedVideoStart(file)).resolves.toEqual(mediaDate);
  });

  it('falls back to mvhd when the video-track mdhd creation time is unset', async () => {
    const movieDate = new Date('2026-01-02T03:04:05.000Z');
    const file = makeVideoFile({
      movieDate,
      tracks: [makeBox('trak', makeBox('mdia', concatArrays(makeUnsetMdhd(), makeBox('hdlr', makeHdlrPayload('vide')))))]
    });

    await expect(loadEmbeddedVideoStart(file)).resolves.toEqual(movieDate);
  });

  it('ignores non-video mdhd boxes when choosing the preferred creation time', async () => {
    const movieDate = new Date('2026-01-02T03:04:05.000Z');
    const audioDate = new Date('2026-01-02T03:03:05.000Z');
    const videoDate = new Date('2026-01-02T03:05:15.000Z');
    const file = makeVideoFile({
      movieDate,
      tracks: [makeTrack({ handlerType: 'soun', mediaDate: audioDate }), makeTrack({ mediaDate: videoDate })]
    });

    await expect(loadEmbeddedVideoStart(file)).resolves.toEqual(videoDate);
  });

  it('falls back to mvhd when a truncated hdlr is followed by another box that starts with vide', async () => {
    const movieDate = new Date('2026-01-02T03:04:05.000Z');
    const mediaDate = new Date('2026-01-02T03:05:15.000Z');
    const truncatedTrack = makeBox(
      'trak',
      makeBox(
        'mdia',
        concatArrays(
          makeBox('mdhd', makeHeaderPayload(mediaDate)),
          makeBox('hdlr', makeShortHdlrPayload()),
          makeInvalidBox('videfree')
        )
      )
    );
    const file = makeVideoFile({
      movieDate,
      tracks: [truncatedTrack]
    });

    await expect(loadEmbeddedVideoStart(file)).resolves.toEqual(movieDate);
  });

  it('fails when embedded creation metadata is missing', async () => {
    const file = new File([makeBox('ftyp', new Uint8Array(8))], 'GX010001.MP4', { type: 'video/mp4' });

    await expect(loadEmbeddedVideoStart(file)).rejects.toThrow(/embedded metadata/i);
  });
});
