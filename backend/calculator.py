# ─────────────────────────────────────────────────────────────
# calculator.py  —  Temps estimés RALI-DEM
#
# Deux formules sont calculées pour chaque question, figées AVANT
# la collecte, afin de comparer leur pouvoir de prédiction sur les
# mêmes temps observés. Aucune des deux n'est affichée à l'étudiant.
#
# ERT-B  (formule actuelle, thèse éq. 3.1, coefficients tirés de
#         la littérature) :
#   T(s) = 20 + 10·Ns + 15·Ncnt + 20·Q + 15·Neg + 10·D + 15·MA
#   Score = min(10, max(1, round(T / 10, 1)))
#
# ERT-A  (formule de Ms Generator V2, version du CODE retenue comme
#         référence ; cf. QuestionsPointAndDurationManager.java,
#         ArticleManager.java, SimpleConnectorManager.java,
#         ComposedSchemas.java, QcmQuestionGenerator.java) :
#   Durée(s) = int(COEFF_DUREE × difficulté(q))
#            + int(NombreMots × 60 / VITESSE_LECTURE)
#   difficulté(q) = difficulté(proposition) + 0,5
#   simple    : Σ coef(article du sujet)  × (1,1 si forme négative)
#   composée  : coef(connecteur) × (diff(P1) + diff(P2)) / 2
#   NombreMots = mots de l'énoncé + mots de tous les choix affichés
#
# Les paramètres sont définis ci-dessous et ne doivent pas être
# modifiés pendant une collecte (PARAMS_VERSION les identifie).
# ─────────────────────────────────────────────────────────────

PARAMS_VERSION = "2026-11-26"

# ── ERT-B ─────────────────────────────────────────────────────
COEFF = {
    "base":          20,
    "proposition":   10,
    "connecteur":    15,
    "quantificateur":20,
    "negation":      15,
    "profondeur":    10,
    "bonus_analyse": 15,
}

SCORE_MAX = 10.0

# Seuils du niveau de complexité. Ils s'appliquent au temps ERT-B
# SANS le bonus du mode Analyse (niveau structurel), pour que le
# niveau de complexité ne soit pas mécaniquement lié au mode Bloom.
SEUILS_COMPLEXITE = {
    "faible": (0,   40),
    "moyen":  (40,  60),
    "eleve":  (60, 9999),
}

# ── ERT-A (Ms Generator V2) ──────────────────────────────────
ERT_A_COEFF_DUREE     = 60      # DEFAULT_DURATION
ERT_A_VITESSE_LECTURE = 250     # DEFAULT_READING_SPEED (mots/minute)
ERT_A_BONUS_QUESTION  = 0.5     # QcmQuestionGenerator : difficulté + 0,5
ERT_A_FACTEUR_NEGATIF = 1.1     # Proposition.autoSetDifficulte (form = -1)

# ArticleManager.getArticleDifficulte
ERT_A_COEF_ARTICLE = {
    "AUCUN":       0.07,   # ARTICLE_TYPE_NO_ARTICLE, ARTICLE_TYPE_ANY
    "DEFINI":      0.08,   # ARTICLE_TYPE_DEFINI
    "INDEFINI":    0.08,   # ARTICLE_TYPE_INDEFINI_0
    "QE":          0.5,    # quantificateur existentiel
    "QE_NOT":      0.5,    # « il n'existe pas »
    "QU":          0.5,    # quantificateur universel
    "MANY":        0.7,    # « plusieurs »
    "ATMOST_ONE":  0.7,    # « au plus un »
}
ERT_A_COEF_ARTICLE_AUTRE = 0.015

# SimpleConnectorManager.getConnectorDifficulte
ERT_A_COEF_CONNECTEUR = {
    "ET":    1.6,
    "OU":    1.6,
    "IMP":   1.8,
    "EQUIV": 1.9,
}
ERT_A_COEF_CONNECTEUR_AUTRE = 1.0


# ═════════════════════════════════════════════════════════════
# ERT-B
# ═════════════════════════════════════════════════════════════

def calculer_complexite(
    nb_propositions:    int,
    nb_connecteurs:     int,
    nb_quantificateurs: int,
    nb_negations:       int,
    profondeur_logique: int,
    mode_bloom:         str,
) -> dict:
    """ERT-B et ses composantes. Clé 'ert_secondes' conservée pour
    les modules existants (examen, mode adaptatif)."""
    Ns   = max(1, int(nb_propositions))
    Ncnt = max(0, int(nb_connecteurs))
    Q    = 1 if int(nb_quantificateurs) > 0 else 0
    Neg  = max(0, min(2, int(nb_negations)))
    D    = max(0, int(profondeur_logique))
    MA   = 1 if str(mode_bloom).lower().strip() == "analyse" else 0

    detail = {
        "base":            COEFF["base"],
        "propositions":    COEFF["proposition"]    * Ns,
        "connecteurs":     COEFF["connecteur"]     * Ncnt,
        "quantificateurs": COEFF["quantificateur"] * Q,
        "negations":       COEFF["negation"]       * Neg,
        "profondeur":      COEFF["profondeur"]     * D,
        "bonus_analyse":   COEFF["bonus_analyse"]  * MA,
    }
    T = round(float(sum(detail.values())), 1)
    T_structurel = round(T - detail["bonus_analyse"], 1)

    score = round(min(SCORE_MAX, max(1.0, T / 10)), 1)

    return {
        "ert_secondes":       T,               # = ERT-B
        "ert_b_s":            T,
        "ert_b_structurel_s": T_structurel,    # sans le bonus Analyse
        "score_pedagogique":  score,
        "niveau_complexite":  _determiner_niveau(T_structurel),
        "detail_calcul":      detail,
        "variables": {"Ns": Ns, "Ncnt": Ncnt, "Q": Q, "Neg": Neg,
                      "D": D, "MA": MA},
    }


def _determiner_niveau(ert: float) -> str:
    for niveau, (mini, maxi) in SEUILS_COMPLEXITE.items():
        if mini <= ert < maxi:
            return niveau
    return "eleve"


def verifier_niveau_cible(ert_structurel: float, niveau_cible: str) -> bool:
    mini, maxi = SEUILS_COMPLEXITE.get(niveau_cible, (0, 9999))
    return mini <= ert_structurel < maxi


def estimer_parametres(niveau_cible: str, mode_bloom: str) -> dict:
    """Paramètres indicatifs par niveau (conservé pour compatibilité)."""
    if niveau_cible == "faible":
        return {"nb_propositions": 1, "nb_connecteurs": 0,
                "nb_quantificateurs": 0, "nb_negations": 0,
                "profondeur_logique": 0}
    elif niveau_cible == "moyen":
        return {"nb_propositions": 2, "nb_connecteurs": 1,
                "nb_quantificateurs": 0, "nb_negations": 0,
                "profondeur_logique": 0}
    return {"nb_propositions": 2, "nb_connecteurs": 1,
            "nb_quantificateurs": 0, "nb_negations": 1,
            "profondeur_logique": 1}


# ═════════════════════════════════════════════════════════════
# ERT-A (Ms Generator V2)
# ═════════════════════════════════════════════════════════════

def difficulte_proposition(prop: dict) -> float:
    """
    Difficulté d'une proposition, structure :
      simple   : {"type": "simple", "articles": ["DEFINI", ...],
                  "negative": False}
      composée : {"type": "compose", "connecteur": "IMP",
                  "p1": {...}, "p2": {...}}
    Une proposition purement symbolique (P, Q sans sujet) a des
    listes d'articles vides et donc une difficulté nulle, comme dans
    Ms Generator V2 (seuls les sujets sont pondérés).
    """
    if not prop:
        return 0.0
    if prop.get("type") == "compose":
        coef = ERT_A_COEF_CONNECTEUR.get(prop.get("connecteur"),
                                         ERT_A_COEF_CONNECTEUR_AUTRE)
        return coef * (difficulte_proposition(prop.get("p1")) +
                       difficulte_proposition(prop.get("p2"))) / 2.0
    d = sum(ERT_A_COEF_ARTICLE.get(a, ERT_A_COEF_ARTICLE_AUTRE)
            for a in prop.get("articles", []))
    if prop.get("negative"):
        d *= ERT_A_FACTEUR_NEGATIF
    return d


def compter_mots(enonce: str, choix: list) -> int:
    """QcmQuestion.calculReadingDuration : découpage sur l'espace."""
    n = len(str(enonce).split(" "))
    for c in choix:
        if str(c).strip():
            n += len(str(c).split(" "))
    return n


def calculer_ert_a(prop: dict, enonce: str, choix: list) -> dict:
    diff_prop = difficulte_proposition(prop)
    diff_q    = diff_prop + ERT_A_BONUS_QUESTION
    nb_mots   = compter_mots(enonce, choix)
    t_diff    = int(ERT_A_COEFF_DUREE * diff_q)
    t_lecture = int(nb_mots * 60 / ERT_A_VITESSE_LECTURE)
    return {
        "ert_a_s":                float(t_diff + t_lecture),
        "ert_a_difficulte_prop":  round(diff_prop, 4),
        "ert_a_difficulte_q":     round(diff_q, 4),
        "ert_a_nb_mots":          nb_mots,
        "ert_a_terme_difficulte": t_diff,
        "ert_a_terme_lecture":    t_lecture,
    }


def calculer_ert_a_version_publiee(prop: dict, enonce: str, choix: list) -> float:
    """Variante du texte de l'article (analyse secondaire) :
    composée = (diff(P1) + diff(P2)) × CoefC, seuls les quantificateurs
    pondérés, sans facteur de forme négative."""
    def diff(p):
        if not p:
            return 0.0
        if p.get("type") == "compose":
            coef = ERT_A_COEF_CONNECTEUR.get(p.get("connecteur"),
                                             ERT_A_COEF_CONNECTEUR_AUTRE)
            return coef * (diff(p.get("p1")) + diff(p.get("p2")))
        return sum(ERT_A_COEF_ARTICLE[a] for a in p.get("articles", [])
                   if a in ("QE", "QE_NOT", "QU", "MANY", "ATMOST_ONE"))
    t = ERT_A_COEFF_DUREE * (diff(prop) + ERT_A_BONUS_QUESTION) \
        + compter_mots(enonce, choix) * 60 / ERT_A_VITESSE_LECTURE
    return round(t, 1)


if __name__ == "__main__":
    p_simple = {"type": "simple", "articles": ["DEFINI"], "negative": False}
    p_imp = {"type": "compose", "connecteur": "IMP",
             "p1": p_simple, "p2": p_simple}
    p_qu = {"type": "simple", "articles": ["QU"], "negative": False}
    enonce = "Quelle est la négation de : « Le professeur explique ce cours » ?"
    choix = ["Le professeur n'explique pas ce cours",
             "Le professeur n'explique jamais ce cours",
             "Le professeur n'explique plus ce cours",
             "Le professeur n'explique que ce cours"]
    for nom, p in [("simple", p_simple), ("implication", p_imp),
                   ("universel", p_qu)]:
        print(nom, calculer_ert_a(p, enonce, choix))
    print("ERT-B", calculer_complexite(1, 0, 0, 1, 0, "comprehension"))
