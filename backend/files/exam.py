# ─────────────────────────────────────────────────────────────
# exam.py  —  Mode examen chronométré RALI-DEM
# Génère une série de questions avec timer basé sur l'ERT.
# Produit un bulletin de résultats complet à la fin.
# ─────────────────────────────────────────────────────────────

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'rali_dem.db')

# ─────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────

# Temps supplémentaire accordé par rapport à l'ERT (en %)
MARGE_TEMPS = 1.5   # l'apprenant a 1.5× l'ERT estimé

# Pénalité de score pour dépassement du temps (par seconde)
PENALITE_TEMPS = 0.05

# Score maximum par question
SCORE_MAX_QUESTION = 10.0


# ─────────────────────────────────────────────────────────────
# INITIALISATION DE LA BASE
# ─────────────────────────────────────────────────────────────

def init_tables_examen():
    """Crée les tables nécessaires au mode examen."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Table des examens
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS examens (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            apprenant       TEXT    NOT NULL DEFAULT "anonyme",
            titre           TEXT    NOT NULL DEFAULT "Examen RALI-DEM",
            objectifs       TEXT    NOT NULL,
            mode_bloom      TEXT    NOT NULL DEFAULT "comprehension",
            niveau          TEXT    NOT NULL DEFAULT "moyen",
            nb_questions    INTEGER NOT NULL DEFAULT 10,
            temps_total_s   REAL    NOT NULL DEFAULT 0,
            score_obtenu    REAL    NOT NULL DEFAULT 0,
            score_max       REAL    NOT NULL DEFAULT 0,
            taux_reussite   REAL    NOT NULL DEFAULT 0,
            statut          TEXT    NOT NULL DEFAULT "en_cours",
            date_debut      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date_fin        TIMESTAMP
        )
    ''')

    # Table des questions d'examen
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions_examen (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            examen_id       INTEGER NOT NULL REFERENCES examens(id),
            numero          INTEGER NOT NULL,
            objectif_code   TEXT    NOT NULL,
            enonce          TEXT    NOT NULL,
            reponse_correcte TEXT   NOT NULL,
            distracteurs    TEXT    NOT NULL,
            ert_secondes    REAL    NOT NULL,
            temps_accorde_s REAL    NOT NULL,
            score_max       REAL    NOT NULL DEFAULT 10,
            reponse_apprenant TEXT,
            est_correct     INTEGER,
            temps_reponse_s REAL,
            score_obtenu    REAL    NOT NULL DEFAULT 0,
            penalite_temps  REAL    NOT NULL DEFAULT 0
        )
    ''')

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
# CRÉATION D'UN EXAMEN
# ─────────────────────────────────────────────────────────────

def creer_examen(
    objectifs:    list,
    mode_bloom:   str  = "comprehension",
    niveau:       str  = "moyen",
    nb_questions: int  = 10,
    apprenant:    str  = "anonyme",
    titre:        str  = "Examen RALI-DEM",
) -> dict:
    """
    Génère un examen complet avec N questions.

    Paramètres
    ----------
    objectifs    : liste des codes objectifs à inclure
                   ex: ["NEG_IMP", "MORGAN", "CONTRAP"]
    mode_bloom   : "comprehension" ou "analyse"
    niveau       : "faible", "moyen" ou "eleve"
    nb_questions : nombre total de questions
    apprenant    : identifiant de l'apprenant
    titre        : titre de l'examen

    Retourne
    --------
    dict avec l'examen complet et les questions générées
    """
    # Import local pour éviter les dépendances circulaires
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from generator import generer_question

    questions_generees = []
    temps_total = 0.0
    score_max_total = 0.0
    i = 0
    tentatives = 0

    while len(questions_generees) < nb_questions and tentatives < nb_questions * 3:
        tentatives += 1
        # Alterner entre les objectifs demandés
        obj = objectifs[i % len(objectifs)]
        i += 1
        try:
            q = generer_question(obj, mode_bloom, niveau)

            # Temps accordé = ERT × marge
            temps_accorde = round(q["ert_secondes"] * MARGE_TEMPS, 1)
            temps_total  += temps_accorde
            score_max_total += SCORE_MAX_QUESTION

            questions_generees.append({
                "numero":          len(questions_generees) + 1,
                "objectif_code":   obj,
                "enonce":          q["enonce"],
                "reponse_correcte":q["reponse_correcte"],
                "distracteurs":    q["distracteurs"],
                "ert_secondes":    q["ert_secondes"],
                "temps_accorde_s": temps_accorde,
                "score_max":       SCORE_MAX_QUESTION,
            })
        except Exception:
            continue

    # Sauvegarder l'examen en base
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO examens
        (apprenant, titre, objectifs, mode_bloom, niveau,
         nb_questions, temps_total_s, score_max)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        apprenant, titre,
        json.dumps(objectifs),
        mode_bloom, niveau,
        len(questions_generees),
        round(temps_total, 1),
        score_max_total,
    ))
    examen_id = cursor.lastrowid

    for q in questions_generees:
        cursor.execute('''
            INSERT INTO questions_examen
            (examen_id, numero, objectif_code, enonce,
             reponse_correcte, distracteurs,
             ert_secondes, temps_accorde_s, score_max)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            examen_id,
            q["numero"],
            q["objectif_code"],
            q["enonce"],
            q["reponse_correcte"],
            json.dumps(q["distracteurs"]),
            q["ert_secondes"],
            q["temps_accorde_s"],
            q["score_max"],
        ))

    conn.commit()
    conn.close()

    return {
        "examen_id":    examen_id,
        "titre":        titre,
        "apprenant":    apprenant,
        "nb_questions": len(questions_generees),
        "temps_total_s": round(temps_total, 1),
        "temps_total_min": round(temps_total / 60, 1),
        "score_max":    score_max_total,
        "questions":    questions_generees,
        "statut":       "en_cours",
        "message":      (
            f"Examen prêt : {len(questions_generees)} questions, "
            f"durée estimée {round(temps_total/60, 1)} minutes."
        ),
    }


# ─────────────────────────────────────────────────────────────
# SOUMISSION D'UNE RÉPONSE
# ─────────────────────────────────────────────────────────────

def soumettre_reponse(
    examen_id:         int,
    numero_question:   int,
    reponse_apprenant: str,
    temps_reponse_s:   float,
) -> dict:
    """
    Enregistre la réponse à une question et calcule le score.
    Applique une pénalité si le temps accordé est dépassé.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Récupérer la question
    cursor.execute('''
        SELECT * FROM questions_examen
        WHERE examen_id = ? AND numero = ?
    ''', (examen_id, numero_question))
    q = cursor.fetchone()

    if not q:
        conn.close()
        raise ValueError(f"Question {numero_question} introuvable.")

    q = dict(q)
    reponse_correcte = q["reponse_correcte"]
    temps_accorde    = q["temps_accorde_s"]
    ert              = q["ert_secondes"]

    # Évaluation
    est_correct = (
        reponse_apprenant.strip().lower() ==
        reponse_correcte.strip().lower()
    )

    # Calcul du score avec pénalité temporelle
    if est_correct:
        score_base = SCORE_MAX_QUESTION
        # Pénalité si dépassement du temps accordé
        if temps_reponse_s > temps_accorde:
            depassement    = temps_reponse_s - temps_accorde
            penalite       = round(depassement * PENALITE_TEMPS, 2)
            penalite       = min(penalite, score_base * 0.5)  # max 50% de pénalité
            score_obtenu   = round(max(score_base - penalite, score_base * 0.5), 2)
        else:
            penalite     = 0.0
            score_obtenu = score_base
    else:
        score_obtenu = 0.0
        penalite     = 0.0

    # Feedback temporel
    if temps_reponse_s <= ert:
        feedback_temps = "⚡ Excellent ! Réponse dans le temps optimal."
    elif temps_reponse_s <= temps_accorde:
        feedback_temps = "⏱️ Réponse dans le temps accordé."
    else:
        feedback_temps = (
            f"⏰ Temps dépassé de {round(temps_reponse_s - temps_accorde, 1)}s. "
            f"Pénalité : -{penalite} points."
        )

    # Mise à jour en base
    cursor.execute('''
        UPDATE questions_examen SET
            reponse_apprenant = ?,
            est_correct       = ?,
            temps_reponse_s   = ?,
            score_obtenu      = ?,
            penalite_temps    = ?
        WHERE examen_id = ? AND numero = ?
    ''', (
        reponse_apprenant,
        int(est_correct),
        temps_reponse_s,
        score_obtenu,
        penalite,
        examen_id,
        numero_question,
    ))
    conn.commit()
    conn.close()

    return {
        "numero":            numero_question,
        "est_correct":       est_correct,
        "reponse_correcte":  reponse_correcte,
        "reponse_apprenant": reponse_apprenant,
        "score_obtenu":      score_obtenu,
        "score_max":         SCORE_MAX_QUESTION,
        "penalite_temps":    penalite,
        "temps_reponse_s":   temps_reponse_s,
        "temps_accorde_s":   temps_accorde,
        "ert_secondes":      ert,
        "feedback_temps":    feedback_temps,
    }


# ─────────────────────────────────────────────────────────────
# BULLETIN DE RÉSULTATS
# ─────────────────────────────────────────────────────────────

def get_bulletin(examen_id: int) -> dict:
    """
    Génère le bulletin de résultats complet d'un examen.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Récupérer l'examen
    cursor.execute('SELECT * FROM examens WHERE id = ?', (examen_id,))
    examen = dict(cursor.fetchone())

    # Récupérer toutes les questions
    cursor.execute('''
        SELECT * FROM questions_examen
        WHERE examen_id = ?
        ORDER BY numero
    ''', (examen_id,))
    questions = [dict(r) for r in cursor.fetchall()]

    # Calculer les statistiques
    nb_repondues = sum(1 for q in questions if q["reponse_apprenant"] is not None)
    nb_correctes = sum(1 for q in questions if q.get("est_correct") == 1)
    score_total  = sum(q.get("score_obtenu", 0) for q in questions)
    score_max    = examen["nb_questions"] * SCORE_MAX_QUESTION
    taux         = round((nb_correctes / nb_repondues * 100), 1) if nb_repondues > 0 else 0
    note_sur_20  = round((score_total / score_max) * 20, 2) if score_max > 0 else 0

    # Résultats par objectif
    par_objectif = {}
    for q in questions:
        obj = q["objectif_code"]
        if obj not in par_objectif:
            par_objectif[obj] = {"nb": 0, "bonnes": 0, "score": 0}
        par_objectif[obj]["nb"]    += 1
        par_objectif[obj]["bonnes"]+= q.get("est_correct", 0)
        par_objectif[obj]["score"] += q.get("score_obtenu", 0)

    for obj in par_objectif:
        nb    = par_objectif[obj]["nb"]
        taux_obj = round(par_objectif[obj]["bonnes"] / nb * 100, 1) if nb > 0 else 0
        par_objectif[obj]["taux"] = taux_obj
        par_objectif[obj]["maitrise"] = _niveau_maitrise(taux_obj)

    # Appréciation globale
    if note_sur_20 >= 16:
        appreciation = "🏆 Très bien — Excellente maîtrise des objectifs."
        mention      = "Très bien"
    elif note_sur_20 >= 14:
        appreciation = "👍 Bien — Bonne maîtrise générale."
        mention      = "Bien"
    elif note_sur_20 >= 12:
        appreciation = "📚 Assez bien — Quelques objectifs à renforcer."
        mention      = "Assez bien"
    elif note_sur_20 >= 10:
        appreciation = "⚠️ Passable — Des lacunes importantes à combler."
        mention      = "Passable"
    else:
        appreciation = "❌ Insuffisant — Reprenez les bases des objectifs échoués."
        mention      = "Insuffisant"

    # Recommandations
    recommandations = []
    for obj, stats in par_objectif.items():
        if stats["taux"] < 50:
            recommandations.append(
                f"• Retravailler l'objectif « {obj} » "
                f"(taux de réussite : {stats['taux']}%)"
            )

    # Clôturer l'examen
    cursor.execute('''
        UPDATE examens SET
            statut        = "termine",
            score_obtenu  = ?,
            taux_reussite = ?,
            date_fin      = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (score_total, taux, examen_id))
    conn.commit()
    conn.close()

    return {
        "examen_id":       examen_id,
        "apprenant":       examen["apprenant"],
        "titre":           examen["titre"],
        "date":            examen["date_debut"],
        "nb_questions":    examen["nb_questions"],
        "nb_repondues":    nb_repondues,
        "nb_correctes":    nb_correctes,
        "score_obtenu":    round(score_total, 2),
        "score_max":       score_max,
        "note_sur_20":     note_sur_20,
        "taux_reussite":   taux,
        "mention":         mention,
        "appreciation":    appreciation,
        "par_objectif":    par_objectif,
        "recommandations": recommandations,
        "questions":       questions,
    }


def _niveau_maitrise(taux: float) -> str:
    """Retourne le niveau de maîtrise selon le taux de réussite."""
    if taux >= 80:
        return "✅ Maîtrisé"
    elif taux >= 60:
        return "⚠️ En cours"
    else:
        return "❌ À retravailler"


# ─────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))

    print("=== Test du mode examen ===\n")

    init_tables_examen()

    # Créer un examen
    examen = creer_examen(
        objectifs    = ["NEG_IMP", "MORGAN", "CONTRAP", "NEG_QUANT"],
        mode_bloom   = "comprehension",
        niveau       = "moyen",
        nb_questions = 4,
        apprenant    = "etudiant_test",
        titre        = "Examen - Négation et Contraposée",
    )

    eid = examen["examen_id"]
    print(f"Examen créé : ID={eid}")
    print(f"Questions   : {examen['nb_questions']}")
    print(f"Durée totale: {examen['temps_total_min']} minutes\n")

    # Simuler les réponses
    for i, q in enumerate(examen["questions"], 1):
        print(f"Q{i} [{q['objectif_code']}] : {q['enonce'][:60]}...")
        print(f"  Temps accordé : {q['temps_accorde_s']}s")

        # Simuler : bonnes réponses pour Q1 et Q3, mauvaises pour Q2 et Q4
        if i in [1, 3]:
            rep      = q["reponse_correcte"]
            temps_rep = q["ert_secondes"] * 0.8   # dans les temps
        else:
            rep      = q["distracteurs"][0]
            temps_rep = q["temps_accorde_s"] * 1.3  # dépassement

        result = soumettre_reponse(eid, i, rep, round(temps_rep, 1))
        symbole = "✅" if result["est_correct"] else "❌"
        print(f"  {symbole} Score : {result['score_obtenu']}/{result['score_max']}")
        print(f"  {result['feedback_temps']}\n")

    # Bulletin final
    bulletin = get_bulletin(eid)
    print("─" * 50)
    print("BULLETIN DE RÉSULTATS")
    print(f"  Apprenant  : {bulletin['apprenant']}")
    print(f"  Note       : {bulletin['note_sur_20']}/20")
    print(f"  Mention    : {bulletin['mention']}")
    print(f"  Taux       : {bulletin['taux_reussite']}%")
    print(f"\n  {bulletin['appreciation']}")
    print(f"\n  Résultats par objectif :")
    for obj, stats in bulletin["par_objectif"].items():
        print(f"    {obj} : {stats['taux']}% — {stats['maitrise']}")
    if bulletin["recommandations"]:
        print(f"\n  Recommandations :")
        for r in bulletin["recommandations"]:
            print(f"    {r}")
