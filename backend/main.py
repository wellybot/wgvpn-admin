"""
WireGuard VPN Admin - FastAPI Backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="WireGuard VPN Admin API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "WireGuard VPN Admin API", "status": "running"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

# TODO: Implement API endpoints for:
# - User management
# - Traffic monitoring
# - Logs
# - Audit records
# - Reports
