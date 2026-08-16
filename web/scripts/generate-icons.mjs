import { writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import zlib from "zlib";

const __dirname = dirname(fileURLToPath(import.meta.url));
const outDir = join(__dirname, "../public/icons");

// Minimal PNG encoder (RGBA, paper bg + sage T approximated as solid blocks)
// Uses a simple approach: create raw PNG via pngjs-like minimal structure
// For reliability, use sharp if available, else write precomputed minimal PNGs

const PAPER = [250, 249, 247, 255];
const GREEN = [61, 122, 92, 255];

function crc32(buf) {
  let c = ~0;
  for (let i = 0; i < buf.length; i++) {
    c ^= buf[i];
    for (let k = 0; k < 8; k++) {
      c = (c >>> 1) ^ (0xedb88320 & -(c & 1));
    }
  }
  return ~c >>> 0;
}

function chunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const typeBuf = Buffer.from(type);
  const crcBuf = Buffer.alloc(4);
  const crc = crc32(Buffer.concat([typeBuf, data]));
  crcBuf.writeUInt32BE(crc);
  return Buffer.concat([len, typeBuf, data, crcBuf]);
}

function createIconPng(size) {
  const raw = [];
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.28;

  for (let y = 0; y < size; y++) {
    raw.push(0); // filter byte
    for (let x = 0; x < size; x++) {
      // Simple T shape: vertical bar + horizontal bar at top
      const inVertical =
        x >= cx - r * 0.35 && x <= cx + r * 0.35 && y >= cy - r * 0.1;
      const inHorizontal =
        y >= cy - r && y <= cy - r * 0.55 &&
        x >= cx - r && x <= cx + r;
      const pixel = inVertical || inHorizontal ? GREEN : PAPER;
      raw.push(...pixel);
    }
  }

  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0);
  ihdr.writeUInt32BE(size, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 6; // RGBA
  ihdr[10] = 0;
  ihdr[11] = 0;
  ihdr[12] = 0;

  const compressed = zlib.deflateSync(Buffer.from(raw));

  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr),
    chunk("IDAT", compressed),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

for (const size of [192, 512]) {
  const png = createIconPng(size);
  const path = join(outDir, `icon-${size}.png`);
  writeFileSync(path, png);
  console.log(`Wrote ${path}`);
}

writeFileSync(join(outDir, "apple-touch-icon.png"), createIconPng(192));
console.log("Wrote apple-touch-icon.png");
