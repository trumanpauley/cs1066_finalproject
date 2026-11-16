/**
 * Hosts the Phaser game inside React. React keeps all state; the scene reads
 * the latest props every frame through a ref, so nothing has to be pushed.
 */

import Phaser from "phaser";
import { useEffect, useRef } from "react";
import type { StageState } from "../ui/sceneTypes";
import { VIEW_H, VIEW_W } from "../ui/projection";
import { TEXTURE_RES } from "../ui/textures";
import { PitchScene } from "./PitchScene";

export function PhaserStage(props: StageState) {
  const host = useRef<HTMLDivElement>(null);
  const latest = useRef(props);
  latest.current = props;

  useEffect(() => {
    if (!host.current) return;
    const game = new Phaser.Game({
      type: Phaser.AUTO,
      parent: host.current,
      width: VIEW_W * TEXTURE_RES,
      height: VIEW_H * TEXTURE_RES,
      backgroundColor: "#070a10",
      banner: false,
      audio: { noAudio: true },
      render: { antialias: true },
      scale: { mode: Phaser.Scale.WIDTH_CONTROLS_HEIGHT, autoCenter: Phaser.Scale.CENTER_HORIZONTALLY },
      scene: new PitchScene(() => latest.current),
    });
    return () => game.destroy(true);
  }, []);

  return (
    <div
      ref={host}
      className="scene phaser-stage"
      role="img"
      aria-label={`Pitcher's view of ${props.hitter.name} at the plate`}
    />
  );
}
