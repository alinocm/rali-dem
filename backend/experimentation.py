# -------------------------------------------------------------
# experimentation.py -- Collecte des donnees experimentales RALI-DEM
#
# Protocole v2 (collecte 2027) :
#   - 30 questions par etudiant : les 15 objectifs x 2 modes Bloom.
#   - 24 questions viennent d'une BANQUE FIXE d'items valides par des
#     enseignants (les memes pour tous), 6 sont GENEREES a la volee ;
#     les combinaisons generees tournent d'un etudiant a l'autre pour
#     que chaque combinaison soit generee aussi souvent que les autres.
#   - Le serveur fixe le plan, l'ordre des questions et l'ordre des
#     options, garde la question servie, corrige la reponse et
#     calcule les deux temps estimes (ERT-A, ERT-B) : rien de tout cela
#     ne transite par le navigateur ni ne lui est montre.
#   - Une reponse ou une evaluation n'est enregistree qu'une fois,
#     meme si le navigateur la renvoie (coupure, double clic).
#   - Une session interrompue reprend a la question suivante.
#   - Les exports ne contiennent jamais nom, prenom ni e-mail.
#
# Les tables du protocole v1 (collecte 2026) sont conservees telles
# quelles ; les colonnes ajoutees restent vides pour ces lignes.
# -------------------------------------------------------------

import os
import csv
import io
import json
import random
import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Optional, Dict, List

PROTOCOLE_VERSION    = "v2"
CONSENTEMENT_VERSION = "2026-11-26"
NB_GENERES           = 6        # questions generees par session (3 par mode)
FEEDBACK_IMMEDIAT    = False    # pas de correction pendant la session (decision du 26/11/2026)

OBJECTIFS = [
    "PROP", "VVER", "TVER", "NEG_SIMPLE", "CONN_ID",
    "CONN_TRAD", "CONN_INV", "IMP", "EQUIV", "MORGAN",
    "NEG_COMP", "NEG_IMP", "QUANT_TRAD", "NEG_QUANT", "CONTRAP",
]
MODES = ["comprehension", "analyse"]
LETTRES = "ABCD"


# =============================================================
# CONNEXION
# =============================================================

def _get_db_path() -> str:
    env = os.environ.get('RALI_DB_PATH')
    if env:
        return env
    base = os.path.dirname(os.path.abspath(__file__))
    for rel in [
        os.path.join(base, '..', 'database', 'rali_dem.db'),
        os.path.join(base, 'database', 'rali_dem.db'),
        os.path.join(base, '..', 'rali_dem.db'),
    ]:
        if os.path.exists(rel):
            return rel
    return os.path.join(base, '..', 'database', 'rali_dem.db')


def _connexion() -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path(), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _colonnes(cur, table: str) -> set:
    return {r[1] for r in cur.execute(f"PRAGMA table_info({table})")}


def _ajouter_colonnes(cur, table: str, colonnes: Dict[str, str]):
    existantes = _colonnes(cur, table)
    for nom, type_sql in colonnes.items():
        if nom not in existantes:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {nom} {type_sql}")


# =============================================================
# INITIALISATION ET MIGRATION DES TABLES
# =============================================================

def init_tables_experimentation():
    """Cree les tables et ajoute les colonnes du protocole v2.
    Idempotent : peut etre appele a chaque demarrage."""
    conn = _connexion()
    cur  = conn.cursor()

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
    _ajouter_colonnes(cur, "exp_participants", {
        "consentement_version": "TEXT",
        "consentement_date":    "TEXT",
    })

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
    _ajouter_colonnes(cur, "exp_sessions", {
        "jeton":             "TEXT",
        "protocole_version": "TEXT",
        "numero_rotation":   "INTEGER",
        "user_agent":        "TEXT",
    })
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_exp_sessions_jeton "
                "ON exp_sessions(jeton) WHERE jeton IS NOT NULL")

    # Banque d'items et items generes servis pendant les sessions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exp_items (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            code_item           TEXT    NOT NULL UNIQUE,
            source              TEXT    NOT NULL,   -- 'banque' | 'genere'
            statut              TEXT    NOT NULL,   -- candidat | valide | rejete | genere
            objectif_code       TEXT    NOT NULL,
            mode_bloom          TEXT    NOT NULL,
            niveau_complexite   TEXT,
            enonce              TEXT    NOT NULL,
            reponse_correcte    TEXT    NOT NULL,
            distracteurs_json   TEXT    NOT NULL,
            nb_choix            INTEGER NOT NULL,
            nb_propositions     INTEGER,
            nb_connecteurs      INTEGER,
            nb_quantificateurs  INTEGER,
            nb_negations        INTEGER,
            profondeur          INTEGER,
            structure_syntaxique TEXT,
            ert_a_s             REAL,
            ert_a_publie_s      REAL,
            ert_a_detail_json   TEXT,
            ert_b_s             REAL,
            ert_b_structurel_s  REAL,
            ert_b_detail_json   TEXT,
            prop_a_json         TEXT,
            params_version      TEXT,
            hash                TEXT,
            commentaire_validation TEXT,
            date_creation       TEXT    NOT NULL,
            date_validation     TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_exp_items_combi "
                "ON exp_items(objectif_code, mode_bloom, statut)")

    # Plan de chaque session : une ligne par rang
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exp_session_items (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id          INTEGER NOT NULL,
            rang                INTEGER NOT NULL,
            objectif_code       TEXT    NOT NULL,
            mode_bloom          TEXT    NOT NULL,
            source              TEXT    NOT NULL,
            item_id             INTEGER,
            ordre_options_json  TEXT,
            date_premier_affichage TEXT,
            nb_affichages       INTEGER NOT NULL DEFAULT 0,
            UNIQUE (session_id, rang),
            FOREIGN KEY (session_id)
                REFERENCES exp_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES exp_items(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS exp_reponses (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id          INTEGER NOT NULL,
            participant_id      INTEGER NOT NULL,
            numero_question     INTEGER NOT NULL,
            objectif_code       TEXT    NOT NULL,
            mode_bloom          TEXT    NOT NULL,
            niveau_complexite   TEXT    NOT NULL,
            enonce              TEXT    NOT NULL,
            choix_a             TEXT    NOT NULL,
            choix_b             TEXT    NOT NULL,
            choix_c             TEXT    NOT NULL,
            choix_d             TEXT    NOT NULL,
            reponse_correcte    TEXT    NOT NULL,
            ert_predit_s        REAL    NOT NULL,
            score_predit        REAL    NOT NULL,
            nb_propositions     INTEGER NOT NULL DEFAULT 2,
            nb_connecteurs      INTEGER NOT NULL DEFAULT 0,
            nb_quantificateurs  INTEGER NOT NULL DEFAULT 0,
            nb_negations        INTEGER NOT NULL DEFAULT 0,
            profondeur          INTEGER NOT NULL DEFAULT 1,
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
    _ajouter_colonnes(cur, "exp_reponses", {
        "protocole_version":   "TEXT",
        "item_id":             "INTEGER",
        "source":              "TEXT",
        "position_correcte":   "INTEGER",
        "position_choisie":    "INTEGER",
        "nb_choix":            "INTEGER",
        "ert_a_s":             "REAL",
        "ert_a_publie_s":      "REAL",
        "ert_b_s":             "REAL",
        "ert_b_structurel_s":  "REAL",
        "temps_client_ms":     "REAL",
        "temps_cache_ms":      "REAL",
        "nb_changements":      "INTEGER",
        "date_reception":      "TEXT",
    })
    # Une seule reponse par (session, rang) pour le protocole v2
    # (les doublons de la collecte v1 restent dans la base, intacts).
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_exp_rep_v2 "
                "ON exp_reponses(session_id, numero_question) "
                "WHERE protocole_version IS NOT NULL")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS exp_eval_qualitative (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id          INTEGER NOT NULL,
            participant_id      INTEGER NOT NULL,
            grammaticalite      INTEGER NOT NULL CHECK(grammaticalite BETWEEN 1 AND 5),
            naturalite          INTEGER NOT NULL CHECK(naturalite BETWEEN 1 AND 5),
            clarte              INTEGER NOT NULL CHECK(clarte BETWEEN 1 AND 5),
            plausibilite_dist   INTEGER NOT NULL CHECK(plausibilite_dist BETWEEN 1 AND 5),
            pertinence_obj      INTEGER NOT NULL CHECK(pertinence_obj BETWEEN 1 AND 5),
            alignement_bloom    INTEGER NOT NULL CHECK(alignement_bloom BETWEEN 1 AND 5),
            acceptabilite       INTEGER NOT NULL CHECK(acceptabilite BETWEEN 1 AND 5),
            utilite_apprentissage INTEGER NOT NULL CHECK(utilite_apprentissage BETWEEN 1 AND 5),
            commentaire         TEXT,
            score_coherence     REAL,
            score_plausibilite  REAL,
            score_acceptabilite REAL,
            score_global        REAL,
            date_eval           TEXT    NOT NULL,
            FOREIGN KEY (session_id)
                REFERENCES exp_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (participant_id)
                REFERENCES exp_participants(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_exp_eval_session "
                "ON exp_eval_qualitative(session_id)")
    _ajouter_colonnes(cur, "exp_eval_qualitative", {
        "protocole_version": "TEXT",
    })
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_exp_eval_v2 "
                "ON exp_eval_qualitative(session_id) "
                "WHERE protocole_version IS NOT NULL")

    conn.commit()
    conn.close()
    print("[EXPERIMENTATION] Tables initialisees (protocole v2).")


# =============================================================
# PARTICIPANTS
# =============================================================

def _participant_public(row) -> Dict:
    return {"participant_id": row["id"], "code_anonyme": row["code_anonyme"]}


def inscrire_participant(
    nom: str, prenom: str, email: str,
    niveau_etudes: str, etablissement: str,
    consentement: bool, utilisateur_id: Optional[int] = None,
    consentement_version: Optional[str] = None,
) -> Dict:
    """
    Inscrit un participant, ou retrouve celui qui a deja utilise cet
    e-mail (reprise apres une coupure). Le consentement doit etre
    donne ; sa version et sa date sont enregistrees.
    """
    if not consentement:
        return {"success": False, "error": "Consentement requis"}
    email_n = (email or "").strip().lower()
    if not email_n:
        return {"success": False, "error": "E-mail requis"}

    conn = _connexion()
    cur  = conn.cursor()
    try:
        row = cur.execute(
            "SELECT * FROM exp_participants WHERE lower(email) = ? "
            "ORDER BY id LIMIT 1", (email_n,)
        ).fetchone()
        if row:
            out = _participant_public(row)
            out.update({"success": True, "deja_inscrit": True})
            return out

        code = "P" + secrets.token_hex(4).upper()
        while cur.execute("SELECT 1 FROM exp_participants WHERE code_anonyme=?",
                          (code,)).fetchone():
            code = "P" + secrets.token_hex(4).upper()
        cur.execute("""
            INSERT INTO exp_participants
            (code_anonyme, nom, prenom, email, niveau_etudes,
             etablissement, consentement, date_inscription, utilisateur_id,
             consentement_version, consentement_date)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (code, (nom or "").strip(), (prenom or "").strip(), email_n,
              niveau_etudes, (etablissement or "").strip(), 1, _now(),
              utilisateur_id, consentement_version or CONSENTEMENT_VERSION,
              _now()))
        conn.commit()
        return {"success": True, "deja_inscrit": False,
                "participant_id": cur.lastrowid, "code_anonyme": code}
    finally:
        conn.close()


def get_participant_by_email(email: str) -> Optional[Dict]:
    conn = _connexion()
    row = conn.execute(
        "SELECT * FROM exp_participants WHERE lower(email) = ?",
        ((email or "").strip().lower(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# =============================================================
# BANQUE D'ITEMS
# =============================================================

def _enregistrer_item(cur, q: Dict, source: str, statut: str) -> int:
    prefixe = "B" if source == "banque" else "G"
    code = f"{prefixe}-{q['objectif_code']}-{q['mode_bloom'][:4].upper()}-" \
           f"{secrets.token_hex(3).upper()}"
    cur.execute("""
        INSERT INTO exp_items (
            code_item, source, statut, objectif_code, mode_bloom,
            niveau_complexite, enonce, reponse_correcte, distracteurs_json,
            nb_choix, nb_propositions, nb_connecteurs, nb_quantificateurs,
            nb_negations, profondeur, structure_syntaxique,
            ert_a_s, ert_a_publie_s, ert_a_detail_json,
            ert_b_s, ert_b_structurel_s, ert_b_detail_json,
            prop_a_json, params_version, hash, date_creation
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        code, source, statut, q["objectif_code"], q["mode_bloom"],
        q.get("niveau_complexite"), q["enonce"], q["reponse_correcte"],
        json.dumps(q["distracteurs"], ensure_ascii=False),
        q.get("nb_choix", 1 + len(q["distracteurs"])),
        q.get("nb_propositions"), q.get("nb_connecteurs"),
        q.get("nb_quantificateurs"), q.get("nb_negations"),
        q.get("profondeur_logique"), q.get("structure_syntaxique"),
        q.get("ert_a_s"), q.get("ert_a_publie_s"),
        json.dumps(q.get("ert_a_detail"), ensure_ascii=False),
        q.get("ert_b_s"), q.get("ert_b_structurel_s"),
        json.dumps(q.get("ert_b_detail"), ensure_ascii=False),
        json.dumps(q.get("prop_a"), ensure_ascii=False),
        q.get("params_version"), q.get("hash"), _now(),
    ))
    return cur.lastrowid


def generer_banque_candidats(nb_par_combinaison: int = 3,
                             seulement_manquantes: bool = False) -> Dict:
    """Genere des items candidats pour chaque (objectif, mode), a faire
    relire par les enseignants avant la collecte. Avec
    seulement_manquantes, ne genere que pour les combinaisons qui n'ont
    pas encore d'item valide (apres un tour de relecture)."""
    from generator import generer_question, EtatGeneration
    nb_par_combinaison = max(1, min(int(nb_par_combinaison), 10))
    conn = _connexion()
    cur  = conn.cursor()
    deja = _banque_validee(cur) if seulement_manquantes else {}
    crees = 0
    for obj in OBJECTIFS:
        for mode in MODES:
            if (obj, mode) in deja:
                continue
            etat = EtatGeneration()
            for _ in range(nb_par_combinaison):
                q = generer_question(obj, mode, etat=etat)
                if q:
                    _enregistrer_item(cur, q, "banque", "candidat")
                    crees += 1
    conn.commit()
    conn.close()
    return {"success": True, "items_crees": crees}


COLONNES_RELECTURE = ["code_item", "objectif_code", "mode_bloom", "enonce",
                      "bonne_reponse", "distracteur_1", "distracteur_2",
                      "distracteur_3", "statut", "commentaire"]


def exporter_banque_csv() -> str:
    """Fiche de relecture pour les enseignants : un item par ligne.
    Separateur ';' pour qu'Excel en francais ouvre directement les
    colonnes. A renvoyer avec la colonne statut remplie (valide ou
    rejete) et, si besoin, un commentaire."""
    conn = _connexion()
    rows = conn.execute("""
        SELECT code_item, statut, objectif_code, mode_bloom,
               enonce, reponse_correcte, distracteurs_json,
               commentaire_validation
        FROM exp_items WHERE source = 'banque'
        ORDER BY objectif_code, mode_bloom, id
    """).fetchall()
    conn.close()
    out = io.StringIO()
    w = csv.writer(out, delimiter=";")
    w.writerow(COLONNES_RELECTURE)
    for r in rows:
        d = json.loads(r["distracteurs_json"]) + ["", "", ""]
        w.writerow([r["code_item"], r["objectif_code"], r["mode_bloom"],
                    r["enonce"], r["reponse_correcte"], d[0], d[1], d[2],
                    r["statut"], r["commentaire_validation"] or ""])
    return out.getvalue()


_STATUTS = {
    "valide": "valide", "validé": "valide", "v": "valide", "oui": "valide",
    "ok": "valide",
    "rejete": "rejete", "rejeté": "rejete", "r": "rejete", "non": "rejete",
    "candidat": "candidat", "": "candidat",
}


def _normaliser_statut(valeur) -> Optional[str]:
    return _STATUTS.get((valeur or "").strip().lower())


def lire_fiche_relecture(contenu: bytes) -> List[Dict]:
    """Lit la fiche renvoyee par les enseignants. Accepte l'UTF-8 (avec
    ou sans BOM) et l'encodage Windows d'Excel, et le separateur ';',
    ',' ou tabulation."""
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texte = contenu.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    premiere = texte.splitlines()[0] if texte.strip() else ""
    sep = max((";", ",", "\t"), key=premiere.count)
    lecteur = csv.DictReader(io.StringIO(texte), delimiter=sep)
    if not lecteur.fieldnames or "code_item" not in [
            (c or "").strip() for c in lecteur.fieldnames]:
        raise ValueError("La fiche doit contenir la colonne code_item "
                         "(utilisez la fiche telechargee depuis l'application).")
    lignes = []
    for ligne in lecteur:
        ligne = {(k or "").strip(): (v or "") for k, v in ligne.items()}
        if ligne.get("code_item", "").strip():
            lignes.append(ligne)
    return lignes


def _items_servis(cur) -> set:
    return {r[0] for r in cur.execute(
        "SELECT DISTINCT item_id FROM exp_session_items WHERE item_id IS NOT NULL")}


def importer_validation_banque(lignes: List[Dict]) -> Dict:
    """Applique les decisions des relecteurs (code_item, statut,
    commentaire). Une fois qu'un item de la banque a ete servi a un
    etudiant, sa combinaison objectif x mode est verrouillee : on ne
    peut plus changer l'item retenu, pour que tous les etudiants
    recoivent le meme."""
    conn = _connexion()
    cur  = conn.cursor()
    servis = _items_servis(cur)
    retenus = _banque_validee(cur)
    combis_verrouillees = {c for c, item in retenus.items() if item in servis}
    maj, inchanges, inconnus, statut_invalide, verrouilles = 0, 0, [], [], []
    for l in lignes:
        code = (l.get("code_item") or "").strip()
        statut = _normaliser_statut(l.get("statut"))
        if statut is None:
            statut_invalide.append(code)
            continue
        item = cur.execute("""SELECT id, statut, objectif_code, mode_bloom,
                                     commentaire_validation
                              FROM exp_items WHERE code_item=? AND source='banque'""",
                           (code,)).fetchone()
        if not item:
            inconnus.append(code)
            continue
        commentaire = (l.get("commentaire") or "").strip()
        if item["statut"] == statut and (item["commentaire_validation"] or "") == commentaire:
            inchanges += 1
            continue
        if statut != item["statut"] and (
                item["id"] in servis
                or (item["objectif_code"], item["mode_bloom"]) in combis_verrouillees):
            verrouilles.append(code)
            continue
        cur.execute("""
            UPDATE exp_items SET statut=?, commentaire_validation=?,
                   date_validation=?
            WHERE id=?
        """, (statut, commentaire, _now(), item["id"]))
        maj += 1
    conn.commit()
    conn.close()
    return {"success": True, "mis_a_jour": maj, "inchanges": inchanges,
            "codes_inconnus": inconnus, "statuts_invalides": statut_invalide,
            "verrouilles": verrouilles, "etat": etat_banque()}


def _banque_validee(cur) -> Dict:
    """(objectif, mode) -> id de l'item valide retenu (le plus ancien)."""
    rows = cur.execute("""
        SELECT objectif_code, mode_bloom, MIN(id) AS item_id
        FROM exp_items WHERE source='banque' AND statut='valide'
        GROUP BY objectif_code, mode_bloom
    """).fetchall()
    return {(r["objectif_code"], r["mode_bloom"]): r["item_id"] for r in rows}


def etat_banque() -> Dict:
    conn = _connexion()
    cur  = conn.cursor()
    valides = _banque_validee(cur)
    servis = _items_servis(cur)
    compte = cur.execute("""
        SELECT statut, COUNT(*) n FROM exp_items WHERE source='banque'
        GROUP BY statut
    """).fetchall()
    detail = {(r["objectif_code"], r["mode_bloom"], r["statut"]): r["n"]
              for r in cur.execute("""
        SELECT objectif_code, mode_bloom, statut, COUNT(*) n
        FROM exp_items WHERE source='banque'
        GROUP BY objectif_code, mode_bloom, statut""")}
    codes = {r["id"]: r["code_item"] for r in cur.execute(
        "SELECT id, code_item FROM exp_items WHERE source='banque'")}
    conn.close()
    combinaisons = []
    for o in OBJECTIFS:
        for m in MODES:
            item = valides.get((o, m))
            combinaisons.append({
                "objectif_code": o, "mode_bloom": m,
                "candidats": detail.get((o, m, "candidat"), 0),
                "valides": detail.get((o, m, "valide"), 0),
                "rejetes": detail.get((o, m, "rejete"), 0),
                "item_retenu": codes.get(item) if item else None,
                "verrouille": bool(item and item in servis),
            })
    manquantes = [f"{c['objectif_code']}/{c['mode_bloom']}"
                  for c in combinaisons if not c["item_retenu"]]
    return {"par_statut": {r["statut"]: r["n"] for r in compte},
            "combinaisons_validees": len(valides),
            "nb_combinaisons": len(OBJECTIFS) * len(MODES),
            "combinaisons_manquantes": manquantes,
            "combinaisons": combinaisons}


# =============================================================
# PLAN DE SESSION
# =============================================================

def _combinaisons_generees(rotation: int) -> set:
    """3 combinaisons generees par mode, decalees d'une session a
    l'autre : sur 5 sessions, chaque objectif est genere une fois
    dans chaque mode. Les deux modes ne generent jamais le meme
    objectif dans une meme session."""
    n = len(OBJECTIFS)
    k = NB_GENERES // 2
    comp = [OBJECTIFS[(k * rotation + j) % n] for j in range(k)]
    anal = [OBJECTIFS[(k * rotation + 7 + j) % n] for j in range(k)]
    return {(o, "comprehension") for o in comp} | {(o, "analyse") for o in anal}


def _ordre_sans_voisins(combis: List[tuple]) -> List[tuple]:
    """Ordre aleatoire ou les deux questions d'un meme objectif ne se
    suivent jamais."""
    for _ in range(500):
        ordre = combis[:]
        random.shuffle(ordre)
        if all(ordre[i][0] != ordre[i + 1][0] for i in range(len(ordre) - 1)):
            return ordre
    return ordre


def creer_session_exp(participant_id: int, user_agent: str = "") -> Dict:
    """Cree la session et son plan, ou renvoie la session en cours du
    participant (reprise)."""
    conn = _connexion()
    cur  = conn.cursor()
    try:
        if not cur.execute("SELECT 1 FROM exp_participants WHERE id=?",
                           (participant_id,)).fetchone():
            return {"success": False, "error": "Participant inconnu"}

        en_cours = cur.execute("""
            SELECT * FROM exp_sessions
            WHERE participant_id=? AND protocole_version=? AND statut='en_cours'
            ORDER BY id DESC LIMIT 1
        """, (participant_id, PROTOCOLE_VERSION)).fetchone()
        if en_cours:
            return {"success": True, "reprise": True,
                    "jeton": en_cours["jeton"],
                    "nb_questions": en_cours["nb_questions_cible"],
                    "nb_repondues": _nb_repondues(cur, en_cours["id"])}

        deja = cur.execute("""
            SELECT 1 FROM exp_sessions
            WHERE participant_id=? AND protocole_version=? AND statut='terminee'
        """, (participant_id, PROTOCOLE_VERSION)).fetchone()
        if deja:
            return {"success": False, "deja_terminee": True,
                    "error": "Vous avez deja termine la session."}

        rotation = cur.execute(
            "SELECT COUNT(*) FROM exp_sessions WHERE protocole_version=?",
            (PROTOCOLE_VERSION,)).fetchone()[0]
        banque = _banque_validee(cur)
        generees = _combinaisons_generees(rotation)

        combis = [(o, m) for o in OBJECTIFS for m in MODES]
        plan = []
        for rang, (o, m) in enumerate(_ordre_sans_voisins(combis), start=1):
            source = "banque" if ((o, m) in banque and (o, m) not in generees) \
                     else "genere"
            plan.append((rang, o, m, source, banque.get((o, m)) if source == "banque" else None))

        jeton = secrets.token_urlsafe(24)
        code  = "S" + secrets.token_hex(4).upper()
        cur.execute("""
            INSERT INTO exp_sessions
            (participant_id, code_session, protocole, nb_questions_cible,
             date_debut, statut, jeton, protocole_version, numero_rotation,
             user_agent)
            VALUES (?,?,?,?,?,'en_cours',?,?,?,?)
        """, (participant_id, code, "v2", len(plan), _now(), jeton,
              PROTOCOLE_VERSION, rotation, (user_agent or "")[:300]))
        sid = cur.lastrowid
        cur.executemany("""
            INSERT INTO exp_session_items
            (session_id, rang, objectif_code, mode_bloom, source, item_id)
            VALUES (?,?,?,?,?,?)
        """, [(sid, r, o, m, s, i) for (r, o, m, s, i) in plan])
        conn.commit()
        return {"success": True, "reprise": False, "jeton": jeton,
                "nb_questions": len(plan), "nb_repondues": 0}
    finally:
        conn.close()


def _session_par_jeton(cur, jeton: str):
    return cur.execute(
        "SELECT * FROM exp_sessions WHERE jeton=? AND protocole_version=?",
        (jeton, PROTOCOLE_VERSION)).fetchone()


def _nb_repondues(cur, session_id: int) -> int:
    return cur.execute(
        "SELECT COUNT(*) FROM exp_reponses WHERE session_id=? "
        "AND protocole_version IS NOT NULL", (session_id,)).fetchone()[0]


def _options_affichees(item) -> List[str]:
    return [item["reponse_correcte"]] + json.loads(item["distracteurs_json"])


# =============================================================
# DEROULEMENT
# =============================================================

def question_suivante(jeton: str) -> Dict:
    """Renvoie la prochaine question sans reponse. Une question deja
    affichee (rechargement, reprise) revient a l'identique : meme
    item, meme ordre des options. Ni la bonne reponse ni les temps
    estimes ne sont envoyes au navigateur."""
    conn = _connexion()
    cur  = conn.cursor()
    try:
        s = _session_par_jeton(cur, jeton)
        if not s:
            return {"success": False, "error": "Session inconnue"}
        if s["statut"] == "terminee":
            return {"success": True, "terminee": True}

        si = cur.execute("""
            SELECT si.* FROM exp_session_items si
            WHERE si.session_id=? AND NOT EXISTS (
                SELECT 1 FROM exp_reponses r
                WHERE r.session_id=si.session_id AND r.numero_question=si.rang
                  AND r.protocole_version IS NOT NULL)
            ORDER BY si.rang LIMIT 1
        """, (s["id"],)).fetchone()
        total = s["nb_questions_cible"]
        if not si:
            return {"success": True, "fin_questions": True,
                    "nb_questions": total, "nb_repondues": total}

        item_id = si["item_id"]
        if si["source"] == "genere" and item_id is None:
            item_id = _generer_pour_session(cur, s["id"], si["objectif_code"],
                                            si["mode_bloom"])
        item = cur.execute("SELECT * FROM exp_items WHERE id=?",
                           (item_id,)).fetchone()
        if si["ordre_options_json"]:
            ordre = json.loads(si["ordre_options_json"])
        else:
            ordre = _options_affichees(item)
            random.shuffle(ordre)
        cur.execute("""
            UPDATE exp_session_items
            SET item_id=?, ordre_options_json=?,
                date_premier_affichage=COALESCE(date_premier_affichage, ?),
                nb_affichages=nb_affichages+1
            WHERE id=?
        """, (item_id, json.dumps(ordre, ensure_ascii=False), _now(), si["id"]))
        conn.commit()
        return {
            "success": True,
            "rang": si["rang"],
            "nb_questions": total,
            "nb_repondues": _nb_repondues(cur, s["id"]),
            "enonce": item["enonce"],
            "options": [{"index": i, "lettre": LETTRES[i], "texte": t}
                        for i, t in enumerate(ordre)],
        }
    finally:
        conn.close()


def _generer_pour_session(cur, session_id: int, objectif: str, mode: str) -> int:
    from generator import generer_question, EtatGeneration
    etat = EtatGeneration()
    etat.historique_hash = {r["hash"] for r in cur.execute("""
        SELECT i.hash FROM exp_session_items si JOIN exp_items i
        ON i.id = si.item_id WHERE si.session_id=? AND i.hash IS NOT NULL
    """, (session_id,))}
    q = generer_question(objectif, mode, etat=etat)
    if q is None:
        raise RuntimeError(f"Generation impossible : {objectif}/{mode}")
    return _enregistrer_item(cur, q, "genere", "genere")


def enregistrer_reponse_exp(
    jeton: str, rang: int, index_choisi: int,
    temps_client_ms: Optional[float] = None,
    temps_cache_ms: Optional[float] = None,
    nb_changements: Optional[int] = None,
    timestamp_debut: Optional[str] = None,
    timestamp_fin: Optional[str] = None,
) -> Dict:
    """Corrige et enregistre une reponse. Idempotent : une reponse deja
    enregistree pour ce rang n'est pas reecrite et le meme resultat
    est renvoye."""
    conn = _connexion()
    cur  = conn.cursor()
    try:
        s = _session_par_jeton(cur, jeton)
        if not s:
            return {"success": False, "error": "Session inconnue"}

        existante = cur.execute("""
            SELECT est_correct, reponse_correcte FROM exp_reponses
            WHERE session_id=? AND numero_question=? AND protocole_version IS NOT NULL
        """, (s["id"], rang)).fetchone()
        if existante:
            return _resultat(existante["est_correct"],
                             existante["reponse_correcte"], deja=True)

        si = cur.execute("""
            SELECT * FROM exp_session_items WHERE session_id=? AND rang=?
        """, (s["id"], rang)).fetchone()
        if not si or si["item_id"] is None or not si["ordre_options_json"]:
            return {"success": False, "error": "Question non affichee"}
        item  = cur.execute("SELECT * FROM exp_items WHERE id=?",
                            (si["item_id"],)).fetchone()
        ordre = json.loads(si["ordre_options_json"])
        if not (0 <= int(index_choisi) < len(ordre)):
            return {"success": False, "error": "Choix invalide"}

        choisi   = ordre[int(index_choisi)]
        correct  = int(choisi == item["reponse_correcte"])
        pos_ok   = ordre.index(item["reponse_correcte"])
        temps_s  = _temps_secondes(temps_client_ms, timestamp_debut, timestamp_fin)
        cols     = (ordre + ["", "", "", ""])[:4]

        cur.execute("""
            INSERT INTO exp_reponses (
                session_id, participant_id, numero_question,
                objectif_code, mode_bloom, niveau_complexite,
                enonce, choix_a, choix_b, choix_c, choix_d,
                reponse_correcte, ert_predit_s, score_predit,
                nb_propositions, nb_connecteurs, nb_quantificateurs,
                nb_negations, profondeur,
                distracteur_choisi, est_correct, temps_reel_s,
                timestamp_debut, timestamp_fin,
                protocole_version, item_id, source,
                position_correcte, position_choisie, nb_choix,
                ert_a_s, ert_a_publie_s, ert_b_s, ert_b_structurel_s,
                temps_client_ms, temps_cache_ms, nb_changements,
                date_reception
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                      ?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            s["id"], s["participant_id"], rang,
            item["objectif_code"], item["mode_bloom"],
            item["niveau_complexite"] or "",
            item["enonce"], cols[0], cols[1], cols[2], cols[3],
            item["reponse_correcte"], item["ert_b_s"],
            round(min(10, max(1, (item["ert_b_s"] or 0) / 10)), 1),
            item["nb_propositions"], item["nb_connecteurs"],
            item["nb_quantificateurs"], item["nb_negations"],
            item["profondeur"],
            choisi, correct, temps_s,
            timestamp_debut or "", timestamp_fin or "",
            PROTOCOLE_VERSION, item["id"], si["source"],
            pos_ok, int(index_choisi), len(ordre),
            item["ert_a_s"], item["ert_a_publie_s"],
            item["ert_b_s"], item["ert_b_structurel_s"],
            temps_client_ms, temps_cache_ms, nb_changements, _now(),
        ))
        cur.execute("""
            UPDATE exp_sessions SET nb_questions_faites=(
                SELECT COUNT(*) FROM exp_reponses
                WHERE session_id=? AND protocole_version IS NOT NULL)
            WHERE id=?
        """, (s["id"], s["id"]))
        conn.commit()
        return _resultat(correct, item["reponse_correcte"], deja=False)
    except sqlite3.IntegrityError:
        # Envoi simultane : la premiere reponse a ete gardee
        conn.rollback()
        r = cur.execute("""
            SELECT est_correct, reponse_correcte FROM exp_reponses
            WHERE session_id=(SELECT id FROM exp_sessions WHERE jeton=?)
              AND numero_question=? AND protocole_version IS NOT NULL
        """, (jeton, rang)).fetchone()
        return _resultat(r["est_correct"], r["reponse_correcte"], deja=True)
    finally:
        conn.close()


def _resultat(correct: int, reponse_correcte: str, deja: bool) -> Dict:
    out = {"success": True, "deja_enregistree": deja}
    if FEEDBACK_IMMEDIAT:
        out["est_correct"] = int(correct)
        out["reponse_correcte"] = reponse_correcte
    return out


def _temps_secondes(temps_ms, debut, fin) -> float:
    """Temps de reponse : duree mesuree par l'horloge monotone du
    navigateur (performance.now) ; a defaut, difference des horodatages."""
    if temps_ms is not None and temps_ms >= 0:
        return round(float(temps_ms) / 1000.0, 3)
    try:
        d = datetime.fromisoformat(str(debut).replace("Z", "+00:00"))
        f = datetime.fromisoformat(str(fin).replace("Z", "+00:00"))
        return round((f - d).total_seconds(), 3)
    except Exception:
        return -1.0      # valeur impossible, reperable a l'analyse


def terminer_session_exp(jeton: str) -> Dict:
    conn = _connexion()
    cur  = conn.cursor()
    try:
        s = _session_par_jeton(cur, jeton)
        if not s:
            return {"success": False, "error": "Session inconnue"}
        st = cur.execute("""
            SELECT COUNT(*) total, SUM(est_correct) ok, AVG(temps_reel_s) tm
            FROM exp_reponses WHERE session_id=? AND protocole_version IS NOT NULL
        """, (s["id"],)).fetchone()
        total, ok = st["total"] or 0, st["ok"] or 0
        score = round(ok / total * 100, 1) if total else 0.0
        if s["statut"] != "terminee":
            duree = None
            try:
                d = datetime.fromisoformat(s["date_debut"])
                if d.tzinfo is None:
                    d = d.replace(tzinfo=timezone.utc)
                duree = round((datetime.now(timezone.utc) - d).total_seconds())
            except Exception:
                pass
            cur.execute("""
                UPDATE exp_sessions SET statut='terminee', date_fin=?,
                    duree_totale_s=?, score_global=?, nb_questions_faites=?
                WHERE id=?
            """, (_now(), duree, score, total, s["id"]))
            conn.commit()
        code = cur.execute("SELECT code_anonyme FROM exp_participants WHERE id=?",
                           (s["participant_id"],)).fetchone()[0]
        return {"success": True, "score_global": score, "nb_correctes": ok,
                "nb_total": total, "temps_moyen_s": st["tm"],
                "code_anonyme": code}
    finally:
        conn.close()


# =============================================================
# EVALUATION QUALITATIVE
# =============================================================

def enregistrer_eval_qualitative(
    jeton: str,
    grammaticalite: int, naturalite: int, clarte: int,
    plausibilite_dist: int, pertinence_obj: int, alignement_bloom: int,
    acceptabilite: int, utilite_apprentissage: int,
    commentaire: str = "",
) -> Dict:
    """Une evaluation par session : un second envoi est ignore."""
    notes = [grammaticalite, naturalite, clarte, plausibilite_dist,
             pertinence_obj, alignement_bloom, acceptabilite,
             utilite_apprentissage]
    if not all(isinstance(n, int) and 1 <= n <= 5 for n in notes):
        return {"success": False, "error": "Notes hors de l'echelle 1-5"}
    conn = _connexion()
    cur  = conn.cursor()
    try:
        s = _session_par_jeton(cur, jeton)
        if not s:
            return {"success": False, "error": "Session inconnue"}
        if cur.execute("""SELECT 1 FROM exp_eval_qualitative
                          WHERE session_id=? AND protocole_version IS NOT NULL""",
                       (s["id"],)).fetchone():
            return {"success": True, "deja_enregistree": True}
        score_coh  = round((grammaticalite + naturalite + clarte) / 3, 2)
        score_plau = round((plausibilite_dist + pertinence_obj + alignement_bloom) / 3, 2)
        score_acc  = round((acceptabilite + utilite_apprentissage) / 2, 2)
        score_glob = round(sum(notes) / 8, 2)
        cur.execute("""
            INSERT INTO exp_eval_qualitative (
                session_id, participant_id,
                grammaticalite, naturalite, clarte,
                plausibilite_dist, pertinence_obj, alignement_bloom,
                acceptabilite, utilite_apprentissage, commentaire,
                score_coherence, score_plausibilite,
                score_acceptabilite, score_global, date_eval,
                protocole_version
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (s["id"], s["participant_id"], *notes,
              (commentaire or "")[:2000], score_coh, score_plau, score_acc,
              score_glob, _now(), PROTOCOLE_VERSION))
        conn.commit()
        return {"success": True, "deja_enregistree": False}
    except sqlite3.IntegrityError:
        conn.rollback()
        return {"success": True, "deja_enregistree": True}
    finally:
        conn.close()


def get_synthese_qualitative(protocole: str = PROTOCOLE_VERSION) -> Dict:
    """Moyennes et ecarts-types par critere (une evaluation par session)."""
    import math
    conn = _connexion()
    cur  = conn.cursor()
    filtre = "protocole_version = ?" if protocole else "protocole_version IS NULL"
    params = (protocole,) if protocole else ()
    criteres = ['grammaticalite', 'naturalite', 'clarte',
                'plausibilite_dist', 'pertinence_obj', 'alignement_bloom',
                'acceptabilite', 'utilite_apprentissage']
    res = {}
    for c in criteres:
        vals = [r[0] for r in cur.execute(
            f"SELECT {c} FROM exp_eval_qualitative WHERE {filtre}", params)]
        n = len(vals)
        moy = sum(vals) / n if n else 0.0
        sd = math.sqrt(sum((v - moy) ** 2 for v in vals) / (n - 1)) if n > 1 else 0.0
        res[c] = {"moy": round(moy, 2), "std": round(sd, 2), "n": n}
    conn.close()
    return {"protocole": protocole or "v1", "criteres": res}


# =============================================================
# EXPORTS (jamais de nom, prenom ni e-mail)
# =============================================================

def _csv(entetes: List[str], lignes) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(entetes)
    for l in lignes:
        w.writerow(list(l))
    return out.getvalue()


def exporter_reponses_v2_csv() -> str:
    """Fichier d'analyse principal : une ligne par reponse, avec les
    deux temps estimes et leurs composantes."""
    conn = _connexion()
    rows = conn.execute("""
        SELECT p.code_anonyme, p.niveau_etudes, p.etablissement,
               s.code_session, s.statut AS statut_session, s.numero_rotation,
               r.numero_question AS rang, i.code_item, r.source,
               r.objectif_code, r.mode_bloom, i.niveau_complexite,
               i.structure_syntaxique, i.nb_propositions, i.nb_connecteurs,
               i.nb_quantificateurs, i.nb_negations, i.profondeur,
               i.ert_a_s, i.ert_a_publie_s, i.ert_a_detail_json,
               i.ert_b_s, i.ert_b_structurel_s, i.ert_b_detail_json,
               r.nb_choix, r.position_correcte, r.position_choisie,
               r.est_correct, r.temps_reel_s, r.temps_cache_ms,
               r.nb_changements, i.params_version
        FROM exp_reponses r
        JOIN exp_sessions s     ON s.id = r.session_id
        JOIN exp_participants p ON p.id = r.participant_id
        LEFT JOIN exp_items i   ON i.id = r.item_id
        WHERE r.protocole_version IS NOT NULL
        ORDER BY p.code_anonyme, r.numero_question
    """).fetchall()
    conn.close()
    entetes = ["code_anonyme", "niveau_etudes", "etablissement",
               "code_session", "statut_session", "numero_rotation",
               "rang", "code_item", "source", "objectif_code", "mode_bloom",
               "niveau_complexite", "structure_syntaxique",
               "nb_propositions", "nb_connecteurs", "nb_quantificateurs",
               "nb_negations", "profondeur",
               "ert_a_s", "ert_a_publie_s", "ert_a_difficulte_prop",
               "ert_a_nb_mots", "ert_a_terme_difficulte", "ert_a_terme_lecture",
               "ert_b_s", "ert_b_structurel_s", "ert_b_base",
               "ert_b_propositions", "ert_b_connecteurs",
               "ert_b_quantificateurs", "ert_b_negations",
               "ert_b_profondeur", "ert_b_bonus_analyse",
               "nb_choix", "position_correcte", "position_choisie",
               "est_correct", "temps_reel_s", "temps_cache_s",
               "nb_changements", "params_version"]

    def ligne(r):
        a = json.loads(r["ert_a_detail_json"] or "{}") or {}
        b = json.loads(r["ert_b_detail_json"] or "{}") or {}
        return [r["code_anonyme"], r["niveau_etudes"], r["etablissement"],
                r["code_session"], r["statut_session"], r["numero_rotation"],
                r["rang"], r["code_item"], r["source"], r["objectif_code"],
                r["mode_bloom"], r["niveau_complexite"],
                r["structure_syntaxique"], r["nb_propositions"],
                r["nb_connecteurs"], r["nb_quantificateurs"],
                r["nb_negations"], r["profondeur"],
                r["ert_a_s"], r["ert_a_publie_s"],
                a.get("ert_a_difficulte_prop"), a.get("ert_a_nb_mots"),
                a.get("ert_a_terme_difficulte"), a.get("ert_a_terme_lecture"),
                r["ert_b_s"], r["ert_b_structurel_s"], b.get("base"),
                b.get("propositions"), b.get("connecteurs"),
                b.get("quantificateurs"), b.get("negations"),
                b.get("profondeur"), b.get("bonus_analyse"),
                r["nb_choix"], r["position_correcte"], r["position_choisie"],
                r["est_correct"], r["temps_reel_s"],
                None if r["temps_cache_ms"] is None
                else round(r["temps_cache_ms"] / 1000, 3),
                r["nb_changements"], r["params_version"]]
    return _csv(entetes, (ligne(r) for r in rows))


def exporter_items_csv() -> str:
    """Tous les items (banque et generes) avec leur texte complet."""
    conn = _connexion()
    rows = conn.execute("""
        SELECT code_item, source, statut, objectif_code, mode_bloom,
               niveau_complexite, enonce, reponse_correcte, distracteurs_json,
               nb_choix, ert_a_s, ert_a_publie_s, ert_b_s, ert_b_structurel_s,
               prop_a_json, params_version, commentaire_validation
        FROM exp_items ORDER BY source, objectif_code, mode_bloom, id
    """).fetchall()
    conn.close()
    return _csv([k for k in rows[0].keys()] if rows else
                ["code_item"], (tuple(r) for r in rows))


def exporter_eval_qualitative_csv(protocole: str = PROTOCOLE_VERSION) -> str:
    conn = _connexion()
    filtre = "e.protocole_version = ?" if protocole else "e.protocole_version IS NULL"
    params = (protocole,) if protocole else ()
    rows = conn.execute(f"""
        SELECT p.code_anonyme, p.niveau_etudes, p.etablissement,
               e.grammaticalite, e.naturalite, e.clarte,
               e.plausibilite_dist, e.pertinence_obj, e.alignement_bloom,
               e.acceptabilite, e.utilite_apprentissage,
               e.score_coherence, e.score_plausibilite,
               e.score_acceptabilite, e.score_global, e.commentaire
        FROM exp_eval_qualitative e
        JOIN exp_participants p ON e.participant_id = p.id
        WHERE {filtre}
        ORDER BY e.date_eval
    """, params).fetchall()
    conn.close()
    return _csv(["code_anonyme", "niveau_etudes", "etablissement",
                 "grammaticalite", "naturalite", "clarte",
                 "plausibilite_distracteurs", "pertinence_objectif",
                 "alignement_bloom", "acceptabilite", "utilite_apprentissage",
                 "score_coherence", "score_plausibilite",
                 "score_acceptabilite", "score_global", "commentaire"],
                (tuple(r) for r in rows))


# -- Exports de la collecte v1 (2026), colonnes dans l'ordre de l'en-tete --

def exporter_donnees_ert_csv() -> str:
    conn = _connexion()
    rows = conn.execute("""
        SELECT p.code_anonyme, p.niveau_etudes, p.etablissement,
               r.objectif_code, r.mode_bloom, r.niveau_complexite,
               r.nb_propositions, r.nb_connecteurs, r.nb_quantificateurs,
               r.nb_negations, r.profondeur, r.ert_predit_s, r.score_predit,
               r.temps_reel_s, r.est_correct
        FROM exp_reponses r
        JOIN exp_participants p ON r.participant_id = p.id
        JOIN exp_sessions s ON r.session_id = s.id
        WHERE r.protocole_version IS NULL
        ORDER BY r.objectif_code, r.mode_bloom
    """).fetchall()
    conn.close()
    return _csv(["code_anonyme", "niveau_etudes", "etablissement",
                 "objectif_code", "mode_bloom", "niveau_complexite",
                 "nb_propositions", "nb_connecteurs", "nb_quantificateurs",
                 "nb_negations", "profondeur", "ert_predit_s", "score_predit",
                 "temps_reel_s", "est_correct"], (tuple(r) for r in rows))


def exporter_donnees_distracteurs_csv() -> str:
    conn = _connexion()
    rows = conn.execute("""
        SELECT p.code_anonyme, p.niveau_etudes, p.etablissement,
               r.objectif_code, r.mode_bloom, r.niveau_complexite, r.enonce,
               r.choix_a, r.choix_b, r.choix_c, r.choix_d,
               r.reponse_correcte, r.distracteur_choisi, r.est_correct,
               r.ert_predit_s, r.temps_reel_s
        FROM exp_reponses r
        JOIN exp_participants p ON r.participant_id = p.id
        JOIN exp_sessions s ON r.session_id = s.id
        WHERE r.protocole_version IS NULL
        ORDER BY r.objectif_code
    """).fetchall()
    conn.close()
    return _csv(["code_anonyme", "niveau_etudes", "etablissement",
                 "objectif_code", "mode_bloom", "niveau_complexite", "enonce",
                 "choix_a", "choix_b", "choix_c", "choix_d",
                 "reponse_correcte", "distracteur_choisi", "est_correct",
                 "ert_predit_s", "temps_reel_s"], (tuple(r) for r in rows))


# =============================================================
# TABLEAU DE BORD (administrateur)
# =============================================================

def get_stats_experimentation() -> Dict:
    conn = _connexion()
    cur  = conn.cursor()
    out = {
        "protocole": PROTOCOLE_VERSION,
        "nb_participants": cur.execute(
            "SELECT COUNT(*) FROM exp_participants").fetchone()[0],
        "sessions_v2": {r["statut"]: r["n"] for r in cur.execute("""
            SELECT statut, COUNT(*) n FROM exp_sessions
            WHERE protocole_version=? GROUP BY statut""", (PROTOCOLE_VERSION,))},
        "nb_reponses_v2": cur.execute(
            "SELECT COUNT(*) FROM exp_reponses WHERE protocole_version=?",
            (PROTOCOLE_VERSION,)).fetchone()[0],
        "nb_reponses_v1": cur.execute(
            "SELECT COUNT(*) FROM exp_reponses WHERE protocole_version IS NULL"
        ).fetchone()[0],
    }
    conn.close()
    out["banque"] = etat_banque()
    return out
