---
name: daily-project-brief
description: |
  Acts as a daily project manager on top of a spreadsheet of projects and markdown memory files. Produces a morning brief (today's priorities, a time-log question, targeted progress questions), then writes the answers back into the spreadsheet and the memory. Always replies in the user's own language. Use this skill whenever the user mentions a morning brief, a daily stand-up, project tracking, today's priorities, a work log, time spent per project, upcoming or missed deadlines, weekly reporting to management, or asks to update a project tracking file after a conversation, even if they never name the file or the skill.
  Assistant de gestion de projet quotidien, à partir d'un tableur de suivi et de fichiers de mémoire markdown. Produit un brief matinal (priorités du jour, journal de bord du temps passé, questions d'avancement ciblées), puis répercute les réponses dans le fichier et dans la mémoire. Répond toujours dans la langue de l'utilisateur. Utilise cette compétence dès que l'utilisateur parle de brief matinal, de point projets, de suivi de projets, de priorités du jour, de journal de bord, de temps passé par projet, d'échéances à relancer, de reporting hebdomadaire à sa direction, ou demande de mettre à jour un fichier de suivi après un échange, même s'il ne nomme pas explicitement le fichier ou la compétence.
---

# Daily project brief

Cette compétence transforme un tableur de suivi de projets en une boucle de pilotage quotidienne : lire, analyser, poser les bonnes questions, consigner les réponses. Elle sert deux besoins qui se renforcent : donner à l'utilisateur un cap clair chaque matin, et maintenir une trace fiable du temps passé, utilisable pour justifier la charge et construire des rétroplannings.

Le fichier de suivi est la source de vérité. La mémoire markdown est la couche de contexte : elle explique pourquoi les choses sont dans l'état où elles sont, et évite de reposer des questions déjà traitées.

**Langue.** Toute la documentation de la compétence est en français, mais le brief, les questions et les notes écrites dans les fichiers suivent la langue de l'utilisateur. Si quelqu'un s'adresse à toi en anglais, tu réponds et tu écris en anglais.

## Démarrage

Trois situations, à distinguer dès le premier message.

**L'utilisateur a déjà une configuration.** Un `config.json` dans le dossier de travail, ou des instructions dans la tâche planifiée qui déclenche le brief. Reprends-la telle quelle et enchaîne sur le brief, sans reposer de questions.

**L'utilisateur a déjà un fichier de suivi mais pas de configuration.** Demande le chemin du dossier, puis laisse `lire_suivi.py` détecter les onglets et les colonnes. Il reconnaît la plupart des intitulés courants. Ne demande que ce qui manque vraiment, puis propose d'enregistrer un `config.json` pour ne pas recommencer demain.

**L'utilisateur n'a rien.** C'est le cas le plus fréquent au premier usage, et le script d'initialisation existe précisément pour ça :

```bash
python3 scripts/initialiser.py "/chemin/vers/le/dossier" --exemples --responsable "Prénom Nom"
```

Il crée un classeur complet (onglet mode d'emploi en première page, onglet des projets avec liste déroulante de statuts et formules, journal quotidien, synthèse hebdomadaire), les deux fichiers de mémoire et un `config.json` renseigné. Ajoute `--exemples` pour trois projets de démonstration que l'utilisateur remplacera, `--partage` si le dossier est visible par la direction.

Après l'initialisation, l'utilisateur n'a qu'à saisir ses projets. Explique-lui en une phrase que seules quatre colonnes comptent au départ : le nom, le statut, l'échéance et la prochaine étape. Le reste se remplit tout seul au fil des briefs.

Les détails des réglages sont dans `references/configuration.md`, à lire quand une structure de fichier sort de l'ordinaire.

## Déroulé du brief matinal

### 1. Charger le contexte

Lis les fichiers de mémoire du dossier de travail, dans cet ordre : le fichier d'index et de règles, puis le fichier d'état courant, puis les éventuels fichiers de consignes. Ils contiennent les règles de travail que l'utilisateur a posées au fil du temps, les décisions récentes, les questions déjà ouvertes et les sujets à ne pas relancer.

Ce point mérite de l'attention : la valeur d'un brief tient largement à ce qu'il ne redemande pas. Un brief qui repose une question à laquelle l'utilisateur a répondu la veille détruit la confiance dans l'outil.

### 2. Récupérer le fichier de suivi

Le fichier vit souvent sur la machine de l'utilisateur (Dropbox, iCloud, disque local) alors que l'analyse se fait dans un environnement séparé. Copie-le vers ton espace de travail avant de le lire, ne travaille jamais directement sur l'original.

Selon les outils disponibles :
- Dossier connecté à la session : outil de mise à disposition des fichiers du périphérique
- Sinon : exécution d'une commande shell sur la machine de l'utilisateur (`osascript` avec `do shell script "cp ..."`) vers le dossier de sortie de la session

Si le fichier ou la mémoire sont inaccessibles (machine éteinte, dossier non synchronisé), produis quand même un brief à partir de ce que tu sais, et signale l'indisponibilité en une ligne. Un brief dégradé vaut mieux qu'un silence.

### 3. Analyser

Utilise `scripts/lire_suivi.py` plutôt que d'écrire du code à la volée : il détecte les colonnes par leur en-tête, filtre les projets clos et sort un état lisible en un appel.

```bash
python3 scripts/lire_suivi.py "<chemin du fichier>" --jours 7
```

Ce que l'analyse doit faire ressortir :

- **Échéances dépassées** : la date de fin prévue est passée et le projet n'est pas clos. C'est le signal le plus fort, il passe devant tout le reste.
- **Échéances proches** (par défaut sous 7 jours), en particulier celles dont l'avancement ne permet pas de tenir la date.
- **Projets bloqués**, et surtout depuis combien de temps. Un blocage qui dure appelle une relance, pas une constatation.
- **Projets prioritaires** peu ou pas avancés.
- **Démarrages du jour** : projets dont la date de début prévue tombe aujourd'hui et qui sont encore au statut « prévu ».
- **Charge de la période** : somme des jours estimés sur les projets qui se chevauchent. Quand elle dépasse le raisonnable, dis-le, c'est un arbitrage à provoquer tôt.
- **Alertes du tableau de bord** et **événements à venir** notés dans la mémoire (réunions, sessions, jalons externes).
- **Dernières entrées du journal quotidien** : questions déjà posées, réponses obtenues, points laissés en suspens.

### 4. Rédiger le brief

Trois blocs, dans cet ordre. La forme compte : le brief est lu debout, avant le premier café.

**a) Le planning du jour.** Cinq lignes maximum, ordonnées par urgence réelle. Chaque ligne porte l'identifiant du projet, l'action attendue, et une justification d'une seule ligne : échéance, priorité ou dépendance. La justification est ce qui rend le brief actionnable plutôt que directif : l'utilisateur peut contester l'ordre s'il voit l'argument.

Ajoute au besoin une ligne « si le temps le permet » pour les sujets réels mais non critiques. Ne gonfle pas la liste principale : un planning de dix items n'est plus un planning.

**b) Le journal de bord.** Demande sur quels projets l'utilisateur a travaillé le dernier jour ouvré et combien de temps sur chacun. Cette question revient chaque jour, elle n'est jamais redondante. Rappelle explicitement les journées ou les projets pour lesquels le temps manque encore, c'est là que les trous se créent.

**c) Une à trois questions d'avancement.** Ciblées, sur des projets actifs, portant sur du concret : pourcentage d'avancement, nature exacte d'un blocage, date réelle, décision en attente. Écarte toute question déjà traitée récemment dans le journal quotidien, et tout sujet que l'utilisateur a demandé de mettre en attente.

Formule les questions de façon à ce qu'une réponse courte suffise. « Que reste-t-il avant publication, l'échéance tient-elle ? » se répond en une phrase ; « où en est ce projet ? » appelle un paragraphe que personne n'écrira.

### 5. Diffuser

Respecte le mode de diffusion configuré. Par défaut, affiche le brief en entier dans la conversation : c'est là que l'utilisateur répond, et un brief tronqué l'oblige à changer de fenêtre. N'envoie un email que si la configuration le prévoit.

## Répercuter les réponses

Quand l'utilisateur répond, la règle est simple : **rien n'est modifié tant qu'il n'a pas répondu.** Pas de réponse, pas d'écriture. Un fichier de suivi qui bouge sans instruction humaine devient inexploitable pour justifier quoi que ce soit.

Sur réponse, mets à jour dans le même mouvement :

1. **L'onglet des projets** : avancement, jours réels cumulés, dates réelles, statut, prochaine étape, notes.
2. **L'onglet du journal quotidien** : une ligne par question traitée, avec la date, la question, la réponse et l'action prise. Inclut le journal du temps passé.
3. **Les fichiers de mémoire** : état courant des projets, décisions du jour, questions encore ouvertes. Le fichier de règles n'est touché que si une règle change.

Les détails techniques (couleurs de statut à appliquer en dur, gestion des formules, insertion de lignes sans casser les références, vérification avant sauvegarde, recopie vers le dossier source) sont dans `references/mise-a-jour-fichier.md`. Lis-le avant toute écriture dans le fichier, les pièges y sont réels et coûteux.

## Comptabiliser le temps

Un jour consigné est une unité de charge, pas une journée calendaire. Quelqu'un qui mène quatre projets en parallèle peut consigner 0,3 jour sur trois d'entre eux le même jour, et la somme d'une journée peut dépasser 1. Ne « corrige » jamais un total qui dépasse 1 sur une date.

Conversion usuelle quand l'utilisateur répond en heures, sur une base de 7,5 heures : 30 min = 0,07 j, 1 h = 0,13 j, 1 h 30 = 0,2 j, 2 h = 0,27 j, 3 h = 0,4 j, une demi-journée = 0,5 j. Adapte si la configuration indique une autre base.

Les jours réels s'ajoutent au cumul existant, ils ne le remplacent pas. Quand l'utilisateur donne une durée sans préciser le projet, demande plutôt que d'attribuer au hasard.

## Reporting hebdomadaire

Si un tableau de bord de synthèse existe, il alimente un point périodique avec la direction. Lis `references/reporting-hebdo.md` quand l'utilisateur prépare ce point ou demande une synthèse hebdomadaire.

L'essentiel : les cellules reprises automatiquement de l'onglet des projets ne se saisissent pas à la main, les indicateurs et les points d'arbitrage se rédigent, et un risque signalé sans décision attendue ni impact chiffré n'a aucune utilité en comité.

## Écrire dans un dossier partagé

Les fichiers de suivi et de mémoire sont fréquemment stockés dans un dossier partagé avec la direction. Tout ce qui y est écrit doit rester factuel et professionnel : état des projets, décisions, actions, échéances. Aucune appréciation sur les personnes, aucun commentaire personnel, aucun sous-entendu sur l'organisation.

Cette contrainte n'est pas cosmétique. Une note de suivi lue par un tiers six mois plus tard doit pouvoir être défendue ligne à ligne.

## Garde-fous

- **Ne touche qu'aux fichiers prévus par la configuration.** Les autres fichiers du dossier (versions antérieures, archives, présentations, annexes) restent intacts sauf demande explicite.
- **Vérifie avant de sauver.** Après toute modification structurelle, recalcule les formules et exige zéro erreur avant de recopier le fichier vers le dossier source.
- **Travaille sur une copie.** L'original ne se modifie qu'à la dernière étape, une fois la vérification passée.
- **Signale les incohérences plutôt que de les résoudre seul.** Une date de fin antérieure à la date de début, un projet à 100 % encore « en cours », un total de charge intenable : ce sont des questions pour le brief du lendemain, pas des corrections silencieuses.

## Fichiers de la compétence

- `references/configuration.md` : réglages, structure de fichier attendue, exemple commenté
- `references/mise-a-jour-fichier.md` : couleurs de statut, formules, insertion de lignes, vérification, recopie
- `references/reporting-hebdo.md` : préparation du point périodique avec la direction
- `scripts/initialiser.py` : création d'un dossier de suivi complet pour qui n'a rien
- `scripts/lire_suivi.py` : lecture et analyse du fichier de suivi
- `scripts/appliquer_statut.py` : application des couleurs de statut en dur

Les trois scripts n'ont besoin que de Python 3 et d'`openpyxl`.
