const QUICKTIME_EPOCH_OFFSET_MS = Date.UTC(1904, 0, 1);
const BOX_HEADER_SIZE = 8;
const LARGE_BOX_HEADER_SIZE = 16;

function decodeBoxType(view, offset) {
  let value = '';
  for (let index = 0; index < 4; index += 1) {
    value += String.fromCharCode(view.getUint8(offset + index));
  }
  return value;
}

function parseBoxHeader(view, offset, totalLength) {
  if (offset + BOX_HEADER_SIZE > totalLength) {
    return null;
  }

  const size32 = view.getUint32(offset);
  const type = decodeBoxType(view, offset + 4);

  if (size32 === 0) {
    return {
      type,
      size: totalLength - offset,
      headerSize: BOX_HEADER_SIZE
    };
  }

  if (size32 === 1) {
    if (offset + LARGE_BOX_HEADER_SIZE > totalLength) {
      throw new Error('Video metadata is truncated.');
    }
    const size64 = Number(view.getBigUint64(offset + BOX_HEADER_SIZE));
    return {
      type,
      size: size64,
      headerSize: LARGE_BOX_HEADER_SIZE
    };
  }

  return {
    type,
    size: size32,
    headerSize: BOX_HEADER_SIZE
  };
}

function readCreationTimeSeconds(view, offset) {
  const version = view.getUint8(offset);
  if (version === 1) {
    return Number(view.getBigUint64(offset + 4));
  }
  return view.getUint32(offset + 4);
}

function creationTimeToDate(secondsSinceQuickTimeEpoch) {
  return new Date(QUICKTIME_EPOCH_OFFSET_MS + secondsSinceQuickTimeEpoch * 1000);
}

function readHeaderCreationTime(view, offset, label) {
  if (offset + 8 > view.byteLength) {
    throw new Error(`${label} metadata is truncated.`);
  }

  const creationTimeSeconds = readCreationTimeSeconds(view, offset);
  if (!Number.isFinite(creationTimeSeconds) || creationTimeSeconds <= 0) {
    throw new Error('Video metadata does not contain a valid creation time.');
  }

  return creationTimeToDate(creationTimeSeconds);
}

function findPreferredCreationTime(view, startOffset, endOffset) {
  let offset = startOffset;
  let movieCreationTime = null;

  while (offset < endOffset) {
    const header = parseBoxHeader(view, offset, endOffset);
    if (!header || header.size < header.headerSize) {
      break;
    }

    const bodyOffset = offset + header.headerSize;
    const boxEnd = Math.min(offset + header.size, endOffset);

    if (header.type === 'mdhd') {
      return readHeaderCreationTime(view, bodyOffset, 'Media header');
    }

    if (header.type === 'mvhd') {
      movieCreationTime = readHeaderCreationTime(view, bodyOffset, 'Movie header');
    }

    if (['moov', 'trak', 'mdia'].includes(header.type)) {
      const nestedCreationTime = findPreferredCreationTime(view, bodyOffset, boxEnd);
      if (nestedCreationTime) {
        return nestedCreationTime;
      }
    }

    offset += header.size;
  }

  return movieCreationTime;
}

function parseMoovCreationTime(buffer, moovHeaderSize) {
  const view = new DataView(buffer);
  const creationTime = findPreferredCreationTime(view, moovHeaderSize, view.byteLength);

  if (creationTime) {
    return creationTime;
  }

  throw new Error('Video metadata does not contain a movie or media header.');
}

async function readFileSlice(file, offset, length) {
  const end = Math.min(file.size, offset + length);
  const blob = file.slice(offset, end);
  if (typeof blob.arrayBuffer === 'function') {
    return blob.arrayBuffer();
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error || new Error('Unable to read video metadata.'));
    reader.readAsArrayBuffer(blob);
  });
}

export async function loadEmbeddedVideoStart(file) {
  let offset = 0;

  while (offset < file.size) {
    const headerBuffer = await readFileSlice(file, offset, LARGE_BOX_HEADER_SIZE);
    if (headerBuffer.byteLength < BOX_HEADER_SIZE) {
      break;
    }

    const headerView = new DataView(headerBuffer);
    const header = parseBoxHeader(headerView, 0, headerBuffer.byteLength);
    if (!header || header.size < header.headerSize) {
      break;
    }

    if (header.type === 'moov') {
      const moovBuffer = await readFileSlice(file, offset, header.size);
      return parseMoovCreationTime(moovBuffer, header.headerSize);
    }

    offset += header.size;
  }

  throw new Error(
    'Unable to read the video creation time from embedded metadata. Verify the file metadata before trimming.'
  );
}

export const __test__ = {
  creationTimeToDate,
  parseMoovCreationTime
};
