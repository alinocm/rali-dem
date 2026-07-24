# ─────────────────────────────────────────────────────────────
# auth.py  —  Module d'authentification RALI-DEM
#
# Sécurité :
#   • Hash SHA-256 + sel aléatoire (stdlib Python, 0 dépendance)
#   • Token HMAC-SHA256 (JWT-like), expiration 24h
#   • Clé secrète via variable d'environnement RALI_SECRET_KEY
#
# Rôles : apprenant | enseignant | administrateur
# Compte admin par défaut : admin@rali-dem.cm / Admin2026!
# ─────────────────────────────────────────────────────────────

import os
import hmac
import json
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

DB_PATH = os.environ.get('RALI_DB_PATH', os.path.join(os.path.dirname(__file__), '..', 'database', 'rali_dem.db'))
SECRET_KEY = os.environ.get('RALI_SECRET_KEY', 'rali-dem-secret-2026-changez-moi')
TOKEN_DUREE_HEURES = 24

NIVEAUX_VALIDES = ['L1', 'L2', 'L3', 'Master 1', 'Master 2', 'Doctorat']
ROLES_VALIDES   = ['apprenant', 'enseignant', 'administrateur']


# ═════════════════════════════════════════════════════════════
# CONNEXION BASE DE DONNÉES
# ═════════════════════════════════════════════════════════════

def _connexion() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ═════════════════════════════════════════════════════════════
# INITIALISATION DES TABLES
# ═════════════════════════════════════════════════════════════

def init_tables_auth():
    """Crée les tables auth et le compte admin par défaut."""
    conn = _connexion()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            nom                 TEXT    NOT NULL,
            prenom              TEXT    NOT NULL,
            email               TEXT    NOT NULL UNIQUE,
            mot_de_passe        TEXT    NOT NULL,
            sel                 TEXT    NOT NULL,
            niveau              TEXT    NOT NULL,
            institution         TEXT    NOT NULL,
            role                TEXT    NOT NULL DEFAULT 'apprenant',
            actif               INTEGER NOT NULL DEFAULT 1,
            date_creation       TEXT    NOT NULL,
            derniere_connexion  TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tokens_invalides (
            token           TEXT NOT NULL PRIMARY KEY,
            date_expiration TEXT NOT NULL
        )
    """)

    conn.commit()
    _creer_admin_si_absent(conn)
    conn.close()


def _creer_admin_si_absent(conn):
    cur   = conn.cursor()
    exist = cur.execute(
        "SELECT id FROM utilisateurs WHERE role = 'administrateur'"
    ).fetchone()
    if not exist:
        sel  = secrets.token_hex(32)
        h    = _hasher_mdp("Admin2026!", sel)
        cur.execute("""
            INSERT INTO utilisateurs
                (nom, prenom, email, mot_de_passe, sel, niveau,
                 institution, role, actif, date_creation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        """, ("Admin", "RALI-DEM", "admin@rali-dem.cm", h, sel,
              "Doctorat", "Université de Yaoundé I",
              "administrateur", _maintenant()))
        conn.commit()
        print("[AUTH] Compte admin créé : admin@rali-dem.cm / Admin2026!")


# ═════════════════════════════════════════════════════════════
# FONCTIONS CRYPTOGRAPHIQUES
# ═════════════════════════════════════════════════════════════

def _hasher_mdp(mot_de_passe: str, sel: str) -> str:
    return hashlib.sha256((sel + mot_de_passe).encode('utf-8')).hexdigest()


def _generer_token(user_id: int, role: str) -> str:
    import base64
    exp = (datetime.now() + timedelta(hours=TOKEN_DUREE_HEURES)).isoformat()
    payload = json.dumps({
        "user_id": user_id,
        "role":    role,
        "exp":     exp,
        "jti":     secrets.token_hex(8),
    }, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(
        payload.encode()).decode().rstrip('=')
    sig = hmac.new(
        SECRET_KEY.encode('utf-8'),
        payload_b64.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"{payload_b64}.{sig}"


def _decoder_token(token: str) -> Optional[dict]:
    import base64
    try:
        payload_b64, sig = token.rsplit('.', 1)
    except ValueError:
        return None
    sig_attendue = hmac.new(
        SECRET_KEY.encode('utf-8'),
        payload_b64.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, sig_attendue):
        return None
    try:
        padding = 4 - len(payload_b64) % 4
        payload = json.loads(
            base64.urlsafe_b64decode(payload_b64 + '=' * padding))
    except Exception:
        return None
    try:
        if datetime.now() > datetime.fromisoformat(payload['exp']):
            return None
    except Exception:
        return None
    return payload


def _maintenant() -> str:
    return datetime.now().isoformat()


# ═════════════════════════════════════════════════════════════
# INSCRIPTION
# ═════════════════════════════════════════════════════════════

def inscrire(nom, prenom, email, mot_de_passe,
             niveau, institution, role='apprenant') -> dict:
    """Inscrit un nouvel utilisateur. Retourne token + infos."""
    if not nom.strip():
        raise ValueError("Le nom est obligatoire.")
    if not prenom.strip():
        raise ValueError("Le prénom est obligatoire.")
    if not email.strip() or '@' not in email:
        raise ValueError("Email invalide.")
    if len(mot_de_passe) < 6:
        raise ValueError("Mot de passe trop court (6 caractères minimum).")
    if niveau not in NIVEAUX_VALIDES:
        raise ValueError(f"Niveau invalide. Valeurs : {NIVEAUX_VALIDES}")
    if not institution.strip():
        raise ValueError("L'institution est obligatoire.")
    if role not in ROLES_VALIDES:
        role = 'apprenant'

    conn = _connexion()
    cur  = conn.cursor()
    exist = cur.execute(
        "SELECT id FROM utilisateurs WHERE LOWER(email)=LOWER(?)",
        (email.strip(),)
    ).fetchone()
    if exist:
        conn.close()
        raise ValueError("Un compte existe déjà avec cet email.")

    sel  = secrets.token_hex(32)
    h    = _hasher_mdp(mot_de_passe, sel)
    cur.execute("""
        INSERT INTO utilisateurs
            (nom,prenom,email,mot_de_passe,sel,niveau,
             institution,role,actif,date_creation)
        VALUES (?,?,?,?,?,?,?,?,1,?)
    """, (nom.strip(), prenom.strip(), email.strip().lower(),
          h, sel, niveau, institution.strip(), role, _maintenant()))
    conn.commit()
    uid = cur.lastrowid
    conn.close()

    return {
        "token":       _generer_token(uid, role),
        "user_id":     uid,
        "nom":         nom.strip(),
        "prenom":      prenom.strip(),
        "email":       email.strip().lower(),
        "niveau":      niveau,
        "institution": institution.strip(),
        "role":        role,
        "message":     "Inscription réussie.",
    }


# ═════════════════════════════════════════════════════════════
# CONNEXION
# ═════════════════════════════════════════════════════════════

def connecter(email: str, mot_de_passe: str) -> dict:
    """Connecte un utilisateur. Retourne token + infos."""
    if not email or not mot_de_passe:
        raise ValueError("Email et mot de passe obligatoires.")

    conn = _connexion()
    cur  = conn.cursor()
    user = cur.execute(
        "SELECT * FROM utilisateurs WHERE LOWER(email)=LOWER(?)",
        (email.strip(),)
    ).fetchone()

    if not user:
        conn.close()
        raise ValueError("Email ou mot de passe incorrect.")
    if not user['actif']:
        conn.close()
        raise ValueError("Compte désactivé. Contactez l'administrateur.")

    if not hmac.compare_digest(
        _hasher_mdp(mot_de_passe, user['sel']), user['mot_de_passe']
    ):
        conn.close()
        raise ValueError("Email ou mot de passe incorrect.")

    cur.execute(
        "UPDATE utilisateurs SET derniere_connexion=? WHERE id=?",
        (_maintenant(), user['id'])
    )
    conn.commit()
    token = _generer_token(user['id'], user['role'])
    conn.close()

    return {
        "token":       token,
        "user_id":     user['id'],
        "nom":         user['nom'],
        "prenom":      user['prenom'],
        "email":       user['email'],
        "niveau":      user['niveau'],
        "institution": user['institution'],
        "role":        user['role'],
        "message":     "Connexion réussie.",
    }


# ═════════════════════════════════════════════════════════════
# DÉCONNEXION
# ═════════════════════════════════════════════════════════════

def deconnecter(token: str) -> dict:
    """Invalide un token (liste noire)."""
    payload = _decoder_token(token)
    if not payload:
        return {"message": "Token déjà invalide."}
    conn = _connexion()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO tokens_invalides VALUES (?,?)",
            (token, payload['exp'])
        )
        conn.commit()
        conn.execute(
            "DELETE FROM tokens_invalides WHERE date_expiration<?",
            (datetime.now().isoformat(),)
        )
        conn.commit()
    finally:
        conn.close()
    return {"message": "Déconnexion réussie."}


# ═════════════════════════════════════════════════════════════
# VÉRIFICATION TOKEN
# ═════════════════════════════════════════════════════════════

def verifier_token(token: str) -> dict:
    """Vérifie un token et retourne le payload."""
    if not token:
        raise ValueError("Token manquant.")
    payload = _decoder_token(token)
    if not payload:
        raise ValueError("Token invalide ou expiré.")
    conn = _connexion()
    rev  = conn.execute(
        "SELECT token FROM tokens_invalides WHERE token=?", (token,)
    ).fetchone()
    conn.close()
    if rev:
        raise ValueError("Token révoqué. Veuillez vous reconnecter.")
    return payload


def verifier_token_request(authorization: Optional[str]) -> dict:
    """Extrait et vérifie le token depuis 'Bearer <token>'."""
    if not authorization or not authorization.startswith('Bearer '):
        raise ValueError("En-tête Authorization manquant ou invalide.")
    return verifier_token(authorization[7:].strip())


# ═════════════════════════════════════════════════════════════
# GESTION DES UTILISATEURS
# ═════════════════════════════════════════════════════════════

def get_utilisateur(user_id: int) -> dict:
    conn = _connexion()
    user = conn.execute(
        """SELECT id,nom,prenom,email,niveau,institution,
                  role,actif,date_creation,derniere_connexion
           FROM utilisateurs WHERE id=?""", (user_id,)
    ).fetchone()
    conn.close()
    if not user:
        raise ValueError(f"Utilisateur {user_id} introuvable.")
    return dict(user)


def get_tous_utilisateurs() -> list:
    """Liste tous les utilisateurs (admin uniquement)."""
    conn = _connexion()
    rows = conn.execute(
        """SELECT id,nom,prenom,email,niveau,institution,
                  role,actif,date_creation,derniere_connexion
           FROM utilisateurs ORDER BY date_creation DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def changer_mot_de_passe(user_id: int,
                          ancien: str,
                          nouveau: str) -> dict:
    if len(nouveau) < 6:
        raise ValueError("Nouveau mot de passe trop court.")
    conn = _connexion()
    cur  = conn.cursor()
    user = cur.execute(
        "SELECT * FROM utilisateurs WHERE id=?", (user_id,)
    ).fetchone()
    if not user:
        conn.close()
        raise ValueError("Utilisateur introuvable.")
    if not hmac.compare_digest(
        _hasher_mdp(ancien, user['sel']), user['mot_de_passe']
    ):
        conn.close()
        raise ValueError("Ancien mot de passe incorrect.")
    nouveau_sel  = secrets.token_hex(32)
    nouveau_hash = _hasher_mdp(nouveau, nouveau_sel)
    cur.execute(
        "UPDATE utilisateurs SET mot_de_passe=?,sel=? WHERE id=?",
        (nouveau_hash, nouveau_sel, user_id)
    )
    conn.commit()
    conn.close()
    return {"message": "Mot de passe modifié avec succès."}


def activer_desactiver(user_id: int,
                        actif:   bool,
                        admin_id: int) -> dict:
    if user_id == admin_id:
        raise ValueError("Impossible de modifier votre propre compte.")
    conn = _connexion()
    conn.execute(
        "UPDATE utilisateurs SET actif=? WHERE id=?",
        (1 if actif else 0, user_id)
    )
    conn.commit()
    conn.close()
    return {"message": f"Compte {'activé' if actif else 'désactivé'}."}


def modifier_role(user_id: int,
                   nouveau_role: str,
                   admin_id: int) -> dict:
    if nouveau_role not in ROLES_VALIDES:
        raise ValueError(f"Rôle invalide : {ROLES_VALIDES}")
    if user_id == admin_id:
        raise ValueError("Impossible de modifier votre propre rôle.")
    conn = _connexion()
    conn.execute(
        "UPDATE utilisateurs SET role=? WHERE id=?",
        (nouveau_role, user_id)
    )
    conn.commit()
    conn.close()
    return {"message": f"Rôle modifié en '{nouveau_role}'."}


# ═════════════════════════════════════════════════════════════
# TEST
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile
    DB_PATH = os.path.join(tempfile.gettempdir(), 'rali_test_auth.db')
    print("=== Test auth.py ===\n")

    init_tables_auth()
    print("1. Init tables ✅")

    r = inscrire("Dupont","Jean","jean@test.cm","MonMdp2026!","L2","UYI")
    print(f"2. Inscription ✅ — token: {r['token'][:25]}...")
    tok = r['token']
    uid = r['user_id']

    r2 = connecter("jean@test.cm","MonMdp2026!")
    print(f"3. Connexion ✅ — rôle: {r2['role']}")

    try:
        inscrire("X","Y","jean@test.cm","test","L2","UYI")
    except ValueError as e:
        print(f"4. Email unique ✅ — {e}")

    try:
        connecter("jean@test.cm","mauvais")
    except ValueError as e:
        print(f"5. Mauvais MDP ✅ — {e}")

    p = verifier_token(tok)
    print(f"6. Token valide ✅ — user_id: {p['user_id']}")

    deconnecter(tok)
    try:
        verifier_token(tok)
    except ValueError as e:
        print(f"7. Token révoqué ✅ — {e}")

    tok2 = connecter("jean@test.cm","MonMdp2026!")['token']
    changer_mot_de_passe(uid,"MonMdp2026!","Nouveau2026!")
    connecter("jean@test.cm","Nouveau2026!")
    print("8. Changement MDP ✅")

    admin = connecter("admin@rali-dem.cm","Admin2026!")
    print(f"9. Admin ✅ — rôle: {admin['role']}")

    users = get_tous_utilisateurs()
    print(f"10. {len(users)} utilisateurs ✅")

    print("\n✅ Tous les tests passent !")
