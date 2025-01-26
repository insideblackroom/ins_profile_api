from fastapi import FastAPI, Request

app = FastAPI()

@app.get("/items/{item_id}")
async def root(item_id: str, request: Request):
    return {"client_host": request.base_url._url, "item_id": item_id}