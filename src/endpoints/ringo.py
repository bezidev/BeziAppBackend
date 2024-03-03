import datetime
import os
import time

import aiofiles
import bcrypt

from fastapi import APIRouter, Header, Form
from ringoapi import RingoAPI
from sqlalchemy import select
from starlette import status
from starlette.responses import Response

from src.endpoints import async_session
from src.endpoints.consts import User, encrypt, sessions, TEST_USERNAME

ringo = APIRouter()


@ringo.get("/bikes/token", status_code=status.HTTP_200_OK)
async def get_token(response: Response, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session:
        print(f"[ACCOUNT] Denied OAUTH2 session {account_session.username}")
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username.startswith("s."):
        # Starš. Tem zavrnemo dostop do kolesarnice, saj bi ga morali imeti samo dijaki
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    if account_session.ringo_url is None:
        return {
            "token": "NO_TOKEN",
        }

    return {"token": account_session.ringo_url}


@ringo.patch("/bikes/token", status_code=status.HTTP_200_OK)
async def change_ringo_url(response: Response, ringo_url: str = Form(), current_password: str | None = Form(None),
                           authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session:
        print(f"[ACCOUNT] Denied OAUTH2 session {account_session.username}")
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username.startswith("s."):
        # Starš. Tem zavrnemo dostop do kolesarnice, saj bi ga morali imeti samo dijaki
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    if current_password == "" or ringo_url == "":
        print(f"[RINGO] Invalid password {account_session.username}")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            "type": "invalid_data",
            "data": "Invalid data.",
            "session": None,
            "error": "Either current_password or ringo_url is empty.",
        }

    ringo_url = ringo_url.strip()

    # Prevent SSRF
    if ringo_url != "DEFAULT_TOKEN" and not ringo_url.startswith("https://www.ringodoor.com/door/?hash="):
        print(f"[RINGO] SSRF check failed for user {account_session.username} {ringo_url}")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            "type": "invalid_url",
            "data": "Invalid URL.",
            "session": None,
            "error": "SSRF check failed.",
        }

    async with async_session() as session:
        user = (await session.execute(select(User).filter_by(username=account_session.username))).first()
        if user is None or user[0] is None:
            response.status_code = status.HTTP_403_FORBIDDEN
            return {
                "type": "no_such_user",
                "data": "No such user.",
                "session": None,
                "error": "Could not find such a user in the database.",
            }
        user = user[0]

        if ringo_url != "DEFAULT_TOKEN":
            bcrypt_password = bcrypt.hashpw(current_password.encode(), user.salt.encode()).decode()
            if bcrypt_password != user.password:
                print(f"[RINGO] Password mismatch {account_session.username}")
                response.status_code = status.HTTP_403_FORBIDDEN
                return {
                    "type": "password_verification_fail",
                    "data": "Invalid password.",
                    "session": None,
                    "error": "Password mismatch.",
                }

        if ringo_url == "DEFAULT_TOKEN":
            user.ringo_url = "DEFAULT_TOKEN"
            sessions[authorization].ringo_url = "DEFAULT_TOKEN"
        else:
            user.ringo_url = encrypt(ringo_url, current_password).decode()
            sessions[authorization].ringo_url = ringo_url

        await session.commit()

        print(f"[RINGO] Successfully set the URL for {account_session.username}")
        return {
            "type": "change_success",
            "data": "OK",
            "session": None,
            "error": None,
        }


@ringo.post("/bikes/open/{door_id}", status_code=status.HTTP_200_OK)
async def open_door(response: Response, door_id: int, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session:
        print(f"[ACCOUNT] Denied OAUTH2 session {account_session.username}")
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username.startswith("s."):
        # Starš. Tem zavrnemo dostop do kolesarnice, saj bi ga morali imeti samo dijaki
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    url = account_session.ringo_url

    # Če nima izbire, defaultaj na defaultni Ringo URL
    if url is None or url == "DEFAULT_TOKEN":
        async with aiofiles.open("doors.log", "a") as f:
            await f.write(f"[RINGO] Vstop s skupnim ključem s strani {account_session.username} ob {datetime.datetime.now().strftime('%d/%m/%Y, %H:%M:%S')}.\n")
        url = os.environ.get("RINGO_TOKEN")

    r = RingoAPI(url)

    if door_id == 0:
        #r.unlock_door()
        pass
    elif door_id == 1:
        #r.unlock_door()
        pass
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            "type": "invalid_door_id",
            "data": "Invalid door_id.",
            "session": None,
            "error": "door_id must be either 0 or 1.",
        }
