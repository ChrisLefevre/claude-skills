# claude-skills

Collection de skills pour Claude. Chacun s'installe séparément, prenez ce qui vous sert.

*A collection of Claude skills, each installable on its own. Documentation is in French, but the skills answer in whatever language you write to them.*

## Les skills

| Skill | À quoi ça sert |
|---|---|
| [**daily-project-brief**](skills/daily-project-brief) | Un point projets chaque matin. Lit votre tableur de suivi, vous donne les priorités du jour avec leur justification, vous demande le temps passé la veille, puis reporte vos réponses dans le fichier. |

## Installation

### Dans Claude Code

Ajoutez le dépôt une seule fois :

```
/plugin marketplace add ChrisLefevre/claude-skills
```

Puis installez ce qui vous intéresse :

```
/plugin install daily-project-brief@claude-skills
```

Si l'installation indique `Run /reload-plugins to activate`, lancez cette commande.

### Dans Claude Cowork ou sur claude.ai

Menu **Customize**, onglet **Plugins**, section **Personal plugins**, bouton **+**, puis **Add marketplace**. Collez l'adresse du dépôt. Les skills disponibles s'affichent, cliquez **Install** sur ceux que vous voulez.

### Mise à jour

Vous ne recevez une nouvelle version que lorsque le numéro de version du skill change dans le manifeste. Réinstaller un skill récupère la dernière version publiée.

## Structure du dépôt

```
.
├── .claude-plugin/
│   └── marketplace.json         manifeste : c'est lui qui rend le dépôt installable
├── skills/
│   └── daily-project-brief/     un dossier par skill
│       ├── SKILL.md
│       ├── README.md
│       ├── references/
│       └── scripts/
├── README.md
└── LICENSE
```

Chaque skill est autonome : son `SKILL.md`, sa documentation et ses scripts vivent dans son dossier. Le manifeste à la racine déclare une entrée par skill, ce qui permet de les installer indépendamment.

## Ajouter un skill

1. Créez `skills/mon-nouveau-skill/` avec au minimum un `SKILL.md` contenant un `name` et une `description` en frontmatter.
2. Ajoutez une entrée dans `.claude-plugin/marketplace.json` :

```json
{
  "name": "mon-nouveau-skill",
  "source": "./",
  "skills": ["./skills/mon-nouveau-skill"],
  "strict": false,
  "version": "1.0.0",
  "description": "Ce que fait le skill, et quand Claude doit le déclencher."
}
```

Le champ `skills` est ce qui isole chaque entrée : sans lui, toutes les entrées chargeraient l'ensemble du dossier `skills/`.

3. Ajoutez une ligne au tableau en haut de ce README.
4. Validez avant de pousser :

```bash
claude plugin validate .          # le manifeste
claude plugin validate ./skills   # le contenu des skills
```

Les deux doivent afficher `Validation passed`.

## Publier une mise à jour

Incrémentez `version` dans l'entrée concernée du manifeste, sinon personne ne reçoit la modification. Validez, puis poussez.

## Licence

MIT, voir [LICENSE](LICENSE).
