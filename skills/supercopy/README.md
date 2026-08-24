# supercopy

Nettoie un texte de tout ce qui trahit une écriture générée par IA.

Écrire comme une IA ne fait plus moderne, ça fait négligent. Le lecteur repère le tiret cadratin, le « Ce n'est pas X, c'est Y », les trois lignes qui rétrécissent vers une chute abstraite, et il en tire une conclusion sur le sérieux de celui qui publie. Ce skill retire ces marques et rend le texte à quelqu'un.

*Cleans the tells of AI-generated writing out of a text. French typography first, English handled too.*

## Ce que ça donne

**Avant**

> Ce n'est pas l'IA qui a vidé nos feeds de leur âme. C'est nous qui n'en avions plus besoin pour publier.
>
> Le process n'est pas plus intelligent. Pas plus sincère. Il est juste plus rapide.
>
> Honnêtement ? Je ne me souviens plus du dernier post qui m'a vraiment touché.
>
> Les experts sont formels : nos feeds n'ont jamais été aussi remplis — et jamais aussi vides.
>
> Du contenu.
> Du volume.
> Du vide.

**Après**

> Nous n'avions plus besoin d'âme pour publier. Le process est juste plus rapide.
>
> Je ne me souviens pas du dernier post qui m'a touché. Nos feeds n'ont jamais été aussi remplis, et jamais aussi vides : on produit du volume, et ce volume est vide.

**Ce qui a été retiré**

- Retournement : « Ce n'est pas l'IA qui... C'est nous qui... »
- Triade : « Pas plus intelligent. Pas plus sincère. »
- Fausse confidence : « Honnêtement ? »
- Autorité non sourcée : « Les experts sont formels »
- Tiret cadratin remplacé par une virgule, devant une coordination
- Escalier décroissant : « Du contenu. Du volume. Du vide. »

## Installation

```
/plugin marketplace add ChrisLefevre/claude-skills
/plugin install supercopy@claude-skills
```

Dans Cowork ou sur claude.ai : **Customize** > **Plugins** > **+** > **Add marketplace**, collez l'adresse du dépôt, puis **Install**.

## Usage

Collez un texte et demandez de le nettoyer. Le skill se déclenche aussi sur « ça fait trop IA », « relis mon post », « enlève les tirets cadratins ».

Par défaut il réécrit directement, puis liste ce qu'il a coupé. Pour un diagnostic sans réécriture, demandez « qu'est-ce qui cloche dans ce texte ».

### Le script seul

La partie mécanique s'exécute sans assistant :

```bash
python3 scripts/nettoyer.py mon-texte.txt
python3 scripts/nettoyer.py mon-texte.txt --sortie propre.txt
echo "un texte — avec un tiret" | python3 scripts/nettoyer.py -
python3 scripts/nettoyer.py mon-texte.txt --json
```

Il corrige la typographie et signale les tics rhétoriques, qui demandent un jugement humain. Aucune dépendance, Python 3 suffit.

## Le traitement du tiret cadratin

C'est la partie la plus demandée, et celle où une substitution unique ne marche pas. Le remplacement dépend de la fonction du tiret :

| Contexte | Remplacement |
|---|---|
| Incise entre deux tirets | Deux virgules |
| Suivi de *et, mais, ou, donc, car* | Virgule |
| Suivi d'une proposition complète | Point |
| Introduit une explication longue | Deux-points |
| Début de ligne | Tiret court |
| Entre deux nombres | « à » |

Le script applique ces règles et rend compte de chaque décision.

Il respecte aussi l'espace avant `;` `:` `!` `?`, propre au français. Beaucoup d'outils de nettoyage écrits pour l'anglais collent ces signes, ce qui remplace un défaut par un autre.

## Ce que le skill ne fait pas

**Il n'ajoute pas de fautes pour faire humain.** Les erreurs volontaires et l'oralité forcée sont un autre genre de tic.

**Il ne sur-corrige pas.** Un tiret justifié reste. Trois éléments réellement distincts restent. Le but est de retirer les réflexes, pas d'appauvrir.

**Il ne réécrit pas à votre place.** Il retire ce qui n'est pas de vous. Si le texte devient plat une fois nettoyé, c'est qu'il n'y avait pas grand-chose dessous, et aucun outil ne corrige cela.

## Structure

```
supercopy/
├── SKILL.md              instructions
├── references/
│   └── tics.md           catalogue complet, variantes, avant/après, section anglaise
└── scripts/
    └── nettoyer.py       typographie automatique et détection des tics
```

## Licence

MIT, voir [LICENSE](../../LICENSE).
