import { readFileSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import sharp from "sharp";

const __dirname = dirname(fileURLToPath(import.meta.url));
const outDir = join(__dirname, "../public/icons");
const svgPath = join(outDir, "icon.svg");

const svg = readFileSync(svgPath);

for (const size of [192, 512]) {
  const png = await sharp(svg).resize(size, size).png().toBuffer();
  const path = join(outDir, `icon-${size}.png`);
  writeFileSync(path, png);
  console.log(`Wrote ${path}`);
}

writeFileSync(
  join(outDir, "apple-touch-icon.png"),
  await sharp(svg).resize(192, 192).png().toBuffer(),
);
console.log("Wrote apple-touch-icon.png");
