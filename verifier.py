#!/usr/bin/env python3
"""Verifie le depot avant publication.

`claude plugin validate` controle la syntaxe des manifestes, mais il n'ouvre pas
les SKILL.md depuis la racine du marketplace et ne verifie pas les contraintes
de l'installateur. Ce script complete : longueur des descriptions, coherence
entre le manifeste et les dossiers, format des noms.

Usage:
    python3 verifier.py
"""

import json
import pathlib
import re
import sys

LIMITE_DESCRIPTION = 1024
LIMITE_NOM = 64
RACINE = pathlib.Path(__file__).parent

erreurs, avertissements = [], []


def frontmatter(chemin):
    texte = chemin.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", texte, re.S)
    if not m:
        return None
    bloc = m.group(1)
    champs = {}
    for cle in ("name", "description"):
        # bloc litteral avec | ou >, teste en premier
        multi = re.search(rf"^{cle}:\s*[|>][-+]?\s*\n((?:[ \t]+.*\n?)+)", bloc, re.M)
        if multi:
            champs[cle] = " ".join(l.strip() for l in multi.group(1).strip().split("\n"))
            continue
        # valeur sur une seule ligne
        simple = re.search(rf"^{cle}:[ \t]*(?![|>]\s*$)(.+)$", bloc, re.M)
        if simple:
            champs[cle] = simple.group(1).strip().strip('"\'')
    return champs


def verifier_skill(dossier):
    nom_dossier = dossier.name
    fichier = dossier / "SKILL.md"

    if not fichier.exists():
        erreurs.append(f"{nom_dossier} : SKILL.md manquant")
        return None

    champs = frontmatter(fichier)
    if champs is None:
        erreurs.append(f"{nom_dossier} : frontmatter YAML absent ou mal ferme")
        return None

    nom = champs.get("name")
    description = champs.get("description")

    if not nom:
        erreurs.append(f"{nom_dossier} : champ 'name' absent du frontmatter")
    else:
        if nom != nom_dossier:
            erreurs.append(f"{nom_dossier} : 'name' vaut '{nom}', il doit valoir '{nom_dossier}'")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", nom):
            erreurs.append(f"{nom_dossier} : 'name' doit etre en kebab-case minuscule")
        if len(nom) > LIMITE_NOM:
            erreurs.append(f"{nom_dossier} : 'name' depasse {LIMITE_NOM} caracteres")

    if not description:
        erreurs.append(f"{nom_dossier} : champ 'description' absent du frontmatter")
    else:
        n = len(description)
        if n > LIMITE_DESCRIPTION:
            erreurs.append(f"{nom_dossier} : description de {n} caracteres, "
                           f"maximum {LIMITE_DESCRIPTION}, retirer {n - LIMITE_DESCRIPTION}")
        elif n > LIMITE_DESCRIPTION * 0.9:
            avertissements.append(f"{nom_dossier} : description a {n} caracteres, "
                                  f"proche de la limite de {LIMITE_DESCRIPTION}")
        if n < 60:
            avertissements.append(f"{nom_dossier} : description tres courte ({n} caracteres), "
                                  f"le declenchement risque d'etre peu fiable")

    for script in (dossier / "scripts").glob("*.py"):
        try:
            compile(script.read_text(encoding="utf-8"), str(script), "exec")
        except SyntaxError as e:
            erreurs.append(f"{nom_dossier} : erreur de syntaxe dans {script.name} ligne {e.lineno}")

    return nom


def main():
    manifeste = RACINE / ".claude-plugin" / "marketplace.json"
    if not manifeste.exists():
        erreurs.append(".claude-plugin/marketplace.json absent, le depot ne sera pas installable")
        declarees = set()
    else:
        try:
            donnees = json.loads(manifeste.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            erreurs.append(f"marketplace.json illisible : {e}")
            donnees = {"plugins": []}

        declarees = set()
        for entree in donnees.get("plugins", []):
            nom = entree.get("name", "?")
            declarees.add(nom)
            if "version" not in entree:
                avertissements.append(f"{nom} : pas de champ 'version', "
                                      f"les mises a jour ne seront pas propagees")
            for chemin in entree.get("skills", []):
                if not (RACINE / chemin.lstrip("./")).is_dir():
                    erreurs.append(f"{nom} : le chemin declare '{chemin}' n'existe pas")
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", nom):
                erreurs.append(f"{nom} : nom de plugin a mettre en kebab-case")

    dossiers = sorted(d for d in (RACINE / "skills").iterdir() if d.is_dir()) \
        if (RACINE / "skills").is_dir() else []

    presents = set()
    print(f"{len(dossiers)} skill(s) dans skills/\n")
    for dossier in dossiers:
        nom = verifier_skill(dossier)
        if nom:
            presents.add(nom)
        champs = frontmatter(dossier / "SKILL.md") if (dossier / "SKILL.md").exists() else None
        taille = len(champs.get("description", "")) if champs else 0
        etat = "ok" if taille and taille <= LIMITE_DESCRIPTION else "a corriger"
        print(f"  {dossier.name:26} description {taille:>5} car.  {etat}")

    for orphelin in presents - declarees:
        avertissements.append(f"{orphelin} : present dans skills/ mais absent du manifeste, "
                              f"personne ne pourra l'installer")
    for fantome in declarees - presents:
        erreurs.append(f"{fantome} : declare au manifeste mais absent de skills/")

    print()
    if avertissements:
        print(f"AVERTISSEMENTS ({len(avertissements)})")
        for a in avertissements:
            print(f"  - {a}")
        print()
    if erreurs:
        print(f"ERREURS ({len(erreurs)})")
        for e in erreurs:
            print(f"  - {e}")
        print("\nCorrigez avant de pousser.")
        sys.exit(1)

    print("Tout est conforme. Pensez a lancer aussi :")
    print("  claude plugin validate .")
    print("  claude plugin validate ./skills")


if __name__ == "__main__":
    main()
