# main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def create_app() -> FastAPI:
    app = FastAPI()

    # Povolený origin pro FE (můžeš přepsat env proměnnou ALLOWED_ORIGIN)
    allowed_origin = os.getenv("ALLOWED_ORIGIN", "https://green-david-app.onrender.com")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[allowed_origin],
        allow_credentials=True,          # kvůli cookies
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routry
    from app.routes import auth
    app.include_router(auth.router)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app

# ASGI entry point (Render/Gunicorn/uvicorn)
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
