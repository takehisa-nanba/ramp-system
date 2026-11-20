"""Serve the built RAMP app and its API on a single local origin."""
import json
import os
from pathlib import Path
import secrets

from cryptography.fernet import Fernet


def load_keys(directory):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "keys.json"
    if not path.exists():
        keys = {name: Fernet.generate_key().decode() for name in ("PII_ENCRYPTION_KEY", "FERNET_ENCRYPTION_KEY")}
        keys.update({name: secrets.token_hex(32) for name in ("JWT_SECRET_KEY", "SECRET_KEY")})
        temporary = directory / f".keys-{secrets.token_hex(8)}"
        with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as output:
            json.dump(keys, output)
        try:
            os.link(temporary, path)
        except FileExistsError:
            pass
        finally:
            temporary.unlink()
    os.environ.update(json.loads(path.read_text()))


def main():
    from subprocess import run
    import sys
    load_keys(Path("/var/lib/ramp"))
    from backend.app import create_app
    from flask import jsonify, send_from_directory
    from waitress import serve
    from local_demo.seed import seed_demo

    run([sys.executable, "-m", "flask", "--app", "backend.app:create_app", "db", "upgrade", "-d", "backend/migrations"], check=True)
    app = create_app()
    with app.app_context():
        seed_demo()
    public = Path("/app/public")

    @app.get("/")
    @app.get("/<path:path>")
    def frontend(path=""):
        if path.startswith("api/"):
            return jsonify(error={"message": "APIが見つかりません。"}), 404
        if path and (public / path).is_file():
            return send_from_directory(public, path)
        return send_from_directory(public, "index.html")

    serve(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
