#!/usr/bin/env bash
# Chaîne complète.
#
#   tools/build.sh piste.mp3          analyse, sons, puis une image par temps (build/beats/sheet.png)
#   tools/build.sh piste.mp3 --video  la même chose, puis la vidéo finale avec le son (build/morph.mp4)
#   tools/build.sh                    sans piste : 120 BPM, planche et vidéo muettes
#
# La planche passe avant la vidéo : on la relit (hors grille, serré, dur à lire)
# avant de lancer le rendu complet.
set -euo pipefail
cd "$(dirname "$0")/.."

TRACK="${1:-}"
VIDEO="${2:-}"
BPM=120

if [[ -n "$TRACK" && "$TRACK" != "--video" ]]; then
  python3 tools/audio.py analyze "$TRACK" --out build/beats.json
  BPM=$(python3 -c "import json; print(json.load(open('build/beats.json'))['bpm'])")
  node tools/render.cjs sfx --bpm "$BPM" --out build/sfx.json
  python3 tools/audio.py mix "$TRACK" --beats build/beats.json --sfx build/sfx.json --out build/mix.wav
else
  VIDEO="${TRACK:-$VIDEO}"
  TRACK=""
fi

node tools/render.cjs beats --bpm "$BPM" --out build/beats

if [[ "$VIDEO" == "--video" || -z "$TRACK" ]]; then
  if [[ -n "$TRACK" ]]; then
    node tools/render.cjs video --bpm "$BPM" --audio build/mix.wav --out build/morph.mp4
  else
    node tools/render.cjs video --bpm "$BPM" --out build/morph.mp4
  fi
fi
