import sqlite3
import os
import json
import numpy as np
from cryptography.fernet import Fernet
from config import DB_PATH, ENCRYPTION_KEY_PATH


def _get_key():
    """Loads or generates the encryption key."""
    if os.path.exists(ENCRYPTION_KEY_PATH):
        with open(ENCRYPTION_KEY_PATH, "rb") as f:
            return f.read()
    else:
        os.makedirs(os.path.dirname(ENCRYPTION_KEY_PATH), exist_ok=True)
        key = Fernet.generate_key()
        with open(ENCRYPTION_KEY_PATH, "wb") as f:
            f.write(key)
        return key


def _get_cipher():
    return Fernet(_get_key())


def _get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            participant_id TEXT PRIMARY KEY,
            template BLOB NOT NULL
        )
    """)
    conn.commit()
    return conn


def save_template(participant_id, template_vector):
    """
    Encrypts and stores a feature vector template for a participant.
    participant_id: string (e.g. "P001")
    template_vector: numpy array of shape (12,)
    """
    cipher = _get_cipher()
    data = json.dumps(template_vector.tolist()).encode()
    encrypted = cipher.encrypt(data)

    conn = _get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO templates (participant_id, template) VALUES (?, ?)",
        (participant_id, encrypted)
    )
    conn.commit()
    conn.close()
    print(f"[Template] Saved template for {participant_id}")


def load_template(participant_id):
    """
    Loads and decrypts a stored template for a participant.
    Returns numpy array of shape (12,), or None if not found.
    """
    conn = _get_connection()
    row = conn.execute(
        "SELECT template FROM templates WHERE participant_id = ?",
        (participant_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    cipher = _get_cipher()
    decrypted = cipher.decrypt(row[0])
    return np.array(json.loads(decrypted.decode()), dtype=float)


def list_participants():
    """Returns a list of all enrolled participant IDs."""
    conn = _get_connection()
    rows = conn.execute("SELECT participant_id FROM templates").fetchall()
    conn.close()
    return [r[0] for r in rows]


def delete_template(participant_id):
    """Deletes a participant's template — used when participant withdraws."""
    conn = _get_connection()
    conn.execute("DELETE FROM templates WHERE participant_id = ?", (participant_id,))
    conn.commit()
    conn.close()
    print(f"[Template] Deleted template for {participant_id}")
