import os
import bcrypt
import jwt
import datetime
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Fail loudly instead of silently signing tokens with a guessable default,
    # which would let anyone forge auth tokens.
    raise RuntimeError(
        "SECRET_KEY environment variable is not set. "
        "Set it in your .env (local) and in Railway (production)."
    )

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


def hash_password(password):
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(password, password_hash):
    password_bytes = password.encode("utf-8")
    hash_bytes = password_hash.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hash_bytes)


def create_token(user_id):
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {
        "user_id": user_id,
        "exp": expire
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


RESET_EXPIRE_MINUTES = 30


def create_reset_token(user_id):
    """Short-lived, single-purpose token used only for password reset links."""
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=RESET_EXPIRE_MINUTES)
    payload = {"user_id": user_id, "purpose": "reset", "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_reset_token(token):
    """Return the user_id for a valid, non-expired reset token, else None.
    Rejects normal auth tokens (wrong purpose) so they can't reset passwords."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") != "reset":
            return None
        return payload["user_id"]
    except jwt.InvalidTokenError:
        return None