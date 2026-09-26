#!/usr/bin/env node
// Rendu de morph.html avec Playwright.
//
//   node tools/render.cjs beats  [--bpm 120] [--offset 0.4] [--out build/beats]
//   node tools/render.cjs still  --t 3.2 [--out build/still.png]
//   node tools/render.cjs sfx    [--bpm 120] [--out build/sfx.json]
//   node tools/render.cjs video  [--bpm 120] [--fps 60] [--sub 4] [--workers 4] [--out build/video.mp4]
//
// La vidéo : `sub` sous-images par image, réparties sur tout l'intervalle de l'image et
// centrées sur son instant, puis mélangées par ffmpeg tmix. La boucle fait exactement
// NB temps : l'image N vaudrait l'image 0, elle n'est donc pas rendue.

const fs = require('fs');
const path = require('path');
const { spawn, execSync } = require('child_process');

function loadPlaywright() {
  try { return require('playwright'); } catch (_) {
    const root = execSync('npm root -g').toString().trim();
    return require(path.join(root, 'playwright'));
  }
}
const { chromium } = loadPlaywright();

const ROOT = path.resolve(__dirname, '..');
const args = process.argv.slice(2);
const mode = args[0];
const opt = (name, dflt) => { const i = args.indexOf('--' + name); return i >= 0 ? args[i + 1] : dflt; };
const BPM = +opt('bpm', 120);
const SIZE = 1440;

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: SIZE, height: SIZE }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('Erreur dans la page :', e.message); process.exit(1); });
  const url = 'file://' + path.join(ROOT, 'morph.html') + `?render=1&bpm=${BPM}`;
  await page.goto(url);
  await page.evaluate(async () => { await document.fonts.load('520 36px Geist'); await document.fonts.ready; });
  return page;
}
const shot = async (page, t) => {
  await page.evaluate(t => window.seek(t), t);
  return page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: SIZE, height: SIZE } });
};

const LABELS = [
  'Bouton, survol', 'Clic', 'Chargeur', 'L’arc accélère', 'Coche', 'Île dynamique', 'Clic, lecteur',
  'Contenu du lecteur', 'Play → pause', 'Saisie de la tête', 'Glissement', 'Relâche',
  'Volume', 'Saisie', 'Au-delà du max', 'Relâche, ressort', 'Interrupteur OFF', 'Clic, ON',
  'Onglets', 'Onglet 2', 'Onglet 3', 'Graphique', 'La courbe se dessine', 'Survol, infobulle',
  '⌘K', 'Frappe « pub »', 'Entrée, toast', 'Retour au bouton',
];

async function beats() {
  const out = path.resolve(opt('out', path.join(ROOT, 'build/beats')));
  const offset = +opt('offset', 0.4);
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await openPage(browser);
  const meta = await page.evaluate(() => window.META);
  const files = [];
  for (let b = 0; b < meta.NB; b++) {
    const t = (b + offset) * meta.B;
    const f = path.join(out, `beat_${String(b).padStart(2, '0')}.png`);
    fs.writeFileSync(f, await shot(page, t));
    files.push({ f, b, t });
  }
  // planche contact : 7 colonnes × 4 lignes, une ligne par paire de mesures
  const cells = files.map(({ f, b, t }) => `<figure><img src="file://${f}"><figcaption><b>${b + 1}</b>
    <span>${LABELS[b] || ''}</span><i>${(b * meta.B).toFixed(2)} s</i></figcaption></figure>`).join('');
  const html = `<!doctype html><meta charset="utf-8"><style>
    body{margin:0;background:#111;font:500 15px system-ui;color:#ddd}
    main{display:grid;grid-template-columns:repeat(7,300px);gap:10px;padding:12px}
    figure{margin:0} img{width:300px;height:300px;display:block;border-radius:4px}
    figcaption{display:flex;gap:8px;padding:6px 2px} b{color:#fff} i{margin-left:auto;color:#888;font-style:normal}
  </style><main>${cells}</main>`;
  const sheet = path.join(out, 'sheet.html');
  fs.writeFileSync(sheet, html);
  const sp = await browser.newPage({ viewport: { width: 7 * 310 + 14, height: 4 * 345 + 20 } });
  await sp.goto('file://' + sheet);
  await sp.waitForLoadState('load');
  await sp.screenshot({ path: path.join(out, 'sheet.png'), fullPage: true });
  await browser.close();
  console.log(`${files.length} images, planche : ${path.join(out, 'sheet.png')}`);
}

async function still() {
  const out = path.resolve(opt('out', path.join(ROOT, 'build/still.png')));
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const browser = await chromium.launch();
  const page = await openPage(browser);
  const ts = String(opt('t', '0')).split(',').map(Number);
  for (const [i, t] of ts.entries()) {
    const f = ts.length > 1 ? out.replace(/\.png$/, `_${i}.png`) : out;
    fs.writeFileSync(f, await shot(page, t));
    console.log(f);
  }
  await browser.close();
}

async function sfx() {
  const out = path.resolve(opt('out', path.join(ROOT, 'build/sfx.json')));
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const browser = await chromium.launch();
  const page = await openPage(browser);
  // panoramique léger d'après la position du curseur à l'écran
  const data = await page.evaluate(() => ({
    meta: window.META,
    events: window.SFX.map(e => {
      window.seek(e.t);
      const x = +(/translate\((-?[\d.]+)px/.exec(document.getElementById('cursor').style.transform) || [0, 720])[1];
      return { ...e, pan: +((x - 720) / 720).toFixed(3) };
    }),
  }));
  fs.writeFileSync(out, JSON.stringify(data, null, 2));
  await browser.close();
  console.log(out);
}

function ffmpeg(argv) {
  const p = spawn('ffmpeg', argv, { stdio: ['pipe', 'ignore', 'pipe'] });
  let err = '';
  p.stderr.on('data', d => { err += d; if (err.length > 20000) err = err.slice(-10000); });
  const done = new Promise((res, rej) => p.on('close', c => c === 0 ? res() : rej(new Error(err))));
  return { p, done };
}
const write = (stream, buf) => new Promise(res => stream.write(buf) ? res() : stream.once('drain', res));

async function video() {
  const out = path.resolve(opt('out', path.join(ROOT, 'build/video.mp4')));
  const fps = +opt('fps', 60), sub = +opt('sub', 4), workers = +opt('workers', 4);
  const tmp = path.join(path.dirname(out), 'segments');
  fs.mkdirSync(tmp, { recursive: true });

  const browser = await chromium.launch();
  const probe = await openPage(browser);
  const meta = await probe.evaluate(() => window.META);
  await probe.close();
  const N = Math.round(meta.L * fps);         // images dans la boucle
  const dt = meta.L / N;                       // pas réel, la boucle tombe juste
  const per = Math.ceil(N / workers);
  const t0 = Date.now();
  let doneFrames = 0;

  const segs = [];
  await Promise.all(Array.from({ length: workers }, async (_, w) => {
    const a = w * per, b = Math.min(N, a + per);
    if (a >= b) return;
    const seg = path.join(tmp, `seg_${w}.mkv`);
    segs[w] = seg;
    const page = await openPage(browser);
    const ff = ffmpeg(['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps * sub), '-i', '-',
      '-vf', `format=gbrp,tmix=frames=${sub},select='eq(mod(n\\,${sub})\\,${sub - 1})',setpts=N/(${fps}*TB)`,
      '-r', String(fps), '-c:v', 'ffv1', '-pix_fmt', 'gbrp', seg]);
    for (let k = a; k < b; k++) {
      for (let i = 0; i < sub; i++) {
        const t = (k + (i + .5) / sub - .5) * dt;   // obturateur 360°, centré sur l'image
        await write(ff.p.stdin, await shot(page, t));
      }
      if (++doneFrames % 60 === 0) {
        const el = (Date.now() - t0) / 1000;
        process.stdout.write(`\r${doneFrames}/${N} images, ${el.toFixed(0)} s`);
      }
    }
    ff.p.stdin.end();
    await ff.done;
    await page.close();
  }));
  await browser.close();
  process.stdout.write('\n');

  const list = path.join(tmp, 'list.txt');
  fs.writeFileSync(list, segs.filter(Boolean).map(s => `file '${s}'`).join('\n'));
  const audio = opt('audio');
  const argv = ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list];
  if (audio) argv.push('-i', path.resolve(audio));
  argv.push('-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p',
    '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-r', String(fps));
  if (audio) argv.push('-c:a', 'aac', '-b:a', '256k', '-shortest');
  argv.push('-movflags', '+faststart', out);
  await ffmpeg(argv).done;
  console.log(`${N} images (${(N / meta.L).toFixed(3)} i/s, boucle ${meta.L.toFixed(3)} s) → ${out}`);
}

const MODES = { beats, still, sfx, video };
if (!MODES[mode]) { console.error('mode : beats | still | sfx | video'); process.exit(1); }
MODES[mode]().catch(e => { console.error(e); process.exit(1); });
