from fastapi import FastAPI

app = FastAPI(
    title="Multimodal Attendance & Engagement Agent"
)

@app.get("/")
def home():
    return {
        "message": "Attendance Agent Backend is Running!"
    }

@app.get("/health")
def health():
    return {"status": "OK"}