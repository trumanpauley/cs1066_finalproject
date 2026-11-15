// Copy the single-file build next to the Streamlit app so Python users
// can run the simulator without installing Node.
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../dist/index.html");
const dest = resolve(here, "../../pitchiq/static/simulator.html");
mkdirSync(dirname(dest), { recursive: true });
copyFileSync(src, dest);
console.log(`Copied build -> ${dest}`);
