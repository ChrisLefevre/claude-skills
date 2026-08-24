# Configuration

La compétence s'adapte à un fichier de suivi existant plutôt que d'en imposer un. Cette fiche décrit ce qu'elle attend, ce qu'elle sait deviner, et ce qu'il faut lui dire.

## Où mettre la configuration

Trois emplacements possibles, par ordre de priorité :

1. Un fichier `config.json` placé à la racine de la compétence
2. Le texte de la tâche planifiée qui déclenche le brief (chemins et règles écrits en clair)
3. La conversation, si l'utilisateur donne les informations à la volée

Au premier usage, si rien n'est configuré, pose les questions manquantes en une seule fois plutôt qu'au fil de l'eau, puis propose d'enregistrer un `config.json` pour éviter de recommencer.

## Modèle de configuration

```json
{
  "dossier_travail": "/chemin/vers/le/dossier",
  "fichier_suivi": "suivi-projets.xlsx",
  "onglets": {
    "projets": "Projets",
    "journal": "Suivi quotidien",
    "dashboard": "Synthèse hebdo"
  },
  "memoire": {
    "index": "MEMORY.md",
    "etat": "etat-projets.md",
    "consignes": "consigne_*.md"
  },
  "diffusion": ["conversation"],
  "email_destinataire": null,
  "langue": "français",
  "style": "concis, pas de tiret cadratin, virgule à la place",
  "base_journee_heures": 7.5,
  "horizon_echeance_jours": 7,
  "dossier_partage": true,
  "reporting": {
    "destinataire": "direction",
    "frequence": "hebdomadaire"
  },
  "fichiers_interdits": [
    "Archives*.xlsx",
    "*.pptx"
  ]
}
```

Aucun de ces champs n'est obligatoire au sens strict, mais `dossier_travail` et `fichier_suivi` sont nécessaires pour travailler.

## Structure attendue du fichier de suivi

### Onglet des projets

Une ligne d'en-tête, puis une ligne par projet. Le script de lecture reconnaît les colonnes par leur intitulé, avec plusieurs variantes acceptées :

| Rôle | Intitulés reconnus |
|---|---|
| Identifiant | ID, N°, Numéro, Ref |
| Priorité | Priorité, Priority, Importance |
| Statut | Statut, Status, État |
| Domaine | Domaine, Catégorie, Axe |
| Libellé | Projet, Intitulé, Nom, Tâche |
| Début prévu | Début prévu, Date début, Start |
| Fin prévue | Fin prévue, Échéance, Deadline, Date fin |
| Début réel | Début réel |
| Fin réelle | Fin réelle |
| Jours estimés | Jours estimés, Charge estimée, Estimé |
| Jours réels | Jours réels, Charge réelle, Réalisé |
| Avancement | Avancement, Progression, % |
| Prochaine étape | Prochaine étape, Next step, Action |
| Responsable | Team, Responsable, Owner, Assigné |
| Notes | Notes, Détails, Commentaires |

Si une colonne porte un intitulé inconnu, indique la correspondance dans `config.json` sous une clé `colonnes`, par exemple `{"colonnes": {"fin_prevue": "Butoir"}}`.

### Statuts

Le script classe les statuts par leur premier mot-clé reconnu, quel que soit le préfixe numérique. Les familles sont : en cours, prévu, bloqué, terminé, annulé, backlog. Un statut « 3. Bloqué » et un statut « Bloqué » sont traités de la même façon.

Les projets terminés et annulés sont exclus de l'analyse quotidienne, mais restent lisibles avec l'option `--tous`.

### Onglet journal quotidien

Quatre colonnes : date, question, réponse, action prise. Les entrées s'ajoutent à la suite, la plus récente en bas. Cet onglet est la mémoire courte de la boucle : c'est lui qu'on relit pour éviter de reposer une question.

### Onglet tableau de bord

Facultatif. S'il existe, il agrège des indicateurs et des points d'arbitrage pour un comité. Il contient souvent des formules qui pointent vers des lignes précises de l'onglet des projets, ce qui a des conséquences détaillées dans `mise-a-jour-fichier.md`.

## Fichiers de mémoire

Trois rôles distincts, qu'il vaut mieux ne pas mélanger :

- **Index et règles** (`MEMORY.md`) : liste des fichiers, conventions, règles de travail posées par l'utilisateur. Il change rarement, et seulement quand une règle évolue.
- **État courant** (`etat-projets.md`) : projets en cours, décisions récentes datées, journal du temps, questions ouvertes, événements à venir. Il change à chaque échange.
- **Consignes** (`consigne_*.md`) : instructions ponctuelles données par l'utilisateur sur la façon de travailler. Une consigne par fichier, on n'y touche pas.

Si ces fichiers n'existent pas encore, propose de les créer au premier usage plutôt que de les créer d'office.

## Accès au fichier depuis un environnement séparé

L'analyse tourne souvent dans un bac à sable qui ne voit pas le disque de l'utilisateur. Deux voies :

**Dossier connecté à la session.** Utilise l'outil de mise à disposition des fichiers du périphérique pour rapatrier le fichier, et son équivalent en écriture pour le renvoyer.

**Pas de dossier connecté.** Passe par une commande shell sur la machine de l'utilisateur :

```
osascript : do shell script "cp '<source>' '<dossier de sortie de la session>'"
```

puis, après modification, la commande inverse. Les chemins contenant des espaces se protègent par des guillemets simples à l'intérieur de la chaîne AppleScript.

Attention : le chemin d'un fichier vu par les outils de lecture de fichiers et son chemin vu par le shell du bac à sable peuvent différer. Vérifie la correspondance avant de conclure qu'un fichier est absent.

## Exemple commenté

Configuration type pour un responsable de périmètre qui présente un point hebdomadaire à sa direction :

```json
{
  "dossier_travail": "/chemin/vers/le/dossier/de/suivi/",
  "fichier_suivi": "suivi-projets.xlsx",
  "onglets": {
    "projets": "Projets",
    "journal": "Suivi quotidien",
    "dashboard": "Synthèse hebdo"
  },
  "memoire": {
    "index": "MEMORY.md",
    "etat": "etat-projets.md",
    "consignes": "consigne_*.md"
  },
  "diffusion": ["conversation"],
  "langue": "français",
  "style": "concis, pas de tiret cadratin",
  "base_journee_heures": 7.5,
  "horizon_echeance_jours": 7,
  "dossier_partage": true,
  "reporting": {"destinataire": "direction", "frequence": "hebdomadaire"},
  "fichiers_interdits": ["suivi-projets-ancien.xlsx", "Archives*.xlsx", "*.pptx", "Annexe*.docx"]
}
```

Deux détails de cet exemple méritent l'attention, parce qu'ils reviennent souvent :

- `dossier_partage` à `true` contraint le style de tout ce qui est écrit dans la mémoire. Voir la section correspondante du SKILL.md.
- La liste `fichiers_interdits` mentionne explicitement une version antérieure du fichier de suivi. Quand deux fichiers portent des noms proches, désigner l'ancien évite de le modifier par erreur. C'est le garde-fou le plus utile de la configuration.
