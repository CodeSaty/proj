import os
import uuid
import random
import math
from contextlib import asynccontextmanager
from typing import Literal, List, Dict, Any

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import motor.motor_asyncio
import certifi
from bson.objectid import ObjectId

# ─────────────────────── Security ───────────────────────

ADMIN_ACCESS_KEY = "PROTOCOL_ZERO_DAY"

async def verify_admin(x_admin_key: str = Header(None)):
    if x_admin_key != ADMIN_ACCESS_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized Access")


# ─────────────────────── Pydantic Models ───────────────────────

class MemberInput(BaseModel):
    name: str
    roll_number: str
    branch: str
    course: str
    study_year: str


class RegisterTeamRequest(BaseModel):
    team_name: str
    members: list[MemberInput]


class ScoreTaskRequest(BaseModel):
    qr_code_hash: str
    stall_id: str
    max_points: int
    outcome: Literal["team_won", "traitor_won"]


class UpdateScoresRequest(BaseModel):
    teammate_wallet: int
    traitor_wallet: int


class UpdateMembersRequest(BaseModel):
    members: List[Dict[str, Any]]


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
    if len(req.members) < 2 or len(req.members) > 4:
        raise HTTPException(status_code=400, detail="A team needs 2 to 4 members")

    members = []
    for m in req.members:
        members.append({
            "name": m.name,
            "roll_number": m.roll_number,
            "branch": m.branch,
            "course": m.course,
            "study_year": m.study_year,
            "is_traitor": False,
        })
        
    traitor_idx = random.randint(0, len(members) - 1)
    members[traitor_idx]["is_traitor"] = True

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

    # Explicitly strip is_traitor so coordinators cannot see who the traitor is
    safe_members = [
        {
            "name": m["name"],
            "roll_number": m.get("roll_number", "N/A"),
            "branch": m.get("branch", "N/A"),
            "course": m.get("course", "N/A"),
            "study_year": m.get("study_year", "N/A"),
        }
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


# ─────────────────────── Admin endpoints (Protected) ───────────────────────

@app.get("/api/admin/stats", dependencies=[Depends(verify_admin)])
async def admin_get_stats():
    """Returns aggregated team stats and transaction logs for the HTML dashboard."""
    teams = []
    async for t in db.teams.find():
        tw = t.get("teammate_wallet", 0)
        trw = t.get("traitor_wallet", 0)
        total_score = tw + trw
        status = "Traitor Leading (Sabotage Active)" if trw > tw else "Team Leading"
        
        teams.append({
            "id": str(t["_id"]),
            "team_name": t.get("team_name", "Unknown"),
            "qr_code_hash": t.get("qr_code_hash", ""),
            "teammate_wallet": tw,
            "traitor_wallet": trw,
            "total_score": total_score,
            "status": status,
            "members": t.get("members", [])
        })

    teams.sort(key=lambda x: x["total_score"], reverse=True)
    
    txns = []
    async for tx in db.transactions.find().sort("_id", -1).limit(20):
        tx["_id"] = str(tx["_id"])
        team = next((t for t in teams if t["qr_code_hash"] == tx.get("qr_code_hash")), None)
        tx["team_name"] = team["team_name"] if team else "Unknown"
        txns.append(tx)
        
    return {
        "teams": teams,
        "transactions": txns,
        "total_teams": len(teams),
        "total_points": sum(t["total_score"] for t in teams),
        "active_traitor_wins": sum(1 for t in teams if t["traitor_wallet"] > t["teammate_wallet"])
    }


@app.post("/api/admin/assign_traitors", dependencies=[Depends(verify_admin)])
async def admin_assign_traitors():
    """Assigns exactly one traitor per team randomly."""
    teams = []
    async for t in db.teams.find():
        teams.append(t)
    
    updated_count = 0
    for team in teams:
        members = team.get("members", [])
        if not members:
            continue
            
        for m in members:
            m["is_traitor"] = False
            
        traitor_idx = random.randint(0, len(members) - 1)
        members[traitor_idx]["is_traitor"] = True
        
        await db.teams.update_one(
            {"_id": team["_id"]},
            {"$set": {"members": members}}
        )
        updated_count += 1
        
    return {"message": f"Assigned traitors for {updated_count} teams."}


@app.post("/api/admin/update_scores/{team_id}", dependencies=[Depends(verify_admin)])
async def admin_update_scores(team_id: str, req: UpdateScoresRequest):
    """Override a team's scores."""
    result = await db.teams.update_one(
        {"_id": ObjectId(team_id)},
        {"$set": {"teammate_wallet": req.teammate_wallet, "traitor_wallet": req.traitor_wallet}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Team not found")
    return {"message": "Yields successfully updated."}


@app.post("/api/admin/update_members/{team_id}", dependencies=[Depends(verify_admin)])
async def admin_update_members(team_id: str, req: UpdateMembersRequest):
    """Override a team's operatives."""
    # Ensure is_traitor is boolean
    clean_members = []
    for m in req.members:
        m["is_traitor"] = bool(m.get("is_traitor", False))
        clean_members.append(m)
        
    result = await db.teams.update_one(
        {"_id": ObjectId(team_id)},
        {"$set": {"members": clean_members}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Team not found")
    return {"message": "Operatives successfully updated."}


@app.post("/api/admin/delete_team/{team_id}", dependencies=[Depends(verify_admin)])
async def admin_delete_team(team_id: str):
    """Permanently delete a team."""
    result = await db.teams.delete_one({"_id": ObjectId(team_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Team not found")
    return {"message": "Syndicate terminated permanently."}


# ─────────────────────── Static Files (must be last) ───────────────────────

os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
