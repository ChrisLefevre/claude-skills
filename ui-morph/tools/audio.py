#!/usr/bin/env python3
"""Analyse de la chanson et mixage des sons d'UI, avec numpy.

    python3 tools/audio.py analyze piste.mp3 [--out build/beats.json]
    python3 tools/audio.py mix piste.mp3 --beats build/beats.json --sfx build/sfx.json [--out build/mix.wav]

analyze : grille des temps (tempo constant ajusté sur toute la piste), phase des
mesures, et point de départ de la boucle sur un temps fort.
mix : extrait la boucle (NB temps) à partir de ce point, synthétise chaque son d'UI,
mesure son pic et le place pour que ce pic tombe sur l'événement. La boucle est
circulaire : un son qui déborde de la fin reprend au début.
"""

import argparse
import json
import pathlib
import subprocess
import sys

import numpy as np

SR = 44100
HOP = 256
NFFT = 2048


def decode(path, channels=2):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", str(channels), "-ar", str(SR), "-f", "f32le", "-"],
        check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, channels).copy()


# ---------------------------------------------------------------------------
# Analyse

def lowpass(x, fc):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / fc) ** 8)
    return np.fft.irfft(X, len(x))


def novelty(mono):
    """Flux spectral (log), bande large et bande basse, une valeur par pas de HOP."""
    win = np.hanning(NFFT).astype(np.float32)
    n = 1 + (len(mono) - NFFT) // HOP
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n)[:, None]
    spec = np.abs(np.fft.rfft(mono[idx] * win, axis=1))
    logs = np.log1p(100 * spec)
    flux = np.maximum(0, np.diff(logs, axis=0, prepend=logs[:1]))
    freqs = np.fft.rfftfreq(NFFT, 1 / SR)
    full = flux.sum(1)
    low = flux[:, freqs < 150].sum(1)
    rms = np.sqrt((mono[idx] ** 2).mean(1))

    def clean(x):
        k = int(0.5 * SR / HOP)
        x = x - np.convolve(x, np.ones(k) / k, mode="same")
        x = np.maximum(0, x)
        return x / (x.max() + 1e-9)

    return clean(full), clean(low), rms


def comb(nov, period, phase):
    """Somme de la nouveauté échantillonnée sur une grille (interpolation linéaire)."""
    pos = np.arange(phase, len(nov) - 1, period)
    i = pos.astype(int)
    f = pos - i
    return float(((1 - f) * nov[i] + f * nov[i + 1]).mean())


def analyze(path, nb=28, bpm_lo=90, bpm_hi=150, prior=120):
    x = decode(path)
    mono = x.mean(1)
    nov, low, rms = novelty(mono)
    fps = SR / HOP

    # tempo : autocorrélation, pondérée autour de 120 BPM
    ac = np.correlate(nov, nov, mode="full")[len(nov) - 1:]
    lags = np.arange(len(ac))
    with np.errstate(divide="ignore"):
        bpm_of = 60 * fps / lags
    ok = (bpm_of >= bpm_lo) & (bpm_of <= bpm_hi)
    weight = np.exp(-0.5 * (np.log2(np.where(ok, bpm_of, prior) / prior) / 0.25) ** 2)
    score = np.where(ok, ac * weight, 0)
    k = int(np.argmax(score))
    a, b, c = ac[k - 1], ac[k], ac[k + 1]
    lag = k + 0.5 * (a - c) / (a - 2 * b + c + 1e-12)

    # affinage : période et phase qui maximisent le peigne sur toute la piste.
    # La phase s'appuie surtout sur l'attaque grave, sinon les charlestons à
    # contretemps décalent la grille d'un demi-temps.
    onset = 0.4 * nov + low
    best = (-1, lag, 0)
    for per in np.linspace(lag * 0.99, lag * 1.01, 81):
        for ph in np.linspace(0, per, 48, endpoint=False):
            s = comb(onset, per, ph)
            if s > best[0]:
                best = (s, per, ph)
    _, per, ph = best
    for ph2 in np.linspace(ph - per / 48, ph + per / 48, 25):
        s = comb(onset, per, ph2 % per)
        if s > best[0]:
            best = (s, per, ph2 % per)
    _, per, ph = best

    beat = per / fps
    bpm = 60 / beat
    # décalage du centre de la fenêtre d'analyse
    first = ph / fps + (NFFT / 2) / SR
    first %= beat
    # affinage à la milliseconde : la grille se cale sur la montée la plus raide de
    # l'enveloppe du signal grave autour de chaque temps (médiane des écarts signés)
    beats = np.arange(first, len(mono) / SR, beat)
    lowsig = lowpass(mono, 200)
    envl = np.convolve(np.abs(lowsig), np.ones(88) / 88, mode="same")     # 2 ms
    rise = np.diff(envl, prepend=envl[0])
    dev = []
    for t in beats[: min(len(beats), 300)]:
        j = int(t * SR)
        a, b2 = max(0, j - int(.04 * SR)), min(len(rise), j + int(.04 * SR))
        if b2 - a < 10 or envl[a:b2].max() < 0.05 * envl.max():
            continue
        dev.append((a + int(np.argmax(rise[a:b2])) - j) / SR)
    shift = float(np.median(dev)) if dev else 0.0
    first = (first + shift) % beat
    beats = np.arange(first, len(mono) / SR, beat)
    # indice de trame dont la fenêtre est centrée sur le temps, maximum sur ±2 trames
    bi = np.clip(np.round((beats - (NFFT / 2) / SR) * fps).astype(int), 2, len(nov) - 4)
    around = lambda x: np.max(np.stack([x[bi + d] for d in range(-2, 4)]), axis=0)

    # phase de mesure : les temps forts portent le plus d'attaque grave et de nouveauté
    strength = around(low) + 0.5 * around(nov)
    bar_score = [float(strength[p::4].mean()) for p in range(4)]
    bar_phase = int(np.argmax(bar_score))
    downbeats = beats[bar_phase::4]

    # départ : un temps fort dont les 7 mesures suivantes sont les plus pleines
    L = nb * beat
    rms_t = np.arange(len(rms)) / fps + (NFFT / 2) / SR
    cands = []
    for i, s in enumerate(downbeats):
        if s + L + 0.05 > len(mono) / SR:
            break
        m = (rms_t >= s) & (rms_t < s + L)
        loud = float(rms[m].mean())
        steady = float(rms[m].std() / (loud + 1e-9))
        hit = float(strength[bar_phase + 4 * i])
        cands.append((loud * (1 - 0.3 * steady) * (1 + 0.15 * hit), float(s), i))
    cands.sort(reverse=True)
    start = cands[0][1] if cands else float(downbeats[0])

    # précision : écart résiduel entre la grille et les attaques, après recalage
    dev = [d - shift for d in dev]
    return {
        "file": str(path),
        "bpm": round(bpm, 4),
        "beat": beat,
        "first_beat": float(first),
        "bar_phase": bar_phase,
        "bar_scores": [round(s, 4) for s in bar_score],
        "start": start,
        "loop_beats": nb,
        "loop_seconds": L,
        "duration": len(mono) / SR,
        "grid_shift_ms": round(shift * 1000, 2),
        "grid_error_ms_median": round(float(np.median(np.abs(dev))) * 1000, 2) if dev else None,
        "candidates": [{"start": round(s, 4), "bar": i, "score": round(v, 5)} for v, s, i in cands[:5]],
    }


# ---------------------------------------------------------------------------
# Sons d'UI, synthétisés (graine fixe : le mixage est reproductible)

def env(n, attack, decay):
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-5), 0, 1)
    return a * np.exp(-np.maximum(0, t - attack) / decay)


def band_noise(n, lo, hi, rng):
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    y = np.fft.irfft(X, n)
    return y / (np.abs(y).max() + 1e-9)


def sine(n, f0, f1=None):
    f = np.full(n, f0, float) if f1 is None else np.geomspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def synth(kind, rng):
    ms = lambda v: int(v * SR / 1000)
    if kind == "down":
        n = ms(90)
        y = 0.55 * band_noise(n, 1800, 7000, rng) * env(n, 0.0004, 0.004)
        y += 0.5 * sine(n, 2300) * env(n, 0.0005, 0.010)
        y += 0.7 * sine(n, 190, 150) * env(n, 0.001, 0.022)
    elif kind == "up":
        n = ms(60)
        y = 0.4 * band_noise(n, 2500, 9000, rng) * env(n, 0.0003, 0.003)
        y += 0.45 * sine(n, 3100) * env(n, 0.0004, 0.007)
    elif kind == "key":
        n = ms(70)
        y = 0.6 * band_noise(n, 2500, 8000, rng) * env(n, 0.0003, 0.0035)
        y += 0.35 * sine(n, 1650) * env(n, 0.0005, 0.009)
        y += 0.3 * sine(n, 240) * env(n, 0.001, 0.015)
    elif kind == "enter":
        n = ms(120)
        y = 0.6 * band_noise(n, 1200, 6000, rng) * env(n, 0.0004, 0.005)
        y += 0.8 * sine(n, 150, 110) * env(n, 0.001, 0.035)
        y += 0.3 * sine(n, 900) * env(n, 0.0006, 0.018)
    elif kind == "toggle":
        n = ms(140)
        y = 0.5 * band_noise(n, 1500, 7000, rng) * env(n, 0.0004, 0.004)
        y += 0.9 * sine(n, 160, 120) * env(n, 0.001, 0.045)
        y += 0.35 * sine(n, 2000) * env(n, 0.0005, 0.012)
    elif kind == "success":
        n = ms(600)
        t0 = ms(70)
        a = sine(n, 1318.5) + 0.25 * sine(n, 2637)
        b = np.zeros(n)
        b[t0:] = (sine(n - t0, 1975.5) + 0.2 * sine(n - t0, 3951))
        y = 0.5 * a * env(n, 0.002, 0.14) + 0.6 * b * np.r_[np.zeros(t0), env(n - t0, 0.002, 0.2)]
    elif kind == "pop":
        n = ms(90)
        y = sine(n, 520, 1150) * env(n, 0.002, 0.025)
    elif kind == "swish":
        n = ms(220)
        t = np.arange(n) / SR
        shape = np.exp(-0.5 * ((t - 0.07) / 0.035) ** 2)
        y = band_noise(n, 900, 6000, rng) * shape
    else:
        raise ValueError(kind)
    return y / (np.abs(y).max() + 1e-9)


GAIN = {"down": .30, "up": .16, "key": .20, "enter": .32, "toggle": .34,
        "success": .20, "pop": .18, "swish": .07}


def peak_index(y):
    e = np.convolve(np.abs(y), np.ones(44) / 44, mode="same")   # enveloppe à 1 ms
    return int(np.argmax(e))


def mix(track, beats_path, sfx_path, out):
    info = json.loads(pathlib.Path(beats_path).read_text())
    sfx = json.loads(pathlib.Path(sfx_path).read_text())
    L = sfx["meta"]["L"]
    x = decode(track)
    s0 = int(round(info["start"] * SR))
    n = int(round(L * SR))
    song = x[s0: s0 + n].astype(np.float64)
    if len(song) < n:
        sys.exit("piste trop courte pour la boucle")

    # raccord de boucle sans clic
    fi, fo = int(0.002 * SR), int(0.008 * SR)
    song[:fi] *= np.linspace(0, 1, fi)[:, None]
    song[-fo:] *= np.linspace(1, 0, fo)[:, None]

    rng = np.random.default_rng(7)
    ui = np.zeros((n, 2))
    placed = []
    for ev in sfx["events"]:
        y = synth(ev["kind"], rng) * GAIN[ev["kind"]]
        pk = peak_index(y)
        at = int(round(ev["t"] * SR)) - pk                 # le pic tombe sur l'événement
        pan = float(np.clip(ev.get("pan", 0), -1, 1)) * 0.35
        lr = np.array([np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)]) * np.sqrt(2)
        idx = (at + np.arange(len(y))) % n                  # boucle circulaire
        np.add.at(ui, idx, y[:, None] * lr[None, :])
        placed.append({"kind": ev["kind"], "t": ev["t"], "peak_ms": round(pk / SR * 1000, 2)})

    # la musique d'abord, les sons d'UI au-dessus sans la noyer
    song_rms = np.sqrt((song ** 2).mean()) + 1e-9
    y = song / song_rms * 0.12 + ui
    peak = np.abs(y).max()
    if peak > 0.89:
        y = np.tanh(y / peak * 1.4) / np.tanh(1.4) * 0.89   # limiteur doux
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-", str(out)],
                   input=pcm.tobytes(), check=True)
    return {"out": str(out), "seconds": n / SR, "events": placed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["analyze", "mix"])
    ap.add_argument("track")
    ap.add_argument("--beats", default="build/beats.json")
    ap.add_argument("--sfx", default="build/sfx.json")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.mode == "analyze":
        res = analyze(a.track)
        out = pathlib.Path(a.out or "build/beats.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res, indent=2, ensure_ascii=False))
        print(json.dumps({k: res[k] for k in ("bpm", "start", "bar_phase", "grid_error_ms_median")}, ensure_ascii=False))
    else:
        res = mix(a.track, a.beats, a.sfx, a.out or "build/mix.wav")
        print(f"{res['out']} ({res['seconds']:.3f} s, {len(res['events'])} sons)")


if __name__ == "__main__":
    main()
