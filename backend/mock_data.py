# -*- coding: utf-8 -*-
"""
Mock data seeder for the Traitor scavenger hunt game.
Inserts 4 teams into MongoDB and simulates transactions to
exercise the leaderboard Top 3 + win-condition logic.

Run: python mock_data.py
"""
import sys
import io

# Fix Windows console encoding for emoji
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pymongo import MongoClient
import uuid
import random
import certifi

MONGO_URI = "mongodb+srv://satyamguptaishere_db_user:8HlaDWsySl09f3sM@cluster0.shnt6yi.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client.traitor_game

# ─────────────── Clear existing data ───────────────
db.teams.delete_many({})
db.transactions.delete_many({})
print("[OK] Cleared existing data.\n")

# ─────────────── Define 4 teams ───────────────
teams = [
    {
        "team_name": "Shadow Foxes",
        "members": [
            {"name": "Arjun", "band_color": "red"},
            {"name": "Priya", "band_color": "yellow"},
            {"name": "Karan", "band_color": "blue"},
            {"name": "Diya", "band_color": "orange"},
        ],
    },
    {
        "team_name": "Neon Vipers",
        "members": [
            {"name": "Sneha", "band_color": "red"},
            {"name": "Rohan", "band_color": "yellow"},
            {"name": "Meera", "band_color": "blue"},
            {"name": "Aditya", "band_color": "orange"},
        ],
    },
    {
        "team_name": "Crimson Wolves",
        "members": [
            {"name": "Vikram", "band_color": "red"},
            {"name": "Ananya", "band_color": "yellow"},
            {"name": "Dev", "band_color": "blue"},
            {"name": "Riya", "band_color": "orange"},
        ],
    },
    {
        "team_name": "Phantom Owls",
        "members": [
            {"name": "Isha", "band_color": "red"},
            {"name": "Sameer", "band_color": "yellow"},
            {"name": "Nisha", "band_color": "blue"},
            {"name": "Kabir", "band_color": "orange"},
        ],
    },
]

# ─────────────── Insert teams ───────────────
inserted_hashes = []

for team_data in teams:
    # Randomly pick one traitor
    traitor_idx = random.randint(0, len(team_data["members"]) - 1)
    members = []
    for i, m in enumerate(team_data["members"]):
        members.append({
            "name": m["name"],
            "band_color": m["band_color"],
            "is_traitor": i == traitor_idx,
        })

    qr_hash = uuid.uuid4().hex
    doc = {
        "team_name": team_data["team_name"],
        "qr_code_hash": qr_hash,
        "teammate_wallet": 0,
        "traitor_wallet": 0,
        "members": members,
    }

    db.teams.insert_one(doc)
    inserted_hashes.append((team_data["team_name"], qr_hash))

    traitor_name = members[traitor_idx]["name"]
    print(f"[+] {team_data['team_name']}  |  QR: {qr_hash[:16]}...  |  Traitor: {traitor_name}")

print()

# ─────────────── Simulate transactions ───────────────
# Designed to produce varied leaderboard positions:
#   Shadow Foxes:   teammate=300, traitor=150  -> Total=450 (Team Wins)     -> Rank 1
#   Neon Vipers:    teammate=100, traitor=225  -> Total=325 (Traitor Wins)  -> Rank 2
#   Crimson Wolves: teammate=150, traitor=150  -> Total=300 (Tie)           -> Rank 3
#   Phantom Owls:   teammate=75,  traitor=75   -> Total=150 (Tie)           -> Rank 4

simulated_scores = [
    # (team_index, stall_id, wallet_field, points)
    (0, "stall_01", "teammate_wallet", 100),
    (0, "stall_02", "teammate_wallet", 100),
    (0, "stall_03", "teammate_wallet", 100),
    (0, "stall_04", "traitor_wallet", 75),
    (0, "stall_05", "traitor_wallet", 75),

    (1, "stall_01", "teammate_wallet", 100),
    (1, "stall_02", "traitor_wallet", 75),
    (1, "stall_03", "traitor_wallet", 75),
    (1, "stall_04", "traitor_wallet", 75),

    (2, "stall_01", "teammate_wallet", 100),
    (2, "stall_02", "teammate_wallet", 50),
    (2, "stall_03", "traitor_wallet", 75),
    (2, "stall_04", "traitor_wallet", 75),

    (3, "stall_01", "teammate_wallet", 75),
    (3, "stall_02", "traitor_wallet", 75),
]

for team_idx, stall_id, wallet_field, points in simulated_scores:
    team_name, qr_hash = inserted_hashes[team_idx]
    winner = "team" if wallet_field == "teammate_wallet" else "traitor"

    db.teams.update_one(
        {"qr_code_hash": qr_hash},
        {"$inc": {wallet_field: points}},
    )

    db.transactions.insert_one({
        "qr_code_hash": qr_hash,
        "stall_id": stall_id,
        "winner": winner,
        "points_awarded": points,
    })

print("[OK] Simulated transactions applied.\n")

# ─────────────── Print summary ───────────────
print("=" * 50)
print("LEADERBOARD PREVIEW")
print("=" * 50)

all_teams = list(db.teams.find().sort("teammate_wallet", -1))
for t in all_teams:
    tw = t["teammate_wallet"]
    trw = t["traitor_wallet"]
    total = tw + trw
    if trw > tw:
        verdict = "Traitor Wins"
    elif tw > trw:
        verdict = "Team Wins"
    else:
        verdict = "Tie"
    print(f"  {t['team_name']:20s}  Team={tw:4d}  Traitor={trw:4d}  Total={total:4d}  -> {verdict}")

print()
print("[OK] Mock data seeded successfully!")
print("   Start FastAPI:   uvicorn main:app --reload --port 8000")
print("   Start Streamlit: streamlit run admin_dash.py")
