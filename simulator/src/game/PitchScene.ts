/**
 * Phaser scene for the pitcher's-view simulator.
 *
 * React owns all game state and passes it in through `getState()`; this
 * scene only draws it (60 fps, WebGL) and adds effects: ball glow and ground
 * shadow, mitt-pop dust, contact sparks, dirt, camera shake and zoom punch.
 * World coordinates are the 800×600 scene from `ui/projection`; the camera
 * zooms 2× so textures and vector drawing stay crisp.
 */

import Phaser from "phaser";
import { zoneBounds, type HitterProfile, type Location } from "../engine";
import { hitterPlacement, mittScreen } from "../ui/figures";
import { buildHitterParts, PART_PX, type PartTexture } from "../ui/hitterArt";
import { hitterSkeleton, type HitterMotion, type Pt } from "../ui/hitterRig";
import { project, unprojectAtPlate, VIEW_H, VIEW_W } from "../ui/projection";
import { CALL_COLORS, type PitchFx, type PitchTrail, type StageState } from "../ui/sceneTypes";
import { buildSvgTextures, MITT_TEX_R, svgDataUrl, TEXTURE_RES } from "../ui/textures";

const IDLE: HitterMotion = { load: 0, swing: 0, take: 0, flinch: 0, mode: "idle" };

/**
 * Dev aid: `?pose=contact:0.4` (or miss/take/load/hbp) freezes the batter at
 * a point in that motion, for tuning the rig. Ignored when absent.
 */
function debugPose(): HitterMotion | null {
  const raw = typeof window === "undefined" ? null : new URLSearchParams(window.location.search).get("pose");
  if (!raw) return null;
  const [mode, value] = raw.split(":");
  const t = Math.min(1, Math.max(0, Number(value ?? 1)));
  switch (mode) {
    case "load":
      return { ...IDLE, load: t, mode: "take" };
    case "take":
      return { ...IDLE, load: 1, take: t, mode: "take" };
    case "contact":
    case "miss":
      return { ...IDLE, load: 1, swing: t, mode };
    case "hbp":
      return { ...IDLE, load: 1, flinch: t, mode: "hbp" };
    default:
      return null;
  }
}
const DEBUG_POSE = debugPose();

/** Batter part images, posed every frame. */
interface HitterParts {
  backThigh: Phaser.GameObjects.Image;
  backShin: Phaser.GameObjects.Image;
  backCleat: Phaser.GameObjects.Image;
  frontThigh: Phaser.GameObjects.Image;
  frontShin: Phaser.GameObjects.Image;
  frontCleat: Phaser.GameObjects.Image;
  pelvis: Phaser.GameObjects.Image;
  torso: Phaser.GameObjects.Image;
  head: Phaser.GameObjects.Image;
  backUpper: Phaser.GameObjects.Image;
  backFore: Phaser.GameObjects.Image;
  frontUpper: Phaser.GameObjects.Image;
  frontFore: Phaser.GameObjects.Image;
  topGlove: Phaser.GameObjects.Image;
  bottomGlove: Phaser.GameObjects.Image;
  bat: Phaser.GameObjects.Image;
}

const ACCENT = 0x7aa2f7;
const FONT = '"Inter", "Segoe UI", system-ui, sans-serif';
const hex = (c: string) => Phaser.Display.Color.HexStringToColor(c).color;

interface Ring {
  x: number;
  y: number;
  born: number;
  color: number;
}

export class PitchScene extends Phaser.Scene {
  private getState: () => StageState;
  private mitt!: Phaser.GameObjects.Image;
  private hitterShadow!: Phaser.GameObjects.Graphics;
  private parts!: HitterParts;
  private partInfo = new Map<string, PartTexture>();
  private overlay!: Phaser.GameObjects.Graphics;
  private ballG!: Phaser.GameObjects.Graphics;
  private glow!: Phaser.GameObjects.Image;
  private labels: Phaser.GameObjects.Text[] = [];
  private dust!: Phaser.GameObjects.Particles.ParticleEmitter;
  private sparks!: Phaser.GameObjects.Particles.ParticleEmitter;
  private dirt!: Phaser.GameObjects.Particles.ParticleEmitter;
  private hover: Location | null = null;
  private rings: Ring[] = [];
  private firedFor = "";

  constructor(getState: () => StageState) {
    super("pitch");
    this.getState = getState;
  }

  preload() {
    for (const t of buildSvgTextures()) {
      this.load.svg(t.key, svgDataUrl(t.svg), { width: t.width, height: t.height });
    }
    for (const t of buildHitterParts()) {
      this.partInfo.set(t.key, t);
      this.load.svg(t.key, svgDataUrl(t.svg), { width: t.width, height: t.height });
    }
  }

  create() {
    const cam = this.cameras.main;
    cam.setZoom(TEXTURE_RES);
    cam.centerOn(VIEW_W / 2, VIEW_H / 2);
    this.makeDotTexture();

    this.add.image(0, 0, "field").setOrigin(0).setScale(1 / TEXTURE_RES).setDepth(0);
    this.mitt = this.add.image(0, 0, "mitt").setDepth(1);
    this.hitterShadow = this.add.graphics().setDepth(1.9);
    const img = (key: string) => {
      const info = this.partInfo.get(key)!;
      return this.add.image(0, 0, key).setOrigin(info.originX, info.originY);
    };
    this.parts = {
      backThigh: img("h-thigh"),
      backShin: img("h-shin"),
      backCleat: img("h-cleat"),
      frontThigh: img("h-thigh"),
      frontShin: img("h-shin"),
      frontCleat: img("h-cleat"),
      pelvis: img("h-pelvis"),
      torso: img("h-torso"),
      head: img("h-head"),
      backUpper: img("h-upper"),
      backFore: img("h-fore"),
      frontUpper: img("h-upper"),
      frontFore: img("h-fore"),
      topGlove: img("h-glove"),
      bottomGlove: img("h-glove"),
      bat: img("h-bat"),
    };
    this.overlay = this.add.graphics().setDepth(5);
    this.glow = this.add.image(0, 0, "dot").setBlendMode(Phaser.BlendModes.ADD).setDepth(8).setVisible(false);
    this.ballG = this.add.graphics().setDepth(9);

    const base = { lifespan: { min: 280, max: 620 }, emitting: false };
    this.dust = this.add
      .particles(0, 0, "dot", {
        ...base,
        speed: { min: 25, max: 95 },
        scale: { start: 0.32, end: 0.06 },
        alpha: { start: 0.75, end: 0 },
        tint: [0xa87652, 0xd9c6ae, 0x8a6244],
        gravityY: 70,
      })
      .setDepth(10);
    this.sparks = this.add
      .particles(0, 0, "dot", {
        ...base,
        speed: { min: 80, max: 260 },
        scale: { start: 0.22, end: 0 },
        alpha: { start: 1, end: 0 },
        tint: [0xffffff, 0xfff1c2, 0xcfe0ff],
        blendMode: Phaser.BlendModes.ADD,
      })
      .setDepth(10);
    this.dirt = this.add
      .particles(0, 0, "dot", {
        ...base,
        lifespan: { min: 400, max: 800 },
        speed: { min: 40, max: 140 },
        angle: { min: 200, max: 340 },
        scale: { start: 0.4, end: 0.1 },
        alpha: { start: 0.8, end: 0 },
        tint: [0x5a4434, 0x7a5d46, 0x3f2f24],
        gravityY: 260,
      })
      .setDepth(10);

    this.input.on("pointermove", (p: Phaser.Input.Pointer) => {
      this.hover = this.pointerToZone(p);
      this.input.setDefaultCursor(this.hover && this.getState().aiming ? "crosshair" : "default");
    });
    this.input.on("pointerdown", (p: Phaser.Input.Pointer) => {
      const loc = this.pointerToZone(p);
      const st = this.getState();
      if (loc && st.aiming) st.onAim(loc);
    });
    this.input.on("gameout", () => {
      this.hover = null;
    });
  }

  update(time: number) {
    const st = this.getState();
    this.drawHitter(st);
    this.drawMitt(st);
    this.drawOverlay(st, time);
    this.drawBall(st);
    this.fireEffects(st.fx, st);
    this.drawRings(time);
  }

  // -------------------------------------------------------------------------
  // Input
  // -------------------------------------------------------------------------

  private grid(hitter: HitterProfile) {
    const zb = zoneBounds(hitter);
    const cw = (zb.right - zb.left) / 3;
    const ch = (zb.top - zb.bottom) / 3;
    return { zb, cw, ch, left: zb.left - cw, right: zb.right + cw, bottom: zb.bottom - ch, top: zb.top + ch };
  }

  private pointerToZone(p: Phaser.Input.Pointer): Location | null {
    const wp = this.cameras.main.getWorldPoint(p.x, p.y);
    const w = unprojectAtPlate(wp.x, wp.y);
    const g = this.grid(this.getState().hitter);
    if (w.x < g.left || w.x > g.right || w.z < g.bottom || w.z > g.top) return null;
    return { x: w.x, z: w.z };
  }

  // -------------------------------------------------------------------------
  // Figures
  // -------------------------------------------------------------------------

  private drawHitter(st: StageState) {
    const place = hitterPlacement(st.hitter.bats);
    const sk = hitterSkeleton(DEBUG_POSE ?? st.frame?.hitter ?? IDLE, this.time.now);
    const k = place.scale / PART_PX; // texture px -> screen px
    const S = (p: Pt) => ({ x: place.sx + place.dir * place.scale * p.x, y: place.sy + place.scale * p.y });
    const P = this.parts;

    // Limb from joint a to joint b (stretched to the projected length).
    const limb = (im: Phaser.GameObjects.Image, a: Pt, b: Pt, depth: number) => {
      const A = S(a);
      const B = S(b);
      const len = Math.hypot(B.x - A.x, B.y - A.y);
      const bone = this.partInfo.get(im.texture.key)!.boneLength!;
      im.setPosition(A.x, A.y)
        .setRotation(Math.atan2(B.y - A.y, B.x - A.x))
        .setScale(len / (bone * PART_PX), k)
        .setDepth(depth);
    };

    // Shadow under the feet.
    const fb = S(sk.feet.back);
    const ff = S(sk.feet.front);
    this.hitterShadow
      .clear()
      .fillStyle(0x000000, 0.3)
      .fillEllipse((fb.x + ff.x) / 2, Math.max(fb.y, ff.y) + 2, Math.abs(ff.x - fb.x) + place.scale * 1.6, place.scale * 0.32);

    // Back leg (farther from the pitcher) is drawn first.
    limb(P.backThigh, sk.hips.back, sk.knees.back, 2.1);
    limb(P.backShin, sk.knees.back, sk.ankles.back, 2.11);
    const cb = S(sk.ankles.back);
    P.backCleat.setPosition(cb.x, cb.y)
      .setScale(place.dir * k, k)
      .setRotation(-sk.feet.backHeel * 0.55 * place.dir)
      .setDepth(2.12);

    // Hips, front leg, torso, head.
    const pv = S(sk.pelvis);
    const nk = S(sk.neck);
    const spineAngle = Math.atan2(nk.y - pv.y, nk.x - pv.x) + Math.PI / 2;
    const hipW = Math.min(1.12, Math.max(0.86, sk.hipSpan + 0.55));
    P.pelvis.setPosition(pv.x, pv.y)
      .setScale(place.dir * k * (hipW / 0.9), k)
      .setRotation(spineAngle * 0.4)
      .setDepth(2.2);

    limb(P.frontThigh, sk.hips.front, sk.knees.front, 2.3);
    limb(P.frontShin, sk.knees.front, sk.ankles.front, 2.31);
    const cf = S(sk.ankles.front);
    P.frontCleat.setPosition(cf.x, cf.y).setScale(place.dir * k, k).setRotation(0).setDepth(2.32);

    const torsoLen = Math.hypot(nk.x - pv.x, nk.y - pv.y) / (place.scale * 1.72);
    const torsoW = Math.min(1.45, Math.max(0.98, sk.shoulderSpan + 0.7));
    P.torso.setPosition(pv.x, pv.y)
      .setScale(place.dir * k * (torsoW / 1.32), k * torsoLen)
      .setRotation(spineAngle)
      .setDepth(2.4);

    const hd = S(sk.head);
    P.head.setPosition(hd.x, hd.y)
      .setScale(place.dir * k, k)
      .setRotation(sk.headTilt * 0.6 * place.dir)
      .setDepth(2.5);

    // Arms: a shoulder turned toward the catcher is behind the torso.
    const backArmDepth = sk.shoulders.backW < -0.1 ? 2.15 : 2.62;
    const frontArmDepth = sk.shoulders.frontW < -0.1 ? 2.16 : 2.64;
    limb(P.backUpper, sk.shoulders.back, sk.elbows.back, backArmDepth);
    limb(P.backFore, sk.elbows.back, sk.hands.top, backArmDepth + 0.005);
    limb(P.frontUpper, sk.shoulders.front, sk.elbows.front, frontArmDepth);
    limb(P.frontFore, sk.elbows.front, sk.hands.bottom, frontArmDepth + 0.005);

    // Bat: behind the head while the barrel points back toward the catcher.
    limb(P.bat, sk.bat.knob, sk.bat.tip, sk.bat.towardCatcher > 0.35 ? 2.45 : 2.6);

    const ht = S(sk.hands.top);
    const hb = S(sk.hands.bottom);
    P.topGlove.setPosition(ht.x, ht.y).setScale(k).setDepth(Math.max(backArmDepth, 2.6) + 0.02);
    P.bottomGlove.setPosition(hb.x, hb.y).setScale(k).setDepth(Math.max(frontArmDepth, 2.6) + 0.03);
  }

  private drawMitt(st: StageState) {
    const zb = zoneBounds(st.hitter);
    const m =
      st.frame?.mitt ?? (st.target ? { ...st.target, pop: 0 } : { x: 0, z: (zb.top + zb.bottom) / 2, pop: 0 });
    const s = mittScreen(m.x, m.z, m.pop);
    this.mitt.setPosition(s.sx, s.sy).setScale(s.r / MITT_TEX_R);
  }

  // -------------------------------------------------------------------------
  // Zone, trails, markers, crosshair
  // -------------------------------------------------------------------------

  private drawOverlay(st: StageState, time: number) {
    const g = this.overlay.clear();
    const { zb, cw, ch, left, right, bottom, top } = this.grid(st.hitter);
    const rect = (l: number, r: number, b: number, t: number) => {
      const a = project(l, 0, t);
      const c = project(r, 0, b);
      return { x: a.sx, y: a.sy, w: c.sx - a.sx, h: c.sy - a.sy };
    };
    const norm = (r: { x: number; y: number; w: number; h: number }) => ({
      x: Math.min(r.x, r.x + r.w),
      y: Math.min(r.y, r.y + r.h),
      w: Math.abs(r.w),
      h: Math.abs(r.h),
    });

    if (st.aiming) {
      const o = norm(rect(left, right, bottom, top));
      g.fillStyle(ACCENT, 0.04).fillRect(o.x, o.y, o.w, o.h);
      dashedRect(g, o, ACCENT, 0.3);
      if (this.hover) {
        const c = Math.floor((this.hover.x - left) / cw);
        const r = Math.floor((this.hover.z - bottom) / ch);
        const cell = norm(rect(left + c * cw, left + (c + 1) * cw, bottom + r * ch, bottom + (r + 1) * ch));
        g.fillStyle(ACCENT, 0.16).fillRect(cell.x, cell.y, cell.w, cell.h);
      }
    }

    const z = norm(rect(zb.left, zb.right, zb.bottom, zb.top));
    g.lineStyle(1, 0xffffff, st.aiming ? 0.2 : 0.09);
    for (const i of [1, 2]) {
      g.lineBetween(z.x + (z.w * i) / 3, z.y, z.x + (z.w * i) / 3, z.y + z.h);
      g.lineBetween(z.x, z.y + (z.h * i) / 3, z.x + z.w, z.y + (z.h * i) / 3);
    }
    g.lineStyle(1.6, 0xffffff, st.aiming ? 0.75 : 0.38).strokeRect(z.x, z.y, z.w, z.h);

    let label = 0;
    st.trails.forEach((t, i) => {
      label = this.drawTrail(g, t, i === st.trails.length - 1 && !st.frame?.ball, label);
    });

    for (const m of st.markers) {
      const p = project(m.loc.x, 0, m.loc.z);
      g.fillStyle(hex(CALL_COLORS[m.call]), 0.92).fillCircle(p.sx, p.sy, 8.5);
      this.label(label++, p.sx, p.sy, String(m.n), "#0e1117", 10);
    }

    if (st.target && st.aiming) {
      const p = project(st.target.x, 0, st.target.z);
      const a = 0.65 + 0.35 * Math.sin(time / 220);
      g.lineStyle(2, ACCENT, a).strokeCircle(p.sx, p.sy, 11);
      g.fillStyle(ACCENT, a).fillCircle(p.sx, p.sy, 2.5);
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        g.lineBetween(p.sx + dx * 13, p.sy + dy * 13, p.sx + dx * 18, p.sy + dy * 18);
      }
    }

    for (let i = label; i < this.labels.length; i++) this.labels[i].setVisible(false);
  }

  /** One pitch's flight path; the latest also shows its no-spin path and break. */
  private drawTrail(g: Phaser.GameObjects.Graphics, t: PitchTrail, latest: boolean, label: number): number {
    const color = hex(t.color);
    g.lineStyle(latest ? 2.2 : 1.4, color, latest ? 0.8 : 0.3);
    g.strokePoints(t.real.map((p) => new Phaser.Math.Vector2(p.sx, p.sy)));
    if (!latest) return label;

    const end = t.real[t.real.length - 1];
    const ghostEnd = t.ghost[t.ghost.length - 1];
    const dx = end.sx - ghostEnd.sx;
    const dy = end.sy - ghostEnd.sy;
    const len = Math.hypot(dx, dy);
    if (len <= 4) return label;

    dashedPolyline(g, t.ghost, 4, 4, 0xffffff, 0.35, 1.1);
    dashedCircle(g, ghostEnd.sx, ghostEnd.sy, 5, 0xffffff, 0.7);
    // Break: dotted black line from the no-spin spot to the actual pitch,
    // over a faint light band so it reads on the dark scene.
    g.lineStyle(4, 0xffffff, 0.3).lineBetween(ghostEnd.sx, ghostEnd.sy, end.sx, end.sy);
    g.fillStyle(0x000000, 1);
    for (let d = 0; d <= len; d += 4) {
      g.fillCircle(ghostEnd.sx + (dx * d) / len, ghostEnd.sy + (dy * d) / len, 1.1);
    }
    const ux = dx / len;
    const uy = dy / len;
    const lx = ghostEnd.sx + dx / 2 - uy * 22;
    const ly = ghostEnd.sy + dy / 2 + ux * 22;
    g.fillStyle(0x0e1117, 0.88).fillRoundedRect(lx - 18, ly - 8, 36, 16, 8);
    this.label(label++, lx, ly, `${t.breakIn} in`, t.color, 10);
    return label;
  }

  private label(i: number, x: number, y: number, text: string, color: string, size: number) {
    if (!this.labels[i]) {
      this.labels[i] = this.add
        .text(0, 0, "", { fontFamily: FONT, fontSize: `${size}px`, fontStyle: "700" })
        .setOrigin(0.5)
        .setResolution(TEXTURE_RES * (window.devicePixelRatio || 1))
        .setDepth(7);
    }
    this.labels[i].setVisible(true).setPosition(x, y).setText(text).setColor(color);
  }

  // -------------------------------------------------------------------------
  // Ball
  // -------------------------------------------------------------------------

  private drawBall(st: StageState) {
    const g = this.ballG.clear();
    const f = st.frame;
    if (!f) {
      this.glow.setVisible(false);
      return;
    }
    if (f.shadow) {
      g.fillStyle(0x000000, f.shadow.alpha).fillEllipse(f.shadow.sx, f.shadow.sy, f.shadow.rx * 2, f.shadow.rx * 0.7);
    }
    if (f.ghost && f.ball) {
      dashedCircle(g, f.ghost.sx, f.ghost.sy, f.ghost.r, hex(st.flightColor ?? "#ffffff"), f.ghost.opacity, 1.4);
    }
    f.trail.forEach((t, i) => {
      g.fillStyle(0xffffff, 0.2 - i * 0.055).fillCircle(t.sx, t.sy, (f.ball?.r ?? 3) * (0.85 - i * 0.2));
    });
    if (!f.ball) {
      this.glow.setVisible(false);
      return;
    }
    const b = f.ball;
    this.glow
      .setVisible(true)
      .setPosition(b.sx, b.sy)
      .setScale((b.r * 4.2) / 32)
      .setAlpha(0.55 * b.opacity);
    g.fillStyle(0xd6d9df, b.opacity).fillCircle(b.sx, b.sy, b.r);
    g.fillStyle(0xffffff, b.opacity).fillCircle(b.sx - b.r * 0.18, b.sy - b.r * 0.2, b.r * 0.78);
    if (b.r > 6) {
      g.lineStyle(1.2, 0xe05d5d, b.opacity);
      g.beginPath();
      g.arc(b.sx + b.r * 1.15, b.sy, b.r * 1.05, Math.PI * 0.8, Math.PI * 1.2);
      g.strokePath();
      g.beginPath();
      g.arc(b.sx - b.r * 1.15, b.sy, b.r * 1.05, -Math.PI * 0.2, Math.PI * 0.2);
      g.strokePath();
    }
  }

  // -------------------------------------------------------------------------
  // Effects
  // -------------------------------------------------------------------------

  private fireEffects(fx: PitchFx | null, st: StageState) {
    const f = st.frame;
    if (!fx || !f?.arrived || this.firedFor === fx.id) return;
    this.firedFor = fx.id;
    const cam = this.cameras.main;
    const plate = project(fx.actual.x, 0, fx.actual.z);

    switch (fx.call) {
      case "ball":
      case "called_strike":
      case "swinging_strike": {
        const m = mittScreen(f.mitt.x, f.mitt.z, 0);
        this.dust.explode(14, m.sx, m.sy);
        this.rings.push({ x: m.sx, y: m.sy, born: this.time.now, color: 0xffffff });
        if (fx.perceivedVelocity >= 95) cam.shake(130, 0.0028);
        if (fx.actual.z < 0.9) {
          const ground = project(fx.actual.x, 0.6, 0);
          this.dirt.explode(16, ground.sx, ground.sy);
        }
        break;
      }
      case "foul":
        this.sparks.explode(12, plate.sx, plate.sy);
        cam.shake(90, 0.0018);
        break;
      case "in_play": {
        this.sparks.explode(26, plate.sx, plate.sy);
        this.rings.push({ x: plate.sx, y: plate.sy, born: this.time.now, color: 0xfff1c2 });
        this.tweens.add({ targets: cam, zoom: TEXTURE_RES * 1.045, duration: 70, yoyo: true, ease: "Quad.easeOut" });
        if (fx.battedBallType === "ground_ball") {
          const ground = project(0, -0.5, 0);
          this.time.delayedCall(120, () => this.dirt.explode(22, ground.sx, ground.sy));
        }
        break;
      }
      case "hit_by_pitch":
        this.dust.explode(10, f.ball?.sx ?? plate.sx, f.ball?.sy ?? plate.sy);
        cam.shake(160, 0.004);
        break;
    }
  }

  private drawRings(now: number) {
    const g = this.ballG;
    this.rings = this.rings.filter((r) => now - r.born < 320);
    for (const r of this.rings) {
      const k = (now - r.born) / 320;
      g.lineStyle(2 * (1 - k) + 0.5, r.color, 0.7 * (1 - k)).strokeCircle(r.x, r.y, 8 + k * 26);
    }
  }

  private makeDotTexture() {
    const tex = this.textures.createCanvas("dot", 64, 64);
    if (!tex) return;
    const ctx = tex.getContext();
    const grad = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    grad.addColorStop(0, "rgba(255,255,255,1)");
    grad.addColorStop(0.35, "rgba(255,255,255,0.55)");
    grad.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 64, 64);
    tex.refresh();
  }
}

// ---------------------------------------------------------------------------
// Drawing helpers
// ---------------------------------------------------------------------------

function dashedPolyline(
  g: Phaser.GameObjects.Graphics,
  pts: { sx: number; sy: number }[],
  dash: number,
  gap: number,
  color: number,
  alpha: number,
  width: number,
) {
  g.lineStyle(width, color, alpha);
  let on = true;
  let left = dash;
  for (let i = 1; i < pts.length; i++) {
    let ax = pts[i - 1].sx;
    let ay = pts[i - 1].sy;
    const bx = pts[i].sx;
    const by = pts[i].sy;
    let seg = Math.hypot(bx - ax, by - ay);
    while (seg > 0) {
      const step = Math.min(left, seg);
      const nx = ax + ((bx - ax) * step) / seg;
      const ny = ay + ((by - ay) * step) / seg;
      if (on) g.lineBetween(ax, ay, nx, ny);
      seg -= step;
      left -= step;
      ax = nx;
      ay = ny;
      if (left <= 0) {
        on = !on;
        left = on ? dash : gap;
      }
    }
  }
}

function dashedCircle(
  g: Phaser.GameObjects.Graphics,
  x: number,
  y: number,
  r: number,
  color: number,
  alpha: number,
  width = 1,
) {
  g.lineStyle(width, color, alpha);
  const n = Math.max(8, Math.round((2 * Math.PI * r) / 5));
  for (let i = 0; i < n; i += 2) {
    g.beginPath();
    g.arc(x, y, r, (i / n) * Math.PI * 2, ((i + 1) / n) * Math.PI * 2);
    g.strokePath();
  }
}

function dashedRect(
  g: Phaser.GameObjects.Graphics,
  r: { x: number; y: number; w: number; h: number },
  color: number,
  alpha: number,
) {
  const pts = [
    { sx: r.x, sy: r.y },
    { sx: r.x + r.w, sy: r.y },
    { sx: r.x + r.w, sy: r.y + r.h },
    { sx: r.x, sy: r.y + r.h },
    { sx: r.x, sy: r.y },
  ];
  dashedPolyline(g, pts, 4, 5, color, alpha, 1);
}
