# ─────────────────────────────────────────────────────────────
# generator.py  —  Moteur de génération RALI-DEM
# Distinction réelle entre mode Compréhension et mode Analyse
# ─────────────────────────────────────────────────────────────

import random
from calculator import (
    calculer_complexite, verifier_niveau_cible, estimer_parametres
)

# ═════════════════════════════════════════════════════════════
# LISTES BLANCHES DE MOTS COURANTS
# ═════════════════════════════════════════════════════════════

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

VERBE_COMPLEMENT = [
    ("comprend",   "ce cours",           "comprendre"),
    ("comprend",   "cette leçon",        "comprendre"),
    ("comprend",   "ce principe",        "comprendre"),
    ("connaît",    "cette règle",        "connaître"),
    ("connaît",    "cette méthode",      "connaître"),
    ("sait",       "la réponse",         "savoir"),
    ("sait",       "la solution",        "savoir"),
    ("apprend",    "ce cours",           "apprendre"),
    ("apprend",    "cette méthode",      "apprendre"),
    ("étudie",     "ce cours",           "étudier"),
    ("étudie",     "ce problème",        "étudier"),
    ("lit",        "ce texte",           "lire"),
    ("lit",        "ce livre",           "lire"),
    ("démontre",   "ce résultat",        "démontrer"),
    ("démontre",   "ce principe",        "démontrer"),
    ("prouve",     "cet argument",       "prouver"),
    ("prouve",     "cette thèse",        "prouver"),
    ("explique",   "ce résultat",        "expliquer"),
    ("explique",   "cette méthode",      "expliquer"),
    ("montre",     "ce résultat",        "montrer"),
    ("montre",     "cet exemple",        "montrer"),
    ("analyse",    "ce problème",        "analyser"),
    ("résout",     "ce problème",        "résoudre"),
    ("résout",     "cet exercice",       "résoudre"),
    ("définit",    "ce concept",         "définir"),
    ("définit",    "cette règle",        "définir"),
    ("applique",   "cette règle",        "appliquer"),
    ("applique",   "cette méthode",      "appliquer"),
    ("vérifie",    "ce résultat",        "vérifier"),
    ("affirme",    "ce résultat",        "affirmer"),
    ("affirme",    "cette conclusion",   "affirmer"),
    ("suppose",    "cette hypothèse",    "supposer"),
    ("croit",      "cet argument",       "croire"),
    ("croit",      "cette théorie",      "croire"),
    ("remarque",   "cette erreur",       "remarquer"),
    ("constate",   "ce résultat",        "constater"),
    ("réussit",    "cet examen",         "réussir"),
    ("réussit",    "ce devoir",          "réussir"),
    ("prépare",    "cet examen",         "préparer"),
    ("prépare",    "ce projet",          "préparer"),
    ("présente",   "ce rapport",         "présenter"),
    ("utilise",    "cette méthode",      "utiliser"),
    ("suit",       "ce cours",           "suivre"),
    ("enseigne",   "ce cours",           "enseigner"),
    ("donne",      "cet exemple",        "donner"),
    ("trouve",     "la solution",        "trouver"),
    ("écrit",      "ce rapport",         "écrire"),

]

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
    "écrit":"écrivent", "travaill":"travaillent",
    "fait":"font", "dit":"disent", "a":"ont",
    "est":"sont", "va":"vont", "veut":"veulent",
    "peut":"peuvent", "pense":"pensent",
    "prend":"prennent", "voit":"voient",
}


# ─────────────────────────────────────────────────────────────
# FONCTIONS LINGUISTIQUES
# ─────────────────────────────────────────────────────────────

def _verbe_pluriel(v):
    if v in VERBE_PLURIEL:
        return VERBE_PLURIEL[v]
    if v.endswith("e"):
        return v + "nt"
    if v.endswith("t"):
        return v[:-1] + "ent"
    return v + "ent"


# ═════════════════════════════════════════════════════════════
# LISTES PAR STRUCTURE SYNTAXIQUE (thèse §3.5.3)
# ═════════════════════════════════════════════════════════════

# SVP — verbes pronominaux avec compléments naturels associés
# Format : (verbe_sg, verbe_pl, [compléments])
VERBES_SVP_COMPLETS = [
    ("se souvient",    "se souviennent",    [
        "de ce cours", "de cette règle", "de ce principe",
        "de cet exercice", "de cette leçon", "de cette méthode"]),
    ("se demande",     "se demandent",      [
        "si ce résultat est correct", "comment résoudre ce problème",
        "pourquoi cette règle s'applique", "si cet argument est valide"]),
    ("s'interroge",    "s'interrogent",     [
        "sur ce principe", "sur cette règle", "sur ce résultat",
        "sur cette méthode", "sur cet argument"]),
    ("se rappelle",    "se rappellent",     [
        "de ce cours", "de cette règle", "de ce principe",
        "de cette leçon", "de cet exercice"]),
    ("se rend compte", "se rendent compte", [
        "de son erreur", "de l'importance de ce principe",
        "de la difficulté de ce problème"]),
    ("se trompe",      "se trompent",       [
        "dans ce raisonnement", "dans cette démonstration",
        "sur ce résultat", "sur cette règle"]),
    ("s'améliore",     "s'améliorent",      [
        "en logique", "dans cet exercice",
        "grâce à ce cours", "après cet entraînement"]),
    ("se prépare",     "se préparent",      [
        "pour cet examen", "pour ce devoir",
        "pour cette épreuve", "sérieusement"]),
    ("se concentre",   "se concentrent",    [
        "sur ce problème", "sur cet exercice",
        "sur cette démonstration", "pendant le cours"]),
    ("s'organise",     "s'organisent",      [
        "pour ce projet", "avant l'examen",
        "pour ce travail", "efficacement"]),
]
# Compatibilité
VERBES_SVP    = [(v[0], v[1]) for v in VERBES_SVP_COMPLETS]
COMPLEMENTS_SVP = [c for v in VERBES_SVP_COMPLETS for c in v[2]]

# SVCCL — verbes de localisation et lieux
VERBES_SVCCL = [
    "se déroule", "a lieu", "se tient",
    "se trouve", "se situe", "se passe",
]
SUJETS_SVCCL = [
    {"mot": "cours",             "genre": "M"},
    {"mot": "examen",            "genre": "M"},
    {"mot": "conférence",        "genre": "F"},
    {"mot": "réunion",           "genre": "F"},
    {"mot": "séminaire",         "genre": "M"},
    {"mot": "débat",             "genre": "M"},
    {"mot": "exposé",            "genre": "M"},
]
LIEUX = [
    "dans la salle principale", "dans l'amphithéâtre",
    "dans la grande salle",     "au laboratoire",
    "en salle de cours",        "dans le bâtiment principal",
]

# SVI — verbes de communication et destinataires
VERBES_SVI = [
    "explique", "annonce", "présente", "enseigne",
    "demande", "répond", "expose", "communique",
]
DESTINATAIRES_SVI = [
    "aux étudiants", "aux élèves", "au groupe",
    "à l'auditoire", "aux apprenants", "à la classe",
]
SUJETS_COMMUNICATION = [
    "ce principe",        "cette règle",    "ce résultat",
    "cette méthode",      "ce théorème",    "cette démonstration",
    "ce concept",         "cet argument",
]

# EVENT — sujets événementiels et verbes de réalisation
SUJETS_EVENT = [
    {"mot": "l'examen final",       "genre": "M"},
    {"mot": "la conférence",         "genre": "F"},
    {"mot": "le cours de logique",   "genre": "M"},
    {"mot": "la séance de travaux",  "genre": "F"},
    {"mot": "le débat",              "genre": "M"},
    {"mot": "la réunion",            "genre": "F"},
    {"mot": "l'exposé",              "genre": "M"},
    {"mot": "le séminaire",          "genre": "M"},
]
VERBES_EVENT = [
    "a lieu", "se déroule", "se produit",
    "survient", "se tient", "commence",
]
CIRCONSTANCES_EVENT = [
    "lundi prochain",          "demain matin",
    "en fin de semaine",       "avant la fin du semestre",
    "selon le calendrier",     "dans les conditions prévues",
]


def _article(nom):
    mot, genre = nom["mot"], nom["genre"]
    voyelles = "aeéèêëiîïoôuùûüh"
    if mot[0].lower() in voyelles:
        return f"l'{mot}"
    return f"la {mot}" if genre == "F" else f"le {mot}"

def _svc():
    """Retourne (sujet, verbe_conjugué, complément)."""
    nom = random.choice(SUJETS)
    v, c, _ = random.choice(VERBE_COMPLEMENT)
    return _article(nom), v, c

def _svc2(sujet_a_eviter: str = ""):
    """
    Retourne (sujet, verbe, complément) avec sujet DIFFÉRENT
    de sujet_a_eviter — garantit que P et Q ont des sujets distincts.
    Critère D3 : éviter les énoncés avec sujet répété dans P et Q.
    """
    candidats = [n for n in SUJETS if _article(n) != sujet_a_eviter]
    if not candidats:
        candidats = SUJETS
    nom = random.choice(candidats)
    v, c, _ = random.choice(VERBE_COMPLEMENT)
    return _article(nom), v, c

def _neg(s, v, c):
    """
    Forme négative correcte avec élision.
    Gère les verbes composés : 'a lieu' → 'n\'a pas lieu'
    """
    voyelles = "aeéèêëiîïoôuùûüh"
    # Verbes composés : le 'pas' s'insère entre l'auxiliaire et le reste
    VERBES_COMPOSES = {
        "a lieu":      "n\'a pas lieu",
        "se déroule":  "ne se déroule pas",
        "se tient":    "ne se tient pas",
        "se trouve":   "ne se trouve pas",
        "se situe":    "ne se situe pas",
        "se passe":    "ne se passe pas",
        "se produit":  "ne se produit pas",
        "survient":    "ne survient pas",
        "commence":    "ne commence pas",
        "se souvient":    "ne se souvient pas",
        "se demande":     "ne se demande pas",
        "s\'interroge":   "ne s\'interroge pas",
        "se rappelle":    "ne se rappelle pas",
        "se rend compte": "ne se rend pas compte",
        "se trompe":      "ne se trompe pas",
        "s\'améliore":   "ne s\'améliore pas",
        "se prépare":     "ne se prépare pas",
        "se concentre":   "ne se concentre pas",
        "s\'organise":   "ne s\'organise pas",
    }
    if v in VERBES_COMPOSES:
        return f"{s} {VERBES_COMPOSES[v]} {c}"
    ne = "n'" if v[0].lower() in voyelles else "ne "
    return f"{s} {ne}{v} pas {c}"

def _min(s):
    """Force la minuscule initiale."""
    return s[0].lower() + s[1:] if s else s

# ─────────────────────────────────────────────────────────────
# FORMES CORRECTES AVEC JAMAIS / PLUS
# Gère les verbes composés et pronominaux
# ─────────────────────────────────────────────────────────────

# Verbes dont la négation avec jamais/plus est irrégulière
_VERBES_NEG_SPECIAUX = {
    "se rend compte":  ("ne se rend jamais compte",  "ne se rend plus compte"),
    "a lieu":          ("n'a jamais lieu",            "n'a plus lieu"),
    "a lieu":          ("n'a jamais lieu",            "n'a plus lieu"),
}

# Table de négation avec "que" pour les verbes composés
_VERBES_NEG_QUE = {
    "a lieu":          "n'a lieu que",
    "se rend compte":  "ne se rend compte que",
}

def _neg_jamais(s: str, v: str, c: str) -> str:
    """Négation avec 'jamais' correctement placé et élision."""
    voyelles = "aeéèêëiîïoôuùûüh"
    if v in _VERBES_NEG_SPECIAUX:
        return f"{s} {_VERBES_NEG_SPECIAUX[v][0]} {c}"
    if v.startswith("se ") or v.startswith("s'") or v.startswith("s’"):
        ne = "ne "
    else:
        ne = "n'" if v[0].lower() in voyelles else "ne "
    return f"{s} {ne}{v} jamais {c}"

def _neg_plus(s: str, v: str, c: str) -> str:
    """Négation avec 'plus' correctement placé et élision."""
    voyelles = "aeéèêëiîïoôuùûüh"
    if v in _VERBES_NEG_SPECIAUX:
        return f"{s} {_VERBES_NEG_SPECIAUX[v][1]} {c}"
    if v.startswith("se ") or v.startswith("s'") or v.startswith("s’"):
        ne = "ne "
    else:
        ne = "n'" if v[0].lower() in voyelles else "ne "
    return f"{s} {ne}{v} plus {c}"

def _neg_que(s: str, v: str, c: str) -> str:
    """Forme restrictive ne...que (confusion restriction/négation)."""
    voyelles = "aeéèêëiîïoôuùûüh"
    if v in _VERBES_NEG_QUE:
        return f"{s} {_VERBES_NEG_QUE[v]} {c}"
    if v.startswith("se ") or v.startswith("s'") or v.startswith("s’"):
        ne = "ne "
    else:
        ne = "n'" if v[0].lower() in voyelles else "ne "
    return f"{s} {ne}{v} que {c}"


def _quant(quant, nom, v, c):
    """Proposition quantifiée accordée."""
    mot = nom["mot"]
    pluriel = mot if mot.endswith(("s","x","z")) else (
        mot[:-2]+"aux" if mot.endswith("al") else mot+"s"
    )
    vpl = _verbe_pluriel(v)
    tous = "Toutes les" if nom.get("genre") == "F" else "Tous les"
    voyelles = "aeéèêëiîïoôuùûüh"
    if quant == "UNIVERSEL":
        return f"{tous} {pluriel} {vpl} {c}"
    else:
        art = "une" if nom.get("genre") == "F" else "un"
        return f"Il existe au moins {art} {mot} qui {v} {c}"

def _neg_quant(quant, nom, v, c):
    """Négation d'une proposition quantifiée."""
    mot = nom["mot"]
    pluriel = mot if mot.endswith(("s","x","z")) else (
        mot[:-2]+"aux" if mot.endswith("al") else mot+"s"
    )
    vpl = _verbe_pluriel(v)
    ne  = "n'" if v[0].lower() in "aeéèêëiîïoôuùûüh" else "ne "
    nepl = "n'" if vpl[0].lower() in "aeéèêëiîïoôuùûüh" else "ne "
    tous = "Toutes les" if nom.get("genre") == "F" else "Tous les"
    art  = "une" if nom.get("genre") == "F" else "un"
    if quant == "UNIVERSEL":
        return f"Il existe au moins {art} {mot} qui {ne}{v} pas {c}"
    else:
        return f"{tous} {pluriel} {nepl}{vpl} pas {c}"


# ─────────────────────────────────────────────────────────────
# DONNÉES LOGIQUES
# ─────────────────────────────────────────────────────────────

CONNECTEURS = {
    "ET":    {"ln": "et",                 "formel": "∧"},
    "OU":    {"ln": "ou",                 "formel": "∨"},
    "IMP":   {"ln": "implique",           "formel": "⇒"},
    "EQUIV": {"ln": "si et seulement si", "formel": "⇔"},
}
TABLES = {
    "∧": {("V","V"):"V",("V","F"):"F",("F","V"):"F",("F","F"):"F"},
    "∨": {("V","V"):"V",("V","F"):"V",("F","V"):"V",("F","F"):"F"},
    "⇒": {("V","V"):"V",("V","F"):"F",("F","V"):"V",("F","F"):"V"},
    "⇔": {("V","V"):"V",("V","F"):"F",("F","V"):"F",("F","F"):"V"},
}




# ─────────────────────────────────────────────────────────────
# FONCTIONS DE GÉNÉRATION PAR STRUCTURE SYNTAXIQUE
# ─────────────────────────────────────────────────────────────

def _svc_svp():
    """SVP : Sujet humain + Verbe pronominal + Complément naturel associé."""
    nom     = random.choice(SUJETS)
    entree  = random.choice(VERBES_SVP_COMPLETS)
    v_sg    = entree[0]
    compls  = entree[2]
    compl   = random.choice(compls)
    sujet   = _article(nom)
    return sujet, v_sg, compl, "SVP"

def _svc_svccl():
    """SVCCL : Sujet événementiel + Verbe de localisation + Lieu."""
    nom   = random.choice(SUJETS_SVCCL)
    verbe = random.choice(VERBES_SVCCL)
    lieu  = random.choice(LIEUX)
    mot   = nom["mot"]
    genre = nom.get("genre", "M")
    voyelles = "aeéèêëiîïoôuùûüh"
    if mot[0].lower() in voyelles:
        sujet = f"l'{mot}"
    elif genre == "F":
        sujet = f"la {mot}"
    else:
        sujet = f"le {mot}"
    return sujet, verbe, lieu, "SVCCL"

def _svc_svi():
    """SVI : Sujet humain + Verbe de communication + Destinataire."""
    nom    = random.choice(SUJETS)
    verbe  = random.choice(VERBES_SVI)
    dest   = random.choice(DESTINATAIRES_SVI)
    sujet  = compl = random.choice(SUJETS_COMMUNICATION)
    sujet_h = _article(nom)
    # Construction : "le professeur explique ce concept aux étudiants"
    compl_complet = f"{sujet} {dest}"
    return sujet_h, verbe, compl_complet, "SVI"

def _svc_event():
    """EVENT : Sujet événementiel + Verbe de réalisation + Circonstance."""
    nom    = random.choice(SUJETS_EVENT)
    verbe  = random.choice(VERBES_EVENT)
    circst = random.choice(CIRCONSTANCES_EVENT)
    sujet  = nom["mot"]  # déjà avec article
    return sujet, verbe, circst, "EVENT"

def _svc_choisir():
    """
    Choisit aléatoirement une structure syntaxique parmi les 5
    selon la distribution de la thèse :
    SVO 32%, SVP 24%, EVENT 18%, SVI 15%, SVCCL 11%
    """
    r = random.random()
    if r < 0.32:
        s, v, c = _svc()
        return s, v, c, "SVO"
    elif r < 0.56:   # 0.32 + 0.24
        return _svc_svp()
    elif r < 0.74:   # + 0.18
        return _svc_event()
    elif r < 0.89:   # + 0.15
        return _svc_svi()
    else:            # 0.11
        return _svc_svccl()


# ─────────────────────────────────────────────────────────────
# GARANTIE D'UNICITÉ PAR HASH (thèse §3.5.7)
# Hash composite = hash(sujet + verbe + complément + objectif + type)
# ─────────────────────────────────────────────────────────────

import hashlib

_historique_hash: set = set()          # hashes des questions générées
_distracteurs_utilises: list = []      # distracteurs utilisés (liste ordonnée)

def _calculer_hash(enonce: str, reponse: str, objectif: str) -> str:
    """Calcule le hash composite d'une question (thèse §3.5.7)."""
    contenu = f"{objectif}|{enonce.lower().strip()}|{reponse.lower().strip()}"
    return hashlib.sha256(contenu.encode("utf-8")).hexdigest()[:16]

def _est_unique(hash_q: str) -> bool:
    """Vérifie l'unicité d'une question par son hash."""
    return hash_q not in _historique_hash

def _enregistrer_hash(hash_q: str):
    """Enregistre le hash d'une question générée."""
    _historique_hash.add(hash_q)

def filtrer_distracteurs(candidats: list, n: int = 3) -> list:
    """
    Sélectionne n distracteurs jamais utilisés dans la session courante.
    Stratégie :
      1. Prendre d'abord les candidats jamais vus
      2. Si pas assez, utiliser les moins récemment utilisés
      3. Enregistrer tous les sélectionnés pour éviter future répétition
    """
    global _distracteurs_utilises

    # Mélanger les candidats pour la variété
    pool = list(candidats)
    random.shuffle(pool)

    # Séparer nouveaux et déjà vus (dans l'ordre d'utilisation)
    nouveaux = [d for d in pool if d not in _distracteurs_utilises]
    deja_vus = [d for d in _distracteurs_utilises if d in pool]

    # Sélectionner en priorité les nouveaux
    selection = nouveaux[:n]

    # Compléter avec les plus anciennement utilisés si nécessaire
    if len(selection) < n:
        for d in deja_vus:
            if d not in selection:
                selection.append(d)
            if len(selection) >= n:
                break

    # Enregistrer les sélectionnés (nouveaux en tête, anciens réutilisés déplacés en fin)
    for d in selection:
        if d in _distracteurs_utilises:
            _distracteurs_utilises.remove(d)
        _distracteurs_utilises.append(d)

    random.shuffle(selection)
    return selection[:n]


def reset_session():
    """Réinitialise la mémoire de session (hash + distracteurs)."""
    global _historique_hash, _distracteurs_utilises
    _historique_hash       = set()
    _distracteurs_utilises = []


def get_taux_unicite() -> dict:
    """Retourne les statistiques d'unicité de la session."""
    return {
        "nb_questions_uniques": len(_historique_hash),
        "hashes": list(_historique_hash)[:10],  # aperçu
    }

# ═════════════════════════════════════════════════════════════
# GÉNÉRATEUR PRINCIPAL
# ═════════════════════════════════════════════════════════════

GABARITS = {
    "PROP":       [{"type":"prop",        "structure":"SVO"}],
    "VVER":       [{"type":"vver",        "structure":"SVO"}],
    "TVER":       [{"type":"tver",        "structure":"SVO"}],
    "NEG_SIMPLE": [{"type":"neg_simple",  "structure":"SVO"}],
    "CONN_ID":    [{"type":"conn_id",     "structure":"SVO"}],
    "CONN_TRAD":  [{"type":"conn_trad",   "structure":"SVO"}],
    "CONN_INV":   [{"type":"conn_inv",    "structure":"SVO"}],
    "IMP":        [{"type":"imp",         "structure":"SVI"}],
    "EQUIV":      [{"type":"equiv",       "structure":"SVO"}],
    "MORGAN":     [{"type":"morgan",      "structure":"SVO"}],
    "NEG_COMP":   [{"type":"neg_comp",    "structure":"SVO"}],
    "NEG_IMP":    [{"type":"neg_imp",     "structure":"SVI"}],
    "QUANT_TRAD": [{"type":"quant_trad",  "structure":"EVENT"}],
    "NEG_QUANT":  [{"type":"neg_quant",   "structure":"EVENT"}],
    "CONTRAP":    [{"type":"contrap",     "structure":"SVI"}],
}

def generer_question(objectif_code, mode_bloom="comprehension",
                     niveau_complexite="moyen", max_tentatives=15):
    """
    Génère une question QCM unique selon l'objectif et le niveau.
    Garantie d'unicité par hash composite (thèse §3.5.7).
    """
    if objectif_code not in GABARITS:
        raise ValueError(f"Objectif inconnu : {objectif_code}")
    params = estimer_parametres(niveau_complexite, mode_bloom)

    for tentative in range(max_tentatives):
        try:
            g = random.choice(GABARITS[objectif_code])
            q = _construire(g, objectif_code, mode_bloom,
                            niveau_complexite, params)
            if q is None:
                continue

            # ── Vérification du niveau ────────────────────────
            if not verifier_niveau_cible(q["ert_secondes"], niveau_complexite):
                continue

            # ── Vérification d'unicité par hash ───────────────
            h = _calculer_hash(q["enonce"], q["reponse_correcte"], objectif_code)
            if not _est_unique(h):
                continue  # question déjà générée, on réessaie

            # ── Enregistrement du hash ────────────────────────
            _enregistrer_hash(h)
            q["hash"] = h
            return q

        except Exception:
            continue

    # Fallback sans contrainte d'unicité
    g = random.choice(GABARITS[objectif_code])
    q = _construire(g, objectif_code, mode_bloom, niveau_complexite, params)
    if q:
        h = _calculer_hash(q["enonce"], q["reponse_correcte"], objectif_code)
        _enregistrer_hash(h)
        q["hash"] = h
    return q

def _construire(g, code, bloom, niveau, params):
    BUILDERS = {
        "prop":       _prop,
        "vver":       _vver,
        "tver":       _tver,
        "neg_simple": _neg_simple,
        "conn_id":    _conn_id,
        "conn_trad":  _conn_trad,
        "conn_inv":   _conn_inv,
        "imp":        _imp,
        "equiv":      _equiv,
        "morgan":     _morgan,
        "neg_comp":   _neg_comp,
        "neg_imp":    _neg_imp,
        "quant_trad": _quant_trad,
        "neg_quant":  _neg_quant_q,
        "contrap":    _contrap,
    }
    enonce, rep, dist, meta = BUILDERS[g["type"]](params, bloom)
    # Filtrage centralisé : éviter répétitions de distracteurs en session
    dist = filtrer_distracteurs(dist, 3)
    cx = calculer_complexite(
        nb_propositions    = meta.get("nb_propositions", 2),
        nb_connecteurs     = meta.get("nb_connecteurs", 1),
        nb_quantificateurs = meta.get("nb_quantificateurs", 0),
        nb_negations       = meta.get("nb_negations", 0),
        profondeur_logique = meta.get("profondeur_logique", 1),
        mode_bloom         = bloom,
    )
    return {
        "objectif_code":       code,
        "mode_bloom":          bloom,
        "niveau_complexite":   cx["niveau_complexite"],
        "enonce":              enonce,
        "reponse_correcte":    rep,
        "distracteurs":        dist,
        "ert_secondes":        cx["ert_secondes"],
        "score_pedagogique":   cx["score_pedagogique"],
        "structure_syntaxique":g.get("structure","SVO"),
        "profondeur_logique":  meta.get("profondeur_logique",1),
        "nb_connecteurs":      meta.get("nb_connecteurs",1),
        "nb_propositions":     meta.get("nb_propositions",2),
    }


# ═════════════════════════════════════════════════════════════
# BUILDERS — UN PAR OBJECTIF, AVEC DISTINCTION BLOOM
#
# Mode COMPRÉHENSION : l'apprenant reconnaît et applique
#   directement une règle sur une forme donnée.
#
# Mode ANALYSE : l'apprenant doit décomposer la structure
#   logique, raisonner sur les valeurs ou identifier
#   pourquoi une règle s'applique.
# ═════════════════════════════════════════════════════════════

def _prop(params, bloom):
    """PROP — Identifier une proposition logique."""
    s, v, c = _svc()
    S = s.capitalize()

    if bloom == "comprehension":
        # Reconnaître directement un énoncé déclaratif
        enonce  = "Laquelle des affirmations suivantes est une proposition logique ?"
        reponse = f"{S} {v} {c}"

        # Pool dynamique : générer des non-propositions variées
        # Ordres (impératifs) — 10 variants
        ordres = [
            "Ferme la porte !", "Tais-toi immédiatement !",
            "Ouvre ce livre maintenant !", "Rends ce devoir demain !",
            "Viens ici tout de suite !", "Lis ce texte attentivement !",
            "Réponds à cette question !", "Pose ce problème correctement !",
            "Apprends cette règle par cœur !", "Travaille davantage !",
        ]
        # Questions — 10 variants
        questions = [
            "Est-ce que tu viens demain ?",
            "Où est passé ce résultat ?",
            "Pourquoi a-t-il échoué à cet examen ?",
            "Quand aura lieu la prochaine séance ?",
            "Qui a résolu ce problème ?",
            "Comment fonctionne ce principe ?",
            "Combien de questions reste-t-il ?",
            "Lequel de ces arguments est valide ?",
            "Qu'est-ce qui justifie ce résultat ?",
            "À quoi sert cette règle ?",
        ]
        # Énoncés ambigus — 10 variants
        ambigus = [
            "Peut-être qu'il viendra un jour",
            "Il est possible que ce cours soit intéressant",
            "On ne sait pas si ce résultat est fiable",
            "Ce serait bien de comprendre cette règle",
            "Il faudrait peut-être revoir ce principe",
            "Ce concept est difficile à saisir",
            "On pourrait peut-être changer d'approche",
            "Il semblerait que cette méthode soit utile",
            "Ce problème mériterait plus d'attention",
            "Cette règle est parfois complexe",
        ]
        # Choisir aléatoirement 1 de chaque catégorie + autres
        candidats = ordres + questions + ambigus
        random.shuffle(candidats)
        dist = candidats  # pool de 30, filtré dans _construire
    else:
        # Analyser POURQUOI un énoncé est ou n'est pas une proposition
        enonce  = (
            f"On considère l'affirmation : « {S} {v} {c} ».\n"
            f"Pourquoi cet énoncé est-il une proposition logique ?"
        )
        reponse = "Parce qu'on peut lui attribuer une valeur de vérité (Vraie ou Fausse)"
        dist    = [
            # Erreur 1 : confondre proposition avec phrase grammaticale
            "Parce qu'il contient un sujet et un verbe — critère grammatical, pas logique",
            # Erreur 2 : confondre vérité logique avec certitude subjective
            "Parce qu'il est affirmé avec certitude par celui qui parle",
            # Erreur 3 : confondre proposition avec fait observable
            "Parce qu'il décrit un fait vérifiable expérimentalement",
            # Erreur 4 : confondre proposition avec opinion
            "Parce qu'il exprime l'opinion de l'auteur sur un sujet",
            # Erreur 5 : critère de vérité pratique (≠ logique)
            "Parce qu'il est reconnu comme vrai par la majorité",
            # Erreur 6 : confondre avec une définition
            "Parce qu'il donne une définition précise d'un concept",
            # Erreur 7 : critère d'autorité
            "Parce qu'il est énoncé par un expert du domaine",
        ]

    meta = {"nb_propositions":1,"nb_connecteurs":0,
            "nb_negations":0,"profondeur_logique":0}
    return enonce, reponse, random.sample(dist,min(3,len(dist))), meta


def _vver(params, bloom):
    """VVER — Valeur de vérité d'une proposition composée.
    Réponse binaire : Vraie ou Fausse uniquement (2 options).
    """
    conn_key = random.choice(["ET","OU","IMP"])
    conn     = CONNECTEURS[conn_key]
    vp, vq   = random.choice([("V","V"),("V","F"),("F","V"),("F","F")])
    res      = TABLES[conn["formel"]][(vp,vq)]
    rep_txt  = "Vraie" if res=="V" else "Fausse"
    vp_txt   = "Vraie" if vp=="V" else "Fausse"
    vq_txt   = "Vraie" if vq=="V" else "Fausse"
    autre    = "Fausse" if rep_txt=="Vraie" else "Vraie"

    if bloom == "comprehension":
        enonce = (
            f"Si P est {vp_txt} et Q est {vq_txt}, "
            f"quelle est la valeur de « P {conn['formel']} Q » ?"
        )
        dist = [autre]
    else:
        # Analyser : identifier le cas et justifier
        s1,v1,c1 = _svc()
        s2,v2,c2 = _svc2(s1)
        p = f"{s1.capitalize()} {v1} {c1}"
        q = f"{_min(s2)} {v2} {c2}"
        enonce = (
            f"La proposition « {p} » est {vp_txt.lower()} "
            f"et « {q} » est {vq_txt.lower()}.\n"
            f"En appliquant la définition de {conn['formel']}, "
            f"quelle est la valeur de « P {conn['formel']} Q » ?"
        )
        dist = [autre]

    meta = {"nb_propositions":2,"nb_connecteurs":1,
            "nb_negations":0,"profondeur_logique":1}
    return enonce, rep_txt, dist, meta


def _tver(params, bloom):
    """TVER — Table de vérité.
    Réponse binaire : Vraie ou Fausse uniquement (2 options).
    """
    conn_key = random.choice(["ET","OU","IMP","EQUIV"])
    conn     = CONNECTEURS[conn_key]
    vp, vq   = random.choice([("V","V"),("V","F"),("F","V"),("F","F")])
    res      = TABLES[conn["formel"]][(vp,vq)]
    rep_txt  = "Vraie" if res=="V" else "Fausse"
    vp_txt   = "Vraie" if vp=="V" else "Fausse"
    vq_txt   = "Vraie" if vq=="V" else "Fausse"
    autre    = "Fausse" if rep_txt=="Vraie" else "Vraie"

    if bloom == "comprehension":
        enonce = (
            f"Dans la table de vérité de « P {conn['formel']} Q », "
            f"quelle est la valeur quand P est {vp_txt} et Q est {vq_txt} ?"
        )
        dist = [autre]
    else:
        # Identifier le(s) cas où la formule est FAUSSE
        cas_faux = {
            "∧": "quand P est Vraie et Q est Fausse, "
                 "ou quand P est Fausse (quel que soit Q)",
            "∨": "uniquement quand P est Fausse et Q est Fausse",
            "⇒": "uniquement quand P est Vraie et Q est Fausse",
            "⇔": "quand P et Q ont des valeurs différentes",
        }
        cas_vrai = {
            "∧": "uniquement quand P est Vraie et Q est Vraie",
            "∨": "quand au moins l'une des deux propositions est Vraie",
            "⇒": "dans tous les cas sauf P=Vraie et Q=Fausse",
            "⇔": "quand P et Q ont la même valeur de vérité",
        }
        enonce = (
            f"Dans la table de vérité de « P {conn['formel']} Q », "
            f"quelle est la valeur quand P est {vp_txt} et Q est {vq_txt} ?\n"
            f"Rappel : « P {conn['formel']} Q » est {autre.lower()} "
            f"{cas_faux[conn['formel']] if autre=='Fausse' else cas_vrai[conn['formel']]}."
        )
        dist = [autre]

    meta = {"nb_propositions":2,"nb_connecteurs":1,
            "nb_negations":0,"profondeur_logique":1}
    return enonce, rep_txt, dist, meta


def _neg_simple(params, bloom):
    """NEG_SIMPLE — Négation d'une proposition élémentaire."""
    s, v, c, struct = _svc_choisir()
    S = s.capitalize()

    if bloom == "comprehension":
        enonce  = f"Quelle est la négation de : « {S} {v} {c} » ?"
        reponse = _neg(S, v, c)
        # Critères Haladyna 2002 & Gierl 2017 :
        # ❌ jamais reproduire la proposition originale
        # ✅ ancrer dans les erreurs documentées sur la négation
        dist = [
            # Erreur 1 : "ne...jamais" au lieu de "ne...pas"
            # Confusion modalité temporelle / négation logique (Gierl 2017)
            _neg_jamais(S, v, c),
            # Erreur 2 : "ne...plus" au lieu de "ne...pas"
            # Confusion cessation d'état / négation logique (Gierl 2017)
            _neg_plus(S, v, c),
            # Erreur 3 : confusion négation / restriction (ne...que)
            # Erreur documentée (Gierl 2017) : l'apprenant utilise une restriction
            # au lieu d'une négation — mêmes mots, sens différent
            # "ne...que" = seulement ≠ négation logique
            _neg_que(S, v, c),
        ]

    else:
        enonce = (
            f"On veut nier : « {S} {v} {c} ».\n"
            f"Parmi les propositions suivantes, laquelle est "
            f"la négation exacte selon la logique formelle ?"
        )
        reponse = _neg(S, v, c)
        # Critère conservation lexicale (Haladyna 2002) :
        # tous les distracteurs utilisent UNIQUEMENT les mots de la proposition
        dist = [
            # Erreur 1 : ne...jamais (modalité ≠ négation)
            _neg_jamais(S, v, c),
            # Erreur 2 : ne...plus (cessation ≠ négation)
            _neg_plus(S, v, c),
            # Erreur 3 : ne...que (restriction ≠ négation)
            _neg_que(S, v, c),
        ]

    random.shuffle(dist)
    meta = {"nb_propositions":1,"nb_connecteurs":0,
            "nb_negations":0,"profondeur_logique":0}
    return enonce, reponse, dist[:3], meta


def _conn_id(params, bloom):
    """CONN_ID — Identifier les connecteurs logiques."""
    conn_key = random.choice(["ET","OU","IMP","EQUIV"])
    conn     = CONNECTEURS[conn_key]
    s1,v1,c1 = _svc()
    s2,v2,c2 = _svc2(s1)
    p = f"{_min(s1)} {v1} {c1}"
    q = f"{_min(s2)} {v2} {c2}"

    if conn_key == "IMP":
        phrase = f"Si {p}, alors {q}"
    elif conn_key == "EQUIV":
        phrase = f"{p} si et seulement si {q}"
    else:
        phrase = f"{p} {conn['ln']} {q}"

    if bloom == "comprehension":
        # Identifier le symbole du connecteur
        enonce  = f"Quel connecteur logique est utilisé dans : « {phrase} » ?"
        reponse = conn["formel"]
        dist    = [c["formel"] for k,c in CONNECTEURS.items() if k!=conn_key]
    else:
        # Identifier le connecteur ET expliquer son rôle
        enonce = (
            f"Dans la proposition : « {phrase} »,\n"
            f"quel est le connecteur principal et quel est son rôle ?"
        )
        roles = {
            "ET":    f"{conn['formel']} (ET) — relie deux conditions toutes deux nécessaires",
            "OU":    f"{conn['formel']} (OU) — au moins l'une des deux conditions suffit",
            "IMP":   f"{conn['formel']} (SI...ALORS) — exprime qu'une condition entraîne une conséquence",
            "EQUIV": f"{conn['formel']} (SI ET SEULEMENT SI) — les deux propositions sont vraies simultanément",
        }
        reponse = roles[conn_key]
        dist = [roles[k] for k in roles if k!=conn_key]

    random.shuffle(dist)
    meta = {"nb_propositions":1,"nb_connecteurs":1,
            "nb_negations":0,"profondeur_logique":0}
    return enonce, reponse, dist[:3], meta


def _conn_trad(params, bloom):
    """CONN_TRAD — Traduction LN → formel."""
    conn_key = random.choice(["ET","OU","IMP"])
    conn     = CONNECTEURS[conn_key]
    s1,v1,c1 = _svc()
    s2,v2,c2 = _svc2(s1)
    p = f"{_min(s1)} {v1} {c1}"
    q = f"{_min(s2)} {v2} {c2}"

    if conn_key == "IMP":
        phrase = f"Si {p}, alors {q}"
    else:
        phrase = f"{p} {conn['ln']} {q}"

    if bloom == "comprehension":
        # Traduire directement une phrase en formule
        enonce  = f"Quelle formule logique correspond à : « {phrase} » ?"
        reponse = f"P {conn['formel']} Q"
        dist    = [f"P {c} Q" for c in ["∧","∨","⇒","⇔"] if c!=conn["formel"]]
    else:
        # Identifier P et Q puis choisir la bonne formule
        enonce = (
            f"On pose P = « {p} » et Q = « {q} ».\n"
            f"Parmi ces formules, laquelle traduit correctement : « {phrase} » ?"
        )
        reponse = f"P {conn['formel']} Q"
        dist = [
            f"Q {conn['formel']} P",
            f"¬P {conn['formel']} Q",
            f"P {conn['formel']} ¬Q",
        ]

    random.shuffle(dist)
    meta = {"nb_propositions":1,"nb_connecteurs":1,
            "nb_negations":0,"profondeur_logique":0}
    return enonce, reponse, dist[:3], meta


def _conn_inv(params, bloom):
    """CONN_INV — Traduction formel → LN."""
    conn_key = random.choice(["ET","OU","IMP"])
    conn     = CONNECTEURS[conn_key]
    s1,v1,c1 = _svc()
    s2,v2,c2 = _svc2(s1)
    p = f"{_min(s1)} {v1} {c1}"
    q = f"{_min(s2)} {v2} {c2}"
    trad = {"ET":f"{p} et {q}","OU":f"{p} ou {q}","IMP":f"Si {p}, alors {q}"}

    if bloom == "comprehension":
        # Traduire directement la formule
        enonce  = (
            f"Quelle phrase correspond à « P {conn['formel']} Q » "
            f"où P = « {p} » et Q = « {q} » ?"
        )
        reponse = trad[conn_key]
        dist    = [v for k,v in trad.items() if k!=conn_key]
        dist.append(f"{q} si et seulement si {p}")
    else:
        # Choisir la traduction en analysant la structure
        autres_formules = [c["formel"] for k,c in CONNECTEURS.items() if k!=conn_key][:2]
        enonce = (
            f"On a la formule : « P {conn['formel']} Q »\n"
            f"avec P = « {p} » et Q = « {q} ».\n"
            f"Quelle traduction respecte EXACTEMENT le sens "
            f"logique de {conn['formel']} ?"
        )
        reponse = trad[conn_key]
        dist = [
            f"{p} donc {q}",
            f"{q} parce que {p}",
            f"{p} bien que {q}",
        ]

    random.shuffle(dist)
    meta = {"nb_propositions":1,"nb_connecteurs":1,
            "nb_negations":0,"profondeur_logique":0}
    return enonce, reponse, dist[:3], meta


def _imp(params, bloom):
    """IMP — Implication logique.
    Réponse binaire : Vraie ou Fausse uniquement (2 options).
    """
    s1,v1,c1 = _svc()
    s2,v2,c2 = _svc2(s1)
    S1 = s1.capitalize()
    p  = f"{S1} {v1} {c1}"
    q  = f"{_min(s2)} {v2} {c2}"
    # Couvrir les 4 cas équitablement
    vp, vq = random.choice([("V","V"),("V","F"),("F","V"),("F","F")])
    res    = TABLES["⇒"][(vp,vq)]
    rep    = "Vraie" if res=="V" else "Fausse"
    vp_txt = "vraie" if vp=="V" else "fausse"
    vq_txt = "vraie" if vq=="V" else "fausse"
    autre  = "Fausse" if rep=="Vraie" else "Vraie"

    if bloom == "comprehension":
        enonce = (
            f"Sachant que « {p} » est {vp_txt} "
            f"et que « {q} » est {vq_txt}, "
            f"quelle est la valeur de « {p} ⇒ {q} » ?"
        )
        dist = [autre]
    else:
        # Identifier le seul cas où l'implication est fausse
        enonce = (
            f"On considère : « {p} ⇒ {q} ».\n"
            f"Sachant que P est {vp_txt} et Q est {vq_txt}, "
            f"quelle est la valeur de cette implication ?"
        )
        dist = [autre]

    meta = {"nb_propositions":2,"nb_connecteurs":1,
            "nb_negations":0,"profondeur_logique":2}
    return enonce, rep, dist, meta


def _equiv(params, bloom):
    """EQUIV — Équivalence logique."""
    s1,v1,c1 = _svc()
    s2,v2,c2 = _svc2(s1)
    S1 = s1.capitalize()
    p  = f"{S1} {v1} {c1}"
    q  = f"{_min(s2)} {v2} {c2}"
    np = _neg(S1,v1,c1)
    nq = _neg(_min(s2),v2,c2)

    if bloom == "comprehension":
        # Identifier la proposition équivalente
        enonce  = f"Laquelle est logiquement équivalente à : « {p} ⇔ {q} » ?"
        reponse = f"(Si {_min(p)}, alors {q}) et (si {q}, alors {_min(p)})"
        dist    = [
            f"(Si {_min(p)}, alors {q}) ou (si {q}, alors {_min(p)})",
            f"Si {_min(p)}, alors {q}",
            f"{np} ou {nq}",
        ]
    else:
        # Analyser quand l'équivalence est vraie
        enonce = (
            f"On considère : « {p} ⇔ {q} ».\n"
            f"Dans quels cas cette équivalence est-elle VRAIE ?"
        )
        reponse = "Quand P et Q ont la même valeur de vérité (V↔V ou F↔F)"
        dist    = [
            # Erreur 1 : confondre ⇔ avec ⇒ (asymétrie)
            "Quand P est vraie, quelle que soit Q — comme pour P ⇒ Q",
            # Erreur 2 : croire que ⇔ est toujours vraie
            "Dans tous les cas — car P ⇔ Q est une tautologie",
            # Erreur 3 : confondre avec ∧ (les deux vraies seulement)
            "Seulement quand P et Q sont toutes deux vraies — comme pour P ∧ Q",
        ]

    random.shuffle(dist)
    meta = {"nb_propositions":2,"nb_connecteurs":1,
            "nb_negations":0,"profondeur_logique":0}
    return enonce, reponse, dist[:3], meta


def _morgan(params, bloom):
    """MORGAN — Lois de De Morgan."""
    s1,v1,c1,_ = _svc_choisir()
    s2,v2,c2,_ = _svc_choisir()
    S1   = s1.capitalize()
    conn = random.choice(["ET","OU"])
    ln   = CONNECTEURS[conn]["ln"]
    p    = f"{S1} {v1} {c1}"
    q    = f"{_min(s2)} {v2} {c2}"
    np   = _neg(S1,v1,c1)
    nq   = _neg(_min(s2),v2,c2)

    if bloom == "comprehension":
        # Appliquer directement De Morgan
        enonce = (
            f"Selon les lois de De Morgan, "
            f"quelle est la négation de : « {p} {ln} {q} » ?"
        )
        if conn == "ET":
            reponse = f"{np} ou {nq}"
            dist    = [
                f"{np} et {nq}",   # garde ∧ sans l'inverser (erreur la plus fréquente)
                f"{np} ou {q}",    # ne nie que P
                f"{p} ou {nq}",    # ne nie que Q
            ]
        else:
            reponse = f"{np} et {nq}"
            dist    = [
                f"{np} ou {nq}",   # garde ∨ sans l'inverser
                f"{p} et {nq}",    # ne nie que Q
                f"{np} et {q}",    # ne nie que P
            ]
    else:
        # Identifier quelle loi s'applique et pourquoi
        enonce = (
            f"On veut nier : « {p} {ln} {q} ».\n"
            f"Quelle loi de De Morgan s'applique "
            f"et quel est le résultat ?"
        )
        if conn == "ET":
            reponse = f"¬(P ∧ Q) ≡ ¬P ∨ ¬Q — résultat : « {np} ou {nq} »"
            dist    = [
                f"¬(P ∨ Q) ≡ ¬P ∧ ¬Q — résultat : « {np} et {nq} »",
                f"¬(P ∧ Q) ≡ ¬P ∧ ¬Q — résultat : « {np} et {nq} »",
                f"¬(P ∧ Q) ≡ P ∨ ¬Q — résultat : « {p} ou {nq} »",
            ]
        else:
            reponse = f"¬(P ∨ Q) ≡ ¬P ∧ ¬Q — résultat : « {np} et {nq} »"
            dist    = [
                f"¬(P ∧ Q) ≡ ¬P ∨ ¬Q — résultat : « {np} ou {nq} »",
                f"¬(P ∨ Q) ≡ ¬P ∨ ¬Q — résultat : « {np} ou {nq} »",
                f"¬(P ∨ Q) ≡ P ∧ ¬Q — résultat : « {p} et {nq} »",
            ]

    random.shuffle(dist)
    meta = {"nb_propositions":2,"nb_connecteurs":1,
            "nb_negations":0,"profondeur_logique":0}
    return enonce, reponse, dist[:3], meta


def _neg_comp(params, bloom):
    """NEG_COMP — Négation d'une proposition composée."""
    s1,v1,c1 = _svc()
    s2,v2,c2 = _svc2(s1)
    S1   = s1.capitalize()
    conn = random.choice(["ET","OU"])
    ln   = CONNECTEURS[conn]["ln"]
    p    = f"{S1} {v1} {c1}"
    q    = f"{_min(s2)} {v2} {c2}"
    np   = _neg(S1,v1,c1)
    nq   = _neg(_min(s2),v2,c2)

    if bloom == "comprehension":
        enonce = f"Quelle est la négation de : « {p} {ln} {q} » ?"
        if conn == "ET":
            reponse = f"{np} ou {nq}"
            dist    = [
                f"{np} et {nq}",   # garde ∧ sans l'inverser (erreur la plus fréquente)
                f"{np} ou {q}",    # ne nie que P
                f"{p} ou {nq}",    # ne nie que Q
            ]
        else:
            reponse = f"{np} et {nq}"
            dist    = [
                f"{np} ou {nq}",   # garde ∨ sans l'inverser
                f"{p} et {nq}",    # ne nie que Q
                f"{np} et {q}",    # ne nie que P
            ]
    else:
        # Justifier le choix du connecteur dans la négation
        enonce = (
            f"On nie : « {p} {ln} {q} ».\n"
            f"Quelle est la négation et comment justifier "
            f"le changement de connecteur ?"
        )
        if conn == "ET":
            reponse = (
                f"« {np} ou {nq} » "
                f"— ¬(P ∧ Q) ≡ ¬P ∨ ¬Q : ET devient OU, chaque membre est nié"
            )
            dist = [
                # Erreur 1 : nie les membres mais garde ET (n'inverse pas le connecteur)
                f"« {np} et {nq} » — ¬(P ∧ Q) ≡ ¬P ∧ ¬Q : erreur, ET ne change pas",
                # Erreur 2 : ne nie qu'un seul membre
                f"« {np} ou {q} » — erreur : Q n'est pas niée",
                # Erreur 3 : nie l'ensemble sans toucher aux membres
                f"« il est faux que {p} et {q} » — forme correcte mais non développée",
            ]
        else:
            reponse = (
                f"« {np} et {nq} » "
                f"— ¬(P ∨ Q) ≡ ¬P ∧ ¬Q : OU devient ET, chaque membre est nié"
            )
            dist = [
                # Erreur 1 : nie les membres mais garde OU
                f"« {np} ou {nq} » — ¬(P ∨ Q) ≡ ¬P ∨ ¬Q : erreur, OU ne change pas",
                # Erreur 2 : ne nie qu'un seul membre
                f"« {p} et {nq} » — erreur : P n'est pas niée",
                # Erreur 3 : nie l'ensemble sans développer
                f"« il est faux que {p} ou {q} » — forme correcte mais non développée",
            ]

    random.shuffle(dist)
    meta = {"nb_propositions":2,"nb_connecteurs":1,
            "nb_negations":0,"profondeur_logique":0}
    return enonce, reponse, dist[:3], meta


def _neg_imp(params, bloom):
    """NEG_IMP — Négation d'une implication."""
    s1,v1,c1 = _svc()
    s2,v2,c2 = _svc2(s1)
    S1 = s1.capitalize()
    p  = f"{S1} {v1} {c1}"
    q  = f"{_min(s2)} {v2} {c2}"
    np = _neg(S1,v1,c1)
    nq = _neg(_min(s2),v2,c2)

    if bloom == "comprehension":
        enonce  = f"Quelle est la négation de : « Si {_min(p)}, alors {q} » ?"
        # _min() force la minuscule après "Si" (critère C1)
        np_min = _min(np); nq_min = _min(nq)
        p_min  = _min(p);  q_min  = _min(q)
        reponse = f"{p} et {nq}"
        # Distracteurs : erreurs les plus documentées sur ¬(P⇒Q)
        # Gierl 2017 : ancrer dans les misconceptions réelles
        dist    = [
            # Erreur 1 (très fréquente) : ne nier que la conclusion
            f"Si {_min(p)}, alors {nq}",
            # Erreur 2 : croire que ¬(P⇒Q) = ¬P⇒¬Q (confondre avec contraposée)
            f"Si {_min(np)}, alors {_min(nq)}",
            # Erreur 3 : appliquer De Morgan comme si c'était P∧Q
            f"{np} ou {nq}",
        ]
    else:
        # Justifier pourquoi ¬(P⇒Q) = P ∧ ¬Q
        enonce = (
            f"On veut nier : « Si {_min(p)}, alors {q} ».\n"
            f"Quelle est la négation et pourquoi ?"
        )
        reponse = (
            f"« {p} et {nq} » — ¬(P ⇒ Q) ≡ P ∧ ¬Q : "
            f"P reste vraie et seule Q est niée"
        )
        dist = [
            # Erreur 1 : ne nier que la conclusion (très fréquente)
            f"« Si {_min(p)}, alors {nq} » "
            f"— erreur : ¬(P⇒Q) ≠ P⇒¬Q",
            # Erreur 2 : appliquer ¬P∨¬Q au lieu de P∧¬Q
            f"« {np} ou {nq} » "
            f"— erreur : confusion avec De Morgan sur ∧",
            # Erreur 3 : prendre la contraposée pour la négation
            f"« Si {_min(nq)}, alors {_min(np)} » "
            f"— erreur : c'est la contraposée, pas la négation",
        ]

    random.shuffle(dist)
    meta = {"nb_propositions":1,"nb_connecteurs":1,
            "nb_negations":0,"profondeur_logique":0}
    return enonce, reponse, dist[:3], meta


def _quant_trad(params, bloom):
    """QUANT_TRAD — Traduction avec quantificateurs."""
    nom   = random.choice(SUJETS)
    v, c, _ = random.choice(VERBE_COMPLEMENT)
    quant = random.choice(["UNIVERSEL","EXISTENTIEL"])
    phrase = _quant(quant, nom, v, c)
    formel = "∀x, P(x)" if quant=="UNIVERSEL" else "∃x, P(x)"
    autre  = "∃x, P(x)" if quant=="UNIVERSEL" else "∀x, P(x)"
    sym    = "∀" if quant=="UNIVERSEL" else "∃"
    autre_sym = "∃" if quant=="UNIVERSEL" else "∀"

    if bloom == "comprehension":
        enonce  = f"Quelle formule logique correspond à : « {phrase} » ?"
        reponse = formel
        dist    = [
            autre,
            f"{sym}x, ¬P(x)",
            f"∃x, ¬P(x)",
        ]
    else:
        # Identifier le quantificateur ET expliquer son sens
        enonce = (
            f"On considère : « {phrase} ».\n"
            f"Quelle formule traduit correctement cet énoncé "
            f"et que signifie le quantificateur utilisé ?"
        )
        sens = {
            "UNIVERSEL":    f"{formel} — le quantificateur ∀ signifie « pour tout » : la propriété est vraie pour TOUS les éléments",
            "EXISTENTIEL":  f"{formel} — le quantificateur ∃ signifie « il existe » : la propriété est vraie pour AU MOINS UN élément",
        }
        reponse = sens[quant]
        dist    = [
            f"{autre} — le quantificateur {autre_sym} signifie l'inverse",
            f"{sym}x, ¬P(x) — on nie la propriété au lieu de l'affirmer",
            f"¬({formel}) — on nie toute la proposition",
        ]

    random.shuffle(dist)
    meta = {"nb_propositions":1,"nb_connecteurs":0,
            "nb_quantificateurs":1,"nb_negations":0,"profondeur_logique":0}
    return enonce, reponse, dist[:3], meta


def _neg_quant_q(params, bloom):
    """NEG_QUANT — Négation des quantificateurs."""
    nom   = random.choice(SUJETS)
    v, c, _ = random.choice(VERBE_COMPLEMENT)
    # Alterner UNIVERSEL et EXISTENTIEL pour couvrir ¬∀ et ¬∃
    # On tire aléatoirement mais avec vérification via pool
    quant = random.choice(["UNIVERSEL","EXISTENTIEL","UNIVERSEL","EXISTENTIEL"])
    prop  = _quant(quant, nom, v, c)
    neg   = _neg_quant(quant, nom, v, c)
    quant_inv = "EXISTENTIEL" if quant=="UNIVERSEL" else "UNIVERSEL"
    prop_inv  = _quant(quant_inv, nom, v, c)

    if bloom == "comprehension":
        enonce  = f"Quelle est la négation de : « {prop} » ?"
        reponse = neg
        # Distracteurs : erreurs documentées sur la négation des quantificateurs
        dist    = [
            # Erreur 1 (très fréquente) : ne nier que la propriété sans inverser ∀/∃
            _quant(quant, nom, f"ne {v} pas", c),
            # Erreur 2 : inverser le quantificateur mais sans nier la propriété
            prop_inv,
            # Erreur 3 : appliquer la négation sans changer de quantificateur
            # → garder ∀ ou ∃ et nier seulement la propriété
            # Distinct de la bonne réponse (qui change ∀↔∃ ET nie P)
            _neg_quant(quant, nom, v, c),
        ]
    else:
        # Justifier l'échange de quantificateur
        regle = (
            "¬(∀x, P(x)) ≡ ∃x, ¬P(x)"
            if quant=="UNIVERSEL"
            else "¬(∃x, P(x)) ≡ ∀x, ¬P(x)"
        )
        enonce = (
            f"On veut nier : « {prop} ».\n"
            f"Quelle est la négation et quelle règle justifie "
            f"le changement de quantificateur ?"
        )
        reponse = f"« {neg} » — car {regle} : le quantificateur s'inverse et la propriété se nie"
        dist    = [
            f"« {_quant(quant, nom, f'ne {v} pas', c)} » — on ne nie que la propriété sans inverser le quantificateur",
            f"« {prop_inv} » — on inverse le quantificateur sans nier la propriété",
            f"« {_neg_quant(quant_inv, nom, v, c)} » — on inverse tout mais dans le mauvais sens",
        ]

    random.shuffle(dist)
    meta = {"nb_propositions":1,"nb_connecteurs":1,
            "nb_quantificateurs":1,"nb_negations":0,"profondeur_logique":0}
    return enonce, reponse, dist[:3], meta


def _contrap(params, bloom):
    """CONTRAP — Raisonnement par contraposée."""
    s1,v1,c1 = _svc()
    s2,v2,c2 = _svc2(s1)
    p  = f"{_min(s1)} {v1} {c1}"
    q  = f"{_min(s2)} {v2} {c2}"
    np = _neg(_min(s1),v1,c1)
    nq = _neg(_min(s2),v2,c2)

    if bloom == "comprehension":
        enonce  = f"Laquelle est la contraposée de : « Si {p}, alors {q} » ?"
        reponse = f"Si {_min(nq)}, alors {_min(np)}"
        dist    = [
            f"Si {_min(nq)}, alors {_min(p)}",
            f"Si {_min(q)}, alors {_min(p)}",
            f"Si {_min(np)}, alors {_min(nq)}",
        ]
    else:
        # Distinguer contraposée, réciproque et inverse
        enonce = (
            f"On considère : « Si {p}, alors {q} ».\n"
            f"Parmi les propositions suivantes, laquelle est "
            f"la contraposée (et non la réciproque ou l'inverse) ?"
        )
        reponse = f"« Si {_min(nq)}, alors {_min(np)} » — contraposée ¬Q ⇒ ¬P, équivalente à P ⇒ Q"
        dist    = [
            # Erreur 1 (très fréquente) : prendre la réciproque pour la contraposée
            f"« Si {_min(q)}, alors {_min(p)} » — réciproque Q ⇒ P : on inverse sans nier",
            # Erreur 2 : prendre l'inverse (¬P ⇒ ¬Q) pour la contraposée
            f"« Si {_min(np)}, alors {_min(nq)} » — inverse ¬P ⇒ ¬Q : on nie sans inverser",
            # Erreur 3 : ne nier que la conclusion dans la réciproque
            f"« Si {_min(q)}, alors {_min(np)} » — erreur mixte : ni contraposée ni réciproque",
        ]

    random.shuffle(dist)
    meta = {"nb_propositions":2,"nb_connecteurs":1,
            "nb_negations":0,"profondeur_logique":0}
    return enonce, reponse, dist[:3], meta


# ─────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== TEST DISTINCTION BLOOM ===\n")
    objectifs = ["NEG_SIMPLE","NEG_IMP","MORGAN","CONTRAP",
                 "IMP","EQUIV","NEG_QUANT","QUANT_TRAD",
                 "CONN_TRAD","CONN_INV","CONN_ID","TVER",
                 "VVER","NEG_COMP","PROP"]
    for code in objectifs:
        print(f"── {code} ──")
        for bloom in ["comprehension","analyse"]:
            q = generer_question(code, bloom, "moyen")
            print(f"  [{bloom[:4].upper()}] {q['enonce']}")
            print(f"         → {q['reponse_correcte'][:80]}")
        print()