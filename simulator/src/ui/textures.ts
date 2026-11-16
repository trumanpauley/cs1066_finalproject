/**
 * SVG art -> texture sources for the Phaser scene.
 *
 * The field, crowd, umpire, catcher, hitter body/head, and mitt are drawn
 * once as SVG (crisp vector art, easy to edit) and handed to Phaser as
 * images at TEXTURE_RES× resolution. Everything that moves is drawn live.
 */

import { createElement as h, type ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  CatcherFigure,
  HITTER_FRAME,
  HitterBody,
  HitterHead,
  MittShape,
  UmpireFigure,
} from "./figures";
import { polygon, project, VIEW_H, VIEW_W } from "./projection";

/** Texture pixels per scene pixel (the game renders at 2× for crispness). */
export const TEXTURE_RES = 2;

export interface SvgTexture {
  key: string;
  svg: string;
  width: number;
  height: number;
}

const svgDoc = (viewBox: string, width: number, height: number, body: ReactElement) =>
  renderToStaticMarkup(
    h("svg", { xmlns: "http://www.w3.org/2000/svg", viewBox, width, height }, body),
  );

/** Tiny deterministic RNG so the crowd looks the same every load. */
function seeded(seed: number) {
  let a = seed;
  return () => {
    a = (a * 1664525 + 1013904223) >>> 0;
    return a / 4294967296;
  };
}

function Field() {
  const plateCorner = project(0, 0, 0);
  const dirt: [number, number, number][] = [];
  for (let a = 0; a <= 360; a += 10) {
    const rad = (a * Math.PI) / 180;
    dirt.push([13 * Math.cos(rad), Math.min(9, 13 * Math.sin(rad)), 0]);
  }

  // Crowd: rows of dim heads and shoulders in the stands.
  const rnd = seeded(7);
  const crowd: ReactElement[] = [];
  for (let row = 0; row < 8; row++) {
    const y = 32 + row * 21;
    const size = 4 + row * 0.55;
    for (let x = -8 + (row % 2) * 9; x < VIEW_W + 10; x += 17 + rnd() * 6) {
      const shade = 22 + Math.floor(rnd() * 26);
      const fill = `rgb(${shade},${shade + 4},${shade + 14})`;
      crowd.push(
        h("g", { key: `${row}-${x.toFixed(0)}`, opacity: 0.55 + rnd() * 0.3 },
          h("circle", { cx: x, cy: y, r: size, fill }),
          h("rect", { x: x - size * 1.5, y: y + size * 0.7, width: size * 3, height: size * 2.6, rx: size, fill }),
        ),
      );
    }
  }

  const lights = [110, 290, 510, 690].map((x, i) =>
    h("circle", { key: i, cx: x, cy: 6, r: 120, fill: "url(#light)" }),
  );

  return h("g", null,
    h("defs", null,
      h("linearGradient", { id: "stands", x1: 0, y1: 0, x2: 0, y2: 1 },
        h("stop", { offset: 0, stopColor: "#05070c" }),
        h("stop", { offset: 1, stopColor: "#111724" })),
      h("linearGradient", { id: "ground", x1: 0, y1: 0, x2: 0, y2: 1 },
        h("stop", { offset: 0, stopColor: "#1b1816" }),
        h("stop", { offset: 1, stopColor: "#2e251e" })),
      h("radialGradient", { id: "clay", cx: 0.5, cy: 0.5, r: 0.5 },
        h("stop", { offset: 0, stopColor: "#4d3c2f" }),
        h("stop", { offset: 1, stopColor: "#34281f" })),
      h("radialGradient", { id: "light", cx: 0.5, cy: 0.5, r: 0.5 },
        h("stop", { offset: 0, stopColor: "#cfe0ff", stopOpacity: 0.22 }),
        h("stop", { offset: 1, stopColor: "#cfe0ff", stopOpacity: 0 })),
      h("linearGradient", { id: "wall", x1: 0, y1: 0, x2: 0, y2: 1 },
        h("stop", { offset: 0, stopColor: "#141b27" }),
        h("stop", { offset: 1, stopColor: "#0c1018" })),
    ),
    h("rect", { width: VIEW_W, height: VIEW_H, fill: "url(#stands)" }),
    ...crowd,
    ...lights,
    h("rect", { x: 0, y: 214, width: VIEW_W, height: 122, fill: "url(#wall)" }),
    h("rect", { x: 0, y: 212, width: VIEW_W, height: 4, fill: "#7aa2f7", opacity: 0.4 }),
    h("rect", { x: 0, y: 334, width: VIEW_W, height: VIEW_H - 334, fill: "url(#ground)" }),
    h("polygon", { points: polygon(dirt), fill: "url(#clay)" }),
    h("g", { stroke: "#e9e4da", strokeOpacity: 0.55, fill: "none", strokeWidth: 2 },
      h("line", { x1: plateCorner.sx, y1: plateCorner.sy, x2: plateCorner.sx - 900, y2: plateCorner.sy + 900 }),
      h("line", { x1: plateCorner.sx, y1: plateCorner.sy, x2: plateCorner.sx + 900, y2: plateCorner.sy + 900 }),
      h("polygon", { points: polygon([[1.21, -3, 0], [5.21, -3, 0], [5.21, 3, 0], [1.21, 3, 0]]), strokeWidth: 1.5 }),
      h("polygon", { points: polygon([[-1.21, -3, 0], [-5.21, -3, 0], [-5.21, 3, 0], [-1.21, 3, 0]]), strokeWidth: 1.5 }),
    ),
    h("polygon", {
      points: polygon([[0.71, 0, 0], [-0.71, 0, 0], [-0.71, -0.71, 0], [0, -1.42, 0], [0.71, -0.71, 0]]),
      fill: "#f4f1ea",
    }),
    h(UmpireFigure),
    h(CatcherFigure),
  );
}

/** Pixels per local foot in the hitter textures. */
export const HITTER_PX_PER_FT = 80 * TEXTURE_RES;

function hitterTexture(key: string, part: ReactElement): SvgTexture {
  const f = HITTER_FRAME;
  const width = Math.round(f.w * HITTER_PX_PER_FT);
  const height = Math.round(f.h * HITTER_PX_PER_FT);
  return { key, svg: svgDoc(`${f.x} ${f.y} ${f.w} ${f.h}`, width, height, part), width, height };
}

/** Mitt texture radius in texture pixels. */
export const MITT_TEX_R = 48;

/** All static textures. Call after the camera height is set. */
export function buildSvgTextures(): SvgTexture[] {
  const W = VIEW_W * TEXTURE_RES;
  const H = VIEW_H * TEXTURE_RES;
  return [
    { key: "field", svg: svgDoc(`0 0 ${VIEW_W} ${VIEW_H}`, W, H, h(Field)), width: W, height: H },
    hitterTexture("hitter-body", h(HitterBody)),
    hitterTexture("hitter-head", h(HitterHead)),
    {
      key: "mitt",
      svg: svgDoc("-1.1 -1.1 2.2 2.2", MITT_TEX_R * 2.2, MITT_TEX_R * 2.2, h(MittShape)),
      width: MITT_TEX_R * 2.2,
      height: MITT_TEX_R * 2.2,
    },
  ];
}

/** Base64 data URL (Phaser's loader decodes data URLs with atob). */
export function svgDataUrl(svg: string): string {
  const bytes = new TextEncoder().encode(svg);
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  }
  return `data:image/svg+xml;base64,${btoa(bin)}`;
}
