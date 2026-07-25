# ─────────────────────────────────────────────────────────────
# calculator.py  —  ComplexityCalculator RALI-DEM
#
# Formule recalibrée (v2) — justification empirique :
#
#   T(s) = 20 + 10·Ns + 15·Ncnt + 20·Q + 15·Neg + 10·D + 15·MA
#   Score = min(10.0, max(1.0, round(T / 10, 1)))
#
# Calibrage basé sur :
#   • Crisp & Ward (2008) : temps médian QCM logique L1-L2 = 25-90s
#   • Rodriguez (2016)    : lecture énoncé 2 propositions = 15-20s
#   • Haladyna (2004)     : score min = 1pt (jamais 0 pour une tentative)
#   • Observations terrain Cameroun (3 enseignants, 45 étudiants)
#
# Coefficients v2 vs v1 :
#   Base          : 45s → 20s  (lecture seule, sans traitement)
#   Proposition   : 25s → 10s  (lecture d'une prop supplémentaire)
#   Connecteur    : 35s → 15s  (identification/application connecteur)
#   Quantificateur: 40s → 20s  (traitement ∀/∃)
#   Négation      : 50s → 15s  (application règle de négation)
#   Profondeur    : 20s → 10s  (niveau logique supplémentaire)
#   Bonus analyse : 30s → 15s  (raisonnement vs reconnaissance)
#
# Score v2 : T/10 (plafonné [1,10])
#   PROP=3pts, VVER=4pts, CONN=5.5pts, MORGAN=6.5pts,
#   NEG_IMP=7.5pts, NEG_QUANT=7.5pts, NEG_QUANT-analyse=10pts
# ─────────────────────────────────────────────────────────────

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

SEUILS_COMPLEXITE = {
    "faible": (0,   40),
    "moyen":  (40,  60),
    "eleve":  (60, 9999),
}


def calculer_complexite(
    nb_propositions:    int,
    nb_connecteurs:     int,
    nb_quantificateurs: int,
    nb_negations:       int,
    profondeur_logique: int,
    mode_bloom:         str,
) -> dict:
    Ns   = max(1, int(nb_propositions))
    Ncnt = max(0, int(nb_connecteurs))
    Q    = max(0, int(nb_quantificateurs))
    Neg  = max(0, int(nb_negations))
    D    = max(0, int(profondeur_logique))   # 0 autorisé pour questions simples
    MA   = 1 if str(mode_bloom).lower().strip() == "analyse" else 0

    T = (
        COEFF["base"]
        + COEFF["proposition"]    * Ns
        + COEFF["connecteur"]     * Ncnt
        + COEFF["quantificateur"] * Q
        + COEFF["negation"]       * Neg
        + COEFF["profondeur"]     * D
        + COEFF["bonus_analyse"]  * MA
    )
    T = round(T, 1)

    score = round(min(SCORE_MAX, max(1.0, T / 10)), 1)
    niveau = _determiner_niveau(T)

    detail = {
        "base":           COEFF["base"],
        "propositions":   COEFF["proposition"]     * Ns,
        "connecteurs":    COEFF["connecteur"]      * Ncnt,
        "quantificateurs":COEFF["quantificateur"]  * Q,
        "negations":      COEFF["negation"]        * Neg,
        "profondeur":     COEFF["profondeur"]      * D,
        "bonus_analyse":  COEFF["bonus_analyse"]   * MA,
        "formule_score":  "T / 10 (plafonné [1, 10])",
    }

    return {
        "ert_secondes":      T,
        "score_pedagogique": score,
        "niveau_complexite": niveau,
        "detail_calcul":     detail,
    }


def _determiner_niveau(ert: float) -> str:
    for niveau, (mini, maxi) in SEUILS_COMPLEXITE.items():
        if mini <= ert < maxi:
            return niveau
    return "eleve"


def verifier_niveau_cible(ert: float, niveau_cible: str) -> bool:
    mini, maxi = SEUILS_COMPLEXITE.get(niveau_cible, (0, 9999))
    return mini <= ert < maxi


def estimer_parametres(niveau_cible: str, mode_bloom: str) -> dict:
    """
    Paramètres calibrés pour respecter les seuils de la thèse.
    Faible : T ≈ 70s  |  Moyen : T ≈ 95-110s  |  Élevé : T ≥ 120s
    """
    # Calibré sur les nouveaux seuils : faible<40s, moyen 40-60s, élevé≥60s
    if niveau_cible == "faible":
        # T cible ≈ 30s → 1 proposition, pas de connecteur
        return {
            "nb_propositions":    1,
            "nb_connecteurs":     0,
            "nb_quantificateurs": 0,
            "nb_negations":       0,
            "profondeur_logique": 0,
        }
    elif niveau_cible == "moyen":
        # T cible ≈ 40-55s → 2 propositions, 0-1 connecteur
        return {
            "nb_propositions":    2,
            "nb_connecteurs":     1,
            "nb_quantificateurs": 0,
            "nb_negations":       0,
            "profondeur_logique": 0,
        }
    else:  # eleve
        # T cible ≥ 60s → 2 propositions, connecteur, négation ou profondeur
        return {
            "nb_propositions":    2,
            "nb_connecteurs":     1,
            "nb_quantificateurs": 0,
            "nb_negations":       1,
            "profondeur_logique": 1,
        }


if __name__ == "__main__":
    print("=== ComplexityCalculator — formule thèse §3.5.6 ===\n")
    cas = [
        (1, 0, 0, 0, 0, "comprehension", "Faible — compréhension"),
        (1, 0, 0, 0, 0, "analyse",       "Faible — analyse"),
        (2, 0, 0, 0, 0, "comprehension", "Moyen — compréhension"),
        (1, 1, 0, 0, 0, "comprehension", "Moyen — connecteur"),
        (1, 0, 1, 0, 0, "comprehension", "Moyen — quantificateur"),
        (2, 1, 0, 0, 0, "comprehension", "Élevé — compréhension"),
        (2, 1, 0, 0, 0, "analyse",       "Élevé — analyse"),
        (2, 1, 1, 1, 1, "analyse",       "Élevé — analyse complexe"),
    ]
    for Ns, Nc, Q, Neg, D, bloom, desc in cas:
        r = calculer_complexite(Ns, Nc, Q, Neg, D, bloom)
        print(f"  {desc}")
        print(f"    T={r['ert_secondes']}s | Score={r['score_pedagogique']}/10 "
              f"| Niveau={r['niveau_complexite'].upper()}")
