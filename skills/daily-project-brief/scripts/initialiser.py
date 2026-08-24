#!/usr/bin/env python3
"""Creation d'un dossier de suivi pret a l'emploi.

Genere le classeur de suivi (onglets Projets, Suivi quotidien, Synthese hebdo),
les deux fichiers de memoire et un config.json renseigne. Tout est conforme a ce
que la competence attend, il n'y a plus qu'a saisir ses projets.

Usage:
    python3 initialiser.py "/chemin/vers/mon/dossier"
    python3 initialiser.py "/chemin/vers/mon/dossier" --nom "suivi-marketing.xlsx" --exemples
    python3 initialiser.py "/chemin/vers/mon/dossier" --responsable "Prenom Nom" --destinataire "COMEX"
"""

import argparse
import datetime as dt
import json
import os
import sys

try:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit("openpyxl requis : pip install openpyxl --break-system-packages")


COULEURS = {
    "1. En cours": "548235",
    "2. Prévu": "2E75B6",
    "3. Bloqué": "C00000",
    "4. Terminé": "A6A6A6",
    "5. Annulé": "D9D9D9",
    "6. Backlog": "BF8F00",
}

COLONNES = [
    ("ID", 6), ("Priorité", 10), ("Statut", 13), ("Catégorie", 14), ("Projet", 46),
    ("Début prévu", 12), ("Échéance", 12), ("Démarré le", 12), ("Terminé le", 12),
    ("Charge prévue (j)", 11), ("Temps passé (j)", 11), ("Écart (j)", 9), ("Avancement", 11),
    ("Prochaine étape", 42), ("Responsable", 20), ("Notes", 50),
]

# Explication de chaque colonne, reprise dans l'onglet Mode d'emploi
AIDE_COLONNES = [
    ("ID", "Un numéro unique par projet. Il ne change jamais, même si le projet est renommé."),
    ("Priorité", "Des étoiles : ⭐️ utile, ⭐️⭐️ important, ⭐️⭐️⭐️ prioritaire. Trois niveaux suffisent."),
    ("Statut", "À choisir dans la liste déroulante. La couleur se met à jour avec le statut."),
    ("Catégorie", "Le domaine ou le client concerné. Sert à regrouper, mettez ce qui vous parle."),
    ("Projet", "Le nom du projet, assez explicite pour être compris par quelqu'un d'autre."),
    ("Début prévu", "Quand le travail devrait commencer. Peut rester vide."),
    ("Échéance", "La date à laquelle le projet doit être terminé. C'est la colonne qui pilote le brief."),
    ("Démarré le", "La date où le travail a réellement commencé."),
    ("Terminé le", "La date de clôture réelle. À remplir au moment de passer le statut à Terminé."),
    ("Charge prévue (j)", "Le nombre de jours de travail estimé au départ."),
    ("Temps passé (j)", "Le temps réellement consacré, en jours. Voir l'explication ci-dessous."),
    ("Écart (j)", "Se calcule tout seul : temps passé moins charge prévue. Ne pas y toucher."),
    ("Avancement", "Un pourcentage, à l'estime. 0 %, 25 %, 50 %, 75 %, 90 %, 100 % suffisent."),
    ("Prochaine étape", "La toute prochaine action concrète, pas l'objectif final. Un projet sans prochaine étape est un projet à l'arrêt."),
    ("Responsable", "Qui porte le projet. Ajoutez les autres personnes impliquées si utile."),
    ("Notes", "L'origine de la demande, les décisions prises, le contexte. C'est ce qui permettra de comprendre le projet dans six mois."),
]

# Ordre des valeurs : ID, Priorite, Statut, Categorie, Projet, Debut prevu, Echeance,
# Demarre le, Termine le, Charge prevue, Temps passe, ECART (formule, laisser None),
# Avancement, Prochaine etape, Responsable, Notes
EXEMPLES = [
    (1, "⭐️⭐️⭐️", "1. En cours", "interne", "Exemple : projet prioritaire en cours",
     dt.date.today() - dt.timedelta(days=10), dt.date.today() + dt.timedelta(days=20),
     dt.date.today() - dt.timedelta(days=10), None, 8, 2.5, None, 0.4,
     "Décrire ici la toute prochaine action, pas l'objectif final",
     "Moi", "Origine de la demande, décisions prises, contexte utile dans six mois."),
    (2, "⭐️⭐️", "2. Prévu", "interne", "Exemple : projet planifié, pas encore démarré",
     dt.date.today() + dt.timedelta(days=7), dt.date.today() + dt.timedelta(days=30),
     None, None, 5, None, None, None, "Cadrer le périmètre avec les parties prenantes",
     "Moi", "Un projet prévu n'a ni date de démarrage ni temps passé, c'est normal."),
    (3, "⭐️", "3. Bloqué", "externe", "Exemple : projet en attente d'un tiers",
     dt.date.today() - dt.timedelta(days=20), dt.date.today() + dt.timedelta(days=5),
     dt.date.today() - dt.timedelta(days=20), None, 3, 1, None, 0.5,
     "Relancer le prestataire, sans réponse depuis deux semaines",
     "Moi", "Noter ici la cause du blocage et son impact, c'est ce qui remonte en réunion."),
]

LEGENDE = ("Légende : ligne verte = en cours, rouge = bloqué, bleue = prévu, grise = terminé ou annulé, "
           "ocre = backlog. À compléter au fil de l'eau : dates réelles, jours réels, avancement, "
           "prochaine étape. La colonne Écart se calcule seule. Ajouter un projet sur la première ligne "
           "libre au-dessus de cette légende.")

FIN = Side(style="thin", color="BFBFBF")
BORDURE = Border(left=FIN, right=FIN, top=FIN, bottom=FIN)


def pastel(hexa, force=0.86):
    r, g, b = int(hexa[0:2], 16), int(hexa[2:4], 16), int(hexa[4:6], 16)
    m = lambda c: int(c + (255 - c) * force)
    return f"{m(r):02X}{m(g):02X}{m(b):02X}"


def styler_entete(ws, ligne, nb_colonnes, couleur="1F3864"):
    for c in range(1, nb_colonnes + 1):
        cel = ws.cell(row=ligne, column=c)
        cel.fill = PatternFill("solid", fgColor=couleur)
        cel.font = Font(bold=True, color="FFFFFF", size=10)
        cel.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cel.border = BORDURE
    ws.row_dimensions[ligne].height = 30


def creer_onglet_projets(wb, avec_exemples):
    ws = wb.active
    ws.title = "Projets"

    ws["A1"] = "SUIVI DE PROJETS — base de données"
    ws["A1"].font = Font(bold=True, size=14, color="1F3864")
    ws.row_dimensions[1].height = 22

    for i, (titre, largeur) in enumerate(COLONNES, start=1):
        ws.cell(row=2, column=i).value = titre
        ws.column_dimensions[get_column_letter(i)].width = largeur
    styler_entete(ws, 2, len(COLONNES))
    ws.freeze_panes = "A3"

    lignes = EXEMPLES if avec_exemples else []
    for i, donnees in enumerate(lignes):
        r = 3 + i
        for c, valeur in enumerate(donnees, start=1):
            if c == 12:      # colonne Ecart : formule posee juste apres
                continue
            cel = ws.cell(row=r, column=c)
            cel.value = valeur
            cel.border = BORDURE
            cel.alignment = Alignment(vertical="top", wrap_text=c in (5, 14, 16))
            if c in (6, 7, 8, 9):
                cel.number_format = "dd/mm/yyyy"
            if c == 13:
                cel.number_format = "0%"
        ws.cell(row=r, column=12).value = (
            f'=IF(AND(ISNUMBER(J{r}),ISNUMBER(K{r})),K{r}-J{r},"")')
        ws.row_dimensions[r].height = 30

        statut = donnees[2]
        franc = COULEURS.get(statut, "A6A6A6")
        clair = pastel(franc)
        for c in range(1, len(COLONNES) + 1):
            ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor=clair)
        cs = ws.cell(row=r, column=3)
        cs.fill = PatternFill("solid", fgColor=franc)
        cs.font = Font(bold=True, color="FFFFFF", size=10)

    # zone libre puis legende
    premiere_libre = 3 + len(lignes)
    for r in range(premiere_libre, premiere_libre + 20):
        for c in range(1, len(COLONNES) + 1):
            cel = ws.cell(row=r, column=c)
            cel.border = BORDURE
            if c in (6, 7, 8, 9):
                cel.number_format = "dd/mm/yyyy"
            if c == 13:
                cel.number_format = "0%"
        ws.cell(row=r, column=12).value = (
            f'=IF(AND(ISNUMBER(J{r}),ISNUMBER(K{r})),K{r}-J{r},"")')

    r_legende = premiere_libre + 21
    ws.cell(row=r_legende, column=1).value = LEGENDE
    ws.merge_cells(start_row=r_legende, start_column=1, end_row=r_legende, end_column=len(COLONNES))
    cel = ws.cell(row=r_legende, column=1)
    cel.font = Font(italic=True, size=9, color="595959")
    cel.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[r_legende].height = 28

    # liste deroulante des statuts
    from openpyxl.worksheet.datavalidation import DataValidation
    dv = DataValidation(type="list", formula1='"' + ",".join(COULEURS) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"C3:C{r_legende - 1}")
    return ws


def creer_onglet_mode_emploi(wb, fichier, responsable):
    """Premiere page du classeur : tout ce qu'il faut savoir sans lire de documentation."""
    ws = wb.create_sheet("Mode d'emploi", 0)
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 74

    ligne = 2

    def bloc_titre(texte):
        nonlocal ligne
        ws.cell(row=ligne, column=2).value = texte
        for c in (2, 3):
            ws.cell(row=ligne, column=c).fill = PatternFill("solid", fgColor="1F3864")
            ws.cell(row=ligne, column=c).font = Font(bold=True, size=11, color="FFFFFF")
        ws.row_dimensions[ligne].height = 22
        ligne += 2

    def paragraphe(texte, gras=False, couleur="000000"):
        nonlocal ligne
        cel = ws.cell(row=ligne, column=2)
        cel.value = texte
        ws.merge_cells(start_row=ligne, start_column=2, end_row=ligne, end_column=3)
        cel.font = Font(bold=gras, size=10, color=couleur)
        cel.alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[ligne].height = max(15, 15 * (len(texte) // 88 + 1))
        ligne += 1

    def paire(gauche, droite, couleur_gauche="1F3864"):
        nonlocal ligne
        g = ws.cell(row=ligne, column=2)
        g.value = gauche
        g.font = Font(bold=True, size=10, color=couleur_gauche)
        g.alignment = Alignment(vertical="top", wrap_text=True)
        d = ws.cell(row=ligne, column=3)
        d.value = droite
        d.font = Font(size=10)
        d.alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[ligne].height = max(15, 14 * (len(droite) // 82 + 1))
        ligne += 1

    ws.cell(row=1, column=2).value = "MODE D'EMPLOI"
    ws.cell(row=1, column=2).font = Font(bold=True, size=18, color="1F3864")
    ws.row_dimensions[1].height = 26
    ligne = 3

    paragraphe(f"Ce classeur est le tableau de bord de vos projets. Il est prévu pour être lu et complété "
               f"chaque jour, en quelques minutes, et pour servir de base à un point régulier avec votre "
               f"direction. Responsable : {responsable}.", couleur="595959")
    ligne += 1

    bloc_titre("EN TROIS MINUTES")
    paire("1. Vos projets", "Ouvrez l'onglet « Projets » et saisissez une ligne par projet. Seules quatre "
                            "colonnes comptent vraiment au départ : le nom, le statut, l'échéance et la prochaine étape.")
    paire("2. Chaque matin", "Demandez à votre assistant « fais-moi mon brief projets du jour ». Il lit ce "
                             "fichier et vous rend les priorités, puis vous pose deux ou trois questions.")
    paire("3. Vous répondez", "Vos réponses sont reportées ici automatiquement : avancement, temps passé, "
                              "statuts, prochaines étapes. Vous n'avez pas à tenir le fichier à la main.")
    ligne += 1

    bloc_titre("LES ONGLETS")
    paire("Projets", "La liste de tous vos projets. C'est le cœur du fichier, tout le reste en découle.")
    paire("Suivi quotidien", "L'historique des questions posées et de vos réponses. Utile pour retrouver "
                             "quand une décision a été prise, et pourquoi.")
    paire("Synthèse hebdo", "La page à présenter en réunion. Les projets prioritaires y remontent tout seuls "
                            "depuis l'onglet Projets, vous ne rédigez que les commentaires et les points d'arbitrage.")
    ligne += 1

    bloc_titre("LES COLONNES DE L'ONGLET PROJETS")
    for nom, aide in AIDE_COLONNES:
        paire(nom, aide)
    ligne += 1

    bloc_titre("LES STATUTS ET LEURS COULEURS")
    for statut, couleur in COULEURS.items():
        cel = ws.cell(row=ligne, column=2)
        cel.value = statut
        cel.fill = PatternFill("solid", fgColor=couleur)
        cel.font = Font(bold=True, size=10, color="FFFFFF")
        cel.alignment = Alignment(horizontal="center")
        explications = {
            "1. En cours": "Le travail a commencé et avance.",
            "2. Prévu": "Décidé et planifié, mais pas encore démarré.",
            "3. Bloqué": "À l'arrêt pour une raison extérieure : attente d'un tiers, d'une décision, d'un budget.",
            "4. Terminé": "Livré et clôturé. La ligne passe en gris, elle sort des priorités du jour.",
            "5. Annulé": "Abandonné. On ne supprime pas la ligne, l'historique reste lisible.",
            "6. Backlog": "Idée notée, pas encore arbitrée. Sans date ni charge tant qu'elle n'est pas décidée.",
        }
        d = ws.cell(row=ligne, column=3)
        d.value = explications.get(statut, "")
        d.font = Font(size=10)
        d.alignment = Alignment(vertical="center", wrap_text=True)
        ligne += 1
    ligne += 1
    paragraphe("Les couleurs sont posées directement dans les cellules plutôt que par mise en forme "
               "conditionnelle : beaucoup d'aperçus rapides et de visionneuses mobiles n'affichent pas "
               "la mise en forme conditionnelle, et le fichier arriverait en noir et blanc chez votre lecteur.",
               couleur="595959")
    ligne += 1

    bloc_titre("COMPTER LE TEMPS PASSÉ")
    paragraphe("Un jour inscrit dans « Temps passé » est une unité de charge, pas une journée de calendrier. "
               "Si vous avancez sur trois projets dans la même journée, vous pouvez inscrire 0,4 jour sur "
               "chacun : le total du jour dépassera 1, et c'est normal.", gras=False)
    ligne += 1
    paire("Repères usuels", "30 min = 0,07 j  |  1 h = 0,13 j  |  1 h 30 = 0,2 j  |  2 h = 0,27 j  |  "
                            "3 h = 0,4 j  |  une demi-journée = 0,5 j   (base 7,5 h par jour)")
    paragraphe("Le temps s'ajoute au cumul existant, il ne le remplace pas. C'est cette colonne qui permet "
               "de justifier une charge et de construire un rétroplanning crédible.", couleur="595959")
    ligne += 1

    bloc_titre("DEUX PRÉCAUTIONS")
    paire("Ajouter un projet", "Utilisez la première ligne vide au-dessus de la légende. Évitez d'insérer une "
                               "ligne au milieu du tableau : l'onglet Synthèse hebdo pointe vers des numéros de "
                               "lignes précis, une insertion décale ses formules.", "C00000")
    paire("Supprimer un projet", "Ne supprimez pas la ligne, passez le statut à « 5. Annulé ». Vous gardez "
                                 "l'historique et le temps déjà consigné.", "C00000")

    return ws


def creer_onglet_journal(wb):
    ws = wb.create_sheet("Suivi quotidien")
    ws["A1"] = "SUIVI QUOTIDIEN — historique des points"
    ws["A1"].font = Font(bold=True, size=14, color="1F3864")
    ws["A2"] = ("Une ligne par question traitée. La colonne « action prise » sert de piste d'audit : "
                "elle doit permettre de reconstituer une modification sans rouvrir l'historique.")
    ws["A2"].font = Font(italic=True, size=9, color="595959")

    entetes = ["Date", "Question", "Réponse", "Action prise"]
    largeurs = [12, 55, 55, 65]
    for i, (t, l) in enumerate(zip(entetes, largeurs), start=1):
        ws.cell(row=4, column=i).value = t
        ws.column_dimensions[get_column_letter(i)].width = l
    styler_entete(ws, 4, len(entetes))
    ws.freeze_panes = "A5"
    for r in range(5, 25):
        ws.cell(row=r, column=1).number_format = "dd/mm/yyyy"
        for c in range(1, 5):
            ws.cell(row=r, column=c).alignment = Alignment(vertical="top", wrap_text=True)
            ws.cell(row=r, column=c).border = BORDURE
    return ws


def creer_onglet_synthese(wb, responsable, destinataire, ligne_legende):
    ws = wb.create_sheet("Synthèse hebdo")
    ws.column_dimensions["A"].width = 48
    for col in "BCDE":
        ws.column_dimensions[col].width = 24

    ws["A1"] = f"SYNTHÈSE HEBDOMADAIRE — {destinataire}"
    ws["A1"].font = Font(bold=True, size=14, color="1F3864")
    ws["A2"], ws["B2"] = "Semaine du :", dt.date.today()
    ws["B2"].number_format = "dd/mm/yyyy"
    ws["C2"] = f"Responsable : {responsable}"

    ligne = 4
    def titre(texte):
        nonlocal ligne
        ws.cell(row=ligne, column=1).value = texte
        ws.cell(row=ligne, column=1).font = Font(bold=True, size=11, color="FFFFFF")
        for c in range(1, 6):
            ws.cell(row=ligne, column=c).fill = PatternFill("solid", fgColor="2E75B6")
        ligne += 1

    titre("1. STATUT GLOBAL")
    ws.cell(row=ligne, column=1).value = "Statut :"
    ws.cell(row=ligne, column=2).value = "🟢 / 🟠 / 🔴"
    ligne += 1
    ws.cell(row=ligne, column=1).value = "Commentaire (3 lignes maximum) :"
    ligne += 2

    titre("2. INDICATEURS CLÉS")
    for i, t in enumerate(["Indicateur", "Valeur", "Objectif", "Écart", "Action si écart"], start=1):
        ws.cell(row=ligne, column=i).value = t
    styler_entete(ws, ligne, 5, "8EA9DB")
    ligne += 5

    titre("3. PROJETS EN COURS PRIORITAIRES")
    for i, t in enumerate(["Projet", "Statut", "Fin prévue", "Prochaine étape", "Avancement"], start=1):
        ws.cell(row=ligne, column=i).value = t
    styler_entete(ws, ligne, 5, "8EA9DB")
    ligne += 1
    depart = ligne
    for k in range(6):
        r_src = 3 + k
        for col, lettre in zip(range(1, 6), ["E", "C", "G", "N", "M"]):
            ws.cell(row=ligne, column=col).value = f'=IF(Projets!A{r_src}="","",Projets!{lettre}{r_src})'
        ws.cell(row=ligne, column=3).number_format = "dd/mm/yyyy"
        ws.cell(row=ligne, column=5).number_format = "0%"
        ligne += 1
    ws.cell(row=ligne, column=1).value = (
        f"Lignes {depart} à {ligne - 1} reprises automatiquement de l'onglet Projets, ne pas saisir à la main. "
        f"Ces formules pointent vers des lignes fixes : toute insertion de ligne dans l'onglet Projets impose de les décaler.")
    ws.cell(row=ligne, column=1).font = Font(italic=True, size=9, color="C00000")
    ligne += 2

    titre("4. POINTS D'ALERTE ET ARBITRAGES")
    for i, t in enumerate(["Risque identifié", "Décision attendue", "Impact si non-décision", "Projet lié"], start=1):
        ws.cell(row=ligne, column=i).value = t
    styler_entete(ws, ligne, 4, "8EA9DB")
    ligne += 5

    titre("5. ACTIONS DE LA SEMAINE")
    for k in range(1, 6):
        ws.cell(row=ligne, column=1).value = f"{k}."
        ligne += 1
    return ws


MEMORY_MODELE = """# MEMORY — Suivi de projets

Mémoire de travail du brief quotidien. Responsable du périmètre : {responsable}.
{phrase_reporting}

## Fichiers

- `MEMORY.md` : ce fichier, index et règles de travail.
- `etat-projets.md` : état courant des projets, décisions, questions ouvertes.
- `consigne_*.md` : consignes de travail données au fil du temps, une par fichier.
- `{fichier}` : base de données de référence (onglets Projets, Suivi quotidien, Synthèse hebdo).

## Règles de travail

1. Langue : {langue}, concis.
2. Couleurs de statut appliquées en dur dans les cellules, la mise en forme conditionnelle n'est pas rendue par tous les visualiseurs.
3. Les formules de l'onglet Synthèse hebdo référencent des lignes fixes de l'onglet Projets. Toute insertion de ligne impose de décaler ces références, puis de vérifier par recalcul (zéro erreur exigé). Un nouveau projet s'ajoute sur la première ligne libre avant la légende, sans décalage.
4. Ne jamais modifier les autres fichiers du dossier sauf demande explicite.
5. Ne modifier le fichier de suivi que sur réponse ou demande explicite.
6. Colonne Jours réels : un jour consigné est une unité de charge, pas une journée calendaire. La somme sur une même date peut dépasser 1 quand plusieurs projets avancent en parallèle.
7. Diffusion du brief : {diffusion}.
{regle_partage}
Dernière mise à jour : {date}
"""

ETAT_MODELE = """# État des projets

Fichier d'état courant, mis à jour à chaque échange.

## Projets actifs

À compléter au premier brief.

## Objectifs du jour

À compléter au premier brief.

## Décisions et actions récentes

## Journal de bord du temps (justification / rétroplanning)

- Règle : le brief demande chaque jour les projets travaillés la veille et le temps passé, consignés dans le Suivi quotidien et dans la colonne Jours réels.

## Questions ouvertes (en attente de réponse)

## Événements à venir

Dernière mise à jour : {date}
"""


def main():
    ap = argparse.ArgumentParser(description="Initialisation d'un dossier de suivi de projets")
    ap.add_argument("dossier")
    ap.add_argument("--nom", default="suivi-projets.xlsx")
    ap.add_argument("--responsable", default="à compléter")
    ap.add_argument("--destinataire", default="direction")
    ap.add_argument("--langue", default="français")
    ap.add_argument("--exemples", action="store_true", help="inclure 3 projets d'exemple")
    ap.add_argument("--partage", action="store_true", help="dossier partagé avec la direction")
    ap.add_argument("--force", action="store_true", help="écraser des fichiers existants")
    args = ap.parse_args()

    os.makedirs(args.dossier, exist_ok=True)
    chemin_xlsx = os.path.join(args.dossier, args.nom)

    existants = [f for f in (chemin_xlsx,
                             os.path.join(args.dossier, "MEMORY.md"),
                             os.path.join(args.dossier, "etat-projets.md"),
                             os.path.join(args.dossier, "config.json"))
                 if os.path.exists(f)]
    if existants and not args.force:
        sys.exit("fichiers déjà présents, rien n'a été touché :\n  " +
                 "\n  ".join(existants) + "\nUtiliser --force pour écraser.")

    wb = openpyxl.Workbook()
    ws = creer_onglet_projets(wb, args.exemples)
    creer_onglet_journal(wb)
    creer_onglet_synthese(wb, args.responsable, args.destinataire, ws.max_row)
    creer_onglet_mode_emploi(wb, args.nom, args.responsable)

    # mise en page : paysage, ajuste a une page de large, en-tetes repetes
    for feuille in wb.worksheets:
        feuille.page_setup.orientation = "landscape"
        feuille.page_setup.paperSize = feuille.PAPERSIZE_A4
        feuille.sheet_properties.pageSetUpPr.fitToPage = True
        feuille.page_setup.fitToWidth = 1
        feuille.page_setup.fitToHeight = 0
        feuille.page_margins.left = feuille.page_margins.right = 0.4
        feuille.page_margins.top = feuille.page_margins.bottom = 0.5
    wb["Projets"].print_title_rows = "1:2"
    wb["Suivi quotidien"].print_title_rows = "1:4"

    wb.active = 0
    wb.save(chemin_xlsx)

    aujourdhui = dt.date.today().isoformat()
    regle_partage = ("8. Dossier partagé : contenu strictement factuel et professionnel, "
                     "aucune appréciation sur les personnes.\n" if args.partage else "")
    phrase_reporting = (f"Reporting {args.destinataire}." if args.destinataire else "")

    with open(os.path.join(args.dossier, "MEMORY.md"), "w", encoding="utf-8") as f:
        f.write(MEMORY_MODELE.format(
            responsable=args.responsable, fichier=args.nom, langue=args.langue,
            diffusion="affichage complet dans la conversation",
            phrase_reporting=phrase_reporting, regle_partage=regle_partage, date=aujourdhui))

    with open(os.path.join(args.dossier, "etat-projets.md"), "w", encoding="utf-8") as f:
        f.write(ETAT_MODELE.format(date=aujourdhui))

    config = {
        "dossier_travail": os.path.abspath(args.dossier),
        "fichier_suivi": args.nom,
        "onglets": {"projets": "Projets", "journal": "Suivi quotidien", "dashboard": "Synthèse hebdo"},
        "memoire": {"index": "MEMORY.md", "etat": "etat-projets.md", "consignes": "consigne_*.md"},
        "diffusion": ["conversation"],
        "email_destinataire": None,
        "langue": args.langue,
        "base_journee_heures": 7.5,
        "horizon_echeance_jours": 7,
        "dossier_partage": args.partage,
        "reporting": {"destinataire": args.destinataire, "frequence": "hebdomadaire"},
        "fichiers_interdits": ["Archives*.xlsx", "*.pptx"],
    }
    with open(os.path.join(args.dossier, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print("Dossier de suivi initialisé :", os.path.abspath(args.dossier))
    for nom in (args.nom, "MEMORY.md", "etat-projets.md", "config.json"):
        print("  -", nom)
    print("\nProchaine étape : saisir ses projets dans l'onglet Projets,")
    print("puis demander « fais-moi mon brief projets du jour ».")


if __name__ == "__main__":
    main()
