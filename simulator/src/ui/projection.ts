/**
 * Perspective camera standing behind the mound, looking at home plate.
 *
 * World coordinates (feet): x = catcher's-view horizontal (+ = first-base
 * side), y = distance from the front of home plate toward the mound, z =
 * height. From the pitcher's side the x axis is mirrored on screen.
 */

export const VIEW_W = 800;
export const VIEW_H = 600;

/**
 * Feet from the plate. Far behind the mound with a long lens (like a TV
 * center-field camera, mirrored): a close camera exaggerates perspective so
 * much that a ball released below eye level appears to climb before it
 * drops. Far back, pitch paths look the way they move — down and across.
 * PX_PER_FT_AT_PLATE keeps the plate the same size either way.
 */
const CAMERA_Y = 130;
const PX_PER_FT_AT_PLATE = 80;
const FOCAL = PX_PER_FT_AT_PLATE * CAMERA_Y;
const CENTER_X = VIEW_W / 2;
/** Screen y of the ground at the front of home plate (kept fixed). */
const GROUND_AT_PLATE_Y = 575;

/**
 * Camera height = the pitcher's release height (about eye level). With the
 * eye at the release point, a pitch that leaves the hand going down also
 * moves down on screen from the very first frame. The horizon moves with
 * the camera so the plate, hitter, and zone stay put on screen.
 */
let cameraZ = 6.0;
let horizonY = GROUND_AT_PLATE_Y - cameraZ * PX_PER_FT_AT_PLATE;

export function setCameraHeight(feet: number): void {
  cameraZ = Math.min(7.0, Math.max(4.5, feet));
  horizonY = GROUND_AT_PLATE_Y - cameraZ * PX_PER_FT_AT_PLATE;
}

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
    sy: horizonY + (cameraZ - z) * scale,
    scale,
  };
}

/** Inverse of `project` on the plate's front plane (y = 0). */
export function unprojectAtPlate(sx: number, sy: number): { x: number; z: number } {
  const scale = FOCAL / CAMERA_Y;
  return { x: (CENTER_X - sx) / scale, z: cameraZ - (sy - horizonY) / scale };
}

export function polygon(points: [number, number, number][]): string {
  return points
    .map(([x, y, z]) => {
      const p = project(x, y, z);
      return `${p.sx.toFixed(1)},${p.sy.toFixed(1)}`;
    })
    .join(" ");
}
