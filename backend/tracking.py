# ─────────────────────────────────────────────────────────────
# tracking.py  —  Module de suivi des évaluations RALI-DEM
#
# Deux types de sessions suivies :
#   1. Sessions adaptatives (parcours adaptatif)
#   2. Sessions examens (mode examen chronométré)
#
# Chaque session est liée à un utilisateur authentifié.
# Toutes les réponses individuelles sont enregistrées
# pour permettre des statistiques détaillées.
# ─────────────────────────────────────────────────────────────

import os
import sqlite3
from datetime import datetime
from typing import Optional

DB_PATH = os.environ.get('RALI_DB_PATH', os.path.join(os.path.dirname(__file__), '..', 'database', 'rali_dem.db'))
# ═════════════════════════════════════════════════════════════
# CONNEXION BASE DE DONNÉES
# ═════════════════════════════════════════════════════════════

def _connexion() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _maintenant() -> str:
    return datetime.now().isoformat()


# ═════════════════════════════════════════════════════════════
# INITIALISATION DES TABLES
# ═════════════════════════════════════════════════════════════

def init_tables_tracking():
    """
    Crée les 4 tables de suivi des évaluations.
    Appelé au démarrage de l'application.
    Recrée les tables si la structure a changé.
    """
    conn = _connexion()
    cur  = conn.cursor()

    # Vérifier si track_reponses_adapt a la bonne structure
    # Si session_id est NOT NULL, recréer les tables
    try:
        info = cur.execute("PRAGMA table_info(track_reponses_adapt)").fetchall()
        for col in info:
            if col[1] == 'session_id' and col[3] == 1:  # notnull=1
                # Ancienne structure — recréer les tables
                print("[TRACKING] Mise à jour structure tables...")
                cur.execute("DROP TABLE IF EXISTS track_reponses_adapt")
                cur.execute("DROP TABLE IF EXISTS track_reponses_exam")
                cur.execute("DROP TABLE IF EXISTS track_sessions_adapt")
                cur.execute("DROP TABLE IF EXISTS track_sessions_exam")
                conn.commit()
                break
    except Exception:
        pass

    # ── Sessions adaptatives ──────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS track_sessions_adapt (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            utilisateur_id    INTEGER NOT NULL,
            objectif_code     TEXT    NOT NULL,
            mode_bloom        TEXT    NOT NULL,
            nb_questions      INTEGER NOT NULL DEFAULT 0,
            nb_correctes      INTEGER NOT NULL DEFAULT 0,
            score_moyen       REAL    NOT NULL DEFAULT 0.0,
            ert_moyen         REAL    NOT NULL DEFAULT 0.0,
            niveau_depart     TEXT    NOT NULL DEFAULT 'faible',
            niveau_final      TEXT    NOT NULL DEFAULT 'faible',
            date_debut        TEXT    NOT NULL,
            date_fin          TEXT,
            duree_secondes    INTEGER,
            terminee          INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (utilisateur_id)
                REFERENCES utilisateurs(id) ON DELETE CASCADE
        )
    """)

    # ── Réponses adaptatives (détail question par question) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS track_reponses_adapt (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id        INTEGER,
            utilisateur_id    INTEGER NOT NULL,
            objectif_code     TEXT    NOT NULL,
            mode_bloom        TEXT    NOT NULL,
            niveau_complexite TEXT    NOT NULL,
            enonce            TEXT    NOT NULL,
            reponse_apprenant TEXT    NOT NULL,
            reponse_correcte  TEXT    NOT NULL,
            est_correct       INTEGER NOT NULL,
            ert_secondes      REAL    NOT NULL DEFAULT 0.0,
            score_question    REAL    NOT NULL DEFAULT 0.0,
            date_reponse      TEXT    NOT NULL,
            
            FOREIGN KEY (utilisateur_id)
                REFERENCES utilisateurs(id) ON DELETE CASCADE
        )
    """)

    # ── Sessions examens ──────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS track_sessions_exam (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            utilisateur_id    INTEGER NOT NULL,
            titre             TEXT    NOT NULL,
            objectifs_codes   TEXT    NOT NULL,
            mode_bloom        TEXT    NOT NULL,
            niveau            TEXT    NOT NULL,
            nb_questions      INTEGER NOT NULL DEFAULT 0,
            nb_correctes      INTEGER NOT NULL DEFAULT 0,
            note_sur_20       REAL    NOT NULL DEFAULT 0.0,
            mention           TEXT    NOT NULL DEFAULT '',
            date_examen       TEXT    NOT NULL,
            duree_secondes    INTEGER,
            termine           INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (utilisateur_id)
                REFERENCES utilisateurs(id) ON DELETE CASCADE
        )
    """)

    # ── Réponses examens (détail question par question) ───────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS track_reponses_exam (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            session_examen_id INTEGER NOT NULL,
            utilisateur_id    INTEGER NOT NULL,
            objectif_code     TEXT    NOT NULL,
            mode_bloom        TEXT    NOT NULL,
            niveau_complexite TEXT    NOT NULL,
            enonce            TEXT    NOT NULL,
            reponse_apprenant TEXT    NOT NULL,
            reponse_correcte  TEXT    NOT NULL,
            est_correct       INTEGER NOT NULL,
            ert_secondes      REAL    NOT NULL DEFAULT 0.0,
            score_question    REAL    NOT NULL DEFAULT 0.0,
            temps_reponse_s   REAL    NOT NULL DEFAULT 0.0,
            date_reponse      TEXT    NOT NULL,
            FOREIGN KEY (session_examen_id)
                REFERENCES track_sessions_exam(id) ON DELETE CASCADE,
            FOREIGN KEY (utilisateur_id)
                REFERENCES utilisateurs(id) ON DELETE CASCADE
        )
    """)

    # ── Index pour accélérer les requêtes statistiques ────────
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_trep_adapt_user
        ON track_reponses_adapt(utilisateur_id)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_trep_adapt_obj
        ON track_reponses_adapt(objectif_code)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_trep_exam_user
        ON track_reponses_exam(utilisateur_id)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_trep_exam_obj
        ON track_reponses_exam(objectif_code)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_tsess_adapt_user
        ON track_sessions_adapt(utilisateur_id)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_tsess_exam_user
        ON track_sessions_exam(utilisateur_id)
    """)

    conn.commit()
    conn.close()
    print("[TRACKING] Tables de suivi initialisées ✅")


# ═════════════════════════════════════════════════════════════
# SESSIONS ADAPTATIVES
# ═════════════════════════════════════════════════════════════

def creer_session_adaptative(
    utilisateur_id: int,
    objectif_code:  str,
    mode_bloom:     str,
    niveau_depart:  str = 'faible',
) -> dict:
    """
    Crée une nouvelle session adaptative liée à l'utilisateur.
    Retourne l'id de la session créée.
    """
    conn = _connexion()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO track_sessions_adapt
            (utilisateur_id, objectif_code, mode_bloom,
             niveau_depart, niveau_final, date_debut)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (utilisateur_id, objectif_code, mode_bloom,
          niveau_depart, niveau_depart, _maintenant()))
    conn.commit()
    session_id = cur.lastrowid
    conn.close()
    return {"session_id": session_id, "message": "Session adaptative créée."}


def enregistrer_reponse_adaptative(
    session_id:        int,
    utilisateur_id:    int,
    objectif_code:     str,
    mode_bloom:        str,
    niveau_complexite: str,
    enonce:            str,
    reponse_apprenant: str,
    reponse_correcte:  str,
    est_correct:       bool,
    ert_secondes:      float,
    score_question:    float,
) -> dict:
    """
    Enregistre une réponse individuelle dans une session adaptative.
    Met à jour les agrégats de la session.
    """
    conn = _connexion()
    cur  = conn.cursor()

    # Si session_id invalide (-1), utiliser NULL
    sid = session_id if (session_id and session_id > 0) else None

    # Insérer la réponse
    cur.execute("""
        INSERT INTO track_reponses_adapt
            (session_id, utilisateur_id, objectif_code, mode_bloom,
             niveau_complexite, enonce, reponse_apprenant,
             reponse_correcte, est_correct, ert_secondes,
             score_question, date_reponse)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (sid, utilisateur_id, objectif_code, mode_bloom,
          niveau_complexite, enonce, reponse_apprenant,
          reponse_correcte, 1 if est_correct else 0,
          ert_secondes, score_question, _maintenant()))

    # Mettre à jour les agrégats de la session
    cur.execute("""
        UPDATE track_sessions_adapt SET
            nb_questions = nb_questions + 1,
            nb_correctes = nb_correctes + ?,
            score_moyen  = (
                SELECT ROUND(AVG(score_question), 2)
                FROM track_reponses_adapt
                WHERE session_id = ?
            ),
            ert_moyen = (
                SELECT ROUND(AVG(ert_secondes), 1)
                FROM track_reponses_adapt
                WHERE session_id = ?
            )
        WHERE id = ?
    """, (1 if est_correct else 0,
          session_id, session_id, session_id))

    conn.commit()
    conn.close()
    return {"message": "Réponse enregistrée."}


def terminer_session_adaptative(
    session_id:   int,
    niveau_final: str,
) -> dict:
    """
    Clôture une session adaptative et calcule la durée.
    """
    conn = _connexion()
    cur  = conn.cursor()

    session = cur.execute(
        "SELECT date_debut FROM track_sessions_adapt WHERE id=?",
        (session_id,)
    ).fetchone()

    duree = None
    if session:
        try:
            debut  = datetime.fromisoformat(session['date_debut'])
            duree  = int((datetime.now() - debut).total_seconds())
        except Exception:
            pass

    cur.execute("""
        UPDATE track_sessions_adapt SET
            niveau_final   = ?,
            date_fin       = ?,
            duree_secondes = ?,
            terminee       = 1
        WHERE id = ?
    """, (niveau_final, _maintenant(), duree, session_id))

    conn.commit()
    conn.close()
    return {"message": "Session adaptative terminée.", "duree": duree}


def get_track_sessions_adapt(
    utilisateur_id: Optional[int] = None,
    objectif_code:  Optional[str] = None,
    limite:         int = 50,
) -> list:
    """
    Retourne les sessions adaptatives.
    Si utilisateur_id est None, retourne toutes (admin).
    """
    conn = _connexion()
    sql  = """
        SELECT sa.*,
               u.nom, u.prenom, u.email, u.niveau, u.institution
        FROM track_sessions_adapt sa
        JOIN utilisateurs u ON sa.utilisateur_id = u.id
        WHERE 1=1
    """
    params = []
    if utilisateur_id is not None:
        sql += " AND sa.utilisateur_id = ?"
        params.append(utilisateur_id)
    if objectif_code:
        sql += " AND sa.objectif_code = ?"
        params.append(objectif_code)
    sql += " ORDER BY sa.date_debut DESC LIMIT ?"
    params.append(limite)

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_track_reponses_adapt(session_id: int) -> list:
    """Retourne le détail des réponses d'une session adaptative."""
    conn = _connexion()
    rows = conn.execute(
        """SELECT * FROM track_reponses_adapt
           WHERE session_id = ?
           ORDER BY date_reponse""",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═════════════════════════════════════════════════════════════
# SESSIONS EXAMENS
# ═════════════════════════════════════════════════════════════

def creer_session_examen(
    utilisateur_id:  int,
    titre:           str,
    objectifs_codes: list,
    mode_bloom:      str,
    niveau:          str,
) -> dict:
    """
    Crée une nouvelle session d'examen liée à l'utilisateur.
    """
    import json
    conn = _connexion()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO track_sessions_exam
            (utilisateur_id, titre, objectifs_codes,
             mode_bloom, niveau, date_examen)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (utilisateur_id, titre,
          json.dumps(objectifs_codes, ensure_ascii=False),
          mode_bloom, niveau, _maintenant()))
    conn.commit()
    session_id = cur.lastrowid
    conn.close()
    return {"session_id": session_id, "message": "Session examen créée."}


def enregistrer_reponse_examen(
    session_examen_id: int,
    utilisateur_id:    int,
    objectif_code:     str,
    mode_bloom:        str,
    niveau_complexite: str,
    enonce:            str,
    reponse_apprenant: str,
    reponse_correcte:  str,
    est_correct:       bool,
    ert_secondes:      float,
    score_question:    float,
    temps_reponse_s:   float = 0.0,
) -> dict:
    """Enregistre une réponse d'examen et met à jour la session."""
    conn = _connexion()
    cur  = conn.cursor()

    cur.execute("""
        INSERT INTO track_reponses_exam
            (session_examen_id, utilisateur_id, objectif_code,
             mode_bloom, niveau_complexite, enonce,
             reponse_apprenant, reponse_correcte, est_correct,
             ert_secondes, score_question, temps_reponse_s,
             date_reponse)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (session_examen_id, utilisateur_id, objectif_code,
          mode_bloom, niveau_complexite, enonce,
          reponse_apprenant, reponse_correcte,
          1 if est_correct else 0,
          ert_secondes, score_question, temps_reponse_s,
          _maintenant()))

    # Mettre à jour nb_questions et nb_correctes
    cur.execute("""
        UPDATE track_sessions_exam SET
            nb_questions = nb_questions + 1,
            nb_correctes = nb_correctes + ?
        WHERE id = ?
    """, (1 if est_correct else 0, session_examen_id))

    conn.commit()
    conn.close()
    return {"message": "Réponse examen enregistrée."}


def terminer_session_examen(session_examen_id: int) -> dict:
    """
    Clôture un examen, calcule la note /20 et la mention.
    """
    conn = _connexion()
    cur  = conn.cursor()

    session = cur.execute(
        "SELECT * FROM track_sessions_exam WHERE id=?",
        (session_examen_id,)
    ).fetchone()

    if not session:
        conn.close()
        raise ValueError(f"Session examen {session_examen_id} introuvable.")

    # Calcul note /20
    nb_q = session['nb_questions']
    nb_c = session['nb_correctes']
    note = round((nb_c / nb_q * 20), 2) if nb_q > 0 else 0.0

    # Mention
    if note >= 18:
        mention = "Très bien"
    elif note >= 16:
        mention = "Bien"
    elif note >= 14:
        mention = "Assez bien"
    elif note >= 10:
        mention = "Passable"
    else:
        mention = "Insuffisant"

    # Durée
    duree = None
    try:
        debut = datetime.fromisoformat(session['date_examen'])
        duree = int((datetime.now() - debut).total_seconds())
    except Exception:
        pass

    cur.execute("""
        UPDATE track_sessions_exam SET
            note_sur_20    = ?,
            mention        = ?,
            duree_secondes = ?,
            termine        = 1
        WHERE id = ?
    """, (note, mention, duree, session_examen_id))

    conn.commit()
    conn.close()

    return {
        "note_sur_20":  note,
        "mention":      mention,
        "nb_questions": nb_q,
        "nb_correctes": nb_c,
        "duree":        duree,
        "message":      "Examen terminé.",
    }


def get_track_sessions_exam(
    utilisateur_id: Optional[int] = None,
    limite:         int = 50,
) -> list:
    """
    Retourne les sessions d'examens terminés.
    Si utilisateur_id est None, retourne toutes (admin).
    """
    import json
    conn = _connexion()
    sql  = """
        SELECT se.*,
               u.nom, u.prenom, u.email, u.niveau, u.institution
        FROM track_sessions_exam se
        JOIN utilisateurs u ON se.utilisateur_id = u.id
        WHERE 1=1
    """
    params = []
    if utilisateur_id is not None:
        sql += " AND se.utilisateur_id = ?"
        params.append(utilisateur_id)
    sql += " ORDER BY se.date_examen DESC LIMIT ?"
    params.append(limite)

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d['objectifs_codes'] = json.loads(d['objectifs_codes'])
        except Exception:
            pass
        result.append(d)
    return result


def get_reponses_examen(session_examen_id: int) -> list:
    """Retourne le détail des réponses d'un examen."""
    conn = _connexion()
    rows = conn.execute(
        """SELECT * FROM track_reponses_exam
           WHERE session_examen_id = ?
           ORDER BY date_reponse""",
        (session_examen_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═════════════════════════════════════════════════════════════
# HISTORIQUE COMPLET D'UN APPRENANT
# ═════════════════════════════════════════════════════════════

def get_historique_apprenant(utilisateur_id: int) -> dict:
    """
    Retourne l'historique complet d'un apprenant :
    - Sessions adaptatives terminées
    - Sessions examens terminées
    - Résumé global
    """
    sessions_adapt = get_track_sessions_adapt(utilisateur_id)
    sessions_exam  = get_track_sessions_exam(utilisateur_id)

    # Résumé global
    total_questions = sum(s['nb_questions'] for s in sessions_adapt) + \
                      sum(s['nb_questions'] for s in sessions_exam)
    total_correctes = sum(s['nb_correctes'] for s in sessions_adapt) + \
                      sum(s['nb_correctes'] for s in sessions_exam)

    taux_global = round(
        total_correctes / total_questions * 100, 1
    ) if total_questions > 0 else 0.0

    notes_exam = [s['note_sur_20'] for s in sessions_exam if s['note_sur_20'] > 0]
    note_moyenne = round(
        sum(notes_exam) / len(notes_exam), 2
    ) if notes_exam else 0.0

    # ERT moyen global
    erts = [s['ert_moyen'] for s in sessions_adapt if s['ert_moyen'] > 0]
    ert_moyen = round(sum(erts) / len(erts), 1) if erts else 0.0

    return {
        "utilisateur_id":    utilisateur_id,
        "sessions_adaptatives": sessions_adapt,
        "sessions_examens":     sessions_exam,
        "resume": {
            "total_sessions_adapt": len(sessions_adapt),
            "total_sessions_exam":  len(sessions_exam),
            "total_questions":      total_questions,
            "total_correctes":      total_correctes,
            "taux_reussite_global": taux_global,
            "note_moyenne_examens": note_moyenne,
            "ert_moyen_sessions":   ert_moyen,
        }
    }


def get_resultats_par_objectif(utilisateur_id: int) -> list:
    """
    Retourne le taux de réussite par objectif pour un apprenant.
    Agrège les réponses adaptatives ET les réponses d'examens.
    """
    conn = _connexion()

    # Réponses adaptatives
    rows_adapt = conn.execute("""
        SELECT objectif_code,
               COUNT(*) as total,
               SUM(est_correct) as correctes,
               AVG(ert_secondes) as ert_moyen,
               AVG(score_question) as score_moyen
        FROM track_reponses_adapt
        WHERE utilisateur_id = ?
        GROUP BY objectif_code
    """, (utilisateur_id,)).fetchall()

    # Réponses examens
    rows_exam = conn.execute("""
        SELECT objectif_code,
               COUNT(*) as total,
               SUM(est_correct) as correctes,
               AVG(ert_secondes) as ert_moyen,
               AVG(score_question) as score_moyen
        FROM track_reponses_exam
        WHERE utilisateur_id = ?
        GROUP BY objectif_code
    """, (utilisateur_id,)).fetchall()

    conn.close()

    # Fusionner adapt + exam par objectif
    fusionnes = {}
    for rows in [rows_adapt, rows_exam]:
        for r in rows:
            code = r['objectif_code']
            if code not in fusionnes:
                fusionnes[code] = {
                    'objectif_code': code,
                    'total':         0,
                    'correctes':     0,
                    'ert_total':     0.0,
                    'score_total':   0.0,
                    'n_ert':         0,
                }
            fusionnes[code]['total']       += r['total']
            fusionnes[code]['correctes']   += r['correctes'] or 0
            fusionnes[code]['ert_total']   += (r['ert_moyen'] or 0) * r['total']
            fusionnes[code]['score_total'] += (r['score_moyen'] or 0) * r['total']
            fusionnes[code]['n_ert']       += r['total']

    # Calculer les moyennes finales
    result = []
    for code, d in fusionnes.items():
        n = d['total']
        result.append({
            'objectif_code': code,
            'total':         n,
            'correctes':     d['correctes'],
            'taux_reussite': round(d['correctes'] / n * 100, 1) if n > 0 else 0.0,
            'ert_moyen':     round(d['ert_total'] / d['n_ert'], 1) if d['n_ert'] > 0 else 0.0,
            'score_moyen':   round(d['score_total'] / n, 2) if n > 0 else 0.0,
        })

    return sorted(result, key=lambda x: x['taux_reussite'])


# ═════════════════════════════════════════════════════════════
# TEST
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile

    # Base temporaire
    DB_PATH = os.path.join(tempfile.gettempdir(), 'rali_test_tracking.db')

    # Créer d'abord la table utilisateurs (dépendance)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT, prenom TEXT, email TEXT UNIQUE,
            mot_de_passe TEXT, sel TEXT,
            niveau TEXT, institution TEXT,
            role TEXT DEFAULT 'apprenant',
            actif INTEGER DEFAULT 1,
            date_creation TEXT, derniere_connexion TEXT
        )
    """)
    conn.execute("""
        INSERT OR IGNORE INTO utilisateurs
            (nom,prenom,email,mot_de_passe,sel,niveau,institution,date_creation)
        VALUES ('Test','User','test@test.cm','hash','sel','L2','UYI','2026-01-01')
    """)
    conn.commit()
    USER_ID = conn.execute(
        "SELECT id FROM utilisateurs WHERE email='test@test.cm'"
    ).fetchone()[0]
    conn.close()

    print("=== Test tracking.py ===\n")

    # 1. Init
    init_tables_tracking()
    print("1. Init tables ✅")

    # 2. Session adaptative
    r = creer_session_adaptative(USER_ID, "NEG_IMP", "comprehension", "faible")
    sid = r['session_id']
    print(f"2. Session adaptative créée ✅ — id: {sid}")

    # 3. Enregistrer réponses
    for i, correct in enumerate([True, False, True, True]):
        enregistrer_reponse_adaptative(
            session_id=sid, utilisateur_id=USER_ID,
            objectif_code="NEG_IMP", mode_bloom="comprehension",
            niveau_complexite="moyen",
            enonce=f"Question {i+1}",
            reponse_apprenant="P et non Q",
            reponse_correcte="P et non Q",
            est_correct=correct,
            ert_secondes=105.0,
            score_question=1.4 if correct else 0.0,
        )
    print("3. 4 réponses adaptatives enregistrées ✅")

    # 4. Terminer session
    r2 = terminer_session_adaptative(sid, "moyen")
    print(f"4. Session terminée ✅ — durée: {r2['duree']}s")

    # 5. Session examen
    r3 = creer_session_examen(
        USER_ID, "Examen Final",
        ["NEG_IMP", "MORGAN", "CONTRAP"],
        "comprehension", "moyen"
    )
    eid = r3['session_id']
    print(f"5. Session examen créée ✅ — id: {eid}")

    # 6. Réponses examen
    for i, correct in enumerate([True, True, False, True, True]):
        enregistrer_reponse_examen(
            session_examen_id=eid, utilisateur_id=USER_ID,
            objectif_code=["NEG_IMP","MORGAN","CONTRAP","NEG_IMP","MORGAN"][i],
            mode_bloom="comprehension", niveau_complexite="moyen",
            enonce=f"Examen Q{i+1}", reponse_apprenant="R",
            reponse_correcte="R", est_correct=correct,
            ert_secondes=105.0, score_question=1.4 if correct else 0.0,
            temps_reponse_s=45.0,
        )
    print("6. 5 réponses examen enregistrées ✅")

    # 7. Terminer examen
    r4 = terminer_session_examen(eid)
    print(f"7. Examen terminé ✅ — note: {r4['note_sur_20']}/20 ({r4['mention']})")

    # 8. Historique apprenant
    hist = get_historique_apprenant(USER_ID)
    r_hist = hist['resume']
    print(f"8. Historique ✅ — {r_hist['total_sessions_adapt']} adapt, "
          f"{r_hist['total_sessions_exam']} exam, "
          f"taux global: {r_hist['taux_reussite_global']}%")

    # 9. Résultats par objectif
    par_obj = get_resultats_par_objectif(USER_ID)
    print(f"9. Résultats par objectif ✅ — {len(par_obj)} objectifs:")
    for o in par_obj:
        print(f"   [{o['objectif_code']}] "
              f"{o['correctes']}/{o['total']} = {o['taux_reussite']}%")

    print("\n✅ Tous les tests passent !")
