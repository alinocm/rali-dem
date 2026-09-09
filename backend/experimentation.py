# -------------------------------------------------------------
# experimentation.py -- Module de collecte des donnees
#                      experimentales RALI-DEM
#
# Protocole : chaque etudiant passe une session chronometree
# de N questions couvrant les objectifs et niveaux cibles.
# Chaque reponse enregistre :
#   - Le temps reel de reponse (validation ERT)
#   - Le distracteur exact choisi (validation diagnostique)
#   - Le profil de l'etudiant (niveau, etablissement)
# -------------------------------------------------------------

import os
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict

def _get_db_path() -> str:
    """Resout le chemin de la base dynamiquement a chaque appel."""
    # Priorite 1 : variable d'environnement (definie par main.py)
    env = os.environ.get('RALI_DB_PATH')
    if env:
        return env
    # Priorite 2 : chemin relatif au fichier
    base = os.path.dirname(os.path.abspath(__file__))
    for rel in [
        os.path.join(base, '..', 'database', 'rali_dem.db'),
        os.path.join(base, 'database', 'rali_dem.db'),
        os.path.join(base, '..', 'rali_dem.db'),
    ]:
        if os.path.exists(rel):
            return rel
    # Priorite 3 : chemin par defaut
    return os.path.join(base, '..', 'database', 'rali_dem.db')


def _connexion() -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _now() -> str:
    return datetime.now().isoformat()


# =============================================================
# INITIALISATION DES TABLES
# =============================================================

def init_tables_experimentation():
    """
    Cree les tables de collecte des donnees experimentales.
    Independant des tables utilisateurs existantes --
    les participants peuvent s'inscrire sans compte.
    """
    conn = _connexion()
    cur  = conn.cursor()

    # -- 1. Participants a l'experimentation ------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exp_participants (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            code_anonyme    TEXT    NOT NULL UNIQUE,
            nom             TEXT,
            prenom          TEXT,
            email           TEXT,
            niveau_etudes   TEXT    NOT NULL,
            etablissement   TEXT,
            consentement    INTEGER NOT NULL DEFAULT 0,
            date_inscription TEXT   NOT NULL,
            utilisateur_id  INTEGER,
            FOREIGN KEY (utilisateur_id)
                REFERENCES utilisateurs(id) ON DELETE SET NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_exp_code "
                "ON exp_participants(code_anonyme)")

    # -- 2. Sessions experimentales ----------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exp_sessions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id      INTEGER NOT NULL,
            code_session        TEXT    NOT NULL UNIQUE,
            protocole           TEXT    NOT NULL DEFAULT 'standard',
            nb_questions_cible  INTEGER NOT NULL DEFAULT 30,
            nb_questions_faites INTEGER NOT NULL DEFAULT 0,
            statut              TEXT    NOT NULL DEFAULT 'en_cours',
            date_debut          TEXT    NOT NULL,
            date_fin            TEXT,
            duree_totale_s      REAL,
            score_global        REAL,
            FOREIGN KEY (participant_id)
                REFERENCES exp_participants(id) ON DELETE CASCADE
        )
    """)

    # -- 3. Reponses experimentales (une ligne par question) ---
    # C'est la table principale pour les deux validations :
    #   - ERT : temps_reel_s vs ert_predit_s
    #   - Distracteurs : distracteur_choisi vs reponse_correcte
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exp_reponses (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id          INTEGER NOT NULL,
            participant_id      INTEGER NOT NULL,
            numero_question     INTEGER NOT NULL,
            objectif_code       TEXT    NOT NULL,
            mode_bloom          TEXT    NOT NULL,
            niveau_complexite   TEXT    NOT NULL,

            -- Question generee
            enonce              TEXT    NOT NULL,
            choix_a             TEXT    NOT NULL,
            choix_b             TEXT    NOT NULL,
            choix_c             TEXT    NOT NULL,
            choix_d             TEXT    NOT NULL,
            reponse_correcte    TEXT    NOT NULL,

            -- Parametres de complexite
            ert_predit_s        REAL    NOT NULL,
            score_predit        REAL    NOT NULL,
            nb_propositions     INTEGER NOT NULL DEFAULT 2,
            nb_connecteurs      INTEGER NOT NULL DEFAULT 0,
            nb_quantificateurs  INTEGER NOT NULL DEFAULT 0,
            nb_negations        INTEGER NOT NULL DEFAULT 0,
            profondeur          INTEGER NOT NULL DEFAULT 1,

            -- Reponse de l'etudiant
            distracteur_choisi  TEXT    NOT NULL,
            est_correct         INTEGER NOT NULL,
            temps_reel_s        REAL    NOT NULL,
            timestamp_debut     TEXT    NOT NULL,
            timestamp_fin       TEXT    NOT NULL,

            FOREIGN KEY (session_id)
                REFERENCES exp_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (participant_id)
                REFERENCES exp_participants(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_exp_rep_session "
                "ON exp_reponses(session_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_exp_rep_objectif "
                "ON exp_reponses(objectif_code)")

    # -- 4. Evaluations qualitatives par les apprenants -------
    # Une evaluation par session -- 6 criteres Likert 1-5
    # Remplace/complete les evaluations par experts (3 juges)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exp_eval_qualitative (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id          INTEGER NOT NULL,
            participant_id      INTEGER NOT NULL,

            -- Critere 1 : Coherence linguistique
            grammaticalite      INTEGER NOT NULL CHECK(grammaticalite BETWEEN 1 AND 5),
            naturalite          INTEGER NOT NULL CHECK(naturalite BETWEEN 1 AND 5),
            clarte              INTEGER NOT NULL CHECK(clarte BETWEEN 1 AND 5),

            -- Critere 2 : Plausibilite pedagogique
            plausibilite_dist   INTEGER NOT NULL CHECK(plausibilite_dist BETWEEN 1 AND 5),
            pertinence_obj      INTEGER NOT NULL CHECK(pertinence_obj BETWEEN 1 AND 5),
            alignement_bloom    INTEGER NOT NULL CHECK(alignement_bloom BETWEEN 1 AND 5),

            -- Critere 3 : Acceptabilite generale
            acceptabilite       INTEGER NOT NULL CHECK(acceptabilite BETWEEN 1 AND 5),
            utilite_apprentissage INTEGER NOT NULL CHECK(utilite_apprentissage BETWEEN 1 AND 5),

            -- Commentaire libre (optionnel)
            commentaire         TEXT,

            -- Scores calcules
            score_coherence     REAL,   -- moyenne grammaticalite+naturalite+clarte
            score_plausibilite  REAL,   -- moyenne plausibilite+pertinence+bloom
            score_acceptabilite REAL,   -- moyenne acceptabilite+utilite
            score_global        REAL,   -- moyenne des 8 criteres

            date_eval           TEXT    NOT NULL,

            FOREIGN KEY (session_id)
                REFERENCES exp_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (participant_id)
                REFERENCES exp_participants(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_exp_eval_session "
                "ON exp_eval_qualitative(session_id)")

    conn.commit()
    conn.close()
    print("[EXPERIMENTATION] Tables initialisees.")


# =============================================================
# GESTION DES PARTICIPANTS
# =============================================================

def inscrire_participant(
    nom: str, prenom: str, email: str,
    niveau_etudes: str, etablissement: str,
    consentement: bool, utilisateur_id: Optional[int] = None
) -> Dict:
    """
    Inscrit un nouveau participant a l'experimentation.
    Genere un code anonyme unique pour la these.
    """
    import hashlib, time
    code = "P" + hashlib.md5(
        f"{email}{time.time()}".encode()
    ).hexdigest()[:8].upper()

    conn = _connexion()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO exp_participants
            (code_anonyme, nom, prenom, email, niveau_etudes,
             etablissement, consentement, date_inscription, utilisateur_id)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (code, nom, prenom, email, niveau_etudes,
              etablissement, int(consentement), _now(), utilisateur_id))
        conn.commit()
        pid = cur.lastrowid
        return {"success": True, "participant_id": pid,
                "code_anonyme": code}
    except sqlite3.IntegrityError:
        return {"success": False, "error": "Email deja inscrit"}
    finally:
        conn.close()


def get_participant_by_email(email: str) -> Optional[Dict]:
    conn = _connexion()
    cur  = conn.cursor()
    row  = cur.execute(
        "SELECT * FROM exp_participants WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# =============================================================
# GESTION DES SESSIONS
# =============================================================

def creer_session_exp(
    participant_id: int,
    protocole: str = "standard",
    nb_questions: int = 30
) -> Dict:
    """
    Cree une nouvelle session experimentale.
    Protocole standard : 30 questions couvrant
    les 15 objectifs ? 2 modes Bloom.
    """
    import uuid
    code = "S" + str(uuid.uuid4())[:8].upper()

    conn = _connexion()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO exp_sessions
        (participant_id, code_session, protocole,
         nb_questions_cible, date_debut, statut)
        VALUES (?,?,?,?,?,'en_cours')
    """, (participant_id, code, protocole, nb_questions, _now()))
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return {"session_id": sid, "code_session": code,
            "nb_questions_cible": nb_questions}


def enregistrer_reponse_exp(
    session_id: int,
    participant_id: int,
    numero_question: int,
    question_data: Dict,
    reponse: Dict
) -> Dict:
    """
    Enregistre une reponse experimentale complete.

    question_data contient : enonce, choix_a/b/c/d,
    reponse_correcte, ert_predit_s, score_predit,
    objectif_code, mode_bloom, niveau_complexite,
    nb_propositions, nb_connecteurs, nb_quantificateurs,
    nb_negations, profondeur.

    reponse contient : distracteur_choisi,
    timestamp_debut, timestamp_fin.
    """
    # Calcul du temps reel
    try:
        debut = datetime.fromisoformat(reponse["timestamp_debut"])
        fin   = datetime.fromisoformat(reponse["timestamp_fin"])
        temps_reel = (fin - debut).total_seconds()
    except Exception:
        temps_reel = 0.0

    distracteur = reponse.get("distracteur_choisi", "")
    est_correct = int(
        distracteur.strip().lower() ==
        question_data.get("reponse_correcte", "").strip().lower()
    )

    conn = _connexion()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO exp_reponses (
            session_id, participant_id, numero_question,
            objectif_code, mode_bloom, niveau_complexite,
            enonce, choix_a, choix_b, choix_c, choix_d,
            reponse_correcte,
            ert_predit_s, score_predit,
            nb_propositions, nb_connecteurs,
            nb_quantificateurs, nb_negations, profondeur,
            distracteur_choisi, est_correct,
            temps_reel_s, timestamp_debut, timestamp_fin
        ) VALUES (
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )
    """, (
        session_id, participant_id, numero_question,
        question_data.get("objectif_code"),
        question_data.get("mode_bloom"),
        question_data.get("niveau_complexite"),
        question_data.get("enonce"),
        question_data.get("choix_a"),
        question_data.get("choix_b"),
        question_data.get("choix_c"),
        question_data.get("choix_d"),
        question_data.get("reponse_correcte"),
        question_data.get("ert_predit_s", 0.0),
        question_data.get("score_predit", 0.0),
        question_data.get("nb_propositions", 2),
        question_data.get("nb_connecteurs", 0),
        question_data.get("nb_quantificateurs", 0),
        question_data.get("nb_negations", 0),
        question_data.get("profondeur", 1),
        distracteur,
        est_correct,
        temps_reel,
        reponse.get("timestamp_debut"),
        reponse.get("timestamp_fin")
    ))

    # Mettre a jour le compteur de la session
    cur.execute("""
        UPDATE exp_sessions
        SET nb_questions_faites = nb_questions_faites + 1
        WHERE id = ?
    """, (session_id,))

    conn.commit()
    conn.close()
    return {"success": True, "est_correct": est_correct,
            "temps_reel_s": round(temps_reel, 2)}


def terminer_session_exp(session_id: int) -> Dict:
    """Cloture une session et calcule le score global."""
    conn = _connexion()
    cur  = conn.cursor()

    stats = cur.execute("""
        SELECT COUNT(*) as total,
               SUM(est_correct) as correctes,
               AVG(temps_reel_s) as temps_moyen,
               AVG(ert_predit_s) as ert_moyen
        FROM exp_reponses WHERE session_id = ?
    """, (session_id,)).fetchone()

    total     = stats["total"] or 0
    correctes = stats["correctes"] or 0
    score     = round((correctes / total * 100), 1) if total > 0 else 0

    # Calculer la duree totale
    session = cur.execute(
        "SELECT date_debut FROM exp_sessions WHERE id = ?",
        (session_id,)
    ).fetchone()

    duree = None
    if session:
        try:
            debut  = datetime.fromisoformat(session["date_debut"])
            duree  = round((datetime.now() - debut).total_seconds(), 0)
        except Exception:
            pass

    cur.execute("""
        UPDATE exp_sessions
        SET statut='terminee', date_fin=?, duree_totale_s=?,
            score_global=?
        WHERE id = ?
    """, (_now(), duree, score, session_id))
    conn.commit()
    conn.close()
    return {"score_global": score, "nb_correctes": correctes,
            "nb_total": total, "temps_moyen_s": stats["temps_moyen"]}


# =============================================================
# EXPORT DES DONNEES POUR LA THESE
# =============================================================

def enregistrer_eval_qualitative(
    session_id: int,
    participant_id: int,
    grammaticalite: int,
    naturalite: int,
    clarte: int,
    plausibilite_dist: int,
    pertinence_obj: int,
    alignement_bloom: int,
    acceptabilite: int,
    utilite_apprentissage: int,
    commentaire: str = ""
) -> Dict:
    """
    Enregistre l'evaluation qualitative d'un participant
    a la fin de sa session (8 criteres Likert 1-5).
    """
    score_coh  = round((grammaticalite + naturalite + clarte) / 3, 2)
    score_plau = round((plausibilite_dist + pertinence_obj + alignement_bloom) / 3, 2)
    score_acc  = round((acceptabilite + utilite_apprentissage) / 2, 2)
    score_glob = round((grammaticalite + naturalite + clarte +
                        plausibilite_dist + pertinence_obj +
                        alignement_bloom + acceptabilite +
                        utilite_apprentissage) / 8, 2)

    conn = _connexion()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO exp_eval_qualitative (
                session_id, participant_id,
                grammaticalite, naturalite, clarte,
                plausibilite_dist, pertinence_obj, alignement_bloom,
                acceptabilite, utilite_apprentissage,
                commentaire,
                score_coherence, score_plausibilite,
                score_acceptabilite, score_global,
                date_eval
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            session_id, participant_id,
            grammaticalite, naturalite, clarte,
            plausibilite_dist, pertinence_obj, alignement_bloom,
            acceptabilite, utilite_apprentissage,
            commentaire,
            score_coh, score_plau, score_acc, score_glob,
            _now()
        ))
        conn.commit()
        return {"success": True,
                "scores": {
                    "coherence": score_coh,
                    "plausibilite": score_plau,
                    "acceptabilite": score_acc,
                    "global": score_glob
                }}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_synthese_qualitative() -> Dict:
    """
    Synthese des evaluations qualitatives par les apprenants.
    Comparable aux Tableaux 4.6 et 4.7 de la these.
    """
    conn = _connexion()
    cur  = conn.cursor()

    # Moyennes et ecart-types pour chaque critere
    stats = cur.execute("""
        SELECT
            AVG(grammaticalite)       as moy_gram,
            AVG(naturalite)           as moy_nat,
            AVG(clarte)               as moy_cla,
            AVG(plausibilite_dist)    as moy_plau,
            AVG(pertinence_obj)       as moy_pert,
            AVG(alignement_bloom)     as moy_bloom,
            AVG(acceptabilite)        as moy_acc,
            AVG(utilite_apprentissage) as moy_util,
            AVG(score_coherence)      as moy_coh,
            AVG(score_plausibilite)   as moy_plas,
            AVG(score_acceptabilite)  as moy_accs,
            AVG(score_global)         as moy_global,
            COUNT(*)                  as n_evaluations
        FROM exp_eval_qualitative
    """).fetchone()

    # Ecart-types
    import math
    criteres = ['grammaticalite','naturalite','clarte',
                'plausibilite_dist','pertinence_obj','alignement_bloom',
                'acceptabilite','utilite_apprentissage']
    std_devs = {}
    for c in criteres:
        vals = [r[0] for r in cur.execute(
            f"SELECT {c} FROM exp_eval_qualitative"
        ).fetchall()]
        if len(vals) > 1:
            mean = sum(vals)/len(vals)
            std_devs[c] = round(math.sqrt(
                sum((v-mean)**2 for v in vals)/(len(vals)-1)
            ), 2)
        else:
            std_devs[c] = 0.0

    conn.close()
    return {
        "n": stats["n_evaluations"],
        "coherence_linguistique": {
            "grammaticalite": {"moy": round(stats["moy_gram"] or 0, 2),
                               "std": std_devs["grammaticalite"]},
            "naturalite":     {"moy": round(stats["moy_nat"] or 0, 2),
                               "std": std_devs["naturalite"]},
            "clarte":         {"moy": round(stats["moy_cla"] or 0, 2),
                               "std": std_devs["clarte"]},
            "moyenne":        round(stats["moy_coh"] or 0, 2),
        },
        "plausibilite_pedagogique": {
            "plausibilite_distracteurs": {
                "moy": round(stats["moy_plau"] or 0, 2),
                "std": std_devs["plausibilite_dist"]},
            "pertinence_objectif": {
                "moy": round(stats["moy_pert"] or 0, 2),
                "std": std_devs["pertinence_obj"]},
            "alignement_bloom": {
                "moy": round(stats["moy_bloom"] or 0, 2),
                "std": std_devs["alignement_bloom"]},
            "moyenne":        round(stats["moy_plas"] or 0, 2),
        },
        "acceptabilite_generale": {
            "acceptabilite":      {"moy": round(stats["moy_acc"] or 0, 2),
                                   "std": std_devs["acceptabilite"]},
            "utilite_apprentissage": {
                "moy": round(stats["moy_util"] or 0, 2),
                "std": std_devs["utilite_apprentissage"]},
            "moyenne":            round(stats["moy_accs"] or 0, 2),
        },
        "score_global": round(stats["moy_global"] or 0, 2),
    }


def exporter_eval_qualitative_csv() -> str:
    """Export CSV de toutes les evaluations qualitatives."""
    import csv, io
    conn = _connexion()
    cur  = conn.cursor()

    rows = cur.execute("""
        SELECT
            p.code_anonyme, p.niveau_etudes, p.etablissement,
            e.grammaticalite, e.naturalite, e.clarte,
            e.plausibilite_dist, e.pertinence_obj, e.alignement_bloom,
            e.acceptabilite, e.utilite_apprentissage,
            e.score_coherence, e.score_plausibilite,
            e.score_acceptabilite, e.score_global,
            e.commentaire
        FROM exp_eval_qualitative e
        JOIN exp_participants p ON e.participant_id = p.id
        ORDER BY e.date_eval
    """).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "code_anonyme","niveau_etudes","etablissement",
        "grammaticalite","naturalite","clarte",
        "plausibilite_distracteurs","pertinence_objectif","alignement_bloom",
        "acceptabilite","utilite_apprentissage",
        "score_coherence","score_plausibilite",
        "score_acceptabilite","score_global","commentaire"
    ])
    for row in rows:
        writer.writerow(list(row))
    return output.getvalue()


def exporter_donnees_ert_csv() -> str:
    """
    Export CSV pour validation ERT :
    temps_reel_s vs ert_predit_s par question.
    C'est le fichier pour calculer r(ERT, temps_reel).
    """
    import csv, io
    conn = _connexion()
    cur  = conn.cursor()

    rows = cur.execute("""
        SELECT
            r.objectif_code,
            r.mode_bloom,
            r.niveau_complexite,
            r.nb_propositions,
            r.nb_connecteurs,
            r.nb_quantificateurs,
            r.nb_negations,
            r.profondeur,
            r.ert_predit_s,
            r.score_predit,
            r.temps_reel_s,
            r.est_correct,
            p.niveau_etudes,
            p.etablissement,
            p.code_anonyme
        FROM exp_reponses r
        JOIN exp_participants p ON r.participant_id = p.id
        JOIN exp_sessions s ON r.session_id = s.id
        WHERE s.statut = 'terminee'
        ORDER BY r.objectif_code, r.mode_bloom
    """).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "code_anonyme", "niveau_etudes", "etablissement",
        "objectif_code", "mode_bloom", "niveau_complexite",
        "nb_propositions", "nb_connecteurs", "nb_quantificateurs",
        "nb_negations", "profondeur",
        "ert_predit_s", "score_predit",
        "temps_reel_s", "est_correct"
    ])
    for row in rows:
        writer.writerow(list(row))
    return output.getvalue()


def exporter_donnees_distracteurs_csv() -> str:
    """
    Export CSV pour validation des distracteurs :
    quel distracteur a ete choisi pour chaque question.
    Permet de calculer la frequence de selection par distracteur.
    """
    import csv, io
    conn = _connexion()
    cur  = conn.cursor()

    rows = cur.execute("""
        SELECT
            r.objectif_code,
            r.mode_bloom,
            r.niveau_complexite,
            r.enonce,
            r.choix_a, r.choix_b, r.choix_c, r.choix_d,
            r.reponse_correcte,
            r.distracteur_choisi,
            r.est_correct,
            r.ert_predit_s,
            r.temps_reel_s,
            p.niveau_etudes,
            p.code_anonyme
        FROM exp_reponses r
        JOIN exp_participants p ON r.participant_id = p.id
        JOIN exp_sessions s ON r.session_id = s.id
        WHERE s.statut = 'terminee'
        ORDER BY r.objectif_code
    """).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "code_anonyme", "niveau_etudes",
        "objectif_code", "mode_bloom", "niveau_complexite",
        "enonce",
        "choix_a", "choix_b", "choix_c", "choix_d",
        "reponse_correcte", "distracteur_choisi",
        "est_correct", "ert_predit_s", "temps_reel_s"
    ])
    for row in rows:
        writer.writerow(list(row))
    return output.getvalue()


def get_stats_experimentation() -> Dict:
    """
    Statistiques globales de l'experimentation
    pour le tableau de bord administrateur.
    """
    conn = _connexion()
    cur  = conn.cursor()

    nb_participants = cur.execute(
        "SELECT COUNT(*) FROM exp_participants"
    ).fetchone()[0]

    nb_sessions = cur.execute(
        "SELECT COUNT(*) FROM exp_sessions WHERE statut='terminee'"
    ).fetchone()[0]

    nb_reponses = cur.execute(
        "SELECT COUNT(*) FROM exp_reponses"
    ).fetchone()[0]

    # Correlation ERT : moyennes par objectif
    stats_ert = cur.execute("""
        SELECT objectif_code, mode_bloom,
               AVG(ert_predit_s) as ert_moy,
               AVG(temps_reel_s) as temps_moy,
               COUNT(*) as n
        FROM exp_reponses
        GROUP BY objectif_code, mode_bloom
        ORDER BY objectif_code
    """).fetchall()

    # Analyse distracteurs : % erreurs par type
    stats_dist = cur.execute("""
        SELECT objectif_code,
               distracteur_choisi,
               COUNT(*) as freq,
               AVG(est_correct) as taux_reussite
        FROM exp_reponses
        WHERE est_correct = 0
        GROUP BY objectif_code, distracteur_choisi
        ORDER BY freq DESC
        LIMIT 20
    """).fetchall()

    conn.close()
    return {
        "nb_participants": nb_participants,
        "nb_sessions_terminees": nb_sessions,
        "nb_reponses_total": nb_reponses,
        "stats_ert": [dict(r) for r in stats_ert],
        "erreurs_frequentes": [dict(r) for r in stats_dist]
    }
