from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/health")
async def health():
    return {"status": "ok", "service": "SmartCheckout API", "version": "1.0.0"}

