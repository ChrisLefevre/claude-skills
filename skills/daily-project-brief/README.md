# daily-project-brief

Un assistant de gestion de projet qui vous fait un point chaque matin.

Il lit votre tableur de projets, vous dit ce qu'il y a à finir aujourd'hui et pourquoi, vous demande sur quoi vous avez travaillé la veille et combien de temps, puis reporte vos réponses dans le fichier. Vous ne tenez plus le tableau à la main, vous répondez à trois questions.

*Documentation and skill are written in French, but the assistant answers in whatever language you write to it. See [English summary](#english-summary) below.*

---

## À quoi ça ressemble

> **Planning du jour**
>
> 1. **#64 Automatisation de la boîte info@** : lancer le cadrage. Fin prévue vendredi, 5 jours estimés, statut encore « Prévu », c'est le point le plus tendu de la semaine.
> 2. **#6 Landing page** : finaliser les pages FR et NL, puis publier. Échéance demain, projet à 90 %.
> 3. **#63 Site partenaire** : échéance dépassée depuis six jours, relancer et fixer une nouvelle date.
>
> **Journal de bord**
>
> Sur quels projets avez-vous travaillé vendredi, et combien de temps sur chacun ?
>
> **Questions**
>
> 1. #6 : que reste-t-il avant publication, l'échéance de demain tient-elle ?
> 2. #64 : avec 5 jours estimés et une fin vendredi, faut-il repousser ou réduire le périmètre ?

Vous répondez en une ou deux phrases. L'avancement, le temps passé, les statuts et les prochaines étapes sont mis à jour dans le fichier, et chaque échange est archivé dans un onglet d'historique.

## Installation

### Dans Claude Code

Deux commandes :

```
/plugin marketplace add ChrisLefevre/claude-skills
/plugin install daily-project-brief@claude-skills
```

Si l'installation indique `Run /reload-plugins to activate`, lancez cette commande.

### Dans Claude Cowork ou sur claude.ai

Ouvrez le menu **Customize**, onglet **Plugins**, section **Personal plugins**, bouton **+**, puis **Add marketplace**. Collez l'adresse du dépôt, puis cliquez sur **Install**. Le skill devient disponible dans vos conversations et dans Cowork.

### Dépendance

```bash
pip install openpyxl
```

LibreOffice est facultatif : il sert à vérifier les formules avant d'enregistrer le fichier.

### Premier démarrage

**Vous n'avez pas encore de fichier de suivi.** Une commande crée tout :

```bash
python3 scripts/initialiser.py "~/Documents/Mes projets" --exemples --responsable "Prénom Nom"
```

Vous obtenez un classeur avec un mode d'emploi en première page, un onglet de projets prêt à remplir, un historique et une page de synthèse pour vos réunions, plus les fichiers de mémoire et la configuration. Il ne reste qu'à saisir vos projets : au départ, seules quatre colonnes comptent, le nom, le statut, l'échéance et la prochaine étape.

**Vous avez déjà un tableur de projets.** Dites simplement où il se trouve. Les onglets et les colonnes sont détectés automatiquement à partir de leurs intitulés, en français comme en anglais. Si un intitulé sort de l'ordinaire, une ligne de configuration suffit à faire la correspondance.

### Usage quotidien

Demandez « fais-moi mon brief projets du jour ». C'est tout.

Pour le recevoir automatiquement chaque matin, créez une tâche planifiée dans votre assistant, en semaine, à l'heure qui vous convient.

## Ce que la compétence sait faire

| | |
|---|---|
| **Brief matinal** | Échéances dépassées et proches, blocages, projets prioritaires peu avancés, démarrages attendus, charge de la période, alertes de synthèse. Cinq priorités maximum, chacune avec sa justification en une ligne. |
| **Journal de bord** | La question du temps passé, posée chaque jour. C'est ce qui permet de justifier une charge et de bâtir un rétroplanning crédible. |
| **Questions ciblées** | Une à trois, sur des projets actifs, jamais deux fois la même. Les sujets que vous mettez en attente ne reviennent pas. |
| **Mise à jour du fichier** | Avancement, temps cumulé, dates réelles, statuts, prochaines étapes, couleurs. Uniquement après votre réponse : sans réponse, rien n'est modifié. |
| **Mémoire** | Deux fichiers markdown gardent l'état des projets, les décisions datées et les questions ouvertes, pour que le brief du lendemain ne reparte pas de zéro. |
| **Reporting** | Préparation du point périodique avec votre direction, à partir de la page de synthèse. |

## Structure du dépôt

```
daily-project-brief/
├── SKILL.md                    instructions de la compétence
├── config.exemple.json         modèle de configuration
├── references/
│   ├── configuration.md        réglages, colonnes reconnues, structure attendue
│   ├── mise-a-jour-fichier.md  couleurs, formules, précautions d'écriture
│   └── reporting-hebdo.md      préparation du point avec la direction
└── scripts/
    ├── initialiser.py          crée un dossier de suivi complet
    ├── lire_suivi.py           lit et analyse le fichier
    └── appliquer_statut.py     pose les couleurs de statut
```

Les scripts s'utilisent aussi seuls, sans assistant :

```bash
python3 scripts/lire_suivi.py "suivi-projets.xlsx" --jours 7
python3 scripts/lire_suivi.py "suivi-projets.xlsx" --json
python3 scripts/appliquer_statut.py "suivi-projets.xlsx" --onglet Projets
```

## Quelques partis pris

**Les couleurs sont posées dans les cellules, pas en mise en forme conditionnelle.** Beaucoup d'aperçus rapides et de visionneuses mobiles n'affichent pas la mise en forme conditionnelle : le fichier arriverait en noir et blanc chez votre lecteur, et perdrait l'essentiel de son information visuelle.

**Un jour de temps passé est une unité de charge, pas une journée de calendrier.** Si vous avancez sur trois projets le même jour, le total de la journée peut dépasser 1. C'est voulu, et le fichier ne le « corrige » jamais.

**Rien n'est écrit sans votre réponse.** Un fichier de suivi qui bouge tout seul ne peut plus servir à justifier quoi que ce soit.

**Le brief ne repose pas une question déjà traitée.** L'historique est relu avant chaque brief. C'est ce qui fait la différence entre un outil qu'on garde et un rappel automatique qu'on finit par ignorer.

**Les incohérences sont signalées, pas corrigées.** Une échéance antérieure à la date de début, un projet à 100 % encore en cours : ce sont des questions pour le lendemain, pas des corrections silencieuses.

## Limites connues

- Le format attendu est un classeur `.xlsx`. Les autres formats de tableur ne sont pas gérés.
- La page de synthèse utilise des formules qui pointent vers des numéros de lignes fixes. Insérer une ligne au milieu de l'onglet des projets décale ces références, la marche à suivre est documentée dans `references/mise-a-jour-fichier.md`.
- La vérification des formules par recalcul suppose LibreOffice installé. Sans lui, la vérification est sautée et le fichier est modifié quand même.

## English summary

**daily-project-brief** turns a project spreadsheet into a daily management loop. Each morning it reads your tracker and returns: today's priorities with a one-line justification each, a work-log question (which projects did you work on yesterday, and for how long), and one to three targeted progress questions. Your answers are written back into the spreadsheet and into two markdown memory files, so tomorrow's brief starts from today's state.

The skill files are in French, but the assistant replies in the language you write to it. Column headers are auto-detected in both French and English. `scripts/initialiser.py` builds a complete tracking folder from scratch if you don't have one, including a built-in user guide sheet.

Requires Python 3 and `openpyxl`. LibreOffice is optional, used to verify formulas before saving.

## Licence

MIT, voir [LICENSE](../../LICENSE).
