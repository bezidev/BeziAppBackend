import copy
import json
import os
import re
import time
import uuid

import aiofiles
from fastapi import Header, Form, status, APIRouter
from sqlalchemy import delete, select
from fastapi.responses import Response

from .consts import async_session, RadioSuggestion, TEST_USERNAME, sessions

radio = APIRouter()


CONFIG = {
    "block_new_radio_suggestions": False,
    "allow_voting": False,
}


async def write_config():
    async with aiofiles.open("config.json", "w+") as f:
        await f.write(json.dumps(CONFIG))
    await get_config()

async def get_config():
    global CONFIG

    if not os.path.exists("config.json"):
        await write_config()
        return
    async with aiofiles.open("config.json", "r") as f:
        CONFIG = json.loads(await f.read())
        print(CONFIG)


RADIO_ADMINS = [
    "mitja.severkar",
    "dora.sega",
]


@radio.post("/radio/suggestions", status_code=status.HTTP_201_CREATED)
async def new_suggestion(
        response: Response,
        description: str = Form(""),
        youtube_id: str = Form(),
        name: str = Form(),
        authorization: str = Header(),
):
    print(youtube_id)
    z = re.search('(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})', youtube_id)
    if z is None:
        yt = youtube_id
    else:
        yt = z[1]
    print(f"[RADIO] New song submitted {yt} {youtube_id}")
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "radio.suggestion.write" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if CONFIG.get("block_new_radio_suggestions") is True:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    id = str(uuid.uuid4())
    suggestion = RadioSuggestion(
        id=id,
        username=account_session.username,
        description=description,
        youtube_id=yt,
        name=name,
        status="WAITING FOR REVIEW",
        reviewed_by="",
        last_status_update=int(time.time()),
        submitted_on=int(time.time()),
        declined_reason="",
        upvotes=[account_session.username],
        downvotes=[],
    )
    async with async_session() as session:
        session.add(suggestion)
        await session.commit()


@radio.get("/radio/suggestions", status_code=status.HTTP_200_OK)
async def get_suggestions(response: Response, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "radio.suggestion.read" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    async with async_session() as session:
        suggestions = (await session.execute(select(RadioSuggestion).order_by(RadioSuggestion.submitted_on.asc()))).all()
    suggestions_json = []

    await get_config()

    waiting = 0
    approved = 0

    waitingTotal = 0
    approvedTotal = 0

    for i in suggestions:
        i = i[0]
        if i.status == "WAITING FOR REVIEW":
            waitingTotal += 1
        elif i.status == "APPROVED":
            approvedTotal += 1

    for i in suggestions:
        i = i[0]

        if CONFIG.get("allow_voting") is not True and account_session.username not in RADIO_ADMINS and i.username != account_session.username and i.status != "WAITING FOR REVIEW":
            continue

        u = i.upvotes
        d = i.downvotes
        ups = 1 if account_session.username in u else (-1 if account_session.username in d else 0)

        t = {
            "id": i.id,
            "youtube_id": i.youtube_id,
            "name": i.name,
            "description": i.description,
            "status": i.status,
            "reviewed_by": i.reviewed_by,
            "last_status_update": i.last_status_update,
            "submitted_on": i.submitted_on,
            "declined_reason": i.declined_reason,
            "can_delete": account_session.username == i.username,
            "upvote_count": len(u) - len(d) if CONFIG.get("allow_voting") else 0,
            "upvote_status": ups if CONFIG.get("allow_voting") else 0,
            "vrsta": "",
        }

        if i.status == "APPROVED" or i.status == "WAITING FOR REVIEW":
            if i.status == "APPROVED":
                approved += 1
                t["vrsta"] = f"{approved}/{approvedTotal}"
            elif i.status == "WAITING FOR REVIEW":
                waiting += 1
                t["vrsta"] = f"{waiting}/{waitingTotal}"

        suggestions_json.append(t)
    return {
        "suggestions": suggestions_json,
        "block_new_radio_suggestions": CONFIG.get("block_new_radio_suggestions"),
        "allow_voting": CONFIG.get("allow_voting"),
        "is_admin": account_session.username in RADIO_ADMINS,
    }


@radio.delete("/radio/suggestions", status_code=status.HTTP_200_OK)
async def delete_suggestion(response: Response, id: str = Form(), authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "radio.suggestion.delete" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    async with async_session() as session:
        suggestion = (await session.execute(select(RadioSuggestion).filter_by(id=id))).first()
        if suggestion is None or suggestion[0] is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return

        suggestion = suggestion[0]

        if suggestion.username != account_session.username:
            response.status_code = status.HTTP_403_FORBIDDEN
            return

        await session.execute(delete(RadioSuggestion).where(RadioSuggestion.id == id))
        await session.commit()


@radio.patch("/radio/suggestions", status_code=status.HTTP_200_OK)
async def change_suggestion_status(
        response: Response,
        id: str = Form(),
        s: str = Form(),
        declined_description: str = Form(),
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "radio.suggestion.status.change" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username not in RADIO_ADMINS:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        suggestion = (await session.execute(select(RadioSuggestion).filter(RadioSuggestion.id == id))).first()
        suggestion = suggestion[0]
        suggestion.declined_reason = declined_description
        suggestion.status = s
        suggestion.last_status_update = int(time.time())
        if s == "WAITING FOR REVIEW":
            suggestion.reviewed_by = ""
        else:
            suggestion.reviewed_by = account_session.username
        await session.commit()


@radio.patch("/radio/suggestions/upvote_downvote", status_code=status.HTTP_200_OK)
async def upvote_downvote_suggestions(
        response: Response,
        id: str = Form(),
        t: str = Form(),
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if CONFIG.get("allow_voting") is not True:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        suggestion = (await session.execute(select(RadioSuggestion).filter(RadioSuggestion.id == id))).first()
        suggestion = suggestion[0]
        if suggestion.status != "WAITING FOR REVIEW":
            response.status_code = status.HTTP_409_CONFLICT
            return
        if t == "upvote":
            u: list = copy.deepcopy(suggestion.downvotes)
            if account_session.username in u:
                u.remove(account_session.username)
                suggestion.downvotes = u

            k: list = copy.deepcopy(suggestion.upvotes)
            if account_session.username in k:
                k.remove(account_session.username)
            else:
                k.append(account_session.username)
            suggestion.upvotes = k
            print(suggestion.upvotes)
        elif t == "downvote":
            u: list = copy.deepcopy(suggestion.upvotes)
            if account_session.username in u:
                u.remove(account_session.username)
                suggestion.upvotes = u

            k: list = copy.deepcopy(suggestion.downvotes)
            if account_session.username in k:
                k.remove(account_session.username)
            else:
                k.append(account_session.username)
            suggestion.downvotes = k
            print(suggestion.downvotes)
        await session.commit()


@radio.patch("/radio/admin/config", status_code=status.HTTP_200_OK)
async def change_config(
        response: Response,
        id: str = Form(),
        authorization: str = Header(),
):
    global CONFIG

    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username not in RADIO_ADMINS:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if not (id == "block_new_radio_suggestions" or id == "allow_voting"):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return

    if CONFIG.get(id) is None:
        CONFIG[id] = False
    CONFIG[id] = not CONFIG[id]
    await write_config()
    return "OK"

