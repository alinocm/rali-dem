import sqlite3
import os
import json

# Chemin vers la base de données
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'rali_dem.db')

# Chemins vers les fichiers JSONL source
DEM_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'DEM.jsonl')
LVF_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'LVF.jsonl')

# ─────────────────────────────────────────────
# CONNEXION
# ─────────────────────────────────────────────

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ─────────────────────────────────────────────
# INITIALISATION COMPLÈTE
# ─────────────────────────────────────────────

def init_database():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")

    _creer_tables(cursor)
    conn.commit()
    _inserer_objectifs(cursor, conn)

    conn.close()
    print("Tables créées.")

def _creer_tables(cursor):

    # ── 1. Objectifs académiques ──────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS objectifs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            code      TEXT    NOT NULL UNIQUE,
            nom       TEXT    NOT NULL,
            description TEXT,
            chapitre  TEXT    NOT NULL
        )
    ''')

    # ── 2. Mots du DEM (noms, adjectifs, adverbes) ───────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dem_mots (
            id            INTEGER PRIMARY KEY,
            mot           TEXT    NOT NULL,
            no_sens       TEXT,
            categorie     TEXT    NOT NULL,
            type_anim     TEXT,
            genre         TEXT,
            domaine_code  TEXT,
            domaine_nom   TEXT,
            niveau_langue TEXT    NOT NULL DEFAULT "standard",
            sens          TEXT,
            contexte      TEXT,
            operateur     TEXT,
            h_aspire      INTEGER NOT NULL DEFAULT 0,
            exclamatif    INTEGER NOT NULL DEFAULT 0,
            interrogatif  INTEGER NOT NULL DEFAULT 0,
            reflexif      INTEGER NOT NULL DEFAULT 0,
            lvf           INTEGER NOT NULL DEFAULT 0
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dem_categorie  ON dem_mots(categorie)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dem_type_anim  ON dem_mots(type_anim)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dem_genre      ON dem_mots(genre)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dem_domaine    ON dem_mots(domaine_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dem_langue     ON dem_mots(niveau_langue)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dem_mot        ON dem_mots(mot)')

    # ── 3. Verbes du LVF ─────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lvf_verbes (
            id              INTEGER PRIMARY KEY,
            verbe           TEXT    NOT NULL,
            code_complet    TEXT    NOT NULL,
            no_sens         INTEGER NOT NULL DEFAULT 1,
            domaine_code    TEXT,
            domaine_clair   TEXT,
            classe          TEXT,
            sens            TEXT,
            operateur       TEXT,
            conjugaison     TEXT,
            lexique         INTEGER,
            dem             INTEGER NOT NULL DEFAULT 0
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lvf_verbe    ON lvf_verbes(verbe)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lvf_domaine  ON lvf_verbes(domaine_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lvf_classe   ON lvf_verbes(classe)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lvf_dem      ON lvf_verbes(dem)')

    # ── 4. Phrases exemples des verbes ───────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lvf_phrases (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            verbe_id  INTEGER NOT NULL REFERENCES lvf_verbes(id),
            phrase    TEXT    NOT NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_phrases_verbe ON lvf_phrases(verbe_id)')

    # ── 5. Constructions syntaxiques des verbes ───────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lvf_constructions (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            verbe_id  INTEGER NOT NULL REFERENCES lvf_verbes(id),
            code      TEXT    NOT NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_const_verbe ON lvf_constructions(verbe_id)')

    # ── 6. Dérivations des verbes (noms et adjectifs dérivés) ─────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lvf_derivations (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            verbe_id  INTEGER NOT NULL REFERENCES lvf_verbes(id),
            type_deriv TEXT   NOT NULL,
            mot_derive TEXT   NOT NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_deriv_verbe ON lvf_derivations(verbe_id)')

    # ── 7. Questions générées ─────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            objectif_code       TEXT    NOT NULL,
            mode_bloom          TEXT    NOT NULL
                                CHECK(mode_bloom IN ("comprehension","analyse")),
            niveau_complexite   TEXT    NOT NULL
                                CHECK(niveau_complexite IN ("faible","moyen","eleve")),
            enonce              TEXT    NOT NULL,
            reponse_correcte    TEXT    NOT NULL,
            distracteurs        TEXT    NOT NULL,
            ert_secondes        REAL    NOT NULL,
            score_pedagogique   REAL    NOT NULL,
            structure_syntaxique TEXT,
            profondeur_logique  INTEGER,
            nb_connecteurs      INTEGER,
            nb_propositions     INTEGER,
            date_creation       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(objectif_code) REFERENCES objectifs(code)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_q_objectif   ON questions(objectif_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_q_bloom      ON questions(mode_bloom)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_q_complexite ON questions(niveau_complexite)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_q_date       ON questions(date_creation)')

    # ── 8. Sessions enseignant ────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            enseignant   TEXT,
            nb_questions INTEGER DEFAULT 0,
            date_session TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

# ─────────────────────────────────────────────
# IMPORT DES DONNÉES
# ─────────────────────────────────────────────

def import_dem(dem_path=None):
    """Importe les mots du DEM.jsonl dans la table dem_mots."""
    path = dem_path or DEM_PATH
    if not os.path.exists(path):
        print(f"Fichier DEM introuvable : {path}")
        return

    conn = get_connection()
    cursor = conn.cursor()

    # Vider la table avant import
    cursor.execute("DELETE FROM dem_mots")
    conn.commit()

    batch = []
    total = 0

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            ca  = obj.get('CA', {})
            dom = obj.get('DOM', {})

            batch.append((
                obj['ID'],
                obj.get('M', ''),
                obj.get('no', None),
                ca.get('catégorie', ''),
                ca.get('type', None),
                ca.get('genre', None),
                dom.get('code', None),
                dom.get('nom', None),
                dom.get('niveau-de-langue', 'standard'),
                obj.get('SENS', None),
                obj.get('CONT', None),
                obj.get('OP', None),
                int(obj.get('h-aspiré', False)),
                int(obj.get('exclamatif', False)),
                int(obj.get('interrogatif', False)),
                int(obj.get('réflexif', False)),
                int(obj.get('LVF', False)),
            ))
            total += 1

            if len(batch) >= 5000:
                cursor.executemany('''
                    INSERT OR REPLACE INTO dem_mots
                    (id, mot, no_sens, categorie, type_anim, genre,
                     domaine_code, domaine_nom, niveau_langue, sens,
                     contexte, operateur, h_aspire, exclamatif,
                     interrogatif, reflexif, lvf)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''', batch)
                conn.commit()
                batch = []
                print(f"  DEM : {total} mots importés...", end='\r')

    if batch:
        cursor.executemany('''
            INSERT OR REPLACE INTO dem_mots
            (id, mot, no_sens, categorie, type_anim, genre,
             domaine_code, domaine_nom, niveau_langue, sens,
             contexte, operateur, h_aspire, exclamatif,
             interrogatif, reflexif, lvf)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', batch)
        conn.commit()

    conn.close()
    print(f"\nDEM importé : {total} entrées.")


def import_lvf(lvf_path=None):
    """Importe les verbes du LVF.jsonl dans les tables lvf_*."""
    path = lvf_path or LVF_PATH
    if not os.path.exists(path):
        print(f"Fichier LVF introuvable : {path}")
        return

    conn = get_connection()
    cursor = conn.cursor()

    # Vider les tables dépendantes avant import
    cursor.execute("DELETE FROM lvf_derivations")
    cursor.execute("DELETE FROM lvf_constructions")
    cursor.execute("DELETE FROM lvf_phrases")
    cursor.execute("DELETE FROM lvf_verbes")
    conn.commit()

    total = 0

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj  = json.loads(line)
            mot  = obj.get('MOT', {})
            dom  = obj.get('DOMAINE', {})
            deriv = obj.get('DERIVATION', {})

            verbe_id = obj['ID']

            # ── Verbe principal ──────────────────────────────────
            cursor.execute('''
                INSERT OR REPLACE INTO lvf_verbes
                (id, verbe, code_complet, no_sens, domaine_code,
                 domaine_clair, classe, sens, operateur, conjugaison,
                 lexique, dem)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                verbe_id,
                mot.get('verbe', ''),
                mot.get('code', ''),
                mot.get('no', 1),
                dom.get('code', None),
                dom.get('clair', None),
                obj.get('CLASSE', None),
                obj.get('SENS', None),
                obj.get('OPERATEUR', None),
                obj.get('CONJUGAISON', None),
                obj.get('LEXIQUE', None),
                int(obj.get('DEM', False)),
            ))

            # ── Phrases exemples ─────────────────────────────────
            for phrase in obj.get('PHRASE', []):
                cursor.execute('''
                    INSERT INTO lvf_phrases (verbe_id, phrase)
                    VALUES (?, ?)
                ''', (verbe_id, phrase))

            # ── Constructions syntaxiques ────────────────────────
            for code in obj.get('CONSTRUCTION', []):
                cursor.execute('''
                    INSERT INTO lvf_constructions (verbe_id, code)
                    VALUES (?, ?)
                ''', (verbe_id, code))

            # ── Dérivations ──────────────────────────────────────
            for adj in deriv.get('adjectifs', []):
                cursor.execute('''
                    INSERT INTO lvf_derivations (verbe_id, type_deriv, mot_derive)
                    VALUES (?, "adjectif", ?)
                ''', (verbe_id, adj))
            for nom in deriv.get('noms', []):
                cursor.execute('''
                    INSERT INTO lvf_derivations (verbe_id, type_deriv, mot_derive)
                    VALUES (?, "nom", ?)
                ''', (verbe_id, nom))

            total += 1
            if total % 2000 == 0:
                conn.commit()
                print(f"  LVF : {total} verbes importés...", end='\r')

    conn.commit()
    conn.close()
    print(f"\nLVF importé : {total} entrées.")


# ─────────────────────────────────────────────
# OBJECTIFS ACADÉMIQUES
# ─────────────────────────────────────────────

def _inserer_objectifs(cursor, conn):
    objectifs = [
        # Chapitre 1 — Fondements
        ("PROP",       "Identifier une proposition",
         "Reconnaître si un énoncé est une proposition logique dont la valeur de vérité est établissable",
         "Fondements de la logique"),
        ("VVER",       "Valeur de vérité",
         "Déterminer la valeur de vérité (Vraie ou Fausse) d'une proposition simple ou composée",
         "Fondements de la logique"),
        ("TVER",       "Table de vérité",
         "Construire ou compléter une table de vérité pour une proposition composée",
         "Fondements de la logique"),
        ("NEG_SIMPLE", "Négation simple",
         "Formuler correctement la négation d'une proposition élémentaire",
         "Fondements de la logique"),
        # Chapitre 2 — Connecteurs
        ("CONN_ID",    "Identifier les connecteurs",
         "Reconnaître ET, OU, ⇒, ⇔ dans une proposition en langage naturel ou formel",
         "Connecteurs logiques"),
        ("CONN_TRAD",  "Traduction langage naturel vers formel",
         "Traduire une proposition en langage naturel vers une formule logique",
         "Connecteurs logiques"),
        ("CONN_INV",   "Traduction formel vers langage naturel",
         "Traduire une formule logique en une phrase correcte en langage naturel",
         "Connecteurs logiques"),
        ("IMP",        "Implication logique",
         "Identifier, évaluer et manipuler une implication P⇒Q",
         "Connecteurs logiques"),
        ("EQUIV",      "Équivalence logique",
         "Identifier, évaluer et manipuler une équivalence P⇔Q",
         "Connecteurs logiques"),
        # Chapitre 3 & 4 — Propriétés et négations
        ("MORGAN",     "Lois de De Morgan",
         "Appliquer non(P∧Q) ≡ nonP∨nonQ et non(P∨Q) ≡ nonP∧nonQ",
         "Propriétés et négations"),
        ("NEG_COMP",   "Négation d'une proposition composée",
         "Formuler la négation d'une proposition composée avec ET, OU, ⇒ ou ⇔",
         "Propriétés et négations"),
        ("NEG_IMP",    "Négation d'une implication",
         "Appliquer non(P⇒Q) ≡ P∧non(Q)",
         "Propriétés et négations"),
        # Chapitre 5 — Quantificateurs
        ("QUANT_TRAD", "Traduire avec quantificateurs",
         "Traduire un énoncé contenant ∀ ou ∃ du langage naturel vers le formel et inversement",
         "Quantificateurs"),
        ("NEG_QUANT",  "Négation des quantificateurs",
         "Appliquer non(∀x P(x)) ≡ ∃x non(P(x)) et non(∃x P(x)) ≡ ∀x non(P(x))",
         "Quantificateurs"),
        # Chapitre 6 — Raisonnements
        ("CONTRAP",    "Raisonnement par contraposée",
         "Reconnaître et utiliser P⇒Q ≡ non(Q)⇒non(P) dans un raisonnement",
         "Raisonnements en logique"),
    ]
    for obj in objectifs:
        cursor.execute('''
            INSERT OR IGNORE INTO objectifs (code, nom, description, chapitre)
            VALUES (?, ?, ?, ?)
        ''', obj)
    conn.commit()


# ─────────────────────────────────────────────
# REQUÊTES UTILITAIRES — DICTIONNAIRE
# ─────────────────────────────────────────────

def get_noms(type_anim=None, genre=None, domaine=None, limit=50):
    """Retourne des noms du DEM filtrés par type, genre et domaine."""
    conn = get_connection()
    cursor = conn.cursor()
    q = '''SELECT id, mot, type_anim, genre, domaine_nom, sens
           FROM dem_mots
           WHERE categorie IN ("N", "A,N")
             AND niveau_langue = "standard"
             AND genre IS NOT NULL
             AND genre != "?"'''
    params = []
    if type_anim:
        q += ' AND type_anim = ?'
        params.append(type_anim)
    if genre:
        q += ' AND genre = ?'
        params.append(genre)
    if domaine:
        q += ' AND domaine_code = ?'
        params.append(domaine)
    q += ' ORDER BY RANDOM() LIMIT ?'
    params.append(limit)
    cursor.execute(q, params)
    result = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return result

def get_verbes(domaine=None, dem_only=True, limit=50):
    """Retourne des verbes du LVF filtrés par domaine."""
    conn = get_connection()
    cursor = conn.cursor()
    q = '''SELECT id, verbe, code_complet, domaine_clair, classe, sens, conjugaison
           FROM lvf_verbes WHERE 1=1'''
    params = []
    if dem_only:
        q += ' AND dem = 1'
    if domaine:
        q += ' AND domaine_code = ?'
        params.append(domaine)
    q += ' ORDER BY RANDOM() LIMIT ?'
    params.append(limit)
    cursor.execute(q, params)
    result = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return result

def get_phrases_verbe(verbe_id):
    """Retourne les phrases exemples d'un verbe."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT phrase FROM lvf_phrases WHERE verbe_id = ?', (verbe_id,))
    result = [r['phrase'] for r in cursor.fetchall()]
    conn.close()
    return result

def get_adjectifs(domaine=None, limit=20):
    """Retourne des adjectifs du DEM."""
    conn = get_connection()
    cursor = conn.cursor()
    q = '''SELECT id, mot, sens, domaine_nom
           FROM dem_mots
           WHERE categorie IN ("A", "A,N")
             AND niveau_langue = "standard"'''
    params = []
    if domaine:
        q += ' AND domaine_code = ?'
        params.append(domaine)
    q += ' ORDER BY RANDOM() LIMIT ?'
    params.append(limit)
    cursor.execute(q, params)
    result = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return result


# ─────────────────────────────────────────────
# REQUÊTES UTILITAIRES — OBJECTIFS & QUESTIONS
# ─────────────────────────────────────────────

def get_all_objectifs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM objectifs ORDER BY chapitre, code')
    result = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return result

def get_objectifs_par_chapitre():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT chapitre FROM objectifs ORDER BY chapitre')
    chapitres = [r['chapitre'] for r in cursor.fetchall()]
    result = {}
    for chap in chapitres:
        cursor.execute(
            'SELECT * FROM objectifs WHERE chapitre = ? ORDER BY code',
            (chap,)
        )
        result[chap] = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return result

def sauvegarder_question(question: dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO questions
        (objectif_code, mode_bloom, niveau_complexite, enonce,
         reponse_correcte, distracteurs, ert_secondes, score_pedagogique,
         structure_syntaxique, profondeur_logique,
         nb_connecteurs, nb_propositions)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        question['objectif_code'],
        question['mode_bloom'],
        question['niveau_complexite'],
        question['enonce'],
        question['reponse_correcte'],
        str(question['distracteurs']),
        question['ert_secondes'],
        question['score_pedagogique'],
        question.get('structure_syntaxique', 'SVO'),
        question.get('profondeur_logique', 1),
        question.get('nb_connecteurs', 1),
        question.get('nb_propositions', 2),
    ))
    conn.commit()
    qid = cursor.lastrowid
    conn.close()
    return qid

def get_questions(limit=50, objectif_code=None):
    conn = get_connection()
    cursor = conn.cursor()
    if objectif_code:
        cursor.execute('''
            SELECT * FROM questions WHERE objectif_code = ?
            ORDER BY date_creation DESC LIMIT ?
        ''', (objectif_code, limit))
    else:
        cursor.execute('''
            SELECT * FROM questions ORDER BY date_creation DESC LIMIT ?
        ''', (limit,))
    result = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return result

def supprimer_question(question_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM questions WHERE id = ?', (question_id,))
    conn.commit()
    conn.close()

def get_statistiques():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as total FROM questions')
    total = cursor.fetchone()['total']
    cursor.execute('SELECT AVG(score_pedagogique) as moy FROM questions')
    moy_score = cursor.fetchone()['moy'] or 0
    cursor.execute('SELECT AVG(ert_secondes) as moy FROM questions')
    moy_ert = cursor.fetchone()['moy'] or 0
    cursor.execute('''
        SELECT o.nom, COUNT(q.id) as nb
        FROM objectifs o
        LEFT JOIN questions q ON o.code = q.objectif_code
        GROUP BY o.code, o.nom ORDER BY nb DESC
    ''')
    par_objectif = [dict(r) for r in cursor.fetchall()]
    cursor.execute('SELECT COUNT(*) as nb FROM dem_mots')
    nb_dem = cursor.fetchone()['nb']
    cursor.execute('SELECT COUNT(*) as nb FROM lvf_verbes WHERE dem = 1')
    nb_lvf = cursor.fetchone()['nb']
    conn.close()
    return {
        'total_questions':  total,
        'score_moyen':      round(moy_score, 2),
        'ert_moyen':        round(moy_ert, 1),
        'par_objectif':     par_objectif,
        'nb_mots_dem':      nb_dem,
        'nb_verbes_lvf':    nb_lvf,
    }


# ─────────────────────────────────────────────
# POINT D'ENTRÉE : initialiser + importer
# ─────────────────────────────────────────────

if __name__ == '__main__':
    import sys
    print("=== Initialisation de la base RALI-DEM ===")
    init_database()

    if '--import' in sys.argv:
        print("\n=== Import DEM ===")
        import_dem()
        print("\n=== Import LVF ===")
        import_lvf()

    print("\nTerminé.")