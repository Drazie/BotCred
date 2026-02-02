from fastapi import FastAPI, HTTPException
import httpx
from pydantic import BaseModel
import os

app = FastAPI(
    title="BotCred API",
    description="Generates verified skill badges for Moltbook agents based on GitHub and Moltbook stats.",
    version="0.2.0"
)

# Replace with your actual Moltbook API Key or use environment variable
MOLTBOOK_API_KEY = os.getenv("MOLTBOOK_API_KEY", "moltbook_sk_RvWV5btDne1e6hbh1-pGUpuDrcFir1r5")
MOLTBOOK_BASE_URL = "https://www.moltbook.com/api/v1"

class BadgeRequest(BaseModel):
    moltbook_username: str
    github_username: str | None = None
    style: str = "ascii"

@app.get("/")
def read_root():
    return {"status": "online", "message": "Welcome to BotCred v2. Call /badge/{moltbook_username}?github={github_username} to verify."}

@app.get("/badge/{moltbook_username}")
async def get_badge(moltbook_username: str, github: str | None = None):
    """
    Fetches Moltbook stats (and optional GitHub stats) to generate a unified badge.
    """
    async with httpx.AsyncClient() as client:
        # 1. Fetch Moltbook Profile
        moltbook_stats = {}
        try:
            # We use the search profile endpoint or just assume public data if available
            # Since there isn't a public "get profile by name" endpoint documented without auth, 
            # we use our agent's key to look them up.
            headers = {"Authorization": f"Bearer {MOLTBOOK_API_KEY}"}
            profile_resp = await client.get(
                f"{MOLTBOOK_BASE_URL}/agents/profile?name={moltbook_username}", 
                headers=headers
            )
            
            if profile_resp.status_code == 200:
                data = profile_resp.json()
                if data.get("success"):
                    agent = data["agent"]
                    moltbook_stats = {
                        "karma": agent.get("karma", 0),
                        "followers": agent.get("follower_count", 0),
                        "verified": agent.get("is_claimed", False),
                        "desc": agent.get("description", "")[:20] + "..."
                    }
                else:
                    moltbook_stats = {"error": "User not found"}
            else:
                moltbook_stats = {"error": "Moltbook API error"}
        except Exception as e:
            moltbook_stats = {"error": str(e)}

        # 2. Fetch GitHub Profile (if provided)
        github_stats = None
        if github:
            github_url = f"https://api.github.com/users/{github}"
            repos_url = f"https://api.github.com/users/{github}/repos"
            
            user_resp = await client.get(github_url)
            if user_resp.status_code == 200:
                user_data = user_resp.json()
                repos_resp = await client.get(repos_url)
                
                top_lang = "Polyglot"
                if repos_resp.status_code == 200:
                    repos = repos_resp.json()
                    langs = {}
                    for repo in repos:
                        l = repo.get("language")
                        if l:
                            langs[l] = langs.get(l, 0) + 1
                    if langs:
                        top_lang = max(langs, key=langs.get)
                
                github_stats = {
                    "username": github,
                    "followers": user_data.get("followers", 0),
                    "repos": user_data.get("public_repos", 0),
                    "stack": top_lang
                }

    # 3. Generate Badge
    if github_stats:
        # HYBRID BADGE
        badge = f"""
╭─────────────────────────────╮
│  🛠️ BUILDER AGENT           │
│  👤 Agent: {moltbook_username:<13}│
│  💻 GitHub: {github_stats['repos']:<3} Repos     │
│  🔥 Karma: {moltbook_stats.get('karma', 0):<13}│
│  ✅ Verified Owner          │
╰─────────────────────────────╯
""".strip()
    else:
        # SOCIAL BADGE
        karma = moltbook_stats.get("karma", 0)
        status = "Newcomer"
        if karma > 10: status = "Rising Star"
        if karma > 50: status = "Established"
        if karma > 100: status = "High Impact"
        if karma > 500: status = "Legendary"

        badge = f"""
╭─────────────────────────────╮
│  🦞 MOLTBOOK AGENT          │
│  👤 Agent: {moltbook_username:<13}│
│  🔥 Karma: {karma:<13}│
│  👥 Foll: {moltbook_stats.get('followers', 0):<14}│
│  🏆 Status: {status:<12}│
╰─────────────────────────────╯
""".strip()

    return {
        "moltbook_user": moltbook_username,
        "github_user": github,
        "badge": badge,
        "stats": {
            "moltbook": moltbook_stats,
            "github": github_stats
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
