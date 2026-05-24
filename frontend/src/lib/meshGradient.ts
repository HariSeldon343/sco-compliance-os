// SCO Compliance OS — MeshGradient WebGL background animato (clean-room)
//
// Shader GLSL custom scritto from scratch (NON copy da OpenHuman/Stripe):
// - Vertex shader trivial (fullscreen quad)
// - Fragment shader: 4 blob radiali animati con sin/cos su uv coords + time,
//   color blend gaussiano-pesato per ottenere effetto "mesh" fluido
// - WebGL2 con fallback graceful: se contesto WebGL2 non disponibile, return
//   handle null e il chiamante (AppBackground.tsx) usa fallback CSS
//
// Pattern: function factory (no class) per init + cleanup espliciti.
// L'animazione gira in requestAnimationFrame loop con cleanup garantito.

export interface MeshGradientOptions {
  /** 4 colori in formato [r, g, b] normalizzato (0-1) per blending shader */
  colors: [
    [number, number, number],
    [number, number, number],
    [number, number, number],
    [number, number, number],
  ];
  /** Velocità animazione (default 0.0006). 0 = statico */
  speed?: number;
  /** Intensità mesh (default 0.85). 0 = colore unico, 1 = blob max separati */
  intensity?: number;
}

export interface MeshGradientHandle {
  /** Stop RAF + release WebGL context */
  destroy: () => void;
  /** Aggiorna colori dinamicamente (es. al theme switch) */
  updateColors: (colors: MeshGradientOptions["colors"]) => void;
}

// ============================================================================
// SHADERS — GLSL clean-room
// ============================================================================

const VERTEX_SHADER = `#version 300 es
in vec2 a_position;
out vec2 v_uv;
void main() {
  v_uv = a_position * 0.5 + 0.5;
  gl_Position = vec4(a_position, 0.0, 1.0);
}
`;

const FRAGMENT_SHADER = `#version 300 es
precision highp float;

in vec2 v_uv;
out vec4 fragColor;

uniform vec3 u_color0;
uniform vec3 u_color1;
uniform vec3 u_color2;
uniform vec3 u_color3;
uniform float u_time;
uniform float u_intensity;
uniform vec2 u_resolution;

// Gaussian falloff distance-based per blob soft
float blob(vec2 uv, vec2 center, float radius) {
  vec2 d = uv - center;
  float dist = length(d);
  return exp(-dist * dist / (radius * radius));
}

void main() {
  vec2 uv = v_uv;
  // Adjust for aspect ratio per evitare blob ovali
  float aspect = u_resolution.x / u_resolution.y;
  uv.x *= aspect;

  float t = u_time;

  // 4 blob in moto lento, traiettorie indipendenti (Lissajous-like)
  vec2 c0 = vec2(0.25 + 0.20 * sin(t * 0.7) * aspect, 0.30 + 0.15 * cos(t * 0.5));
  vec2 c1 = vec2(0.75 * aspect + 0.18 * cos(t * 0.6), 0.25 + 0.20 * sin(t * 0.9));
  vec2 c2 = vec2(0.20 + 0.22 * cos(t * 0.8) * aspect, 0.75 + 0.18 * sin(t * 0.4));
  vec2 c3 = vec2(0.80 * aspect + 0.15 * sin(t * 0.5), 0.78 + 0.22 * cos(t * 0.7));

  // Radius soft (mesh feel)
  float radius = 0.55 * u_intensity;

  // Weight gaussian per ogni colore
  float w0 = blob(uv, c0, radius);
  float w1 = blob(uv, c1, radius);
  float w2 = blob(uv, c2, radius);
  float w3 = blob(uv, c3, radius);

  float total = w0 + w1 + w2 + w3 + 0.0001;

  // Color blend pesato
  vec3 color = (u_color0 * w0 + u_color1 * w1 + u_color2 * w2 + u_color3 * w3) / total;

  // Output con alpha 1 (l'opacity finale è gestita da CSS sul canvas wrapper)
  fragColor = vec4(color, 1.0);
}
`;

// ============================================================================
// HELPERS — compile shader + link program (boilerplate WebGL)
// ============================================================================

function compileShader(
  gl: WebGL2RenderingContext,
  type: number,
  source: string,
): WebGLShader | null {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    // Disabilitato console.error in produzione; il fallback CSS prende il sopravvento
    gl.deleteShader(shader);
    return null;
  }
  return shader;
}

function createProgram(gl: WebGL2RenderingContext): WebGLProgram | null {
  const vs = compileShader(gl, gl.VERTEX_SHADER, VERTEX_SHADER);
  const fs = compileShader(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER);
  if (!vs || !fs) return null;

  const program = gl.createProgram();
  if (!program) return null;

  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);

  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    gl.deleteProgram(program);
    return null;
  }

  // Shader objects possono essere eliminati una volta linkato il programma
  gl.deleteShader(vs);
  gl.deleteShader(fs);

  return program;
}

// ============================================================================
// MAIN — init MeshGradient + RAF loop + cleanup
// ============================================================================

/**
 * Inizializza un MeshGradient WebGL su un canvas HTMLElement.
 * Ritorna null se WebGL2 non è disponibile (caller deve usare fallback CSS).
 */
export function initMeshGradient(
  canvas: HTMLCanvasElement,
  options: MeshGradientOptions,
): MeshGradientHandle | null {
  // Try WebGL2 (con fallback graceful se non disponibile)
  const gl = canvas.getContext("webgl2", {
    alpha: true,
    premultipliedAlpha: false,
    antialias: false,
    powerPreference: "low-power",
  }) as WebGL2RenderingContext | null;

  if (!gl) {
    return null;
  }

  const program = createProgram(gl);
  if (!program) {
    return null;
  }

  // Fullscreen quad (2 triangoli)
  const positions = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]);
  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);

  const positionLoc = gl.getAttribLocation(program, "a_position");
  gl.enableVertexAttribArray(positionLoc);
  gl.vertexAttribPointer(positionLoc, 2, gl.FLOAT, false, 0, 0);

  // Uniform locations (cache per perf)
  const u_color0 = gl.getUniformLocation(program, "u_color0");
  const u_color1 = gl.getUniformLocation(program, "u_color1");
  const u_color2 = gl.getUniformLocation(program, "u_color2");
  const u_color3 = gl.getUniformLocation(program, "u_color3");
  const u_time = gl.getUniformLocation(program, "u_time");
  const u_intensity = gl.getUniformLocation(program, "u_intensity");
  const u_resolution = gl.getUniformLocation(program, "u_resolution");

  // State mutable runtime
  let currentColors = options.colors;
  const speed = options.speed ?? 0.0006;
  const intensity = options.intensity ?? 0.85;

  // Resize handler (DPR-aware ma capped a 1.5x per perf)
  const resize = () => {
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    const rect = canvas.getBoundingClientRect();
    const w = Math.max(1, Math.floor(rect.width * dpr));
    const h = Math.max(1, Math.floor(rect.height * dpr));
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
      gl.viewport(0, 0, w, h);
    }
  };

  window.addEventListener("resize", resize);
  resize();

  // RAF loop
  let rafId = 0;
  let startTime = performance.now();

  const render = (now: number) => {
    const elapsed = (now - startTime) * speed;
    resize();

    gl.useProgram(program);
    gl.uniform3fv(u_color0, currentColors[0]);
    gl.uniform3fv(u_color1, currentColors[1]);
    gl.uniform3fv(u_color2, currentColors[2]);
    gl.uniform3fv(u_color3, currentColors[3]);
    gl.uniform1f(u_time, elapsed);
    gl.uniform1f(u_intensity, intensity);
    gl.uniform2f(u_resolution, canvas.width, canvas.height);

    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

    rafId = requestAnimationFrame(render);
  };

  rafId = requestAnimationFrame(render);

  return {
    destroy: () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener("resize", resize);
      try {
        gl.deleteBuffer(buffer);
        gl.deleteProgram(program);
      } catch {
        // Context già perso (es. tab background, hibernation) — non bloccante
      }
    },
    updateColors: (colors) => {
      currentColors = colors;
      // start anim da zero per smooth transition (anti-jitter sui cambi colore)
      startTime = performance.now();
    },
  };
}

// ============================================================================
// DEFAULT COLORS — brand SCO (navy + blue + amber + lavender)
// ============================================================================

/** Brand SCO palette normalizzata 0-1 per shader uniform vec3 */
export const SCO_DEFAULT_COLORS: MeshGradientOptions["colors"] = [
  [48 / 255, 46 / 255, 92 / 255],     // #302e5c navy SCO primary
  [0 / 255, 116 / 255, 180 / 255],    // #0074b4 blue SCO secondary
  [255 / 255, 167 / 255, 39 / 255],   // #ffa727 amber SCO accent
  [155 / 255, 138 / 255, 251 / 255],  // #9b8afb lavender accent palette
];

/** Variante dark mode (toni desaturati per non disturbare) */
export const SCO_DARK_COLORS: MeshGradientOptions["colors"] = [
  [26 / 255, 24 / 255, 50 / 255],     // primary-800 (deep navy)
  [0 / 255, 80 / 255, 124 / 255],     // secondary-700 (deep blue)
  [184 / 255, 111 / 255, 16 / 255],   // amber-700 (deep amber)
  [85 / 255, 80 / 255, 153 / 255],    // primary-400 (lavender-navy)
];
