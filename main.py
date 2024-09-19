# main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import httpx

app = FastAPI()

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8000", "http://127.0.0.1", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

NEWS_API_ENDPOINT = "https://eventregistry.org/api/v1/article/getArticles"
API_KEY = "88c189af-3096-48b4-b989-6dfd40076cfe"

class NewsRequest(BaseModel):
    keyword: str
    location: Optional[str] = None
    jobs_filter: bool = False
    page: int = 1
    count: int = 10

@app.post("/api/news")
async def get_news(req: NewsRequest):
    news_api_req = {
        "action": "getArticles",
        "keyword": req.keyword,
        "ignoreSourceGroupUri": "paywall/paywalled_sources",
        "articlesPage": req.page,
        "articlesCount": req.count,
        "articlesSortBy": "date",
        "articlesSortByAsc": False,
        "dataType": ["news", "pr"],
        "forceMaxDataTimeWindow": 31,
        "resultType": "articles",
        "apiKey": API_KEY,
    }
    
    if req.location:
        news_api_req["sourceLocationUri"] = [f"http://en.wikipedia.org/wiki/{req.location}"]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(NEWS_API_ENDPOINT, json=news_api_req)
            response.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request to news API timed out")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=f"Error from news API: {exc.response.text}")
    except httpx.RequestError as exc:
        raise HTTPException(status_code=500, detail=f"An error occurred while requesting news: {str(exc)}")

    result = response.json()

    if req.jobs_filter:
        articles = result.get("articles", {}).get("results", [])
        job_articles = [
            article for article in articles
            if is_job_related(article)
        ]
        result["articles"]["results"] = job_articles

    return result

def is_job_related(article):
    title = article.get("title", "").lower()
    return "job" in title or "career" in title or "employment" in title

@app.get("/")
async def read_root():
    return {"message": "Welcome to the News API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)