from datetime import datetime

import bcrypt
from fastapi import APIRouter, HTTPException

from .auth_tokens import create_access_token
from .db import get_db
from .models import UserCreate, UserLogin

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register_user(user: UserCreate):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE email=? OR username=?",
        (user.email, user.username),
    )
    existing = cursor.fetchone()

    if existing:
        db.close()
        raise HTTPException(status_code=400, detail="Utilisateur déjà existant")

    hashed = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()

    cursor.execute(
        """
        INSERT INTO users (username, email, password_hash, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (user.username, user.email, hashed, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    db.commit()
    db.close()

    return {"message": "Utilisateur créé"}


@router.post("/login")
def login_user(credentials: UserLogin):
    db = get_db()
    cursor = db.cursor()

    # On accepte username OU email dans le champ "username" côté front.
    cursor.execute(
        "SELECT * FROM users WHERE username=? OR email=?",
        (credentials.username, credentials.username),
    )
    user = cursor.fetchone()

    # Message générique volontairement identique dans les deux cas
    # (ne pas révéler si c'est le login ou le mot de passe qui est faux).
    invalid = HTTPException(status_code=401, detail="Identifiants invalides")

    if not user:
        db.close()
        raise invalid

    if not bcrypt.checkpw(credentials.password.encode(), user["password_hash"].encode()):
        db.close()
        raise invalid

    db.close()

    token = create_access_token(user["username"])

    return {
        "message": "Connexion réussie",
        "username": user["username"],
        "email": user["email"],
        "access_token": token,
        "token_type": "bearer",
    }
