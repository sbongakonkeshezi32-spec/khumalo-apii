import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

from app.database.connection import engine, Base
from app.routes.songs import router as songs_router

load_dotenv()

# Initialize SQLite database tables automatically at startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Khumalo Music Platform Gateway Integration",
    description="A complete FastAPI backend enabling Artists to publish tracks, Admins to approve releases, and Public users to stream music hosted on MEGA.",
    version="1.0.0",
    docs_url="/docs",       # Enable Swagger UI
    redoc_url="/redoc"      # Enable ReDoc
)

cors_origins = os.getenv("CORS_ORIGINS", '["*"]')
try:
    import json
    origins = json.loads(cors_origins)
except Exception:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route to serve Cover Images out of uploads folder
upload_directory = "uploads"
os.makedirs(os.path.join(upload_directory, "covers"), exist_ok=True)
app.mount("/static", StaticFiles(directory=upload_directory), name="static")

@app.get("/", response_class=HTMLResponse)
def get_root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Khumalo Music Gateway API Node</title>
        <style>
            body { background-color: #050505; color: #e0e0e0; font-family: system-ui, sans-serif; margin: 0; display: flex; flex-direction: column; min-height: 100vh; }
            header { background: linear-gradient(135deg, #FFD700, #B8860B); color: #000; padding: 40px 20px; text-align: center; }
            h1 { margin: 0; font-size: 2.5rem; font-weight: 900; letter-spacing: 2px; }
            .subtitle { font-size: 1rem; margin-top: 10px; font-weight: bold; }
            .container { max-width: 800px; margin: 40px auto; padding: 0 20px; flex: 1; }
            .card { background-color: #0f0f0f; border: 1px solid rgba(255, 215, 0, 0.15); border-radius: 12px; padding: 30px; box-shadow: 0 8px 16px rgba(0,0,0,0.5); margin-bottom: 30px; text-align: center;}
            h2 { color: #FFD700; border-bottom: 1px solid rgba(255, 215, 0, 0.25); padding-bottom: 10px; margin-top: 0; text-align: left;}
            .btn { display: inline-block; background-color: #FFD700; color: #000; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; margin-top: 15px; }
            .endpoints-list { list-style: none; padding: 0; text-align: left; }
            .endpoint-item { display: flex; align-items: center; padding: 10px 0; border-bottom: 1px dashed rgba(240,240,240,0.1); }
            .method { font-size: 0.8rem; font-weight: bold; padding: 4px 8px; border-radius: 4px; width: 80px; text-align: center; margin-right: 15px; }
            .method.get { background-color: #4CAF50; color: #fff; }
            .method.post { background-color: #2196F3; color: #fff; }
            .path { font-family: monospace; font-size: 1.05rem; color: #FFF; flex: 1; }
            .desc { font-size: 0.9rem; color: #b0b0b0; }
        </style>
    </head>
    <body>
        <header>
            <h1>KM KHUMALO MUSIC</h1>
            <div class="subtitle">BACKEND GATEWAY API CLUSTER</div>
        </header>
        <div class="container">
            <div class="card">
                <h2>Welcome, System Creator!</h2>
                <p>The backend gateway is active and connected securely to your MEGA account <strong>seansibae@gmail.com</strong>.</p>
                <a href="/docs" class="btn">Launch API Swagger Docs</a>
            </div>
        </div>
    </body>
    </html>
    """

app.include_router(songs_router)