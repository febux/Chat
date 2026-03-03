"""
Public routes configuration.
"""
from typing import Annotated

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse

from src.schemas.users.user_get import User
from src.app.utils.current_user import get_current_user
from src.app.utils.templates import templates

router = APIRouter(tags=["authorization"])


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def redirect_to_auth(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
):
    return RedirectResponse(url="/chats")


@router.get("/auth", response_class=HTMLResponse, summary="Страница авторизации", include_in_schema=False)
async def authorization(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})


@router.get("/chats", response_class=HTMLResponse, summary="Страница чата", include_in_schema=False)
async def get_chats_page(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
):
    context = {
        "request": request,
        "user": current_user,
    }
    return templates.TemplateResponse("chat.html", context)
