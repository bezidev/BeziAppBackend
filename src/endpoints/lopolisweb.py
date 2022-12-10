import base64
import json
import os

from fastapi import Header, Form, APIRouter
from lopolis import LoPolisAPI
from fastapi import status
from fastapi.responses import Response

from .consts import sessions, lopolis_sessions


lopolis = APIRouter()


@lopolis.post("/lopolis/login", status_code=status.HTTP_200_OK)
async def lopolis_login(response: Response, username: str = Form(), password: str = Form(), authorization: str = Header()):
    global lopolis_sessions

    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return

    lopolis = LoPolisAPI()
    await lopolis.get_token(username, password)
    session = base64.b64encode(os.urandom(64)).decode()
    lopolis_sessions[authorization] = lopolis

    return {"session": session}


@lopolis.get("/lopolis/meals", status_code=status.HTTP_200_OK)
async def get_meals(response: Response, month: str, year: str, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None or lopolis_sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    lopolis_session = lopolis_sessions[authorization]
    return await lopolis_session.get_menus(year, month)


@lopolis.post("/lopolis/meals", status_code=status.HTTP_200_OK)
async def set_meals(response: Response, month: str, year: str, authorization: str = Header(), lopolis_response: str = Form()):
    if authorization == "" or sessions.get(authorization) is None or lopolis_sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    lopolis_session = lopolis_sessions[authorization]
    # print(lopolis_response)
    return await lopolis_session.set_menus(year, month, json.loads(lopolis_response))


@lopolis.get("/lopolis/checkouts", status_code=status.HTTP_200_OK)
async def get_meals(response: Response, month: str, year: str, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None or lopolis_sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    lopolis_session = lopolis_sessions[authorization]
    return await lopolis_session.get_checkouts(year, month)


@lopolis.post("/lopolis/checkouts", status_code=status.HTTP_200_OK)
async def set_meals(response: Response, month: str, year: str, authorization: str = Header(), lopolis_response: str = Form()):
    if authorization == "" or sessions.get(authorization) is None or lopolis_sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    lopolis_session = lopolis_sessions[authorization]
    return await lopolis_session.set_checkouts(year, month, json.loads(lopolis_response))
