# ─────────────────────────────────────────────────────────────
# calculator.py  —  ComplexityCalculator RALI-DEM
# Formule originale (thèse §3.5.6, validée par 3 enseignants)
#
# T(s) = 45 + 25·Ns + 35·Ncnt + 40·Q + 50·Neg + 20·D + 30·MA
# Score = min(10, round((T/60) × (0.8 + 0.4·MA), 2))
# ─────────────────────────────────────────────────────────────

COEFF = {
    "base":          45,
    "proposition":   25,
    "connecteur":    35,
    "quantificateur":40,
    "negation":      50,
    "profondeur":    20,
    "bonus_analyse": 30,
}

SCORE_BASE    = 0.8
SCORE_ANALYSE = 0.4
SCORE_MAX     = 10.0

SEUILS_COMPLEXITE = {
    "faible": (0,    80),
    "moyen":  (80,  120),
    "eleve":  (120, 9999),
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

    score = min(SCORE_MAX, round((T / 60) * (SCORE_BASE + SCORE_ANALYSE * MA), 2))
    niveau = _determiner_niveau(T)

    detail = {
        "base":          COEFF["base"],
        "propositions":  COEFF["proposition"]    * Ns,
        "connecteurs":   COEFF["connecteur"]     * Ncnt,
        "quantificateurs":COEFF["quantificateur"]* Q,
        "negations":     COEFF["negation"]       * Neg,
        "profondeur":    COEFF["profondeur"]     * D,
        "bonus_analyse": COEFF["bonus_analyse"]  * MA,
        "multiplicateur_score": round(SCORE_BASE + SCORE_ANALYSE * MA, 2),
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
    if niveau_cible == "faible":
        return {
            "nb_propositions":    1,
            "nb_connecteurs":     0,
            "nb_quantificateurs": 0,
            "nb_negations":       0,
            "profondeur_logique": 0,
        }
    elif niveau_cible == "moyen":
        return {
            "nb_propositions":    2,
            "nb_connecteurs":     0,
            "nb_quantificateurs": 0,
            "nb_negations":       0,
            "profondeur_logique": 0,
        }
    else:  # eleve
        return {
            "nb_propositions":    2,
            "nb_connecteurs":     1,
            "nb_quantificateurs": 0,
            "nb_negations":       0,
            "profondeur_logique": 0,
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