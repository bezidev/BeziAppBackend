import base64
import json
import os

from fastapi import Header, Form, APIRouter
from lopolis import LoPolisAPI
from fastapi import status
from fastapi.responses import Response

from .consts import TEST_USERNAME, sessions

lopolis = APIRouter()


@lopolis.get("/lopolis/meals", status_code=status.HTTP_200_OK)
async def get_meals(response: Response, month: str, year: str, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "lopolis.meals.read" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    try:
        menus = await account_session.lopolis_session.get_menus(year, month)
    except:
        try:
            await account_session.login()
            menus = await account_session.lopolis_session.get_menus(year, month)
        except Exception as e:
            response.status_code = status.HTTP_403_FORBIDDEN
            return {
                "error": e,
                "data": "Not authorized using Lo.Polis",
            }

    return menus


@lopolis.post("/lopolis/meals", status_code=status.HTTP_200_OK)
async def set_meals(response: Response, month: str, year: str, authorization: str = Header(), lopolis_response: str = Form()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "lopolis.meals.write" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    try:
        menus = await account_session.lopolis_session.set_menus(year, month, json.loads(lopolis_response))
    except:
        try:
            await account_session.login()
            menus = await account_session.lopolis_session.set_menus(year, month, json.loads(lopolis_response))
        except Exception as e:
            response.status_code = status.HTTP_403_FORBIDDEN
            return {
                "error": e,
                "data": "Not authorized using Lo.Polis",
            }

    return menus


@lopolis.get("/lopolis/checkouts", status_code=status.HTTP_200_OK)
async def get_checkouts(response: Response, month: str, year: str, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "lopolis.checkouts.read" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    try:
        checkouts = await account_session.lopolis_session.get_checkouts(year, month)
    except:
        try:
            await account_session.login()
            checkouts = await account_session.lopolis_session.get_checkouts(year, month)
        except Exception as e:
            response.status_code = status.HTTP_403_FORBIDDEN
            return {
                "error": e,
                "data": "Not authorized using Lo.Polis",
            }

    return checkouts


@lopolis.post("/lopolis/checkouts", status_code=status.HTTP_200_OK)
async def set_checkouts(response: Response, month: str, year: str, authorization: str = Header(), lopolis_response: str = Form()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "lopolis.checkouts.write" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    try:
        checkouts = await account_session.lopolis_session.set_checkouts(year, month, json.loads(lopolis_response))
    except:
        try:
            await account_session.login()
            checkouts = await account_session.lopolis_session.set_checkouts(year, month, json.loads(lopolis_response))
        except Exception as e:
            response.status_code = status.HTTP_403_FORBIDDEN
            return {
                "error": e,
                "data": "Not authorized using Lo.Polis",
            }

    return checkouts
