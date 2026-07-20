from fastapi import APIRouter

router = APIRouter(tags=["website"])


@router.get("/")
async def home():
    return "Website module is working"
