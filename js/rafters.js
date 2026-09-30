// The Rafters: a WebGL arena ceiling with UConn's championship banners swaying under the lights.
// Exposes mount(el, {titles, secondary, onPick, onHover}) -> {destroy}
import * as THREE from 'three';

const NAVY = '#0a1c48', NAVY2 = '#061233', WHITE = '#f4f6fb', GOLD = '#e3bd6e', RED = '#e4002b';

function bannerTexture(b, big) {
  const W = 512, H = 1024, c = document.createElement('canvas');
  c.width = W; c.height = H;
  const g = c.getContext('2d');
  // swallowtail silhouette
  g.beginPath(); g.moveTo(0, 0); g.lineTo(W, 0); g.lineTo(W, H); g.lineTo(W / 2, H - 120); g.lineTo(0, H); g.closePath();
  const grd = g.createLinearGradient(0, 0, 0, H);
  grd.addColorStop(0, big ? NAVY : '#0d2152'); grd.addColorStop(1, NAVY2);
  g.fillStyle = grd; g.fill();
  g.save(); g.clip();
  // weave texture
  g.globalAlpha = .06; g.fillStyle = '#fff';
  for (let y = 0; y < H; y += 4) g.fillRect(0, y, W, 1);
  g.globalAlpha = 1;
  // trim
  const trim = b.kind === 'title' ? GOLD : WHITE;
  g.strokeStyle = trim; g.lineWidth = 10;
  g.beginPath(); g.moveTo(22, 40); g.lineTo(22, H - 40); g.lineTo(W / 2, H - 150); g.lineTo(W - 22, H - 40); g.lineTo(W - 22, 40); g.stroke();
  g.fillStyle = RED; g.fillRect(0, 0, W, 34);
  g.restore();
  g.textAlign = 'center'; g.fillStyle = WHITE;
  g.font = '400 64px Graduate, Rockwell, serif';
  g.fillText('UCONN', W / 2, 140);
  g.fillStyle = trim; g.fillRect(W / 2 - 90, 168, 180, 5);
  if (b.kind === 'title') {
    g.fillStyle = WHITE; g.font = '900 250px "Big Shoulders Display", Impact, sans-serif';
    g.fillText(String(b.y), W / 2, 440);
    g.font = '800 58px "Big Shoulders Display", Impact, sans-serif'; g.fillStyle = GOLD;
    g.fillText('NCAA NATIONAL', W / 2, 540); g.fillText('CHAMPIONS', W / 2, 600);
    g.fillStyle = WHITE; g.font = '700 46px "Barlow Condensed", sans-serif';
    if (b.rec) g.fillText(b.rec, W / 2, 690);
    g.font = '600 32px "Barlow Condensed", sans-serif'; g.fillStyle = '#b9c3da';
    if (b.coach) g.fillText(b.coach.toUpperCase(), W / 2, 740);
    if (b.mop) { g.font = '600 26px "Barlow Condensed", sans-serif'; g.fillText(('MOP ' + b.mop).toUpperCase(), W / 2, 784); }
  } else {
    g.fillStyle = WHITE; g.font = '800 64px "Big Shoulders Display", Impact, sans-serif';
    const lines = (b.label || '').toUpperCase().split('\n');
    lines.forEach((l, i) => g.fillText(l, W / 2, 290 + i * 70));
    g.font = '900 170px "Big Shoulders Display", Impact, sans-serif';
    g.fillText(String(b.y), W / 2, 290 + lines.length * 70 + 170);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  return t;
}

function scoreboardTexture() {
  const c = document.createElement('canvas'); c.width = 1024; c.height = 384;
  const g = c.getContext('2d');
  g.fillStyle = '#020306'; g.fillRect(0, 0, c.width, c.height);
  g.fillStyle = '#0d1426'; g.fillRect(0, 0, c.width, 60); g.fillRect(0, c.height - 60, c.width, 60);
  g.font = '900 150px Doto, monospace'; g.textAlign = 'center';
  g.fillStyle = '#ffb347'; g.shadowColor = '#ff8a1e'; g.shadowBlur = 24;
  g.fillText('HUSKIES', 512, 250);
  g.shadowBlur = 0; g.fillStyle = '#e4002b'; g.font = '700 34px "Barlow Condensed", sans-serif';
  g.fillText('★ ★ ★ ★ ★ ★', 512, 42);
  g.fillStyle = '#9fb0d4'; g.fillText('STORRS · HARTFORD', 512, c.height - 18);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

export function mount(host, { titles = [], secondary = [], onPick, onHover } = {}) {
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  } catch (e) { return null; }
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  host.prepend(renderer.domElement);

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x040a18, 0.018);
  const camera = new THREE.PerspectiveCamera(46, 1, 0.1, 400);

  // Dome lattice (Gampel's steel dome, abstracted)
  const dome = new THREE.Group();
  const icos = new THREE.IcosahedronGeometry(70, 4);
  const pos = icos.attributes.position;
  for (let i = 0; i < pos.count; i++) { const y = pos.getY(i); pos.setY(i, Math.max(y, -2) * 0.42); }
  const edges = new THREE.EdgesGeometry(icos, 1);
  const lat = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0x3a5288, transparent: true, opacity: 0.32 }));
  lat.position.y = 22; dome.add(lat);
  // catwalk rings
  for (const [r, y, o] of [[34, 20, .5], [52, 17, .35], [20, 24, .4]]) {
    const ring = new THREE.Mesh(new THREE.TorusGeometry(r, 0.12, 6, 120), new THREE.MeshBasicMaterial({ color: 0x6a82b8, transparent: true, opacity: o }));
    ring.rotation.x = Math.PI / 2; ring.position.y = y; dome.add(ring);
  }
  scene.add(dome);

  // Center-hung scoreboard
  const sbTex = scoreboardTexture();
  const sb = new THREE.Group();
  const sbMatFace = new THREE.MeshBasicMaterial({ map: sbTex });
  const sbMatSide = new THREE.MeshStandardMaterial({ color: 0x0b1220, metalness: .6, roughness: .5 });
  const sbBox = new THREE.Mesh(new THREE.BoxGeometry(12, 4.5, 12), [sbMatFace, sbMatFace, sbMatSide, sbMatSide, sbMatFace, sbMatFace]);
  sb.add(sbBox);
  const ringLed = new THREE.Mesh(new THREE.CylinderGeometry(7.6, 7.6, .7, 48, 1, true), new THREE.MeshBasicMaterial({ color: 0xe4002b, side: THREE.DoubleSide }));
  ringLed.position.y = -3; sb.add(ringLed);
  sb.position.set(0, 25, -42); sb.scale.setScalar(.8); scene.add(sb);

  // Banners
  const all = [...titles.map((b) => ({ ...b, kind: 'title' })), ...secondary.map((b) => ({ ...b, kind: b.kind || 'other' }))];
  const banners = [];
  const SEGX = 14, SEGY = 26;
  const nT = titles.length;
  all.forEach((b, i) => {
    const big = b.kind === 'title';
    const w = big ? 4.6 : 2.8, h = w * 2;
    const geo = new THREE.PlaneGeometry(w, h, SEGX, SEGY);
    geo.translate(0, -h / 2, 0);
    const base = Float32Array.from(geo.attributes.position.array);
    const mat = new THREE.MeshStandardMaterial({ map: bannerTexture(b, big), side: THREE.DoubleSide, roughness: .82, metalness: 0, alphaTest: .5, transparent: false });
    const m = new THREE.Mesh(geo, mat);
    let x, y, z;
    if (big) { const k = i - (nT - 1) / 2; x = k * 5.6; y = 12 + Math.abs(k) * .2; z = -14 - Math.abs(k) * 1.1; }
    else { const j = i - nT, n = all.length - nT, k = j - (n - 1) / 2; x = k * 9 + (k < 0 ? -12 : 12); y = 15.5; z = -24; }
    m.position.set(x, y, z);
    m.rotation.y = -x * 0.012;
    m.userData = { b, base, phase: i * 1.7, amp: big ? 1 : .7, h };
    // pole
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(.06, .06, w + .6, 8), new THREE.MeshStandardMaterial({ color: 0xc9ced8, metalness: .9, roughness: .3 }));
    pole.rotation.z = Math.PI / 2; pole.position.set(x, y + .05, z); scene.add(pole);
    scene.add(m); banners.push(m);
  });

  // Lights
  scene.add(new THREE.HemisphereLight(0x3d5ea8, 0x05070d, 0.55));
  const key = new THREE.SpotLight(0xfff2dc, 900, 90, Math.PI / 5, .55, 1.6);
  key.position.set(0, -18, 8); key.target.position.set(0, 6, -18); scene.add(key, key.target);
  const rim1 = new THREE.SpotLight(0x8fc1ff, 520, 80, Math.PI / 7, .7, 1.6); rim1.position.set(-26, -8, -4); rim1.target.position.set(-6, 8, -18); scene.add(rim1, rim1.target);
  const rim2 = new THREE.SpotLight(0xffd29a, 520, 80, Math.PI / 7, .7, 1.6); rim2.position.set(26, -8, -4); rim2.target.position.set(6, 8, -18); scene.add(rim2, rim2.target);

  // Light beams (additive cones)
  const beamMat = new THREE.MeshBasicMaterial({ color: 0x9cc4ff, transparent: true, opacity: .045, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
  const beams = [];
  for (const [bx, tx, c] of [[-22, -8, 0x9cc4ff], [22, 8, 0xffd29a], [0, 0, 0xfff2dc], [-10, -14, 0x9cc4ff], [10, 14, 0xffd29a]]) {
    const cone = new THREE.Mesh(new THREE.ConeGeometry(4.5, 40, 32, 1, true), beamMat.clone());
    cone.material.color.setHex(c);
    cone.position.set((bx + tx) / 2, -4, -10);
    cone.lookAt(tx, 20, -22); cone.rotateX(Math.PI / 2);
    scene.add(cone); beams.push(cone);
  }

  // Dust in the light
  const N = reduce ? 0 : 900;
  const dGeo = new THREE.BufferGeometry();
  const dp = new Float32Array(N * 3), dv = new Float32Array(N);
  for (let i = 0; i < N; i++) { dp[i * 3] = (Math.random() - .5) * 60; dp[i * 3 + 1] = Math.random() * 30 - 6; dp[i * 3 + 2] = -Math.random() * 34 + 4; dv[i] = .2 + Math.random() * .6; }
  dGeo.setAttribute('position', new THREE.BufferAttribute(dp, 3));
  const dust = new THREE.Points(dGeo, new THREE.PointsMaterial({ color: 0xcfe0ff, size: .07, transparent: true, opacity: .55, depthWrite: false, blending: THREE.AdditiveBlending }));
  scene.add(dust);

  // Interaction
  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2(-9, -9);
  let hovered = null, px = 0, py = 0, tx = 0, ty = 0;
  const onMove = (e) => {
    const r = renderer.domElement.getBoundingClientRect();
    mouse.x = ((e.clientX - r.left) / r.width) * 2 - 1; mouse.y = -((e.clientY - r.top) / r.height) * 2 + 1;
    tx = mouse.x; ty = mouse.y;
    hoverCheck(e);
  };
  const hoverCheck = (e) => {
    ray.setFromCamera(mouse, camera);
    const hit = ray.intersectObjects(banners)[0]?.object || null;
    if (hit !== hovered) { hovered = hit; renderer.domElement.style.cursor = hit ? 'pointer' : ''; }
    onHover?.(hovered?.userData.b || null, e);
  };
  const onLeave = () => { mouse.set(-9, -9); tx = ty = 0; hovered = null; onHover?.(null); };
  const onClick = (e) => { onMove(e); if (hovered) onPick?.(hovered.userData.b); };
  renderer.domElement.addEventListener('pointermove', onMove);
  renderer.domElement.addEventListener('pointerleave', onLeave);
  renderer.domElement.addEventListener('click', onClick);

  const resize = () => {
    // the canvas is shorter than the section on phones (copy flows below it)
    const w = host.clientWidth, h = renderer.domElement.clientHeight || host.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.fov = w < 700 ? 58 : 46;
    camera.updateProjectionMatrix();
  };
  const ro = new ResizeObserver(resize); ro.observe(host); resize();

  let visible = true, raf = 0, last = performance.now(), t = 0;
  const io = new IntersectionObserver(([en]) => { visible = en.isIntersecting; if (visible) kick(); }, { threshold: 0 });
  io.observe(host);
  const onVis = () => { if (!document.hidden) kick(); };
  document.addEventListener('visibilitychange', onVis);

  const intro = { k: reduce ? 1 : 0 };
  function frame(now) {
    raf = 0;
    const dt = Math.min((now - last) / 1000, 0.05); last = now;
    t += dt;
    intro.k = Math.min(1, intro.k + dt * 0.35);
    const ease = 1 - Math.pow(1 - intro.k, 3);
    // camera: rise from the floor into the rafters, then drift with the pointer
    px += (tx - px) * Math.min(1, dt * 2.5); py += (ty - py) * Math.min(1, dt * 2.5);
    const drift = reduce ? 0 : Math.sin(t * .15) * 1.2;
    camera.position.set(px * 3 + drift, -10 + ease * 6 + py * 1.5, 14 - ease * 2);
    camera.lookAt(px * 2, 11.5 + py * 1.5 + (1 - ease) * -6, -18);
    if (!reduce) {
      for (const m of banners) {
        const { base, phase, amp, h } = m.userData;
        const p = m.geometry.attributes.position;
        const hot = m === hovered ? 1.8 : 1;
        for (let i = 0; i < p.count; i++) {
          const bx = base[i * 3], by = base[i * 3 + 1];
          const d = -by / h; // 0 at the pole, 1 at the tail
          p.array[i * 3 + 2] = Math.sin(t * 1.1 + phase + bx * .9 + by * .5) * .22 * d * amp * hot + Math.sin(t * .6 + phase) * .35 * d * d * amp;
        }
        p.needsUpdate = true; m.geometry.computeVertexNormals();
        m.rotation.z = Math.sin(t * .5 + phase) * .015;
      }
      const a = dust.geometry.attributes.position;
      for (let i = 0; i < N; i++) { a.array[i * 3 + 1] += dv[i] * dt * .4; if (a.array[i * 3 + 1] > 26) a.array[i * 3 + 1] = -6; a.array[i * 3] += Math.sin(t + i) * dt * .05; }
      a.needsUpdate = true;
      sb.rotation.y = t * .08;
      beams.forEach((b, i) => { b.material.opacity = .04 + Math.sin(t * .7 + i) * .012; });
    }
    renderer.render(scene, camera);
    if (visible && !document.hidden && (!reduce || intro.k < 1)) kick();
  }
  function kick() { if (!raf) { last = performance.now(); raf = requestAnimationFrame(frame); } }
  // Fonts must be ready before we paint the canvases
  document.fonts?.ready.then(() => {
    banners.forEach((m) => { m.material.map.dispose(); m.material.map = bannerTexture(m.userData.b, m.userData.b.kind === 'title'); m.material.needsUpdate = true; });
    sbMatFace.map.dispose(); sbMatFace.map = scoreboardTexture(); sbMatFace.needsUpdate = true;
    kick();
  });
  kick();

  return {
    destroy() {
      cancelAnimationFrame(raf); raf = 0; visible = false;
      ro.disconnect(); io.disconnect();
      document.removeEventListener('visibilitychange', onVis);
      scene.traverse((o) => { o.geometry?.dispose(); const ms = Array.isArray(o.material) ? o.material : o.material ? [o.material] : []; ms.forEach((mm) => { mm.map?.dispose(); mm.dispose(); }); });
      renderer.dispose(); renderer.domElement.remove();
    },
  };
}
