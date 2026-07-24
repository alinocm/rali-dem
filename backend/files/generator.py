# ─────────────────────────────────────────────────────────────
# generator.py  —  Moteur de génération RALI-DEM
# Inclut les listes blanches de mots courants intégrées
# ─────────────────────────────────────────────────────────────

import random
from calculator import (
    calculer_complexite, verifier_niveau_cible, estimer_parametres
)

# ═════════════════════════════════════════════════════════════
# LISTES BLANCHES DE MOTS COURANTS
# Intégrées directement — aucune dépendance au dictionnaire DEM
# pour garantir des phrases lisibles par un étudiant de niveau moyen
# ═════════════════════════════════════════════════════════════

# ── Sujets humains ────────────────────────────────────────────
SUJETS = [
    {"mot": "étudiant",   "genre": "M"},
    {"mot": "élève",      "genre": "M"},
    {"mot": "professeur", "genre": "M"},
    {"mot": "médecin",    "genre": "M"},
    {"mot": "avocat",     "genre": "M"},
    {"mot": "directeur",  "genre": "M"},
    {"mot": "candidat",   "genre": "M"},
    {"mot": "patient",    "genre": "M"},
    {"mot": "auteur",     "genre": "M"},
    {"mot": "chercheur",  "genre": "M"},
    {"mot": "lecteur",    "genre": "M"},
    {"mot": "joueur",     "genre": "M"},
    {"mot": "enfant",     "genre": "M"},
    {"mot": "adulte",     "genre": "M"},
    {"mot": "citoyen",    "genre": "M"},
    {"mot": "habitant",   "genre": "M"},
    {"mot": "touriste",   "genre": "M"},
    {"mot": "voisin",     "genre": "M"},
    {"mot": "ami",        "genre": "M"},
    {"mot": "parent",     "genre": "M"},
    {"mot": "femme",      "genre": "F"},
    {"mot": "fille",      "genre": "F"},
]

# ── Paires verbe + complément sémantiquement cohérentes ───────
# Format : (verbe_il/elle, complément, infinitif, verbe_ils/elles)
VERBE_COMPLEMENT = [
    # Apprentissage / cognition
    ("comprend",   "ce cours",           "comprendre"),
    ("comprend",   "cette leçon",        "comprendre"),
    ("comprend",   "ce principe",        "comprendre"),
    ("connaît",    "cette règle",        "connaître"),
    ("connaît",    "ce principe",        "connaître"),
    ("connaît",    "cette méthode",      "connaître"),
    ("sait",       "la réponse",         "savoir"),
    ("sait",       "la solution",        "savoir"),
    ("sait",       "ce principe",        "savoir"),
    ("apprend",    "ce cours",           "apprendre"),
    ("apprend",    "cette leçon",        "apprendre"),
    ("apprend",    "cette méthode",      "apprendre"),
    ("étudie",     "ce cours",           "étudier"),
    ("étudie",     "ce sujet",           "étudier"),
    ("étudie",     "ce problème",        "étudier"),
    ("lit",        "ce texte",           "lire"),
    ("lit",        "ce livre",           "lire"),
    ("lit",        "ce rapport",         "lire"),
    # Démonstration / preuve
    ("démontre",   "ce résultat",        "démontrer"),
    ("démontre",   "ce principe",        "démontrer"),
    ("prouve",     "cet argument",       "prouver"),
    ("prouve",     "cette thèse",        "prouver"),
    ("explique",   "ce résultat",        "expliquer"),
    ("explique",   "cette méthode",      "expliquer"),
    ("explique",   "ce principe",        "expliquer"),
    ("montre",     "ce résultat",        "montrer"),
    ("montre",     "cette solution",     "montrer"),
    ("montre",     "cet exemple",        "montrer"),
    ("analyse",    "ce problème",        "analyser"),
    ("analyse",    "ce texte",           "analyser"),
    ("résout",     "ce problème",        "résoudre"),
    ("résout",     "cet exercice",       "résoudre"),
    ("définit",    "ce concept",         "définir"),
    ("définit",    "cette règle",        "définir"),
    ("applique",   "cette règle",        "appliquer"),
    ("applique",   "cette méthode",      "appliquer"),
    ("vérifie",    "ce résultat",        "vérifier"),
    ("vérifie",    "cette réponse",      "vérifier"),
    # Affirmation / opinion
    ("affirme",    "ce résultat",        "affirmer"),
    ("affirme",    "cette conclusion",   "affirmer"),
    ("suppose",    "cette hypothèse",    "supposer"),
    ("suppose",    "ce résultat",        "supposer"),
    ("croit",      "cet argument",       "croire"),
    ("croit",      "cette théorie",      "croire"),
    ("remarque",   "cette erreur",       "remarquer"),
    ("remarque",   "ce problème",        "remarquer"),
    ("constate",   "ce résultat",        "constater"),
    ("constate",   "cette amélioration", "constater"),
    # Action / réussite
    ("réussit",    "cet examen",         "réussir"),
    ("réussit",    "ce devoir",          "réussir"),
    ("prépare",    "cet examen",         "préparer"),
    ("prépare",    "ce projet",          "préparer"),
    ("présente",   "ce rapport",         "présenter"),
    ("présente",   "ce résultat",        "présenter"),
    ("utilise",    "cette méthode",      "utiliser"),
    ("utilise",    "ce principe",        "utiliser"),
    ("suit",       "ce cours",           "suivre"),
    ("suit",       "cette méthode",      "suivre"),
    ("enseigne",   "ce cours",           "enseigner"),
    ("enseigne",   "ce principe",        "enseigner"),
    ("donne",      "cet exemple",        "donner"),
    ("donne",      "cette réponse",      "donner"),
    ("trouve",     "la solution",        "trouver"),
    ("trouve",     "la réponse",         "trouver"),
    ("écrit",      "ce rapport",         "écrire"),
    ("écrit",      "ce devoir",          "écrire"),
]

# Table des formes verbales au pluriel (ils/elles)
VERBE_PLURIEL = {
    "comprend":"comprennent", "connaît":"connaissent",
    "sait":"savent", "apprend":"apprennent",
    "étudie":"étudient", "lit":"lisent",
    "démontre":"démontrent", "prouve":"prouvent",
    "explique":"expliquent", "montre":"montrent",
    "analyse":"analysent", "résout":"résolvent",
    "définit":"définissent", "applique":"appliquent",
    "vérifie":"vérifient", "affirme":"affirment",
    "suppose":"supposent", "croit":"croient",
    "remarque":"remarquent", "constate":"constatent",
    "réussit":"réussissent", "prépare":"préparent",
    "présente":"présentent", "utilise":"utilisent",
    "suit":"suivent", "enseigne":"enseignent",
    "donne":"donnent", "trouve":"trouvent",
    "écrit":"écrivent", "voit":"voient",
    "prend":"prennent", "fait":"font",
    "dit":"disent", "a":"ont",
    "est":"sont", "va":"vont",
    "veut":"veulent", "peut":"peuvent",
    "travaille":"travaillent", "pense":"pensent",
    "travaill":"travaillent", "vérifi":"vérifient",
}

def _verbe_pluriel(v: str) -> str:
    """Retourne la forme ils/elles du verbe."""
    if v in VERBE_PLURIEL:
        return VERBE_PLURIEL[v]
    if v.endswith("e"):
        return v + "nt"
    if v.endswith("t"):
        return v[:-1] + "ent"
    return v + "ent"


# ─────────────────────────────────────────────────────────────
# FONCTIONS DE CONSTRUCTION LINGUISTIQUE
# ─────────────────────────────────────────────────────────────

def _article(nom: dict) -> str:
    """Retourne le sujet avec article défini accordé (avec élision)."""
    mot    = nom["mot"]
    genre  = nom["genre"]
    voyelles = "aeéèêëiîïoôuùûüh"
    if mot[0].lower() in voyelles:
        return f"l'{mot}"
    return f"la {mot}" if genre == "F" else f"le {mot}"


def _sujet_verbe_complement():
    """Retourne un triplet (sujet, verbe, complément) cohérent."""
    nom = random.choice(SUJETS)
    verbe, complement, _ = random.choice(VERBE_COMPLEMENT)
    sujet = _article(nom)
    return sujet, verbe, complement


def _neg(sujet: str, verbe: str, complement: str) -> str:
    """Forme la négation correcte avec élision (ne → n' devant voyelle)."""
    voyelles = "aeéèêëiîïoôuùûüh"
    ne = "n'" if verbe[0].lower() in voyelles else "ne "
    return f"{sujet} {ne}{verbe} pas {complement}"


def _quant_prop(quant: str, nom: dict, verbe: str, complement: str) -> str:
    """Forme une proposition avec quantificateur correctement accordée."""
    mot = nom["mot"]
    # Pluriel
    if mot.endswith(("s", "x", "z")):
        pluriel = mot
    elif mot.endswith("al"):
        pluriel = mot[:-2] + "aux"
    else:
        pluriel = mot + "s"

    voyelles = "aeéèêëiîïoôuùûüh"
    if quant == "UNIVERSEL":
        return f"Tous les {pluriel} {verbe} {complement}"
    else:
        art = "un" if mot[0].lower() not in voyelles else "un"
        return f"Il existe au moins {art} {mot} qui {verbe} {complement}"


def _neg_quant_prop(quant: str, nom: dict, verbe: str, complement: str) -> str:
    """Négation correcte d'une proposition quantifiée."""
    mot = nom["mot"]
    if mot.endswith(("s", "x", "z")):
        pluriel = mot
    elif mot.endswith("al"):
        pluriel = mot[:-2] + "aux"
    else:
        pluriel = mot + "s"

    voyelles = "aeéèêëiîïoôuùûüh"
    ne = "n'" if verbe[0].lower() in voyelles else "ne "

    if quant == "UNIVERSEL":
        # non(∀x P(x)) = ∃x non(P(x))
        art = "un" if mot[0].lower() not in voyelles else "un"
        return f"Il existe au moins {art} {mot} qui {ne}{verbe} pas {complement}"
    else:
        # non(∃x P(x)) = ∀x non(P(x))
        verbe_pl = _verbe_pluriel(verbe)
        ne_pl = "n'" if verbe_pl[0].lower() in voyelles else "ne "
        tous = "Toutes les" if nom.get("genre") == "F" else "Tous les"
        return f"{tous} {pluriel} {ne_pl}{verbe_pl} pas {complement}"


# ─────────────────────────────────────────────────────────────
# DONNÉES LOGIQUES
# ─────────────────────────────────────────────────────────────

CONNECTEURS = {
    "ET":    {"ln": "et",                 "formel": "∧"},
    "OU":    {"ln": "ou",                 "formel": "∨"},
    "IMP":   {"ln": "implique",           "formel": "⇒"},
    "EQUIV": {"ln": "si et seulement si", "formel": "⇔"},
}

TABLES_VERITE = {
    "∧": {("V","V"):"V", ("V","F"):"F", ("F","V"):"F", ("F","F"):"F"},
    "∨": {("V","V"):"V", ("V","F"):"V", ("F","V"):"V", ("F","F"):"F"},
    "⇒": {("V","V"):"V", ("V","F"):"F", ("F","V"):"V", ("F","F"):"V"},
    "⇔": {("V","V"):"V", ("V","F"):"F", ("F","V"):"F", ("F","F"):"V"},
}

# ─────────────────────────────────────────────────────────────
# GABARITS PAR OBJECTIF
# ─────────────────────────────────────────────────────────────

GABARITS = {
    "PROP":       [{"type": "choix_proposition",        "structure": "SVO"}],
    "VVER":       [{"type": "valeur_verite",             "structure": "SVO"}],
    "TVER":       [{"type": "table_verite",              "structure": "SVO"}],
    "NEG_SIMPLE": [{"type": "negation_simple",           "structure": "SVO"}],
    "CONN_ID":    [{"type": "identifier_connecteur",     "structure": "SVO"}],
    "CONN_TRAD":  [{"type": "traduction_ln_formel",      "structure": "SVO"}],
    "CONN_INV":   [{"type": "traduction_formel_ln",      "structure": "SVO"}],
    "IMP":        [{"type": "implication",               "structure": "SVI"}],
    "EQUIV":      [{"type": "equivalence",               "structure": "SVO"}],
    "MORGAN":     [{"type": "de_morgan",                 "structure": "SVO"}],
    "NEG_COMP":   [{"type": "negation_composee",         "structure": "SVO"}],
    "NEG_IMP":    [{"type": "negation_implication",      "structure": "SVI"}],
    "QUANT_TRAD": [{"type": "quantificateur_traduction", "structure": "EVENT"}],
    "NEG_QUANT":  [{"type": "negation_quantificateur",   "structure": "EVENT"}],
    "CONTRAP":    [{"type": "contraposee",               "structure": "SVI"}],
}

# ─────────────────────────────────────────────────────────────
# GÉNÉRATEUR PRINCIPAL
# ─────────────────────────────────────────────────────────────

def generer_question(
    objectif_code:     str,
    mode_bloom:        str = "comprehension",
    niveau_complexite: str = "moyen",
    max_tentatives:    int = 10,
) -> dict:
    if objectif_code not in GABARITS:
        raise ValueError(f"Objectif inconnu : {objectif_code}")

    params = estimer_parametres(niveau_complexite, mode_bloom)

    for _ in range(max_tentatives):
        try:
            gabarit  = random.choice(GABARITS[objectif_code])
            question = _construire_question(
                gabarit, objectif_code, mode_bloom,
                niveau_complexite, params
            )
            if question and verifier_niveau_cible(
                question["ert_secondes"], niveau_complexite
            ):
                return question
        except Exception:
            continue

    # Fallback : retourner même si le niveau n'est pas exact
    gabarit = random.choice(GABARITS[objectif_code])
    return _construire_question(
        gabarit, objectif_code, mode_bloom, niveau_complexite, params
    )


def _construire_question(gabarit, objectif_code, mode_bloom,
                         niveau_complexite, params):
    constructeurs = {
        "negation_simple":          _neg_simple,
        "negation_composee":        _neg_composee,
        "negation_implication":     _neg_implication,
        "negation_quantificateur":  _neg_quantificateur,
        "valeur_verite":            _valeur_verite,
        "table_verite":             _table_verite,
        "implication":              _implication,
        "equivalence":              _equivalence,
        "de_morgan":                _de_morgan,
        "contraposee":              _contraposee,
        "traduction_ln_formel":     _trad_ln_formel,
        "traduction_formel_ln":     _trad_formel_ln,
        "identifier_connecteur":    _id_connecteur,
        "quantificateur_traduction":_quant_trad,
        "choix_proposition":        _choix_proposition,
    }
    type_q = gabarit["type"]
    if type_q not in constructeurs:
        raise ValueError(f"Type inconnu : {type_q}")

    enonce, reponse, distracteurs, meta = constructeurs[type_q](params, mode_bloom)

    complexite = calculer_complexite(
        nb_propositions    = meta.get("nb_propositions", 2),
        nb_connecteurs     = meta.get("nb_connecteurs", 1),
        nb_quantificateurs = meta.get("nb_quantificateurs", 0),
        nb_negations       = meta.get("nb_negations", 0),
        profondeur_logique = meta.get("profondeur_logique", 1),
        mode_bloom         = mode_bloom,
    )

    return {
        "objectif_code":       objectif_code,
        "mode_bloom":          mode_bloom,
        "niveau_complexite":   complexite["niveau_complexite"],
        "enonce":              enonce,
        "reponse_correcte":    reponse,
        "distracteurs":        distracteurs,
        "ert_secondes":        complexite["ert_secondes"],
        "score_pedagogique":   complexite["score_pedagogique"],
        "structure_syntaxique":gabarit.get("structure", "SVO"),
        "profondeur_logique":  meta.get("profondeur_logique", 1),
        "nb_connecteurs":      meta.get("nb_connecteurs", 1),
        "nb_propositions":     meta.get("nb_propositions", 2),
    }


# ─────────────────────────────────────────────────────────────
# CONSTRUCTEURS SPÉCIALISÉS
# ─────────────────────────────────────────────────────────────

def _neg_simple(params, mode_bloom):
    """NEG_SIMPLE — négation d'une proposition élémentaire."""
    s, v, c = _sujet_verbe_complement()
    S = s.capitalize()

    enonce  = f"Quelle est la négation correcte de : « {S} {v} {c} » ?"
    reponse = _neg(S, v, c)

    dist = [
        f"{S} {v} {c}",
        f"Il n'est pas vrai que {s} {v} {c} ou {s} {v} autre chose",
        _neg(S, v, "tout ce qu'il fait"),
    ]
    random.shuffle(dist)
    meta = {"nb_propositions":1, "nb_connecteurs":0,
            "nb_negations":1, "profondeur_logique":1}
    return enonce, reponse, dist[:3], meta


def _neg_composee(params, mode_bloom):
    """NEG_COMP — négation avec ET ou OU (De Morgan)."""
    s1,v1,c1 = _sujet_verbe_complement()
    s2,v2,c2 = _sujet_verbe_complement()
    S1 = s1.capitalize()
    conn = random.choice(["ET", "OU"])
    ln   = CONNECTEURS[conn]["ln"]
    p    = f"{S1} {v1} {c1}"
    q    = f"{s2} {v2} {c2}"

    enonce = f"Quelle est la négation correcte de : « {p} {ln} {q} » ?"

    if conn == "ET":
        reponse = f"{_neg(S1,v1,c1)} ou {_neg(s2,v2,c2)}"
        dist = [
            f"{_neg(S1,v1,c1)} et {_neg(s2,v2,c2)}",
            f"{p} ou {q}",
            f"Il n'est pas vrai que {p}",
        ]
    else:
        reponse = f"{_neg(S1,v1,c1)} et {_neg(s2,v2,c2)}"
        dist = [
            f"{_neg(S1,v1,c1)} ou {_neg(s2,v2,c2)}",
            f"{p} et {q}",
            f"Il n'est pas vrai que {q}",
        ]
    random.shuffle(dist)
    meta = {"nb_propositions":2, "nb_connecteurs":1,
            "nb_negations":2, "profondeur_logique":1}
    return enonce, reponse, dist[:3], meta


def _neg_implication(params, mode_bloom):
    """NEG_IMP — non(P⇒Q) ≡ P ∧ non(Q)."""
    s1,v1,c1 = _sujet_verbe_complement()
    s2,v2,c2 = _sujet_verbe_complement()
    S1 = s1.capitalize()
    p  = f"{S1} {v1} {c1}"
    q  = f"{s2} {v2} {c2}"
    nq = _neg(s2, v2, c2)

    p = p[0].lower() + p[1:] if p else p
    enonce  = f"Quelle est la négation de : « Si {p}, alors {q} » ?"
    reponse = f"{p} et {nq}"
    dist = [
        f"Si {p}, alors {nq}",
        f"{_neg(S1,v1,c1)} ou {q}",
        f"Si {nq}, alors {_neg(S1,v1,c1)}",
    ]
    random.shuffle(dist)
    meta = {"nb_propositions":2, "nb_connecteurs":1,
            "nb_negations":1, "profondeur_logique":2}
    return enonce, reponse, dist[:3], meta


def _neg_quantificateur(params, mode_bloom):
    """NEG_QUANT — négation de ∀ et ∃."""
    nom   = random.choice(SUJETS)
    v, c, _ = random.choice(VERBE_COMPLEMENT)
    quant = random.choice(["UNIVERSEL", "EXISTENTIEL"])

    prop_base = _quant_prop(quant, nom, v, c)
    reponse   = _neg_quant_prop(quant, nom, v, c)
    quant_inv = "EXISTENTIEL" if quant == "UNIVERSEL" else "UNIVERSEL"

    enonce = f"Quelle est la négation correcte de : « {prop_base} » ?"
    dist = [
        _quant_prop(quant, nom, f"ne {v} pas", c),
        _neg_quant_prop(quant_inv, nom, v, c),
        _quant_prop(quant_inv, nom, v, c),
    ]
    random.shuffle(dist)
    meta = {"nb_propositions":1, "nb_connecteurs":0,
            "nb_quantificateurs":1, "nb_negations":1, "profondeur_logique":1}
    return enonce, reponse, dist[:3], meta


def _valeur_verite(params, mode_bloom):
    """VVER — calculer V/F d'une proposition composée."""
    conn_key = random.choice(["ET", "OU", "IMP"])
    conn     = CONNECTEURS[conn_key]
    vp       = random.choice(["V", "F"])
    vq       = random.choice(["V", "F"])
    res      = TABLES_VERITE[conn["formel"]][(vp, vq)]
    rep_txt  = "Vraie" if res == "V" else "Fausse"
    vp_txt   = "Vraie" if vp == "V" else "Fausse"
    vq_txt   = "Vraie" if vq == "V" else "Fausse"

    enonce = (f"Si P est {vp_txt} et Q est {vq_txt}, "
              f"quelle est la valeur de « P {conn['formel']} Q » ?")
    autres = [v for v in ["Vraie","Fausse"] if v != rep_txt]
    dist   = autres + ["On ne peut pas savoir", "Indéterminée"]
    random.shuffle(dist)
    meta = {"nb_propositions":2, "nb_connecteurs":1,
            "nb_negations":0, "profondeur_logique":1}
    return enonce, rep_txt, dist[:3], meta


def _table_verite(params, mode_bloom):
    """TVER — lire une table de vérité."""
    conn_key = random.choice(["ET", "OU", "IMP", "EQUIV"])
    conn     = CONNECTEURS[conn_key]
    vp       = random.choice(["V", "F"])
    vq       = random.choice(["V", "F"])
    res      = TABLES_VERITE[conn["formel"]][(vp, vq)]
    rep_txt  = "Vraie" if res == "V" else "Fausse"
    vp_txt   = "Vraie" if vp == "V" else "Fausse"
    vq_txt   = "Vraie" if vq == "V" else "Fausse"

    enonce = (f"Dans la table de vérité de « P {conn['formel']} Q », "
              f"quelle est la valeur quand P est {vp_txt} et Q est {vq_txt} ?")
    autres = [v for v in ["Vraie","Fausse"] if v != rep_txt]
    dist   = autres + ["Indéterminée"]
    random.shuffle(dist)
    meta = {"nb_propositions":2, "nb_connecteurs":1,
            "nb_negations":0, "profondeur_logique":1}
    return enonce, rep_txt, dist[:3], meta


def _implication(params, mode_bloom):
    """IMP — évaluer P⇒Q."""
    s1,v1,c1 = _sujet_verbe_complement()
    s2,v2,c2 = _sujet_verbe_complement()
    S1 = s1.capitalize()
    vp = random.choice(["V","F"])
    vq = random.choice(["V","F"])
    res    = TABLES_VERITE["⇒"][(vp, vq)]
    rep    = "Vraie" if res == "V" else "Fausse"
    vp_txt = "vraie" if vp == "V" else "fausse"
    vq_txt = "vraie" if vq == "V" else "fausse"
    p = f"{S1} {v1} {c1}"
    q = f"{s2} {v2} {c2}"

    enonce = (f"Sachant que « {p} » est {vp_txt} et "
              f"« {q} » est {vq_txt}, "
              f"quelle est la valeur de « {p} ⇒ {q} » ?")
    autres = [v for v in ["Vraie","Fausse"] if v != rep]
    dist   = autres + ["On ne peut pas savoir", "Indéterminée"]
    random.shuffle(dist)
    meta = {"nb_propositions":2, "nb_connecteurs":1,
            "nb_negations":0, "profondeur_logique":2}
    return enonce, rep, dist[:3], meta


def _equivalence(params, mode_bloom):
    """EQUIV — identifier la proposition équivalente à P⇔Q."""
    s1,v1,c1 = _sujet_verbe_complement()
    s2,v2,c2 = _sujet_verbe_complement()
    S1 = s1.capitalize()
    p  = f"{S1} {v1} {c1}"
    q  = f"{s2} {v2} {c2}"
    np = _neg(S1,v1,c1)
    nq = _neg(s2,v2,c2)

    enonce  = f"Laquelle est logiquement équivalente à : « {p} ⇔ {q} » ?"
    p  = p[0].lower()  + p[1:]  if p  else p
    q  = q[0].lower()  + q[1:]  if q  else q
    np = np[0].lower() + np[1:] if np else np
    nq = nq[0].lower() + nq[1:] if nq else nq
    reponse = f"(Si {p}, alors {q}) et (si {q}, alors {p})"
    dist = [
        f"(Si {p}, alors {q}) ou (si {q}, alors {p})",
        f"Si {p}, alors {q}",
        f"{np} ou {nq}",
    ]
    random.shuffle(dist)
    meta = {"nb_propositions":2, "nb_connecteurs":2,
            "nb_negations":0, "profondeur_logique":2}
    return enonce, reponse, dist[:3], meta


def _de_morgan(params, mode_bloom):
    """MORGAN — appliquer les lois de De Morgan."""
    s1,v1,c1 = _sujet_verbe_complement()
    s2,v2,c2 = _sujet_verbe_complement()
    S1   = s1.capitalize()
    conn = random.choice(["ET","OU"])
    ln   = CONNECTEURS[conn]["ln"]
    p    = f"{S1} {v1} {c1}"
    q    = f"{s2} {v2} {c2}"
    np   = _neg(S1,v1,c1)
    nq   = _neg(s2,v2,c2)

    enonce = (f"Selon les lois de De Morgan, "
              f"quelle est la négation de : « {p} {ln} {q} » ?")
    if conn == "ET":
        reponse = f"{np} ou {nq}"
        dist = [f"{np} et {nq}", f"{p} ou {q}",
                f"Il n'est pas vrai que {p}"]
    else:
        reponse = f"{np} et {nq}"
        dist = [f"{np} ou {nq}", f"{p} et {q}",
                f"Il n'est pas vrai que {q}"]
    random.shuffle(dist)
    meta = {"nb_propositions":2, "nb_connecteurs":1,
            "nb_negations":2, "profondeur_logique":2}
    return enonce, reponse, dist[:3], meta


def _contraposee(params, mode_bloom):
    """CONTRAP — P⇒Q ≡ non(Q)⇒non(P)."""
    s1,v1,c1 = _sujet_verbe_complement()
    s2,v2,c2 = _sujet_verbe_complement()
    S1 = s1.capitalize()
    p  = f"{S1} {v1} {c1}"
    q  = f"{s2} {v2} {c2}"
    np = _neg(S1,v1,c1)
    nq = _neg(s2,v2,c2)

    p = p[0].lower() + p[1:] if p else p
    q = q[0].lower() + q[1:] if q else q
    np = np[0].lower() + np[1:] if np else np
    nq = nq[0].lower() + nq[1:] if nq else nq
    enonce  = f"Laquelle est la contraposée de : « Si {p}, alors {q} » ?"
    reponse = f"Si {nq}, alors {np}"
    dist = [
        f"Si {nq}, alors {p}",
        f"Si {q}, alors {p}",
        f"Si {np}, alors {nq}",
    ]
    random.shuffle(dist)
    meta = {"nb_propositions":2, "nb_connecteurs":1,
            "nb_negations":2, "profondeur_logique":2}
    return enonce, reponse, dist[:3], meta


def _trad_ln_formel(params, mode_bloom):
    """CONN_TRAD — traduire une phrase en formule logique."""
    conn_key = random.choice(["ET","OU","IMP"])
    conn     = CONNECTEURS[conn_key]
    s1,v1,c1 = _sujet_verbe_complement()
    s2,v2,c2 = _sujet_verbe_complement()
    S1 = s1.capitalize()
    p  = f"{S1} {v1} {c1}"
    q  = f"{s2} {v2} {c2}"

    if conn_key == "IMP":
        phrase = f"Si {p}, alors {q}"
    elif conn_key == "EQUIV":
        phrase = f"{p} si et seulement si {q}"
    else:
        phrase = f"{p} {conn['ln']} {q}"

    enonce  = f"Quelle formule logique correspond à : « {phrase} » ?"
    reponse = f"P {conn['formel']} Q"
    autres  = [f"P {c} Q" for c in ["∧","∨","⇒","⇔"]
               if c != conn["formel"]]
    random.shuffle(autres)
    meta = {"nb_propositions":2, "nb_connecteurs":1,
            "nb_negations":0, "profondeur_logique":1}
    return enonce, reponse, autres[:3], meta


def _trad_formel_ln(params, mode_bloom):
    """CONN_INV — traduire une formule en langage naturel."""
    conn_key = random.choice(["ET","OU","IMP"])
    conn     = CONNECTEURS[conn_key]
    s1,v1,c1 = _sujet_verbe_complement()
    s2,v2,c2 = _sujet_verbe_complement()
    S1 = s1.capitalize()
    p  = f"{S1} {v1} {c1}"
    q  = f"{s2} {v2} {c2}"

    enonce = (f"Quelle phrase correspond à « P {conn['formel']} Q » "
              f"où P = « {p} » et Q = « {q} » ?")
    p = p[0].lower() + p[1:] if p else p
    q = q[0].lower() + q[1:] if q else q
    trad = {
        "ET":  f"{p} et {q}",
        "OU":  f"{p} ou {q}",
        "IMP": f"Si {p}, alors {q}",
    }
    reponse = trad[conn_key]
    autres  = [v for k,v in trad.items() if k != conn_key]
    autres.append(f"{q} si et seulement si {p}")
    random.shuffle(autres)
    meta = {"nb_propositions":2, "nb_connecteurs":1,
            "nb_negations":0, "profondeur_logique":1}
    return enonce, reponse, autres[:3], meta


def _id_connecteur(params, mode_bloom):
    """CONN_ID — identifier le connecteur dans une phrase."""
    conn_key = random.choice(["ET","OU","IMP","EQUIV"])
    conn     = CONNECTEURS[conn_key]
    s1,v1,c1 = _sujet_verbe_complement()
    s2,v2,c2 = _sujet_verbe_complement()
    S1 = s1.capitalize()
    p  = f"{S1} {v1} {c1}"
    q  = f"{s2} {v2} {c2}"

    if conn_key == "IMP":
        phrase = f"Si {p}, alors {q}"
    elif conn_key == "EQUIV":
        phrase = f"{p} si et seulement si {q}"
    else:
        phrase = f"{p} {conn['ln']} {q}"

    enonce  = f"Quel connecteur logique est utilisé dans : « {phrase} » ?"
    reponse = conn["formel"]
    autres  = [c["formel"] for k,c in CONNECTEURS.items() if k != conn_key]
    random.shuffle(autres)
    meta = {"nb_propositions":2, "nb_connecteurs":1,
            "nb_negations":0, "profondeur_logique":1}
    return enonce, reponse, autres[:3], meta


def _quant_trad(params, mode_bloom):
    """QUANT_TRAD — traduire un énoncé avec quantificateur."""
    nom   = random.choice(SUJETS)
    v, c, _ = random.choice(VERBE_COMPLEMENT)
    quant = random.choice(["UNIVERSEL","EXISTENTIEL"])
    phrase = _quant_prop(quant, nom, v, c)  # utilise déjà _verbe_pluriel
    formel = "∀x, P(x)" if quant == "UNIVERSEL" else "∃x, P(x)"
    autre  = "∃x, P(x)" if quant == "UNIVERSEL" else "∀x, P(x)"

    enonce  = f"Quelle formule logique correspond à : « {phrase} » ?"
    reponse = formel
    dist    = [
        autre,
        f"{'∀' if quant=='UNIVERSEL' else '∃'}x, ¬P(x)",
        "∃x, ¬P(x)",
    ]
    random.shuffle(dist)
    meta = {"nb_propositions":1, "nb_connecteurs":0,
            "nb_quantificateurs":1, "nb_negations":0, "profondeur_logique":1}
    return enonce, reponse, dist[:3], meta


def _choix_proposition(params, mode_bloom):
    """PROP — reconnaître une proposition logique."""
    s, v, c = _sujet_verbe_complement()
    S = s.capitalize()
    enonce  = "Laquelle des affirmations suivantes est une proposition logique ?"
    reponse = f"{S} {v} {c}"
    dist    = [
        "Ferme la porte !",
        "Est-ce que tu viens demain ?",
        "Peut-être qu'il viendra un jour",
    ]
    random.shuffle(dist)
    meta = {"nb_propositions":1, "nb_connecteurs":0,
            "nb_negations":0, "profondeur_logique":1}
    return enonce, reponse, dist[:3], meta


# ─────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Test du générateur RALI-DEM ===\n")
    tests = [
        ("NEG_SIMPLE",  "comprehension", "faible"),
        ("NEG_COMP",    "comprehension", "moyen"),
        ("NEG_IMP",     "comprehension", "moyen"),
        ("MORGAN",      "analyse",       "moyen"),
        ("CONTRAP",     "analyse",       "eleve"),
        ("NEG_QUANT",   "analyse",       "eleve"),
        ("QUANT_TRAD",  "comprehension", "faible"),
        ("CONN_TRAD",   "comprehension", "faible"),
        ("IMP",         "comprehension", "moyen"),
    ]
    for code, bloom, niveau in tests:
        print(f"── {code} | {bloom} | {niveau} ──")
        q = generer_question(code, bloom, niveau)
        print(f"  Q : {q['enonce']}")
        print(f"  R : {q['reponse_correcte']}")
        print(f"  D1: {q['distracteurs'][0]}")
        print(f"  D2: {q['distracteurs'][1]}")
        print(f"  D3: {q['distracteurs'][2]}")
        print(f"  ERT={q['ert_secondes']}s | "
              f"Score={q['score_pedagogique']}/10 | "
              f"Niveau={q['niveau_complexite'].upper()}")
        print()
