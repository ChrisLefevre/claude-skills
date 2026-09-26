# ui-morph

Une seule forme qui devient douze composants d'interface en 7 mesures à 120 BPM :
bouton, chargeur, coche, île dynamique, lecteur, barre de progression, volume,
interrupteur, onglets, graphique, palette ⌘K, toast, puis retour au bouton. La boucle
est parfaite : la dernière image raccorde avec la première, position et vitesse du
curseur comprises.

## Fichiers

| Fichier | Rôle |
|---|---|
| `morph.html` | L'animation, carré 1440×1440, autonome (Geist intégrée). Toute l'image est calculée par `seek(t)`. |
| `tools/render.cjs` | Rendu Playwright : une image par temps, images fixes, liste des sons, vidéo. |
| `tools/audio.py` | Analyse de la chanson (numpy) et mixage des sons d'UI. |
| `tools/build.sh` | La chaîne complète. |

## Aperçu

Ouvrir `morph.html` dans un navigateur lit l'animation en temps réel.
`morph.html?t=4.5` affiche l'image à 4,5 s, `?bpm=118` recale tout sur un autre tempo.

Pour un aperçu avec lecture, défilement par temps, ralenti et sons d'UI :

```
node tools/render.cjs sfx --out build/sfx.json
python3 tools/preview.py            # écrit build/preview.html
```

## Rendu

```
tools/build.sh piste.mp3          # analyse, sons, planche d'une image par temps
tools/build.sh piste.mp3 --video  # puis la vidéo finale avec le son
tools/build.sh                    # sans piste : 120 BPM, muet
```

Il faut `node` avec Playwright et Chromium, `ffmpeg`, `python3` avec numpy.
Les sorties vont dans `build/`, ignoré par git.

## Principes

- **Temps pur.** Aucune transition CSS, aucun minuteur, aucun état porté d'une image
  à l'autre. `seek(t)` réécrit chaque style à partir de `t`.
- **Ressorts en forme fermée.** Une valeur qui change de cible plusieurs fois est la
  somme d'un ressort par changement. Les phases bouclent, et le cycle précédent est
  ajouté, d'où une couture sans à-coup.
- **Bords sur ressorts différents.** Le bord avant de l'indicateur d'onglet et du
  bouton d'interrupteur est plus rapide que le bord arrière, ce qui étire la pastille.
- **Manipulation directe.** Pendant un appui, la valeur (progression, volume,
  infobulle) se calcule depuis la position du curseur. Au relâchement, elle repart en
  ressort depuis sa position et sa vitesse.
- **Son.** La grille des temps est ajustée sur toute la piste, recalée à la
  milliseconde sur l'attaque grave, et la boucle démarre sur un temps fort. Chaque son
  d'UI est placé pour que son pic mesuré tombe sur son événement.
- **Flou de mouvement.** 4 sous-images par image, obturateur à 360°, mélangées par
  `ffmpeg tmix`, sortie à 60 i/s.
