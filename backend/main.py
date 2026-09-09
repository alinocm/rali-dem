# -*- coding: utf-8 -*-
# -------------------------------------------------------------
# main.py  --  API FastAPI RALI-DEM (version complete)
# -------------------------------------------------------------

import os
import sys

# Ajouter le dossier backend au sys.path
# Fonctionne dans les deux cas :
#   - local    : python backend/main.py
#   - Railway  : uvicorn backend.main:app
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List

# -- Chemins dynamiques (local vs Railway) ---------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

# Sur Railway : utiliser /data pour la persistance (Volume)
# En local : utiliser database/ dans le projet
if os.environ.get("RAILWAY_ENVIRONMENT"):
    DB_DIR = "/data"
else:
    DB_DIR = os.path.join(ROOT_DIR, "database")

os.makedirs(DB_DIR, exist_ok=True)

# Injecter le chemin dans tous les modules
os.environ["RALI_DB_PATH"] = os.path.join(DB_DIR, "rali_dem.db")

# -- Imports modules RALI-DEM ----------------------------------
from database  import init_database, get_all_objectifs
from generator import generer_question, reset_session
from corrector import corriger
from adaptive  import (init_tables_adaptatives,
               creer_session, enregistrer_reponse, get_session)
from exam      import (init_tables_examen,
               creer_examen, soumettre_reponse, get_bulletin)
from tools     import (
    get_rapport_erreurs, get_indice,
    exporter_fiche_html,
    exporter_json as exp_json,
    exporter_csv as exp_csv,
    exporter_moodle_xml
)
from auth      import (
    init_tables_auth, inscrire, connecter, deconnecter,
    verifier_token_request, get_utilisateur,
    get_tous_utilisateurs, changer_mot_de_passe,
    activer_desactiver, modifier_role
)
from tracking  import (
    init_tables_tracking,
    creer_session_adaptative, enregistrer_reponse_adaptative,
    terminer_session_adaptative,
    creer_session_examen,
    enregistrer_reponse_examen as track_rep_exam,
    terminer_session_examen,
    get_historique_apprenant, get_resultats_par_objectif
)
from experimentation import (
    init_tables_experimentation,
    inscrire_participant, get_participant_by_email,
    creer_session_exp, enregistrer_reponse_exp,
    terminer_session_exp,
    enregistrer_eval_qualitative,
    get_synthese_qualitative,
    exporter_donnees_ert_csv,
    exporter_donnees_distracteurs_csv,
    exporter_eval_qualitative_csv,
    get_stats_experimentation
)

from stats import (
    get_tableau_bord, get_stats_objectifs,
    get_stats_apprenant, get_stats_cohorte,
    get_matrice_correlations, get_progression_temporelle,
    exporter_stats_json, exporter_stats_csv, exporter_stats_spss
)

# =============================================================
# INITIALISATION
# =============================================================

app = FastAPI(
    title="RALI-DEM API",
    description="Generateur automatique de questions de logique mathematique",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# -- Autoriser le domaine Railway ------------------------------
from fastapi import Request
from fastapi.responses import JSONResponse

@app.middleware("http")
async def add_railway_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

# -- Gestionnaire global d'exceptions -> toujours du JSON -----
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Garantit que toute erreur 500 est renvoyee en JSON, jamais en texte brut."""
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    print(f"[ERREUR 500] {request.method} {request.url.path} -> {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Erreur interne : {str(exc)}"}
    )

# -- Servir le frontend ----------------------------------------
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')
INDEX_HTML   = os.path.join(FRONTEND_DIR, 'index.html')

@app.get("/")
def root():
    """Sert la page principale de l'application."""
    return FileResponse(INDEX_HTML)

@app.get("/test")
def route_test():
    """Page de test minimale."""
    chemin = os.path.join(FRONTEND_DIR, "test_connexion.html")
    if os.path.exists(chemin):
        return FileResponse(chemin)
    from fastapi.responses import HTMLResponse
    return HTMLResponse("<h2>Test OK - serveur repond</h2>")

@app.get("/experimentation")
@app.get("/experimentation.html")
def route_experimentation():
    """Interface de passation pour les etudiants participants."""
    chemin = os.path.join(FRONTEND_DIR, "experimentation_ui.html")
    if os.path.exists(chemin):
        return FileResponse(chemin)
    raise HTTPException(404,
        f"Copiez experimentation_ui.html dans {FRONTEND_DIR}")

@app.get("/index.html")
def index():
    return FileResponse(INDEX_HTML)

@app.on_event("startup")
def startup():
    import sqlite3

    db_path = os.environ.get("RALI_DB_PATH", "non defini")
    print(f"[RALI-DEM] DB_PATH    = {db_path}")
    print(f"[RALI-DEM] RAILWAY    = {os.environ.get('RAILWAY_ENVIRONMENT', 'local')}")

    # Creer /data si Railway
    if os.environ.get("RAILWAY_ENVIRONMENT"):
        os.makedirs("/data", exist_ok=True)

    init_database()
    init_tables_auth()
    init_tables_tracking()
    init_tables_experimentation()

    # Initialisation des tables adaptatives et examen
    # (import inline pour eviter les conflits de nommage)
    import adaptive as _adp
    import exam     as _exam
    _adp.init_tables_adaptatives()
    _exam.init_tables_examen()

    # Verifier et creer l'admin si absent
    try:
        conn = sqlite3.connect(db_path)
        nb = conn.execute(
            "SELECT COUNT(*) FROM utilisateurs WHERE role='administrateur'"
        ).fetchone()[0]
        conn.close()
        if nb == 0:
            print("[RALI-DEM] [WARN]  Aucun admin -- recreation forcee")
            from auth import init_tables_auth as _init_auth
            import sqlite3 as _sq, secrets as _sec, hashlib as _hl
            from datetime import datetime as _dt, timezone as _tz
            conn2 = _sq.connect(db_path)
            sel = _sec.token_hex(32)
            h   = _hl.sha256(("Admin2026!" + sel).encode()).hexdigest()
            now = _dt.now(_tz.utc).isoformat()
            conn2.execute("""
                INSERT OR IGNORE INTO utilisateurs
                    (nom, prenom, email, mot_de_passe, sel, niveau,
                     institution, role, actif, date_creation)
                VALUES (?,?,?,?,?,?,?,?,1,?)
            """, ("Admin","RALI-DEM","admin@rali-dem.cm",
                  h, sel, "Doctorat",
                  "Universite de Yaounde I","administrateur", now))
            conn2.commit()
            conn2.close()
            print("[RALI-DEM] [OK] Compte admin cree : admin@rali-dem.cm / Admin2026!")
        else:
            print(f"[RALI-DEM] [OK] Admin present ({nb} compte(s))")
    except Exception as e:
        print(f"[RALI-DEM] [WARN]  Erreur verification admin : {e}")

    print("[RALI-DEM] Demarrage [OK]")


@app.get("/api/diagnostic")
def diagnostic():
    """Route de diagnostic -- verifier l'etat de la BD en ligne."""
    import sqlite3
    db_path = os.environ.get("RALI_DB_PATH", "inconnu")
    try:
        conn = sqlite3.connect(db_path)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        nb_users = conn.execute("SELECT COUNT(*) FROM utilisateurs").fetchone()[0]
        nb_admin = conn.execute(
            "SELECT COUNT(*) FROM utilisateurs WHERE role='administrateur'"
        ).fetchone()[0]
        conn.close()
        return {
            "db_path":   db_path,
            "tables":    [t[0] for t in tables],
            "nb_users":  nb_users,
            "nb_admin":  nb_admin,
            "railway":   os.environ.get("RAILWAY_ENVIRONMENT", "local"),
        }
    except Exception as e:
        return {"error": str(e), "db_path": db_path}


@app.post("/api/diagnostic/creer_admin")
def creer_admin_force():
    """Force la creation du compte admin si absent.
    A appeler une seule fois apres le premier deploiement.
    """
    import sqlite3, secrets, hashlib
    db_path = os.environ.get("RALI_DB_PATH", "inconnu")
    try:
        conn = sqlite3.connect(db_path)
        exist = conn.execute(
            "SELECT id FROM utilisateurs WHERE email='admin@rali-dem.cm'"
        ).fetchone()
        if exist:
            conn.close()
            return {"message": "Compte admin deja existant", "id": exist[0]}

        # Creer le compte admin
        sel = secrets.token_hex(32)
        mdp = "Admin2026!"
        h   = hashlib.sha256((mdp + sel).encode()).hexdigest()
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("""
            INSERT INTO utilisateurs
                (nom, prenom, email, mot_de_passe, sel, niveau,
                 institution, role, actif, date_creation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        """, ("Admin", "RALI-DEM", "admin@rali-dem.cm", h, sel,
              "Doctorat", "Universite de Yaounde I",
              "administrateur", now))
        conn.commit()
        conn.close()
        return {"message": "Compte admin cree avec succes",
                "email": "admin@rali-dem.cm",
                "mot_de_passe": "Admin2026!"}
    except Exception as e:
        return {"error": str(e)}


# =============================================================
# MODELES PYDANTIC
# =============================================================

class DemandeQuestion(BaseModel):
    objectif_code:     str
    mode_bloom:        str = "comprehension"
    niveau_complexite: str = "moyen"
    sauvegarder:       bool = False

class DemandeCorrection(BaseModel):
    objectif_code:     str
    reponse_correcte:  str
    reponse_apprenant: str
    enonce:            str
    distracteurs:      List[str] = []
    mode_bloom:        str = "comprehension"

class DemandeSession(BaseModel):
    objectif_code: str
    mode_bloom:    str = "comprehension"
    apprenant:     str = ""
    niveau_depart: str = "faible"

class DemandeReponse(BaseModel):
    session_id:        int
    enonce:            str
    reponse_correcte:  str
    reponse_apprenant: str
    est_correct:       bool
    ert_secondes:      float = 0.0
    score_question:    float = 0.0

class DemandeExamen(BaseModel):
    objectifs:    List[str]
    mode_bloom:   str = "comprehension"
    niveau:       str = "moyen"
    nb_questions: int = 10
    apprenant:    str = ""
    titre:        str = "Examen RALI-DEM"

class DemandeRepExamen(BaseModel):
    examen_id:         int
    numero_question:   int = 1
    reponse_apprenant: str
    temps_reponse_s:   float = 0.0
    # Champs tracking (optionnels)
    objectif_code:     str = ""
    enonce:            str = ""
    reponse_correcte:  str = ""
    est_correct:       bool = False
    ert_secondes:      float = 0.0
    score_question:    float = 0.0

class DemandeExport(BaseModel):
    questions:    List[dict]
    titre:        str  = "Fiche d'exercices -- Logique mathematique"
    avec_corrige: bool = False
    enseignant:   str  = ""
    niveau:       str  = ""
    format:       str  = "html"

# -- Auth ------------------------------------------------------
class DemandeInscription(BaseModel):
    nom:          str
    prenom:       str
    email:        str
    mot_de_passe: str
    niveau:       str
    institution:  str
    role:         str = "apprenant"

class DemandeConnexion(BaseModel):
    email:        str
    mot_de_passe: str

class DemandeMdp(BaseModel):
    ancien_mdp:  str
    nouveau_mdp: str

class DemandeRole(BaseModel):
    nouveau_role: str

# -- Tracking --------------------------------------------------
class DemandeSessionAdapt(BaseModel):
    objectif_code: str
    mode_bloom:    str = "comprehension"
    niveau_depart: str = "faible"

class DemandeRepAdapt(BaseModel):
    session_id:        int
    objectif_code:     str
    mode_bloom:        str
    niveau_complexite: str
    enonce:            str
    reponse_apprenant: str
    reponse_correcte:  str
    est_correct:       bool
    ert_secondes:      float = 0.0
    score_question:    float = 0.0

class DemandeTerminerAdapt(BaseModel):
    session_id:   int
    niveau_final: str

class DemandeSessionExam(BaseModel):
    titre:           str
    objectifs_codes: List[str]
    mode_bloom:      str = "comprehension"
    niveau:          str = "moyen"


# -- Modeles experimentation -----------------------------------
class InscriptionParticipant(BaseModel):
    nom: str
    prenom: str
    email: str
    niveau_etudes: str
    etablissement: str
    consentement: bool
    utilisateur_id: Optional[int] = None

class DemandeSessionExp(BaseModel):
    participant_id: int
    protocole: str = "standard"
    nb_questions: int = 30

class ReponseExp(BaseModel):
    session_id: int
    participant_id: int
    numero_question: int
    question_data: dict
    reponse: dict

class DemandeTerminerExp(BaseModel):
    session_id: int

class DemandeRepExamTrack(BaseModel):
    session_examen_id: int
    objectif_code:     str
    mode_bloom:        str
    niveau_complexite: str
    enonce:            str
    reponse_apprenant: str
    reponse_correcte:  str
    est_correct:       bool
    ert_secondes:      float = 0.0
    score_question:    float = 0.0
    temps_reponse_s:   float = 0.0


# =============================================================
# HELPERS
# =============================================================

def _verifier_auth(authorization: Optional[str]) -> dict:
    """Verifie le token et retourne le payload."""
    try:
        return verifier_token_request(authorization)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

def _verifier_admin(authorization: Optional[str]) -> dict:
    """Verifie que l'utilisateur est admin."""
    payload = _verifier_auth(authorization)
    if payload.get("role") != "administrateur":
        raise HTTPException(status_code=403, detail="Acces reserve a l'administrateur.")
    return payload


# Route alias pour compatibilite avec l'ancien dashboard
@app.get("/api/statistiques")
def route_statistiques_alias(authorization: Optional[str] = Header(None)):
    """Alias de /api/stats/tableau_bord pour compatibilite."""
    try:
        return get_tableau_bord()
    except Exception as e:
        # Retourner des stats vides si pas de donnees
        return {
            "apprenants": {"total": 0, "actifs_7_jours": 0},
            "sessions":   {"adaptatives": 0, "examens": 0, "total": 0},
            "reponses":   {"total": 0, "taux_reussite": 0.0, "ert_moyen": 0.0},
            "examens":    {"note_moyenne": 0.0},
            "objectifs":  {"plus_echoue": None, "mieux_maitrise": None},
            "date_calcul": "N/A",
        }

# =============================================================
# ROUTES -- GENERATION
# =============================================================

@app.post("/api/generer")
def route_generer(d: DemandeQuestion):
    try:
        q = generer_question(d.objectif_code, d.mode_bloom, d.niveau_complexite)
        if not q:
            raise HTTPException(500, "Impossible de generer une question.")
        return q
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/corriger")
def route_corriger(d: DemandeCorrection):
    return corriger(
        objectif_code     = d.objectif_code,
        reponse_correcte  = d.reponse_correcte,
        reponse_apprenant = d.reponse_apprenant,
        enonce            = d.enonce,
        distracteurs      = d.distracteurs,
    )

@app.get("/api/objectifs")
def route_objectifs():
    return get_all_objectifs()

@app.get("/api/indice/{objectif_code}/{niveau}")
def route_indice(objectif_code: str, niveau: int):
    return get_indice(objectif_code, niveau)

@app.get("/api/rapport_erreurs")
def route_rapport(apprenant: str = "",
                  authorization: Optional[str] = Header(None)):
    # Si connecte, filtrer par utilisateur_id pour un rapport personnel
    utilisateur_id = None
    try:
        if authorization:
            payload = verifier_token_request(authorization)
            utilisateur_id = payload.get("user_id")
    except Exception:
        pass
    return get_rapport_erreurs(apprenant, utilisateur_id=utilisateur_id)


# =============================================================
# ROUTES -- PARCOURS ADAPTATIF
# =============================================================

@app.post("/api/adaptive/session")
def route_creer_session(d: DemandeSession):
    reset_session()
    return creer_session(d.objectif_code, d.mode_bloom,
                         d.apprenant, d.niveau_depart)

@app.post("/api/adaptive/reponse")
def route_reponse_adaptive(d: DemandeReponse):
    return enregistrer_reponse(
        d.session_id, d.enonce, d.reponse_correcte,
        d.reponse_apprenant, d.est_correct,
        d.ert_secondes, d.score_question
    )

@app.get("/api/adaptive/historique/{session_id}")
def route_historique_session(session_id: int):
    return get_session(session_id)

@app.post("/api/adaptive/terminer/{session_id}")
def route_terminer_session(session_id: int):
    return get_session(session_id)


# =============================================================
# ROUTES -- EXAMEN
# =============================================================

@app.post("/api/examen/creer")
def route_creer_examen(d: DemandeExamen):
    reset_session()
    return creer_examen(d.objectifs, d.mode_bloom, d.niveau,
                        d.nb_questions, d.apprenant, d.titre)

@app.post("/api/examen/reponse")
def route_reponse_examen(d: DemandeRepExamen):
    return soumettre_reponse(
        d.examen_id, d.numero_question,
        d.reponse_apprenant, d.temps_reponse_s
    )

@app.post("/api/examen/repondre")
def route_repondre_examen(d: DemandeRepExamen):
    """Alias de /api/examen/reponse pour compatibilite frontend."""
    return soumettre_reponse(
        d.examen_id, d.numero_question,
        d.reponse_apprenant, d.temps_reponse_s
    )

@app.post("/api/examen/terminer/{examen_id}")
def route_terminer_examen(examen_id: int):
    return get_bulletin(examen_id)

@app.get("/api/examen/{examen_id}")
def route_get_examen(examen_id: int):
    return get_bulletin(examen_id)

@app.get("/api/examen/bulletin/{examen_id}")
def route_get_bulletin(examen_id: int):
    """Alias pour recuperer le bulletin d'un examen."""
    return get_bulletin(examen_id)


# =============================================================
# ROUTES -- EXPORT FICHES
# =============================================================

@app.post("/api/exporter")
def route_exporter_html(d: DemandeExport):
    html = exporter_fiche_html(d.questions, d.titre,
                                d.avec_corrige, d.enseignant, d.niveau)
    return HTMLResponse(content=html)

@app.post("/api/exporter/json")
def route_exporter_json(d: DemandeExport):
    contenu = exp_json(d.questions, d.titre,
                       d.avec_corrige, d.enseignant, d.niveau)
    return Response(content=contenu, media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="fiche_rali_dem.json"'})

@app.post("/api/exporter/csv")
def route_exporter_csv(d: DemandeExport):
    contenu = exp_csv(d.questions, d.titre,
                      d.avec_corrige, d.enseignant, d.niveau)
    return Response(content=contenu.encode("utf-8-sig"), media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="fiche_rali_dem.csv"'})

@app.post("/api/exporter/moodle")
def route_exporter_moodle(d: DemandeExport):
    contenu = exporter_moodle_xml(d.questions, d.titre,
                                   d.avec_corrige, d.enseignant, d.niveau)
    return Response(content=contenu.encode("utf-8"), media_type="application/xml",
        headers={"Content-Disposition": 'attachment; filename="fiche_rali_dem.xml"'})


# =============================================================
# ROUTES -- AUTHENTIFICATION
# =============================================================

@app.post("/api/auth/inscription")
def route_inscription(d: DemandeInscription):
    try:
        return inscrire(d.nom, d.prenom, d.email, d.mot_de_passe,
                        d.niveau, d.institution, d.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/connexion")
def route_connexion(d: DemandeConnexion):
    try:
        return connecter(d.email, d.mot_de_passe)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/api/auth/deconnexion")
def route_deconnexion(authorization: Optional[str] = Header(None)):
    token = (authorization or "").replace("Bearer ", "").strip()
    return deconnecter(token)

@app.get("/api/auth/profil")
def route_profil(authorization: Optional[str] = Header(None)):
    payload = _verifier_auth(authorization)
    return get_utilisateur(payload["user_id"])

@app.put("/api/auth/mot_de_passe")
def route_changer_mdp(d: DemandeMdp,
                       authorization: Optional[str] = Header(None)):
    payload = _verifier_auth(authorization)
    try:
        return changer_mot_de_passe(payload["user_id"], d.ancien_mdp, d.nouveau_mdp)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================
# ROUTES -- ADMIN UTILISATEURS
# =============================================================

@app.get("/api/admin/utilisateurs")
def route_tous_utilisateurs(authorization: Optional[str] = Header(None)):
    _verifier_admin(authorization)
    return get_tous_utilisateurs()

@app.put("/api/admin/utilisateurs/{user_id}/role")
def route_modifier_role(user_id: int, d: DemandeRole,
                         authorization: Optional[str] = Header(None)):
    payload = _verifier_admin(authorization)
    try:
        return modifier_role(user_id, d.nouveau_role, payload["user_id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/admin/utilisateurs/{user_id}/actif")
def route_activer(user_id: int, actif: int = 1,
                   authorization: Optional[str] = Header(None)):
    payload = _verifier_admin(authorization)
    try:
        return activer_desactiver(user_id, bool(actif), payload["user_id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================
# ROUTES -- TRACKING ADAPTATIF
# =============================================================

@app.post("/api/tracking/session_adaptative")
def route_creer_sess_adapt(d: DemandeSessionAdapt,
                             authorization: Optional[str] = Header(None)):
    payload = _verifier_auth(authorization)
    return creer_session_adaptative(
        payload["user_id"], d.objectif_code,
        d.mode_bloom, d.niveau_depart
    )

@app.post("/api/tracking/reponse_adaptative")
def route_rep_adapt(d: DemandeRepAdapt,
                     authorization: Optional[str] = Header(None)):
    payload = _verifier_auth(authorization)
    uid = payload["user_id"]
    print(f"[TRACKING] reponse_adaptative: user={uid} session={d.session_id} obj={d.objectif_code} correct={d.est_correct}")
    try:
        result = enregistrer_reponse_adaptative(
            d.session_id, uid,
            d.objectif_code, d.mode_bloom, d.niveau_complexite,
            d.enonce, d.reponse_apprenant, d.reponse_correcte,
            d.est_correct, d.ert_secondes, d.score_question
        )
        print(f"[TRACKING] [OK] enregistre: {result}")
        return result
    except Exception as e:
        print(f"[TRACKING] [ERR] erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tracking/terminer_adaptative")
def route_terminer_adapt(d: DemandeTerminerAdapt,
                          authorization: Optional[str] = Header(None)):
    _verifier_auth(authorization)
    return terminer_session_adaptative(d.session_id, d.niveau_final)


# =============================================================
# ROUTES -- TRACKING EXAMEN
# =============================================================

@app.post("/api/tracking/session_examen")
def route_creer_sess_exam(d: DemandeSessionExam,
                            authorization: Optional[str] = Header(None)):
    payload = _verifier_auth(authorization)
    return creer_session_examen(
        payload["user_id"], d.titre,
        d.objectifs_codes, d.mode_bloom, d.niveau
    )

@app.post("/api/tracking/reponse_examen")
def route_rep_exam_track(d: DemandeRepExamTrack,
                          authorization: Optional[str] = Header(None)):
    payload = _verifier_auth(authorization)
    return track_rep_exam(
        d.session_examen_id, payload["user_id"],
        d.objectif_code, d.mode_bloom, d.niveau_complexite,
        d.enonce, d.reponse_apprenant, d.reponse_correcte,
        d.est_correct, d.ert_secondes, d.score_question,
        d.temps_reponse_s
    )

@app.post("/api/tracking/terminer_examen/{session_examen_id}")
def route_terminer_exam_track(session_examen_id: int,
                                authorization: Optional[str] = Header(None)):
    _verifier_auth(authorization)
    return terminer_session_examen(session_examen_id)


# =============================================================
# ROUTES -- HISTORIQUE APPRENANT
# =============================================================

@app.get("/api/tracking/historique")
def route_historique(authorization: Optional[str] = Header(None)):
    payload = _verifier_auth(authorization)
    uid = payload["user_id"]
    print(f"[HISTORIQUE] user={uid}")

    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'rali_dem.db')
    conn = sqlite3.connect(db_path)

    # Compter directement dans la BD
    nb_rep = conn.execute("SELECT COUNT(*) FROM track_reponses_adapt WHERE utilisateur_id=?", (uid,)).fetchone()[0]
    nb_ses = conn.execute("SELECT COUNT(*) FROM track_sessions_adapt WHERE utilisateur_id=?", (uid,)).fetchone()[0]
    print(f"[HISTORIQUE] BD directe: {nb_rep} reponses, {nb_ses} sessions pour user={uid}")

    # Verifier structure table
    cols = conn.execute("PRAGMA table_info(track_reponses_adapt)").fetchall()
    print(f"[HISTORIQUE] Colonnes track_reponses_adapt: {[c[1] for c in cols]}")
    conn.close()

    hist    = get_historique_apprenant(uid)
    par_obj = get_resultats_par_objectif(uid)
    hist["par_objectif"] = par_obj
    print(f"[HISTORIQUE] Resultat: sessions={len(hist.get('sessions_adaptatives',[]))}, par_obj={len(par_obj)}")
    return hist

@app.get("/api/tracking/historique/{user_id}")
def route_historique_admin(user_id: int,
                             authorization: Optional[str] = Header(None)):
    _verifier_admin(authorization)
    hist    = get_historique_apprenant(user_id)
    par_obj = get_resultats_par_objectif(user_id)
    hist["par_objectif"] = par_obj
    return hist


# =============================================================
# ROUTES -- STATISTIQUES (admin)
# =============================================================

@app.get("/api/stats/tableau_bord")
def route_tableau_bord(authorization: Optional[str] = Header(None)):
    _verifier_admin(authorization)
    return get_tableau_bord()

@app.get("/api/stats/objectifs")
def route_stats_objectifs(authorization: Optional[str] = Header(None)):
    _verifier_admin(authorization)
    return get_stats_objectifs()

@app.get("/api/stats/cohorte")
def route_stats_cohorte(niveau: Optional[str] = None,
                         institution: Optional[str] = None,
                         authorization: Optional[str] = Header(None)):
    _verifier_admin(authorization)
    return get_stats_cohorte(niveau, institution)

@app.get("/api/stats/apprenant/{user_id}")
def route_stats_apprenant(user_id: int,
                            authorization: Optional[str] = Header(None)):
    _verifier_admin(authorization)
    try:
        return get_stats_apprenant(user_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

@app.get("/api/stats/correlations")
def route_correlations(authorization: Optional[str] = Header(None)):
    _verifier_admin(authorization)
    return get_matrice_correlations()

@app.get("/api/stats/progression")
def route_progression(granularite: str = "semaine",
                       authorization: Optional[str] = Header(None)):
    _verifier_admin(authorization)
    return get_progression_temporelle(granularite)

# -- Exports stats ---------------------------------------------

@app.get("/api/stats/exporter/json")
def route_export_stats_json(authorization: Optional[str] = Header(None)):
    _verifier_admin(authorization)
    contenu = exporter_stats_json('all')
    return Response(content=contenu, media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="rali_dem_stats.json"'})

@app.get("/api/stats/exporter/csv/{type_stats}")
def route_export_stats_csv(type_stats: str,
                             authorization: Optional[str] = Header(None)):
    _verifier_admin(authorization)
    contenu = exporter_stats_csv(type_stats)
    return Response(content=contenu.encode("utf-8-sig"), media_type="text/csv",
        headers={"Content-Disposition":
                 f'attachment; filename="rali_dem_{type_stats}.csv"'})

@app.get("/api/stats/exporter/spss")
def route_export_stats_spss(authorization: Optional[str] = Header(None)):
    _verifier_admin(authorization)
    try:
        contenu = exporter_stats_spss('reponses')
        return Response(content=contenu,
            media_type="application/octet-stream",
            headers={"Content-Disposition":
                     'attachment; filename="rali_dem_stats.sav"'})
    except ImportError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================
# ROUTES -- EXPERIMENTATION (collecte donnees these)
# =============================================================

@app.post("/api/exp/inscrire")
def route_exp_inscrire(d: InscriptionParticipant):
    """Inscription d'un participant a l'experimentation.
    Accessible sans authentification -- formulaire public."""
    return inscrire_participant(
        d.nom, d.prenom, d.email,
        d.niveau_etudes, d.etablissement,
        d.consentement, d.utilisateur_id
    )

@app.post("/api/exp/session")
def route_exp_creer_session(d: DemandeSessionExp):
    """Cree une session experimentale pour un participant."""
    return creer_session_exp(
        d.participant_id, d.protocole, d.nb_questions
    )

@app.post("/api/exp/reponse")
def route_exp_reponse(d: ReponseExp):
    """Enregistre une reponse avec temps reel et distracteur choisi."""
    return enregistrer_reponse_exp(
        d.session_id, d.participant_id,
        d.numero_question, d.question_data, d.reponse
    )

@app.post("/api/exp/terminer/{session_id}")
def route_exp_terminer(session_id: int):
    """Cloture une session experimentale."""
    return terminer_session_exp(session_id)

@app.get("/api/exp/stats")
def route_exp_stats(authorization: Optional[str] = Header(None)):
    """Statistiques globales de l'experimentation (admin)."""
    _verifier_admin(authorization)
    return get_stats_experimentation()

@app.get("/api/exp/participants")
def route_exp_liste_participants(
    authorization: Optional[str] = Header(None)
):
    """Liste tous les participants avec leurs informations completes."""
    _verifier_admin(authorization)
    from experimentation import _connexion
    conn = _connexion()
    cur  = conn.cursor()
    rows = cur.execute("""
        SELECT
            p.id, p.code_anonyme, p.nom, p.prenom, p.email,
            p.niveau_etudes, p.etablissement, p.date_inscription,
            COUNT(DISTINCT s.id)  as nb_sessions,
            COUNT(DISTINCT r.id)  as nb_reponses,
            AVG(r.est_correct)    as taux_reussite,
            AVG(r.temps_reel_s)   as temps_moyen,
            e.score_global        as score_qualitatif
        FROM exp_participants p
        LEFT JOIN exp_sessions s
            ON s.participant_id = p.id AND s.statut = 'terminee'
        LEFT JOIN exp_reponses r ON r.participant_id = p.id
        LEFT JOIN exp_eval_qualitative e ON e.participant_id = p.id
        GROUP BY p.id
        ORDER BY p.date_inscription DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/exp/participant/{code_anonyme}")
def route_exp_detail_participant(
    code_anonyme: str,
    authorization: Optional[str] = Header(None)
):
    """Detail complet d'un participant : reponses + evaluation."""
    _verifier_admin(authorization)
    from experimentation import _connexion
    conn = _connexion()
    cur  = conn.cursor()

    # Infos participant
    p = cur.execute("""
        SELECT id, code_anonyme, nom, prenom, email,
               niveau_etudes, etablissement, date_inscription
        FROM exp_participants WHERE code_anonyme = ?
    """, (code_anonyme,)).fetchone()

    if not p:
        conn.close()
        raise HTTPException(404, "Participant non trouve")

    pid = p["id"]

    # Reponses par objectif
    reponses = cur.execute("""
        SELECT objectif_code, mode_bloom, niveau_complexite,
               ert_predit_s, temps_reel_s, est_correct,
               distracteur_choisi, reponse_correcte,
               timestamp_debut
        FROM exp_reponses
        WHERE participant_id = ?
        ORDER BY numero_question
    """, (pid,)).fetchall()

    # Evaluation qualitative
    eval_q = cur.execute("""
        SELECT grammaticalite, naturalite, clarte,
               plausibilite_dist, pertinence_obj, alignement_bloom,
               acceptabilite, utilite_apprentissage,
               score_coherence, score_plausibilite,
               score_acceptabilite, score_global, commentaire
        FROM exp_eval_qualitative
        WHERE participant_id = ?
        ORDER BY date_eval DESC LIMIT 1
    """, (pid,)).fetchone()

    conn.close()

    return {
        "participant": dict(p),
        "reponses": [dict(r) for r in reponses],
        "evaluation": dict(eval_q) if eval_q else None,
        "stats": {
            "nb_reponses": len(reponses),
            "nb_correctes": sum(1 for r in reponses if r["est_correct"]),
            "taux_reussite": round(
                sum(1 for r in reponses if r["est_correct"])
                / len(reponses) * 100, 1
            ) if reponses else 0,
            "temps_moyen": round(
                sum(r["temps_reel_s"] for r in reponses)
                / len(reponses), 1
            ) if reponses else 0,
            "ert_moyen": round(
                sum(r["ert_predit_s"] for r in reponses)
                / len(reponses), 1
            ) if reponses else 0,
        }
    }

@app.get("/api/exp/export/ert")
def route_exp_export_ert(authorization: Optional[str] = Header(None)):
    """Export CSV pour validation ERT : temps_reel vs ert_predit."""
    _verifier_admin(authorization)
    contenu = exporter_donnees_ert_csv()
    return Response(
        content=contenu.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition":
                 'attachment; filename="exp_validation_ert.csv"'}
    )


# -- Evaluation qualitative -----------------------------------

class EvalQualitative(BaseModel):
    session_id: int
    participant_id: int
    grammaticalite: int
    naturalite: int
    clarte: int
    plausibilite_dist: int
    pertinence_obj: int
    alignement_bloom: int
    acceptabilite: int
    utilite_apprentissage: int
    commentaire: str = ""

@app.post("/api/exp/evaluation_qualitative")
def route_exp_eval(d: EvalQualitative):
    """Enregistre l'evaluation qualitative finale de l'apprenant."""
    return enregistrer_eval_qualitative(
        d.session_id, d.participant_id,
        d.grammaticalite, d.naturalite, d.clarte,
        d.plausibilite_dist, d.pertinence_obj, d.alignement_bloom,
        d.acceptabilite, d.utilite_apprentissage,
        d.commentaire
    )

@app.get("/api/exp/synthese_qualitative")
def route_exp_synthese(authorization: Optional[str] = Header(None)):
    """Synthese des evaluations qualitatives (admin)."""
    _verifier_admin(authorization)
    return get_synthese_qualitative()

@app.get("/api/exp/export/qualitatif")
def route_exp_export_qual(authorization: Optional[str] = Header(None)):
    """Export CSV des evaluations qualitatives."""
    _verifier_admin(authorization)
    contenu = exporter_eval_qualitative_csv()
    return Response(
        content=contenu.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition":
                 'attachment; filename="exp_evaluation_qualitative.csv"'}
    )

@app.get("/api/exp/export/distracteurs")
def route_exp_export_dist(authorization: Optional[str] = Header(None)):
    """Export CSV pour validation distracteurs."""
    _verifier_admin(authorization)
    contenu = exporter_donnees_distracteurs_csv()
    return Response(
        content=contenu.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition":
                 'attachment; filename="exp_validation_distracteurs.csv"'}
    )

# =============================================================
# LANCEMENT
# =============================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
