import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from urllib.parse import urlsplit
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl

app = FastAPI(title="Agent-generated URL Shortener", version="1.0.0")
DB_PATH = os.getenv("SHORTENER_DB", "shortener.db")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")

@contextmanager
def db():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()

def init_db():
    with db() as con:
        con.execute("CREATE TABLE IF NOT EXISTS links (code TEXT PRIMARY KEY, url TEXT NOT NULL, created_at TEXT NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS clicks (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL, clicked_at TEXT NOT NULL, FOREIGN KEY(code) REFERENCES links(code))")

class LinkRequest(BaseModel):
    url: HttpUrl

class LinkResponse(BaseModel):
    code: str
    short_url: str
    original_url: str

@app.on_event("startup")
def startup():
    init_db()

@app.post("/api/links", response_model=LinkResponse, status_code=201)
def create_link(body: LinkRequest):
    parsed = urlsplit(str(body.url))
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(422, "Only HTTP(S) URLs allowed")
    with db() as con:
        for _ in range(8):
            code = secrets.token_urlsafe(6)
            try:
                con.execute("INSERT INTO links VALUES (?, ?, ?)", (code, str(body.url), datetime.now(timezone.utc).isoformat()))
                return LinkResponse(code=code, short_url=f"{BASE_URL}/{code}", original_url=str(body.url))
            except sqlite3.IntegrityError:
                continue
    raise HTTPException(503, "Unable to allocate unique code")

@app.get("/api/links/{code}/analytics")
def analytics(code: str):
    with db() as con:
        row = con.execute("SELECT * FROM links WHERE code=?", (code,)).fetchone()
        if row is None:
            raise HTTPException(404, "Unknown short code")
        count = con.execute("SELECT COUNT(*) FROM clicks WHERE code=?", (code,)).fetchone()[0]
        return {"code":code, "original_url":row["url"], "created_at":row["created_at"], "clicks":count}

@app.get("/{code}")
def redirect(code: str):
    with db() as con:
        row = con.execute("SELECT url FROM links WHERE code=?", (code,)).fetchone()
        if row is None:
            raise HTTPException(404, "Unknown short code")
        con.execute("INSERT INTO clicks(code, clicked_at) VALUES (?,?)", (code, datetime.now(timezone.utc).isoformat()))
        return RedirectResponse(row["url"], status_code=307)
