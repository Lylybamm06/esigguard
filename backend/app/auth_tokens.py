"""
Émission et vérification des tokens de session (JWT).

Avant cette version, /api/auth/login validait les identifiants mais
n'émettait rien : aucune route de l'API ne vérifiait qui appelait, et le
dashboard laissait accéder à /dashboard, /analyze, /history sans être
connecté. Ce module ajoute une vraie protection par token.
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Header, HTTPException

ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24


def _secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET manquant dans backend/.env (voir backend/.env.example)."
        )
    return secret


def create_access_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def get_current_user(authorization: str = Header(default=None)) -> str:
    """
    Dépendance FastAPI à ajouter sur les routes protégées :
        def route(user: str = Depends(get_current_user)): ...

    Lit l'en-tête "Authorization: Bearer <token>", vérifie le token,
    et renvoie le username. Lève une 401 si absent/invalide/expiré.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentification requise")

    token = authorization.removeprefix("Bearer ").strip()

    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expirée, reconnecte-toi")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide")

    return payload["sub"]
