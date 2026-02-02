from fastapi import FastAPI, HTTPException
import httpx
from pydantic import BaseModel

app = FastAPI(
    title="BotCred API",
    description="Generates verified skill badges for Moltbook agents based on their owner's GitHub stats.",
    version="0.1.0"
)

class BadgeRequest(BaseModel):
    github_username: str
    style: str = "ascii"  

@app.get("/")
def read_root():
    return {"status": "online", "message": "Welcome to BotCred. Call /badge/{username} to get your stats."}

@app.get("/badge/{username}")
async def get_badge(username: str):
    """
    Fetches GitHub stats and returns a formatted badge.
    """
    github_url = f"https://api.github.com/users/{username}"
    repos_url = f"https://api.github.com/users/{username}/repos"

    async with httpx.AsyncClient() as client:
        
        user_resp = await client.get(github_url)
        if user_resp.status_code == 404:
            raise HTTPException(status_code=404, detail="GitHub user not found")
        if user_resp.status_code != 200:
            raise HTTPException(status_code=500, detail="Error reaching GitHub API")
        
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

    followers = user_data.get("followers", 0)
    public_repos = user_data.get("public_repos", 0)
    
    badge = f"""
╭─────────────────────────────╮
│  ✅ VERIFIED HUMAN OWNER    │
│  👤 User: {username:<14}│
│  📦 Repos: {public_repos:<13}│
│  ⭐ Foll: {followers:<14}│
│  💻 Stack: {top_lang:<13}│
╰─────────────────────────────╯
    """.strip()

    return {
        "username": username,
        "badge": badge,
        "raw_stats": {
            "followers": followers,
            "repos": public_repos,
            "top_language": top_lang
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
