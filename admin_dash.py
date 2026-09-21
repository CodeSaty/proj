import streamlit as st
import pandas as pd
from pymongo import MongoClient
import certifi
import time

# ─────────────── MongoDB Connection ───────────────
MONGO_URI = "mongodb+srv://satyamguptaishere_db_user:8HlaDWsySl09f3sM@cluster0.shnt6yi.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client.traitor_game

# ─────────────── Page Config ───────────────
st.set_page_config(
    page_title="Traitor Hunt — Admin",
    page_icon="🕵️",
    layout="wide",
)

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .stMetric { border-radius: 12px; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #0a0a0f, #1a1a2e); }
</style>
""", unsafe_allow_html=True)

# ─────────────── Sidebar ───────────────
st.sidebar.title("🕵️ Traitor Hunt")
page = st.sidebar.radio("Navigate", [
    "👁️ God's Eye",
    "🏆 Leaderboard",
    "📜 Transactions",
])

# ─────────────── Helper: Load Teams ───────────────
def load_teams():
    teams = list(db.teams.find())
    for t in teams:
        t["_id"] = str(t["_id"])
    return teams


# ─────────────── God's Eye ───────────────
if page == "👁️ God's Eye":
    st.title("👁️ God's Eye — All Teams & Traitors")
    st.caption("This view reveals the traitor identity in each team.")

    teams = load_teams()

    if not teams:
        st.info("No teams registered yet. Run `mock_data.py` to seed some.")
    else:
        for team in teams:
            with st.expander(f"🏷️ {team['team_name']}  |  QR: `{team['qr_code_hash'][:12]}...`", expanded=True):
                col1, col2 = st.columns(2)
                col1.metric("Team Wallet 🤝", team["teammate_wallet"])
                col2.metric("Traitor Wallet 🕵️", team["traitor_wallet"])

                # Members table
                member_rows = []
                for m in team.get("members", []):
                    role = "🔴 TRAITOR" if m.get("is_traitor") else "🟢 Teammate"
                    member_rows.append({
                        "Name": m["name"],
                        "Band Color": m["band_color"],
                        "Role": role,
                    })

                df = pd.DataFrame(member_rows)

                # Highlight traitor rows
                def highlight_traitor(row):
                    if row["Role"] == "🔴 TRAITOR":
                        return ["background-color: rgba(255, 23, 68, 0.15); color: #ff1744; font-weight: bold"] * len(row)
                    return [""] * len(row)

                st.dataframe(
                    df.style.apply(highlight_traitor, axis=1),
                    use_container_width=True,
                    hide_index=True,
                )

    # Auto-refresh
    time.sleep(3)
    st.rerun()


# ─────────────── Leaderboard ───────────────
elif page == "🏆 Leaderboard":
    st.title("🏆 Live Leaderboard")

    teams = load_teams()

    if not teams:
        st.info("No teams registered yet.")
    else:
        # Calculate total scores and sort
        for t in teams:
            t["total_score"] = t["teammate_wallet"] + t["traitor_wallet"]

        teams_sorted = sorted(teams, key=lambda x: x["total_score"], reverse=True)

        # Top 3 podium
        st.subheader("🥇 Top 3 Teams")
        medals = ["🥇", "🥈", "🥉"]

        top3 = teams_sorted[:3]
        if top3:
            cols = st.columns(len(top3))
            for i, team in enumerate(top3):
                with cols[i]:
                    st.markdown(f"### {medals[i]} {team['team_name']}")
                    st.metric("Total Score", team["total_score"])

                    tw = team["teammate_wallet"]
                    trw = team["traitor_wallet"]

                    if trw > tw:
                        st.error("🕵️ **Traitor Wins!**")
                        st.caption(f"Traitor: {trw} pts  vs  Team: {tw} pts")
                    elif tw > trw:
                        st.success("🤝 **Team Wins!**")
                        st.caption(f"Team: {tw} pts  vs  Traitor: {trw} pts")
                    else:
                        st.warning("⚖️ **It's a Tie!**")
                        st.caption(f"Both wallets: {tw} pts")

        st.divider()

        # Full leaderboard table
        st.subheader("Full Rankings")
        leaderboard_data = []
        for i, t in enumerate(teams_sorted, 1):
            rank = medals[i - 1] if i <= 3 else f"#{i}"
            tw = t["teammate_wallet"]
            trw = t["traitor_wallet"]
            verdict = "🕵️ Traitor" if trw > tw else ("🤝 Team" if tw > trw else "⚖️ Tie")
            leaderboard_data.append({
                "Rank": rank,
                "Team": t["team_name"],
                "Team Wallet": tw,
                "Traitor Wallet": trw,
                "Total Score": t["total_score"],
                "Winner": verdict,
            })

        st.dataframe(
            pd.DataFrame(leaderboard_data),
            use_container_width=True,
            hide_index=True,
        )

    # Auto-refresh
    time.sleep(3)
    st.rerun()


# ─────────────── Transactions ───────────────
elif page == "📜 Transactions":
    st.title("📜 Transaction Log")

    txns = list(db.transactions.find().sort("_id", -1).limit(50))

    if not txns:
        st.info("No transactions logged yet.")
    else:
        txn_data = []
        for tx in txns:
            # Look up team name
            team = db.teams.find_one({"qr_code_hash": tx["qr_code_hash"]})
            team_name = team["team_name"] if team else "Unknown"
            txn_data.append({
                "Team": team_name,
                "Stall": tx.get("stall_id", "—"),
                "Winner": tx.get("winner", "—").title(),
                "Points": tx.get("points_awarded", 0),
                "QR Hash": tx["qr_code_hash"][:12] + "...",
            })

        st.dataframe(
            pd.DataFrame(txn_data),
            use_container_width=True,
            hide_index=True,
        )

    # Auto-refresh
    time.sleep(3)
    st.rerun()
