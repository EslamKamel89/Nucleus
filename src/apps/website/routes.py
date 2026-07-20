from fastapi import APIRouter, Request

from src.core.jinjia import templates

router = APIRouter(tags=["website"])


@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="website/pages/landing-page.html",
        context={},
    )
