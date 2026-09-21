import streamlit as st
import pandas as pd
from pymongo import MongoClient
import certifi
import time
from bson.objectid import ObjectId

# ─────────────── MongoDB Connection ───────────────
MONGO_URI = "mongodb+srv://satyamguptaishere_db_user:8HlaDWsySl09f3sM@cluster0.shnt6yi.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client.traitor_game

# ─────────────── Page Config ───────────────
st.set_page_config(
    page_title="VICE GRID // Admin",
    page_icon="🌴",
    layout="wide",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Share+Tech+Mono&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Share Tech Mono', monospace !important;
        background-color: #0f0518 !important;
        color: #e5e7eb !important;
    }
    
    .stApp {
        background-image: 
            radial-gradient(circle at top right, #3d165c 0%, transparent 60%),
            linear-gradient(to bottom, #1a0a2a, #0f0518);
        background-attachment: fixed;
    }

    h1, h2, h3, .st-emotion-cache-1629p8f h1, .st-emotion-cache-10trblm h1 {
        font-family: 'Bebas Neue', sans-serif !important;
        color: #ff00ff !important;
        letter-spacing: 0.1em;
        text-shadow: 2px 2px #00ffff;
        transform: skewX(-5deg);
    }
    
    .stMetric { 
        border: 2px solid #ff00ff; 
        border-radius: 4px; 
        padding: 10px;
        background: rgba(26, 10, 42, 0.85);
        box-shadow: 0 0 10px rgba(255, 0, 255, 0.3);
    }
    
    [data-testid="stMetricValue"] {
        color: #ffe600 !important;
        font-size: 2rem !important;
        text-shadow: 0 0 5px rgba(255, 230, 0, 0.5);
    }

    [data-testid="stSidebar"] { 
        background-color: #1a0a2a !important;
        border-right: 2px solid #00ffff;
    }
    
    .stButton>button {
        background-color: transparent !important;
        color: #ffe600 !important;
        border: 2px solid #ff00ff !important;
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 1.2rem !important;
        letter-spacing: 2px;
        transform: skewX(-5deg);
        box-shadow: 0 0 10px rgba(255, 0, 255, 0.4) !important;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #ff00ff !important;
        color: #fff !important;
        border-color: #00ffff !important;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.8) !important;
    }
    
    /* Specific Danger Button Styling */
    .stButton>button[kind="primary"] {
        border-color: #ff0000 !important;
        color: #ff0000 !important;
        box-shadow: 0 0 10px rgba(255, 0, 0, 0.4) !important;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #ff0000 !important;
        color: #fff !important;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────── Sidebar ───────────────
st.sidebar.title("🌴 VICE GRID")
page = st.sidebar.radio("Navigate", [
    "👁️ SEC_NET // GOD'S EYE",
    "🏆 GLOBAL YIELD RANKINGS",
    "📜 AUDIT LOGS",
    "🛠️ COMMAND CENTER (CRUD)"
])

# ─────────────── Helper: Load Teams ───────────────
def load_teams():
    teams = list(db.teams.find())
    for t in teams:
        t["_id"] = str(t["_id"])
    return teams


# ─────────────── God's Eye ───────────────
if page == "👁️ SEC_NET // GOD'S EYE":
    st.title("👁️ SEC_NET // GOD'S EYE")
    
    col_title, col_btn = st.columns([2, 1])
    with col_title:
        st.caption("ELEVATED CLEARANCE: Traitor identities exposed.")
    with col_btn:
        if st.button("🚨 ASSIGN TRAITORS GLOBALLY", type="primary", use_container_width=True):
            import requests
            try:
                res = requests.post("http://localhost:3000/admin/assign_traitors")
                if res.status_code == 200:
                    st.success(res.json().get("message"))
                else:
                    st.error("Failed to assign traitors.")
            except Exception as e:
                st.error(f"Error connecting to backend: {e}")

    teams = load_teams()

    if not teams:
        st.info("No teams registered yet.")
    else:
        for team in teams:
            with st.expander(f"🏷️ {team['team_name']}  |  QR: `{team['qr_code_hash'][:12]}...`", expanded=True):
                col1, col2 = st.columns(2)
                col1.metric("Team Wallet 🤝", team["teammate_wallet"])
                col2.metric("Traitor Wallet 🕵️", team["traitor_wallet"])

                member_rows = []
                for m in team.get("members", []):
                    role = "⚠️ TRAITOR" if m.get("is_traitor") else "🟢 OPERATIVE"
                    member_rows.append({
                        "Name": m["name"],
                        "Role": role,
                        "Course": m.get("course", ""),
                        "Branch": m.get("branch", ""),
                    })

                df = pd.DataFrame(member_rows)

                def highlight_traitor(row):
                    if row["Role"] == "⚠️ TRAITOR":
                        return ["background-color: rgba(255, 0, 255, 0.2); color: #ff00ff; font-weight: bold;"] * len(row)
                    return [""] * len(row)

                st.dataframe(
                    df.style.apply(highlight_traitor, axis=1),
                    use_container_width=True,
                    hide_index=True,
                )

    time.sleep(3)
    st.rerun()


# ─────────────── Leaderboard ───────────────
elif page == "🏆 GLOBAL YIELD RANKINGS":
    st.title("🏆 GLOBAL YIELD RANKINGS")

    teams = load_teams()

    if not teams:
        st.info("No teams registered yet.")
    else:
        for t in teams:
            t["total_score"] = t["teammate_wallet"] + t["traitor_wallet"]

        teams_sorted = sorted(teams, key=lambda x: x["total_score"], reverse=True)

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

        st.subheader("ALL SYNDICATES")
        leaderboard_data = []
        for i, t in enumerate(teams_sorted, 1):
            rank = medals[i - 1] if i <= 3 else f"#{i}"
            tw = t["teammate_wallet"]
            trw = t["traitor_wallet"]
            verdict = "⚠️ TRAITOR" if trw > tw else ("🟢 TEAM" if tw > trw else "⚖️ TIE")
            leaderboard_data.append({
                "Rank": rank,
                "Syndicate": t["team_name"],
                "Team Yield": tw,
                "Traitor Yield": trw,
                "Total Yield": t["total_score"],
                "Verdict": verdict,
            })

        st.dataframe(
            pd.DataFrame(leaderboard_data),
            use_container_width=True,
            hide_index=True,
        )

    time.sleep(3)
    st.rerun()


# ─────────────── Transactions ───────────────
elif page == "📜 AUDIT LOGS":
    st.title("📜 ARBITRATION AUDIT LOGS")

    txns = list(db.transactions.find().sort("_id", -1).limit(50))

    if not txns:
        st.info("No transactions logged yet.")
    else:
        txn_data = []
        for tx in txns:
            team = db.teams.find_one({"qr_code_hash": tx["qr_code_hash"]})
            team_name = team["team_name"] if team else "UNKNOWN"
            txn_data.append({
                "Syndicate": team_name.upper(),
                "Node ID": tx.get("stall_id", "—").upper(),
                "Verdict": tx.get("winner", "—").upper(),
                "Yield": tx.get("points_awarded", 0),
                "Hash Ref": tx["qr_code_hash"][:12].upper() + "...",
            })

        st.dataframe(
            pd.DataFrame(txn_data),
            use_container_width=True,
            hide_index=True,
        )

    time.sleep(3)
    st.rerun()


# ─────────────── Command Center (CRUD) ───────────────
elif page == "🛠️ COMMAND CENTER (CRUD)":
    st.title("🛠️ COMMAND CENTER (CRUD)")
    st.caption("WARNING: Changes made here directly manipulate the database. Auto-refresh is disabled on this page to prevent input loss.")
    
    teams = load_teams()
    
    if not teams:
        st.info("No teams registered yet. Use the Registration Page to add new teams.")
    else:
        # 1. Select Team
        team_options = {t["_id"]: f"{t['team_name']} (Hash: {t['qr_code_hash'][:8]})" for t in teams}
        selected_id = st.selectbox("Select Syndicate to Modify", options=list(team_options.keys()), format_func=lambda x: team_options[x])
        
        target_team = next((t for t in teams if t["_id"] == selected_id), None)
        
        if target_team:
            st.divider()
            
            # --- OVERRIDE SCORES ---
            st.subheader("OVERRIDE YIELDS (SCORES)")
            col_t, col_tr = st.columns(2)
            with col_t:
                new_team_score = st.number_input("Team Wallet", value=target_team["teammate_wallet"], step=100)
            with col_tr:
                new_traitor_score = st.number_input("Traitor Wallet", value=target_team["traitor_wallet"], step=100)
                
            if st.button("SAVE YIELDS"):
                db.teams.update_one(
                    {"_id": ObjectId(selected_id)},
                    {"$set": {"teammate_wallet": new_team_score, "traitor_wallet": new_traitor_score}}
                )
                st.success(f"Yields updated for {target_team['team_name']}!")
                time.sleep(1)
                st.rerun()
                
            st.divider()
            
            # --- EDIT OPERATIVES ---
            st.subheader("EDIT OPERATIVES")
            st.caption("You can edit fields, add new rows, or delete existing rows below.")
            
            df_members = pd.DataFrame(target_team.get("members", []))
            
            # Use data_editor to allow adding/deleting rows
            edited_df = st.data_editor(
                df_members, 
                num_rows="dynamic",
                use_container_width=True,
                key=f"editor_{selected_id}"
            )
            
            if st.button("SAVE OPERATIVES"):
                # Convert DF back to list of dicts
                updated_members = edited_df.to_dict('records')
                # Ensure is_traitor is boolean (pandas sometimes converts to string or object)
                for m in updated_members:
                    m['is_traitor'] = bool(m.get('is_traitor', False))
                    
                db.teams.update_one(
                    {"_id": ObjectId(selected_id)},
                    {"$set": {"members": updated_members}}
                )
                st.success("Operatives data synced to database!")
                time.sleep(1)
                st.rerun()

            st.divider()

            # --- DELETE TEAM ---
            st.subheader("DANGER ZONE")
            with st.expander("🚨 DESTRUCTIVE ACTIONS"):
                st.error("Warning: Deleting a syndicate is permanent and cannot be undone.")
                confirm_name = st.text_input("Type the team name to confirm deletion:")
                
                if st.button("DELETE SYNDICATE", type="primary"):
                    if confirm_name == target_team['team_name']:
                        db.teams.delete_one({"_id": ObjectId(selected_id)})
                        st.success(f"Team '{target_team['team_name']}' has been terminated.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Team name did not match. Deletion aborted.")
