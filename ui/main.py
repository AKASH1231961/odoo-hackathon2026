import os
from pathlib import Path
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).parent
API_URL = os.environ.get("API_URL", "http://localhost:8000")
FORWARD_REQUEST = ("authorization", "content-type", "accept")
FORWARD_RESPONSE = ("content-type", "content-disposition", "x-total-count")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # One shared client, so requests reuse connections to the API
    app.state.api = httpx.AsyncClient(base_url=API_URL, timeout=60)
    yield
    await app.state.api.aclose()


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")

@app.get("/auth-rbac.html", response_class=HTMLResponse)
async def auth_rbac(request: Request):
    return templates.TemplateResponse(request, "auth-rbac.html")

@app.get("/plan-builder.html", response_class=HTMLResponse)
async def plan_builder(request: Request):
    return templates.TemplateResponse(request, "plan-builder.html")

@app.get("/pipeline.html", response_class=HTMLResponse)
async def pipeline(request: Request):
    return templates.TemplateResponse(request, "pipeline.html")

@app.get("/invoicing.html", response_class=HTMLResponse)
async def invoicing(request: Request):
    return templates.TemplateResponse(request, "invoicing.html")

@app.get("/customer-portal.html", response_class=HTMLResponse)
async def customer_portal(request: Request):
    return templates.TemplateResponse(request, "customer-portal.html")

@app.get("/dashboard.html", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")

@app.get("/pricing.html", response_class=HTMLResponse)
async def pricing(request: Request):
    return templates.TemplateResponse(request, "pricing.html")

# Password reset emails link here
@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password(request: Request):
    return templates.TemplateResponse(request, "auth-rbac.html")

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
async def api_proxy(path: str, request: Request):
    headers = {k: v for k, v in request.headers.items() if k in FORWARD_REQUEST}
    try:
        upstream = await request.app.state.api.request(
            request.method, f"/{path}", params=request.query_params,
            headers=headers, content=await request.body(),
        )
    except httpx.HTTPError:
        return JSONResponse({"detail": "The server is not reachable. Try again shortly."}, status_code=502)
    return Response(
        upstream.content, status_code=upstream.status_code,
        headers={k: v for k, v in upstream.headers.items() if k in FORWARD_RESPONSE},
    )
