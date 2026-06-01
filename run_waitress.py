from __future__ import annotations

import os
from waitress import serve
from app import app

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    print(f"UroSCC-LS Risk AI is running at http://127.0.0.1:{port}")
    serve(app, host=host, port=port, threads=8)
