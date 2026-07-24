# ─────────────────────────────────────────────────────────────
# adaptive.py  —  Parcours adaptatif RALI-DEM
# Ajuste automatiquement le niveau de complexité
# selon les performances de l'apprenant en temps réel.
# ─────────────────────────────────────────────────────────────

import json
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'rali_dem.db')

# ─────────────────────────────────────────────────────────────
# CONSTANTES DU MOTEUR ADAPTATIF
# ─────────────────────────────────────────────────────────────

NIVEAUX        = ["faible", "moyen", "eleve"]
SEUIL_MONTEE   = 3   # bonnes réponses consécutives pour monter
SEUIL_DESCENTE = 2   # mauvaises réponses consécutives pour descendre

MESSAGES_NIVEAU = {
    "montee": {
        "faible→moyen": (
            "🎉 Excellent ! Vous maîtrisez le niveau de base. "
            "On passe au niveau intermédiaire !"
        ),
        "moyen→eleve": (
            "🏆 Très bien ! Vous êtes prêt pour les questions avancées. "
            "On passe au niveau élevé !"
        ),
    },
    "descente": {
        "moyen→faible": (
            "💪 Pas de panique ! On revient sur les bases "
            "pour consolider vos acquis."
        ),
        "eleve→moyen": (
            "💪 Ces questions sont difficiles. "
            "On revient au niveau intermédiaire pour renforcer les fondations."
        ),
    },
    "maintien": (
        "Continuez ainsi, vous progressez bien !"
    ),
}


# ─────────────────────────────────────────────────────────────
# INITIALISATION DE LA BASE (table sessions_adaptatives)
# ─────────────────────────────────────────────────────────────

def init_tables_adaptatives():
    """Crée les tables nécessaires au parcours adaptatif."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Session adaptative
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions_adaptatives (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            apprenant           TEXT    NOT NULL DEFAULT "anonyme",
            objectif_code       TEXT    NOT NULL,
            mode_bloom          TEXT    NOT NULL DEFAULT "comprehension",
            niveau_actuel       TEXT    NOT NULL DEFAULT "faible",
            nb_bonnes           INTEGER NOT NULL DEFAULT 0,
            nb_mauvaises        INTEGER NOT NULL DEFAULT 0,
            bonnes_consecutives INTEGER NOT NULL DEFAULT 0,
            mauvaises_consecutives INTEGER NOT NULL DEFAULT 0,
            nb_questions_total  INTEGER NOT NULL DEFAULT 0,
            score_global        REAL    NOT NULL DEFAULT 0.0,
            statut              TEXT    NOT NULL DEFAULT "en_cours",
            date_debut          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date_fin            TIMESTAMP
        )
    ''')

    # Historique des réponses dans une session adaptative
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historique_adaptatif (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      INTEGER NOT NULL
                            REFERENCES sessions_adaptatives(id),
            question_id     INTEGER,
            objectif_code   TEXT    NOT NULL,
            niveau          TEXT    NOT NULL,
            enonce          TEXT    NOT NULL,
            reponse_correcte TEXT   NOT NULL,
            reponse_apprenant TEXT  NOT NULL,
            est_correct     INTEGER NOT NULL DEFAULT 0,
            ert_secondes    REAL,
            score_question  REAL,
            evenement       TEXT,
            date_reponse    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
# GESTION DES SESSIONS
# ─────────────────────────────────────────────────────────────

def creer_session(
    objectif_code: str,
    mode_bloom:    str  = "comprehension",
    apprenant:     str  = "anonyme",
    niveau_depart: str  = "faible",
) -> dict:
    """
    Crée une nouvelle session adaptative et retourne son état initial.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO sessions_adaptatives
        (apprenant, objectif_code, mode_bloom, niveau_actuel)
        VALUES (?, ?, ?, ?)
    ''', (apprenant, objectif_code, mode_bloom, niveau_depart))

    conn.commit()
    session_id = cursor.lastrowid
    conn.close()

    return {
        "session_id":    session_id,
        "apprenant":     apprenant,
        "objectif_code": objectif_code,
        "mode_bloom":    mode_bloom,
        "niveau_actuel": niveau_depart,
        "nb_bonnes":     0,
        "nb_mauvaises":  0,
        "bonnes_consecutives":   0,
        "mauvaises_consecutives": 0,
        "nb_questions_total": 0,
        "score_global":  0.0,
        "statut":        "en_cours",
        "message":       f"Session démarrée au niveau {niveau_depart.upper()}. Bonne chance !",
    }


def get_session(session_id: int) -> dict:
    """Retourne l'état actuel d'une session."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM sessions_adaptatives WHERE id = ?',
        (session_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Session {session_id} introuvable.")
    return dict(row)


# ─────────────────────────────────────────────────────────────
# MOTEUR ADAPTATIF PRINCIPAL
# ─────────────────────────────────────────────────────────────

def enregistrer_reponse(
    session_id:        int,
    enonce:            str,
    reponse_correcte:  str,
    reponse_apprenant: str,
    est_correct:       bool,
    ert_secondes:      float = 0.0,
    score_question:    float = 0.0,
    question_id:       int   = None,
) -> dict:
    """
    Enregistre une réponse et met à jour le niveau si nécessaire.

    Retourne l'état mis à jour de la session avec :
        - le nouveau niveau
        - l'événement (montée / descente / maintien)
        - le message à afficher à l'apprenant
        - les statistiques actualisées
    """
    session = get_session(session_id)

    if session["statut"] != "en_cours":
        raise ValueError("Cette session est terminée.")

    # ── Mise à jour des compteurs ─────────────────────────────
    nb_bonnes    = session["nb_bonnes"]
    nb_mauvaises = session["nb_mauvaises"]
    bonnes_cons  = session["bonnes_consecutives"]
    mauvaises_cons = session["mauvaises_consecutives"]
    niveau       = session["niveau_actuel"]
    nb_total     = session["nb_questions_total"] + 1
    score_cumul  = session["score_global"]

    if est_correct:
        nb_bonnes   += 1
        bonnes_cons += 1
        mauvaises_cons = 0
        score_cumul += score_question
    else:
        nb_mauvaises   += 1
        mauvaises_cons += 1
        bonnes_cons     = 0

    # ── Décision d'ajustement du niveau ──────────────────────
    ancien_niveau = niveau
    evenement     = "maintien"
    message       = MESSAGES_NIVEAU["maintien"]

    if bonnes_cons >= SEUIL_MONTEE:
        # Tentative de montée
        idx = NIVEAUX.index(niveau)
        if idx < len(NIVEAUX) - 1:
            niveau      = NIVEAUX[idx + 1]
            evenement   = "montee"
            cle         = f"{ancien_niveau}→{niveau}"
            message     = MESSAGES_NIVEAU["montee"].get(
                cle, f"🎉 Niveau supérieur atteint : {niveau.upper()} !"
            )
            bonnes_cons = 0   # réinitialiser le compteur

    elif mauvaises_cons >= SEUIL_DESCENTE:
        # Tentative de descente
        idx = NIVEAUX.index(niveau)
        if idx > 0:
            niveau         = NIVEAUX[idx - 1]
            evenement      = "descente"
            cle            = f"{ancien_niveau}→{niveau}"
            message        = MESSAGES_NIVEAU["descente"].get(
                cle, f"💪 Retour au niveau {niveau.upper()} pour consolider."
            )
            mauvaises_cons = 0   # réinitialiser le compteur

    # ── Score global (moyenne pondérée) ──────────────────────
    score_global = round(score_cumul / nb_total, 2) if nb_total > 0 else 0.0

    # ── Sauvegarder dans l'historique ────────────────────────
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO historique_adaptatif
        (session_id, question_id, objectif_code, niveau, enonce,
         reponse_correcte, reponse_apprenant, est_correct,
         ert_secondes, score_question, evenement)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session_id,
        question_id,
        session["objectif_code"],
        ancien_niveau,
        enonce,
        reponse_correcte,
        reponse_apprenant,
        int(est_correct),
        ert_secondes,
        score_question,
        evenement,
    ))

    # ── Mettre à jour la session ──────────────────────────────
    cursor.execute('''
        UPDATE sessions_adaptatives SET
            niveau_actuel          = ?,
            nb_bonnes              = ?,
            nb_mauvaises           = ?,
            bonnes_consecutives    = ?,
            mauvaises_consecutives = ?,
            nb_questions_total     = ?,
            score_global           = ?
        WHERE id = ?
    ''', (
        niveau, nb_bonnes, nb_mauvaises,
        bonnes_cons, mauvaises_cons,
        nb_total, score_global,
        session_id,
    ))

    conn.commit()
    conn.close()

    return {
        "session_id":              session_id,
        "niveau_actuel":           niveau,
        "niveau_precedent":        ancien_niveau,
        "evenement":               evenement,
        "message":                 message,
        "est_correct":             est_correct,
        "nb_bonnes":               nb_bonnes,
        "nb_mauvaises":            nb_mauvaises,
        "bonnes_consecutives":     bonnes_cons,
        "mauvaises_consecutives":  mauvaises_cons,
        "nb_questions_total":      nb_total,
        "score_global":            score_global,
        "progression":             _calculer_progression(
                                       nb_bonnes, nb_total
                                   ),
    }


def terminer_session(session_id: int) -> dict:
    """Clôture une session et retourne le bilan final."""
    session = get_session(session_id)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE sessions_adaptatives
        SET statut = "terminee", date_fin = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (session_id,))

    # Récupérer l'historique complet
    cursor.execute('''
        SELECT * FROM historique_adaptatif
        WHERE session_id = ?
        ORDER BY date_reponse
    ''', (session_id,))
    historique = [dict(r) for r in cursor.fetchall()]

    conn.commit()
    conn.close()

    nb_total    = session["nb_questions_total"]
    nb_bonnes   = session["nb_bonnes"]
    score       = session["score_global"]
    niveau_final = session["niveau_actuel"]

    # Message de bilan
    taux = (nb_bonnes / nb_total * 100) if nb_total > 0 else 0
    if taux >= 80:
        appreciation = "🏆 Excellent travail ! Vous maîtrisez cet objectif."
    elif taux >= 60:
        appreciation = "👍 Bon travail ! Quelques points à revoir."
    elif taux >= 40:
        appreciation = "📚 Des progrès à faire. Revoyez les règles de base."
    else:
        appreciation = "💡 Cet objectif nécessite plus de pratique. Ne vous découragez pas !"

    return {
        "session_id":    session_id,
        "objectif_code": session["objectif_code"],
        "apprenant":     session["apprenant"],
        "niveau_final":  niveau_final,
        "nb_questions":  nb_total,
        "nb_bonnes":     nb_bonnes,
        "nb_mauvaises":  session["nb_mauvaises"],
        "taux_reussite": round(taux, 1),
        "score_global":  score,
        "appreciation":  appreciation,
        "historique":    historique,
    }


# ─────────────────────────────────────────────────────────────
# UTILITAIRES
# ─────────────────────────────────────────────────────────────

def _calculer_progression(nb_bonnes: int, nb_total: int) -> dict:
    """Calcule la progression vers le prochain changement de niveau."""
    taux = round((nb_bonnes / nb_total * 100), 1) if nb_total > 0 else 0.0
    return {
        "taux_reussite":         taux,
        "bonnes_pour_monter":    SEUIL_MONTEE,
        "mauvaises_pour_descendre": SEUIL_DESCENTE,
    }


def get_historique_session(session_id: int) -> list:
    """Retourne l'historique complet des réponses d'une session."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM historique_adaptatif
        WHERE session_id = ?
        ORDER BY date_reponse
    ''', (session_id,))
    result = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return result


def get_sessions_apprenant(apprenant: str) -> list:
    """Retourne toutes les sessions d'un apprenant."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM sessions_adaptatives
        WHERE apprenant = ?
        ORDER BY date_debut DESC
    ''', (apprenant,))
    result = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return result


# ─────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))

    print("=== Test du parcours adaptatif ===\n")

    # Initialiser les tables
    init_tables_adaptatives()

    # Créer une session
    session = creer_session(
        objectif_code = "NEG_IMP",
        mode_bloom    = "comprehension",
        apprenant     = "etudiant_test",
        niveau_depart = "faible",
    )
    sid = session["session_id"]
    print(f"Session créée : ID={sid}")
    print(f"Niveau départ : {session['niveau_actuel'].upper()}")
    print(f"Message : {session['message']}\n")

    # Simuler 8 réponses
    reponses = [
        (True,  "Bonne réponse 1"),
        (True,  "Bonne réponse 2"),
        (True,  "Bonne réponse 3 → devrait monter au niveau MOYEN"),
        (False, "Mauvaise réponse 1"),
        (True,  "Bonne réponse"),
        (True,  "Bonne réponse"),
        (True,  "Bonne réponse → devrait monter au niveau ÉLEVÉ"),
        (False, "Mauvaise réponse 1"),
        (False, "Mauvaise réponse 2 → devrait descendre au niveau MOYEN"),
    ]

    for i, (correct, label) in enumerate(reponses, 1):
        etat = enregistrer_reponse(
            session_id        = sid,
            enonce            = f"Question test {i}",
            reponse_correcte  = "bonne réponse",
            reponse_apprenant = "bonne réponse" if correct else "mauvaise",
            est_correct       = correct,
            ert_secondes      = 45.0,
            score_question    = 5.0 if correct else 0.0,
        )
        symbole = "✅" if correct else "❌"
        print(f"  Q{i} {symbole} {label}")
        print(f"     Niveau : {etat['niveau_actuel'].upper()} "
              f"| Événement : {etat['evenement']}")
        if etat["evenement"] != "maintien":
            print(f"     → {etat['message']}")
        print()

    # Bilan final
    bilan = terminer_session(sid)
    print("─" * 50)
    print("BILAN FINAL")
    print(f"  Questions : {bilan['nb_questions']}")
    print(f"  Bonnes    : {bilan['nb_bonnes']}")
    print(f"  Taux      : {bilan['taux_reussite']}%")
    print(f"  Score     : {bilan['score_global']}/10")
    print(f"  Niveau    : {bilan['niveau_final'].upper()}")
    print(f"  {bilan['appreciation']}")
