import os
import uuid
import random
import math
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import motor.motor_asyncio
import certifi


# ─────────────────────── Pydantic Models ───────────────────────

class MemberInput(BaseModel):
    name: str
    band_color: str


class RegisterTeamRequest(BaseModel):
    team_name: str
    members: list[MemberInput]


class ScoreTaskRequest(BaseModel):
    qr_code_hash: str
    stall_id: str
    max_points: int
    outcome: Literal["team_won", "traitor_won"]


# ─────────────────────── MongoDB Lifespan ───────────────────────

db_client: motor.motor_asyncio.AsyncIOMotorClient = None
db = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_client, db
    MONGO_URI = "mongodb+srv://satyamguptaishere_db_user:8HlaDWsySl09f3sM@cluster0.shnt6yi.mongodb.net/?appName=Cluster0"
    db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    db = db_client.traitor_game
    # Verify connection
    await db_client.admin.command("ping")
    print("[OK] Connected to MongoDB Atlas - traitor_game")
    yield
    db_client.close()
    print("[--] MongoDB connection closed")


# ─────────────────────── FastAPI App ───────────────────────

app = FastAPI(title="Traitor Scavenger Hunt", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────── Endpoints ───────────────────────

@app.post("/register_team")
async def register_team(req: RegisterTeamRequest):
    if len(req.members) < 2:
        raise HTTPException(status_code=400, detail="A team needs at least 2 members")

    # Randomly select one traitor
    traitor_index = random.randint(0, len(req.members) - 1)

    members = []
    for i, m in enumerate(req.members):
        members.append({
            "name": m.name,
            "band_color": m.band_color,
            "is_traitor": i == traitor_index,
        })

    qr_code_hash = uuid.uuid4().hex

    team_doc = {
        "team_name": req.team_name,
        "qr_code_hash": qr_code_hash,
        "teammate_wallet": 0,
        "traitor_wallet": 0,
        "members": members,
    }

    result = await db.teams.insert_one(team_doc)
    team_doc["_id"] = str(result.inserted_id)

    return {
        "message": "Team registered successfully",
        "team_name": team_doc["team_name"],
        "qr_code_hash": qr_code_hash,
        "members": members,
    }


@app.get("/team/{qr_code_hash}")
async def get_team(qr_code_hash: str):
    team = await db.teams.find_one({"qr_code_hash": qr_code_hash})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Strip is_traitor from member data — coordinators must NOT see this
    safe_members = [
        {"name": m["name"], "band_color": m["band_color"]}
        for m in team["members"]
    ]

    return {
        "team_name": team["team_name"],
        "teammate_wallet": team["teammate_wallet"],
        "traitor_wallet": team["traitor_wallet"],
        "members": safe_members,
    }


@app.post("/score_task")
async def score_task(req: ScoreTaskRequest):
    team = await db.teams.find_one({"qr_code_hash": req.qr_code_hash})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if req.outcome == "team_won":
        points = req.max_points
        wallet_field = "teammate_wallet"
        winner = "team"
    else:
        points = int(math.floor(req.max_points * 0.75))
        wallet_field = "traitor_wallet"
        winner = "traitor"

    # Update the wallet
    await db.teams.update_one(
        {"qr_code_hash": req.qr_code_hash},
        {"$inc": {wallet_field: points}},
    )

    # Log the transaction
    await db.transactions.insert_one({
        "qr_code_hash": req.qr_code_hash,
        "stall_id": req.stall_id,
        "winner": winner,
        "points_awarded": points,
    })

    # Fetch updated balances
    updated = await db.teams.find_one({"qr_code_hash": req.qr_code_hash})

    return {
        "message": f"{winner.title()} scored {points} points!",
        "teammate_wallet": updated["teammate_wallet"],
        "traitor_wallet": updated["traitor_wallet"],
    }


# ─────────────────────── Admin endpoint (God's Eye) ───────────────────────

@app.get("/admin/teams")
async def admin_get_all_teams():
    """Returns ALL team data including is_traitor — for admin use only."""
    teams = []
    async for team in db.teams.find():
        team["_id"] = str(team["_id"])
        teams.append(team)
    return teams


# ─────────────────────── Static Files (must be last) ───────────────────────

os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
