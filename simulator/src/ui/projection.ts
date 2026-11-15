/**
 * Perspective camera standing behind the mound, looking at home plate.
 *
 * World coordinates (feet): x = catcher's-view horizontal (+ = first-base
 * side), y = distance from the front of home plate toward the mound, z =
 * height. From the pitcher's side the x axis is mirrored on screen.
 */

export const VIEW_W = 800;
export const VIEW_H = 600;

const CAMERA_Y = 64; // feet from the plate
export const CAMERA_Z = 6.0; // a pitcher's eye height
const PX_PER_FT_AT_PLATE = 80;
const FOCAL = PX_PER_FT_AT_PLATE * CAMERA_Y;
const CENTER_X = VIEW_W / 2;
const HORIZON_Y = 95;

export interface ScreenPoint {
  sx: number;
  sy: number;
  /** Pixels per foot at this depth. */
  scale: number;
}

export function project(x: number, y: number, z: number): ScreenPoint {
  const depth = Math.max(CAMERA_Y - y, 0.5);
  const scale = FOCAL / depth;
  return {
    sx: CENTER_X - x * scale,
    sy: HORIZON_Y + (CAMERA_Z - z) * scale,
    scale,
  };
}

/** Inverse of `project` on the plate's front plane (y = 0). */
export function unprojectAtPlate(sx: number, sy: number): { x: number; z: number } {
  const scale = FOCAL / CAMERA_Y;
  return { x: (CENTER_X - sx) / scale, z: CAMERA_Z - (sy - HORIZON_Y) / scale };
}

export function polygon(points: [number, number, number][]): string {
  return points
    .map(([x, y, z]) => {
      const p = project(x, y, z);
      return `${p.sx.toFixed(1)},${p.sy.toFixed(1)}`;
    })
    .join(" ");
}
