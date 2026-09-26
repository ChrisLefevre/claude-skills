#!/usr/bin/env python3
"""Page d'aperçu interactive : morph.html + lecture, défilement par temps, ralenti, sons d'UI.

    node tools/render.cjs sfx [--bpm 120] --out build/sfx.json
    python3 tools/preview.py [--sfx build/sfx.json] [--out build/preview.html]

La page reprend morph.html sans le modifier et pilote son horloge (window.MORPH_CONTROLLED).
Elle est écrite sans <html>, <head> ni <body> : c'est le format d'une page publiée en Artifact.
"""

import argparse
import base64
import json
import pathlib
import re
import subprocess
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import audio  # noqa: E402

LABELS = [
    "Bouton, survol", "Clic", "Chargeur", "L’arc accélère", "Coche", "Île dynamique", "Clic, lecteur",
    "Contenu du lecteur", "Play → pause", "Saisie de la tête", "Glissement", "Relâche",
    "Volume", "Saisie", "Au-delà du max", "Relâche, ressort", "Interrupteur OFF", "Clic, ON",
    "Onglets", "Onglet 2", "Onglet 3", "Graphique", "La courbe se dessine", "Survol, infobulle",
    "⌘K", "Frappe « pub »", "Entrée, toast", "Retour au bouton",
]

CSS = """
:root {
  --pv-bg: #F6F6F5; --pv-ink: #0A0A0B; --pv-mute: #6E6B66; --pv-line: #E1DFDA;
  --pv-rail: #D9D6D0; --pv-chip: #ECEAE6; --pv-focus: #0A0A0B;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --pv-bg: #0C0C0D; --pv-ink: #EDECEA; --pv-mute: #8F8B85; --pv-line: #262524;
    --pv-rail: #34322F; --pv-chip: #1C1B1A; --pv-focus: #EDECEA; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --pv-bg: #0C0C0D; --pv-ink: #EDECEA; --pv-mute: #8F8B85; --pv-line: #262524;
  --pv-rail: #34322F; --pv-chip: #1C1B1A; --pv-focus: #EDECEA; color-scheme: dark;
}
html, body { background: var(--pv-bg); }
body { color: var(--pv-ink); font-family: Geist, system-ui, sans-serif; padding-inline: 16px; padding-block: 20px 28px; }
.pv { width: min(100%, calc(100dvh - 190px), 860px); min-width: min(100%, 320px); margin-inline: auto; display: grid; gap: 14px; }
.fit { position: relative; width: 100%; aspect-ratio: 1; max-width: 100%; overflow: hidden; border-radius: 18px;
       box-shadow: 0 0 0 1px var(--pv-line); }
.fit #stage { position: absolute; left: 0; top: 0; transform-origin: 0 0; }
.row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.btn { appearance: none; border: 0; background: var(--pv-chip); color: var(--pv-ink); font: inherit; font-size: 14px;
       font-weight: 520; height: 36px; padding-inline: 12px; border-radius: 10px; display: inline-flex; align-items: center;
       gap: 8px; cursor: pointer; }
.btn[aria-pressed="true"] { background: var(--pv-ink); color: var(--pv-bg); }
.btn:focus-visible, .scrub input:focus-visible + .rail { outline: 2px solid var(--pv-focus); outline-offset: 2px; }
.btn svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
#play { width: 44px; height: 44px; padding: 0; justify-content: center; border-radius: 22px; background: var(--pv-ink); color: var(--pv-bg); }
#play svg { width: 20px; height: 20px; fill: currentColor; stroke: none; }
.scrub { position: relative; flex: 1 1 240px; height: 44px; }
.scrub input { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0; margin: 0; cursor: pointer; z-index: 2; }
.rail { position: absolute; left: 0; right: 0; top: 17px; height: 6px; border-radius: 3px; background: var(--pv-rail); }
.fillbar { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 3px; background: var(--pv-ink); }
.ticks { position: absolute; left: 0; right: 0; top: 27px; height: 12px; }
.ticks i { position: absolute; top: 0; width: 1px; height: 5px; background: var(--pv-mute); opacity: .55; }
.ticks i.bar { height: 9px; opacity: 1; }
.ticks b { position: absolute; top: -26px; font-size: 11px; font-weight: 520; color: var(--pv-mute); transform: translateX(3px); }
.time { font-size: 14px; font-variant-numeric: tabular-nums; color: var(--pv-mute); min-width: 92px; text-align: right; }
.now { flex: 1 1 220px; font-size: 15px; display: flex; gap: 10px; align-items: baseline; min-width: 0; }
.now span { color: var(--pv-mute); font-variant-numeric: tabular-nums; font-size: 13px; letter-spacing: .02em; }
.now strong { font-weight: 560; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.seg { display: inline-flex; gap: 4px; }
.hint { font-size: 12px; color: var(--pv-mute); }
@media (max-width: 520px) { .time { min-width: 0; } .hint { display: none; } }
"""

CONTROLS = """
  <div class="row">
    <button id="play" class="btn" aria-label="Pause"><svg viewBox="0 0 24 24"><path id="playIco" d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z"/></svg></button>
    <div class="scrub">
      <input id="scrub" type="range" min="0" step="0.001" value="0" aria-label="Position dans la boucle">
      <div class="rail"><div class="fillbar" id="fillbar"></div></div>
      <div class="ticks" id="ticks"></div>
    </div>
    <div class="time" id="time">0,00 s</div>
  </div>
  <div class="row">
    <div class="now"><span id="where">Mesure 1 · temps 1</span><strong id="label">Bouton, survol</strong></div>
    <div class="seg" role="group" aria-label="Vitesse">
      <button class="btn spd" data-s="1" aria-pressed="true">1×</button>
      <button class="btn spd" data-s="0.5" aria-pressed="false">0,5×</button>
      <button class="btn spd" data-s="0.25" aria-pressed="false">0,25×</button>
    </div>
    <button id="sound" class="btn" aria-pressed="false"><svg viewBox="0 0 24 24"><path d="M11 5 6.5 9H3.5v6h3l4.5 4z"/><path d="M15.5 9a4.5 4.5 0 0 1 0 6"/><path d="M18.5 6a8.5 8.5 0 0 1 0 12"/></svg>Sons d’UI</button>
  </div>
  <div class="hint">Espace : lecture ou pause. Flèches : temps précédent ou suivant. Musique à venir, seuls les sons d’interface jouent.</div>
"""

SCRIPT = r"""
(() => {
  const { L, B, NB } = window.META;
  const LABELS = __LABELS__;
  const $ = id => document.getElementById(id);
  const stage = $('stage'), fit = document.querySelector('.fit');
  const resize = () => { stage.style.transform = `scale(${fit.clientWidth / 1440})`; };
  new ResizeObserver(resize).observe(fit); resize();

  const scrub = $('scrub'); scrub.max = L;
  $('ticks').innerHTML = Array.from({ length: NB + 1 }, (_, b) => {
    const x = (b / NB * 100).toFixed(3);
    return b % 4 === 0
      ? `<i class="bar" style="left:${x}%"></i>${b < NB ? `<b style="left:${x}%">${b / 4 + 1}</b>` : ''}`
      : `<i style="left:${x}%"></i>`;
  }).join('');

  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let playing = !reduce, speed = 1, soundOn = false, dragging = false;
  let t0 = reduce ? 3.6 : 0, p0 = performance.now();
  let ctx = null, buf = null, src = null, c0 = 0, o0 = 0;
  const wrap = t => ((t % L) + L) % L;

  function now() {
    if (!playing) return t0;
    if (src) return o0 + (ctx.currentTime - c0);            // l'audio mène l'horloge
    return t0 + (performance.now() - p0) / 1000 * speed;
  }
  function rebase() { t0 = wrap(now()); p0 = performance.now(); }
  function stopAudio() { if (src) { try { src.stop(); } catch (_) {} src.disconnect(); src = null; } }
  function startAudio() {
    stopAudio();
    if (!soundOn || !playing || speed !== 1 || !buf || dragging) return;
    src = ctx.createBufferSource(); src.buffer = buf; src.loop = true; src.connect(ctx.destination);
    o0 = t0; c0 = ctx.currentTime; src.start(0, wrap(o0));
  }
  function change(fn) { rebase(); stopAudio(); fn(); p0 = performance.now(); startAudio(); ui(); }

  const fmt = t => t.toFixed(2).replace('.', ',') + ' s';
  function ui() {
    $('play').setAttribute('aria-label', playing ? 'Pause' : 'Lecture');
    $('playIco').setAttribute('d', playing ? 'M7 5h3.5v14H7zM13.5 5H17v14h-3.5z' : 'M8 5.5v13l10.5-6.5z');
    document.querySelectorAll('.spd').forEach(b => b.setAttribute('aria-pressed', String(+b.dataset.s === speed)));
    $('sound').setAttribute('aria-pressed', String(soundOn));
  }

  function frame() {
    const t = wrap(now());
    window.seek(t);
    if (!dragging) scrub.value = t;
    $('fillbar').style.width = (t / L * 100).toFixed(3) + '%';
    $('time').textContent = fmt(t);
    const b = Math.floor(t / B + 1e-6) % NB;
    $('where').textContent = `Mesure ${Math.floor(b / 4) + 1} · temps ${b % 4 + 1}`;
    $('label').textContent = LABELS[b];
    requestAnimationFrame(frame);
  }

  $('play').onclick = () => change(() => { playing = !playing; });
  document.querySelectorAll('.spd').forEach(btn => btn.onclick = () => change(() => { speed = +btn.dataset.s; }));
  scrub.addEventListener('input', () => { dragging = true; stopAudio(); t0 = +scrub.value; p0 = performance.now(); });
  scrub.addEventListener('change', () => { dragging = false; t0 = +scrub.value; p0 = performance.now(); startAudio(); });
  addEventListener('keydown', e => {
    if (e.target.closest('button') && (e.key === ' ' || e.key === 'Enter')) return;
    if (e.key === ' ') { e.preventDefault(); $('play').click(); }
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      e.preventDefault();
      change(() => {
        playing = false;
        const b = Math.round(t0 / B) + (e.key === 'ArrowRight' ? 1 : -1);
        t0 = wrap(b * B);
      });
    }
  });

  $('sound').onclick = async () => {
    if (!ctx) {
      try {
        ctx = new (window.AudioContext || window.webkitAudioContext)();
        const bin = atob(window.MORPH_SFX);
        const bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        buf = await ctx.decodeAudioData(bytes.buffer);
      } catch (_) { $('sound').disabled = true; return; }
    }
    await ctx.resume();
    change(() => { soundOn = !soundOn; if (soundOn) speed = 1; });
  };

  ui();
  requestAnimationFrame(frame);
})();
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sfx", default=str(ROOT / "build/sfx.json"))
    ap.add_argument("--out", default=str(ROOT / "build/preview.html"))
    a = ap.parse_args()

    src = (ROOT / "morph.html").read_text()
    css = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
    css = css.replace("html, body { background: var(--canvas); overflow: hidden; }", "")
    stage = re.search(r"<body>\s*(<div id=\"stage\">.*?)\n<script>", src, re.S).group(1)
    script = re.search(r"<script>(.*?)</script>", src, re.S).group(1)
    font = re.search(r"(<style>@font-face.*?</style>)", src, re.S).group(1)

    # sons d'UI seuls, sur la boucle exacte
    sfx = json.loads(pathlib.Path(a.sfx).read_text())
    L = sfx["meta"]["L"]
    n = int(round(L * audio.SR))
    ui, _ = audio.ui_layer(sfx["events"], n)
    ui = ui / (np.abs(ui).max() + 1e-9) * 0.8
    pcm = (ui * 32767).astype("<i2").tobytes()
    wav = subprocess.run(["ffmpeg", "-v", "error", "-f", "s16le", "-ar", str(audio.SR), "-ac", "2", "-i", "-",
                          "-ar", "32000", "-f", "wav", "-"], input=pcm, capture_output=True, check=True).stdout

    page = "\n".join([
        "<title>Morph UI</title>",
        font,
        f"<style>{css}{CSS}</style>",
        f'<main class="pv">\n  <div class="fit">{stage}</div>{CONTROLS}</main>',
        f"<script>window.MORPH_CONTROLLED = true; window.MORPH_BPM = {sfx['meta']['BPM']};</script>",
        f"<script>{script}</script>",
        f"<script>window.MORPH_SFX = '{base64.b64encode(wav).decode()}';</script>",
        "<script>" + SCRIPT.replace("__LABELS__", json.dumps(LABELS, ensure_ascii=False)) + "</script>",
    ])
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"{out} ({len(page) / 1e6:.2f} Mo)")


if __name__ == "__main__":
    main()
