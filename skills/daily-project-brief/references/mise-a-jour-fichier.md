# Mise à jour du fichier de suivi

À lire avant toute écriture. Les pièges décrits ici cassent silencieusement un fichier : les erreurs n'apparaissent qu'à l'ouverture suivante, souvent devant quelqu'un d'autre.

## Ordre des opérations

1. Travailler sur la copie déjà rapatriée dans l'espace de travail, jamais sur l'original
2. Appliquer les modifications avec openpyxl (`keep_vba=True` si le fichier est en `.xlsm`)
3. Appliquer les couleurs de statut
4. Vérifier les formules par recalcul, exiger zéro erreur
5. Recopier vers le dossier source
6. Consigner ce qui a été fait dans le fichier de mémoire d'état

Sauter l'étape 4 est la principale source de dégâts.

## Couleurs de statut en dur

La mise en forme conditionnelle d'Excel n'est pas rendue par tous les visualiseurs, en particulier l'aperçu rapide de macOS. Un fichier qui s'affiche en noir et blanc chez le lecteur perd l'essentiel de son information visuelle. Les couleurs se posent donc en dur dans les cellules.

Palette par défaut, modifiable dans la configuration :

| Statut | Couleur de fond | Code |
|---|---|---|
| En cours | vert | `548235` |
| Prévu | bleu | `2E75B6` |
| Bloqué | rouge | `C00000` |
| Backlog | ocre | `BF8F00` |
| Terminé | gris | `A6A6A6` |
| Annulé | gris clair | `D9D9D9` |

Trois niveaux se combinent :

1. **Cellule de statut** : fond en couleur franche, texte blanc et gras
2. **Ligne entière** : teinte pastel de la même couleur, pour repérer le statut d'un coup d'œil sans lire la colonne
3. **Lignes closes** : projets terminés ou annulés en gris, texte grisé

Le script `scripts/appliquer_statut.py` calcule les pastels automatiquement et applique les trois niveaux :

```bash
python3 scripts/appliquer_statut.py "<fichier>" --onglet Projets
python3 scripts/appliquer_statut.py "<fichier>" --onglet Projets --lignes 8,65,69
```

Sans `--lignes`, il traite toutes les lignes de données de l'onglet.

## Formules et références de lignes

C'est le piège principal. Les onglets de synthèse référencent souvent des lignes précises de l'onglet des projets, par exemple `=Projets!F8`. Ces références ne sont pas des plages nommées, elles ne suivent pas les déplacements faits par un script.

Conséquences pratiques :

- **Insérer une ligne au milieu** de l'onglet des projets décale tout ce qui suit et fait pointer les formules de synthèse sur les mauvais projets. Si c'est inévitable, il faut décaler manuellement toutes les références concernées, puis vérifier.
- **Ajouter un projet sur la première ligne libre** avant la ligne de légende ne décale rien. C'est la façon sûre d'ajouter un projet.
- **La ligne de légende** en bas du tableau se déplace d'un cran à chaque ajout. Vérifie qu'elle est toujours sous le dernier projet, sinon un nouveau projet se retrouve visuellement hors tableau.
- **Supprimer une ligne** est à éviter. Un projet abandonné passe au statut annulé, il ne disparaît pas : l'historique de charge reste lisible.

Avant toute insertion, repère les formules qui pointent vers l'onglet des projets :

```python
import openpyxl
wb = openpyxl.load_workbook(chemin)  # sans data_only
for nom in wb.sheetnames:
    ws = wb[nom]
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value.startswith('=') and 'Projets' in c.value:
                print(nom, c.coordinate, c.value)
```

## Vérification par recalcul

Après modification, recalcule le classeur et compte les erreurs. LibreOffice en mode sans interface fait le travail :

```bash
soffice --headless --convert-to xlsx --outdir <dossier_sortie> <fichier>
```

puis relis le résultat avec `data_only=True` et compte les cellules contenant `#REF!`, `#VALUE!`, `#DIV/0!`, `#NAME?`, `#N/A`.

Le critère est binaire : zéro erreur, sinon on ne recopie pas.

Deux précautions issues de l'expérience :

- Exécute le recalcul sur une copie placée dans le disque local du bac à sable (`/tmp`), pas dans un dossier monté. LibreOffice bloque parfois sur les systèmes de fichiers montés.
- Compare aussi le **nombre total de formules** avant et après. Un nombre qui baisse sans raison signale des formules écrasées par des valeurs, ce qu'aucun test d'erreur ne détecte.

## Écriture dans l'onglet journal

Une ligne par question traitée, ajoutée en bas :

| Colonne | Contenu |
|---|---|
| Date | date du jour |
| Question | la question posée, telle que posée |
| Réponse | la réponse de l'utilisateur, résumée sans l'interpréter |
| Action prise | ce qui a été modifié dans le fichier, avec les valeurs |

La colonne « action prise » sert de piste d'audit. Elle doit permettre de reconstituer une modification sans rouvrir l'historique : « avancement porté de 50 à 90 %, 0,4 j ajoutés, total 1,15 j » plutôt que « mis à jour ».

Le journal du temps passé mérite sa propre ligne, même quand il ne déclenche aucun changement de statut.

## Écriture dans les fichiers de mémoire

Le fichier d'état se met à jour à chaque échange :

- État courant des projets touchés
- Une entrée datée dans les décisions et actions récentes, mentionnant la vérification des formules et la recopie
- Le journal du temps de la journée
- La liste des questions ouvertes, en retirant celles qui viennent d'être fermées

Le fichier d'index et de règles ne bouge que si une règle change, et dans ce cas la date de dernière mise à jour se corrige aussi.

Les questions ouvertes méritent une discipline particulière : une liste qui ne fait que grossir devient inutilisable. Retire les entrées traitées, fusionne les doublons, et marque explicitement les sujets mis en attente à la demande de l'utilisateur pour ne pas les relancer.

## Ajouter un nouveau projet

1. Repérer la première ligne libre avant la légende
2. Renseigner au minimum : identifiant, priorité, statut, domaine, libellé, dates prévues, jours estimés, prochaine étape
3. Écrire dans les notes l'origine de la demande et la date de création, c'est ce qui permettra de comprendre le projet dans trois mois
4. Déplacer la ligne de légende d'un cran
5. Vérifier qu'aucune référence des onglets de synthèse ne pointait sur l'ancienne ligne de légende
6. Recalculer, puis recopier

Quand un projet déjà réalisé est inscrit rétroactivement, il entre directement au statut terminé avec ses dates réelles, son avancement à 100 % et sa charge consignée. C'est légitime et utile : la charge du mois doit refléter le travail fait, pas seulement le travail planifié.

## Recopie vers le dossier source

Dernière étape, une fois la vérification passée. Selon les outils :

- Dossier connecté : outil d'écriture des fichiers du périphérique
- Sinon : `osascript` avec `do shell script "cp '<copie vérifiée>' '<chemin d'origine>'"`

Le fichier reprend exactement son nom et son emplacement d'origine. Pas de suffixe de version, pas de fichier parallèle : la source de vérité reste unique.
