import hashlib
from werkzeug.security import generate_password_hash
from sqlalchemy import create_engine, text

# === Configure your database connection ===
# Replace with your actual DB URL (Postgres example):
DATABASE_URL = "postgresql+psycopg2://postgres:or9T#u-x5PZo--@localhost:5432/gennis"

engine = create_engine(DATABASE_URL)


def is_sha256_hash(value: str) -> bool:
    """Check if value looks like a raw sha256 hash."""
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())


def migrate_passwords():
    with engine.begin() as conn:
        # Fetch all users
        users = conn.execute(text("SELECT id, password FROM users")).fetchall()
        print(users)
        for user_id, password in users:
            print(user_id)
            if password and is_sha256_hash(password):
                print(f"[+] Migrating user {user_id}")

                # We can't recover original plain password, only re-hash when user logs in.
                # So here we wrap sha256 hash inside pbkdf2 (not ideal).
                new_hash = generate_password_hash(password, method="pbkdf2:sha256")

                conn.execute(
                    text("UPDATE users SET password = :p WHERE id = :uid"),
                    {"p": new_hash, "uid": user_id}
                )

        print("✅ Migration complete!")


if __name__ == "__main__":
    migrate_passwords()
