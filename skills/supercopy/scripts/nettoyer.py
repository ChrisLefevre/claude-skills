#!/usr/bin/env python3
"""Passe typographique sur un texte, et signalement des tics rhetoriques.

Traite ce qui est mecanique : tirets cadratins remplaces selon leur fonction
dans la phrase, guillemets, points de suspension, espaces insecables, puces
decoratives. Signale ensuite ce qui demande un jugement humain.

Usage:
    python3 nettoyer.py texte.txt
    python3 nettoyer.py texte.txt --sortie propre.txt
    echo "mon texte" | python3 nettoyer.py -
    python3 nettoyer.py texte.txt --langue en
    python3 nettoyer.py texte.txt --json
"""

import argparse
import json
import re
import sys
import unicodedata

CADRATIN = "—"       # —
DEMI_CADRATIN = "–"  # –
TIRETS_LONGS = f"[{CADRATIN}{DEMI_CADRATIN}]"

COORDINATIONS = r"(?:et|mais|ou|donc|car|ni|or|puis|alors|sauf|voire)"
COORDINATIONS_EN = r"(?:and|but|or|so|yet|nor|then)"

# Verbes conjugues frequents : indice qu'un segment est une proposition complete
INDICES_PROPOSITION = re.compile(
    r"\b(?:je|tu|il|elle|on|nous|vous|ils|elles|c'est|ce n'est|il y a|"
    r"personne|rien|tout|cela|ça)\b", re.I)


# --------------------------------------------------------------------------
# Tirets longs
# --------------------------------------------------------------------------

def _nettoyer_espaces(texte, langue="fr"):
    """Recolle la ponctuation apres substitution.

    En francais, la ponctuation double (; : ! ?) garde une espace avant elle,
    contrairement a l'anglais. Ne recoller que la virgule et le point evite
    de casser cette regle en corrigeant les tirets.
    """
    if langue == "fr":
        texte = re.sub(r"\s+([,.])", r"\1", texte)
    else:
        texte = re.sub(r"\s+([,;:.!?])", r"\1", texte)
    texte = re.sub(r"([,;:])(?=[^\s\d])", r"\1 ", texte)
    texte = re.sub(r"[ \t]{2,}", " ", texte)
    return texte


def traiter_tirets(ligne, langue="fr", journal=None):
    """Remplace les tirets longs selon leur fonction. Retourne la ligne traitee."""
    journal = journal if journal is not None else []
    coord = COORDINATIONS if langue == "fr" else COORDINATIONS_EN

    # 1. Debut de ligne : liste ou dialogue -> tiret court
    m = re.match(rf"^(\s*){TIRETS_LONGS}\s*", ligne)
    if m:
        ligne = re.sub(rf"^(\s*){TIRETS_LONGS}\s*", r"\1- ", ligne, count=1)
        journal.append(("tiret en debut de ligne", "remplace par un tiret court"))

    # 2. Intervalle entre deux nombres -> "a" (fr) ou tiret court (en)
    def _intervalle(m):
        journal.append((f"intervalle {m.group(0)}", "tiret d'intervalle remplace"))
        return f"{m.group(1)} à {m.group(2)}" if langue == "fr" else f"{m.group(1)}-{m.group(2)}"
    ligne = re.sub(rf"(\d+)\s*{TIRETS_LONGS}\s*(\d+)", _intervalle, ligne)

    # 3. Paire de tirets encadrant une incise -> virgules
    def _incise(m):
        journal.append((f"incise « {m.group(2).strip()} »", "encadree par des virgules"))
        return f"{m.group(1)}, {m.group(2).strip()}, {m.group(3)}"
    motif_incise = rf"(\S)\s*{TIRETS_LONGS}\s*([^{CADRATIN}{DEMI_CADRATIN}]+?)\s*{TIRETS_LONGS}\s*(\S)"
    precedent = None
    while precedent != ligne:
        precedent = ligne
        ligne = re.sub(motif_incise, _incise, ligne, count=1)

    # 4. Tiret unique restant : la fonction depend de ce qui suit
    def _unique(m):
        avant, apres = m.group(1), m.group(2)
        suite = apres.lstrip()

        # suivi d'une coordination -> virgule
        if re.match(rf"^{coord}\b", suite, re.I):
            journal.append((f"tiret avant « {suite.split()[0]} »", "remplace par une virgule"))
            return f"{avant}, {apres}"

        # suivi d'une proposition complete -> point
        if INDICES_PROPOSITION.match(suite) or re.match(r"^(?:This|That|It|We|They|I)\b", suite):
            fin = "." if not avant.endswith((".", "!", "?")) else ""
            majuscule = suite[0].upper() + suite[1:] if suite else suite
            journal.append((f"tiret avant « {suite[:28]}... »", "coupe en deux phrases"))
            return f"{avant}{fin} {majuscule}"

        # sinon : developpement ou apposition -> deux-points si le segment est long,
        # virgule sinon
        if len(suite.split()) >= 8:
            journal.append((f"tiret avant « {suite[:28]}... »", "remplace par deux-points"))
            return f"{avant} : {apres}"
        journal.append((f"tiret avant « {suite[:28]}... »", "remplace par une virgule"))
        return f"{avant}, {apres}"

    precedent = None
    while precedent != ligne:
        precedent = ligne
        ligne = re.sub(rf"(\S)\s*{TIRETS_LONGS}\s*(.+)$", _unique, ligne, count=1)

    return _nettoyer_espaces(ligne, langue), journal


# --------------------------------------------------------------------------
# Autres marqueurs typographiques
# --------------------------------------------------------------------------

PUCES = "•●▪‣⁃∙·–➜➔→⇒✅⭐ὒ5"


def traiter_typographie(texte, langue="fr"):
    journal = []

    def compte(motif, remplacement, libelle, drapeaux=0):
        nonlocal texte
        n = len(re.findall(motif, texte, drapeaux))
        if n:
            texte = re.sub(motif, remplacement, texte, flags=drapeaux)
            journal.append((libelle, f"{n} occurrence{'s' if n > 1 else ''}"))

    # points de suspension en caractere unique
    compte("…", "...", "points de suspension en caractere unique")

    # guillemets courbes
    if langue == "fr":
        compte("[“”]", '"', "guillemets courbes")
    else:
        compte("[“”]", '"', "curly double quotes")
    compte("[‘’]", "'", "apostrophes courbes" if langue == "fr" else "curly apostrophes")

    # puces decoratives et emoji en debut de ligne
    compte(rf"^[ \t]*[{PUCES}]+[ \t]*", "- ", "puces decoratives", re.M)
    compte(r"^[ \t]*[\U0001F300-\U0001FAFF☀-➿][ \t]*", "", "emoji en debut de ligne", re.M)

    # espaces insecables devant la ponctuation double (francais)
    if langue == "fr":
        n = len(re.findall(r"(?<=\S)[ ]([;:!?])", texte))
        if n:
            texte = re.sub(r"(?<=\S)[ ]([;:!?])", " \\1", texte)
            journal.append(("espaces insecables", f"{n} pose{'s' if n > 1 else ''} devant ; : ! ?"))
        n = len(re.findall(r"(?<=\S)[ ]?«[ ]?|[ ]?»", texte))
        texte = re.sub(r"«[ ]?", "« ", texte)
        texte = re.sub(r"[ ]?»", " »", texte)
        if n:
            journal.append(("guillemets francais", "espaces insecables ajustees"))

    # espaces multiples et fins de ligne
    texte = re.sub(r"[ \t]+$", "", texte, flags=re.M)
    texte = re.sub(r"\n{3,}", "\n\n", texte)

    return texte, journal


# --------------------------------------------------------------------------
# Signalement des tics rhetoriques
# --------------------------------------------------------------------------

TICS_FR = [
    ("retournement", r"(?:ce|Ce)\s+n['’]est pas\s+.{3,60}?\.\s*(?:C['’]est|c['’]est)\b",
     "negation suivie d'une revelation"),
    ("retournement", r"[Ll]e (?:probleme|problème|sujet|point) n['’]est pas\s+.{3,50}?,\s*c['’]est\b",
     "negation suivie d'une revelation"),
    ("fausse confidence", r"\b(?:Honn[eê]tement\s*\?|Soyons (?:clairs|honn[eê]tes)|"
     r"[Jj]e vais [eê]tre franc|On ne va pas se mentir|Entre nous|[Ss]oyons clairs|"
     r"[Aa]vouons-le|[Ss]poiler\s*:)", "marqueur d'intimite simule"),
    ("autorite non sourcee", r"\b(?:[Ll]es experts sont formels|[Dd]es [ée]tudes montrent|"
     r"[Ll]es (?:observateurs|analystes|sp[ée]cialistes) s['’]accordent|"
     r"[Ii]l est (?:largement|g[ée]n[ée]ralement) admis|[Oo]n le sait (?:tous|bien))",
     "source invoquee sans etre nommee"),
    ("chute artificielle", r"\b(?:[Ee]t voici le vrai (?:probl[eè]me|sujet)|"
     r"[Ee]t c['’]est l[aà] que tout bascule|[Cc]e que personne ne (?:dit|voit)|"
     r"[Ll]a v[ée]rit[ée],? c['’]est que|[Vv]oil[aà] le vrai|[Ee]t pourtant)",
     "annonceur de revelation"),
    ("symbolisme gonfle", r"\b(?:riche )?(?:tapisserie|mosa[iï]que|symphonie|ballet|"
     r"kal[ée]idoscope|odyss[ée]e)\b", "metaphore decorative"),
    ("metaphore filee", r"\b(?:a pris le volant|aux commandes|le gouvernail|"
     r"copilote|pilote automatique|dans le cockpit|garde-fou)\b", "image mecanique etiree"),
    ("euphemisme corporate", r"\b(?:optimise[rz]? la cadence|adresser (?:ce|le) sujet|"
     r"activer (?:un|le) levier|industrialise[rz]?|monte[rz]? en puissance|"
     r"cr[ée]ation de valeur|synergi\w+|impacte[rz]?)\b", "terme de gestion decoratif"),
    ("formule d'ouverture", r"^\s*(?:[AÀ] l['’][eè]re (?:du|de la|des)|Dans un monde o[uù]|"
     r"[Ff]orce est de constater|[Ii]l est important de noter|[Dd]e nos jours)",
     "ouverture generique"),
    ("vocabulaire IA", r"\b(?:plonge(?:ons|r)\s+dans|d[ée]cryptage|incontournable|"
     r"r[ée]volutionnaire|game.?changer|disruptif|ph[ée]nom[ée]nal)\b",
     "mot marqueur"),
]

TICS_EN = [
    ("false antithesis", r"[Ii]t['’]s not (?:about )?.{3,40}?[.,]\s*[Ii]t['’]s\b", "negation then reveal"),
    ("fake confidence", r"\b(?:Let['’]s be honest|Honestly\?|I['’]ll be blunt|"
     r"Real talk|Here['’]s the thing)", "simulated intimacy"),
    ("unsourced authority", r"\b(?:[Ss]tudies show|[Ee]xperts agree|"
     r"[Ii]t is widely (?:known|accepted)|[Rr]esearch suggests)", "source never named"),
    ("inflated symbolism", r"\b(?:rich )?(?:tapestry|mosaic|symphony|kaleidoscope|odyssey)\b",
     "decorative metaphor"),
    ("AI vocabulary", r"\b(?:delve|leverage|seamless|robust|game.?changer|"
     r"in today['’]s (?:rapidly )?evolving|underscore[sd]?|testament to)\b", "marker word"),
]


def detecter_triades(texte):
    """Trois fragments courts et consecutifs, chacun sur sa ligne."""
    trouves = []
    lignes = [l.strip() for l in texte.split("\n")]
    for i in range(len(lignes) - 2):
        trio = lignes[i:i + 3]
        if all(l and l.endswith(".") and 1 <= len(l.split()) <= 5 for l in trio):
            longueurs = [len(l) for l in trio]
            forme = "escalier decroissant" if longueurs == sorted(longueurs, reverse=True) else "triade"
            trouves.append((forme, " / ".join(trio)))
    # chute finale : trois dernieres lignes non vides, de longueur decroissante
    fin = [l for l in lignes if l][-3:]
    if len(fin) == 3:
        longueurs = [len(l) for l in fin]
        if longueurs == sorted(longueurs, reverse=True) and longueurs[0] > longueurs[2] * 1.2:
            if all(l.endswith((".", "!", "?")) for l in fin):
                trouves.append(("chute en degrade", " / ".join(fin)))

    # triade sur une seule ligne : trois segments courts separes par des points
    for l in lignes:
        segments = [s.strip() for s in re.split(r"(?<=[.!?])\s+", l) if s.strip()]
        if len(segments) == 3 and all(1 <= len(s.split()) <= 6 for s in segments):
            trouves.append(("triade", l))
    return trouves


def detecter_tics(texte, langue="fr"):
    regles = TICS_FR if langue == "fr" else TICS_EN
    trouves = []
    for nom, motif, explication in regles:
        for m in re.finditer(motif, texte, re.M):
            fragment = m.group(0).strip().replace("\n", " ")
            trouves.append((nom, fragment[:70], explication))
    for forme, fragment in detecter_triades(texte):
        trouves.append((forme, fragment[:70], "structure ternaire mecanique"))
    return trouves


# --------------------------------------------------------------------------

def deviner_langue(texte):
    marqueurs_fr = len(re.findall(r"\b(?:le|la|les|des|une|est|nous|vous|dans|pour|qui|que)\b",
                                  texte, re.I))
    marqueurs_en = len(re.findall(r"\b(?:the|and|is|are|of|to|for|with|that|this)\b", texte, re.I))
    return "fr" if marqueurs_fr >= marqueurs_en else "en"


def nettoyer(texte, langue=None):
    langue = langue or deviner_langue(texte)
    journal_tirets = []
    lignes = []
    for ligne in texte.split("\n"):
        if re.search(TIRETS_LONGS, ligne):
            ligne, journal_tirets = traiter_tirets(ligne, langue, journal_tirets)
        lignes.append(ligne)
    texte = "\n".join(lignes)
    texte, journal_typo = traiter_typographie(texte, langue)
    tics = detecter_tics(texte, langue)
    return texte, langue, journal_tirets, journal_typo, tics


def main():
    ap = argparse.ArgumentParser(description="Nettoyage typographique et detection des tics")
    ap.add_argument("fichier", help="chemin du fichier, ou - pour l'entree standard")
    ap.add_argument("--sortie", default=None, help="fichier de sortie (defaut : stdout)")
    ap.add_argument("--langue", choices=["fr", "en"], default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--silencieux", action="store_true", help="texte seul, sans rapport")
    args = ap.parse_args()

    texte = sys.stdin.read() if args.fichier == "-" else open(args.fichier, encoding="utf-8").read()
    propre, langue, tirets, typo, tics = nettoyer(texte, args.langue)

    if args.json:
        print(json.dumps({
            "langue": langue,
            "texte": propre,
            "tirets": [{"cas": a, "action": b} for a, b in tirets],
            "typographie": [{"element": a, "detail": b} for a, b in typo],
            "tics": [{"type": a, "fragment": b, "explication": c} for a, b, c in tics],
        }, ensure_ascii=False, indent=2))
        return

    if args.sortie:
        with open(args.sortie, "w", encoding="utf-8") as f:
            f.write(propre)
    else:
        print(propre)

    if args.silencieux:
        return

    rapport = []
    if tirets:
        rapport.append(f"TIRETS LONGS ({len(tirets)})")
        rapport += [f"  {cas} -> {action}" for cas, action in tirets]
    if typo:
        rapport.append(f"TYPOGRAPHIE ({len(typo)})")
        rapport += [f"  {element} : {detail}" for element, detail in typo]
    if tics:
        rapport.append(f"TICS A REECRIRE A LA MAIN ({len(tics)})")
        for nom, fragment, explication in tics:
            rapport.append(f"  [{nom}] {fragment}")
            rapport.append(f"      {explication}")
    if not rapport:
        rapport.append("Rien a signaler.")

    sortie = sys.stderr if not args.sortie else sys.stdout
    print("\n" + "\n".join(rapport), file=sortie)


if __name__ == "__main__":
    main()
