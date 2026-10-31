from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

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