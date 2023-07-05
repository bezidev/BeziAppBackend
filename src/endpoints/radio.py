import time
import uuid

from fastapi import Header, Form, status, APIRouter
from sqlalchemy import delete, select
from fastapi.responses import Response

from .consts import async_session, RadioSuggestion, TEST_USERNAME, sessions

radio = APIRouter()


RADIO_ADMINS = [
    "mitja.severkar",
]


@radio.post("/radio/suggestions", status_code=status.HTTP_201_CREATED)
async def new_suggestion(
        response: Response,
        description: str = Form(),
        youtube_id: str = Form(),
        name: str = Form(),
        authorization: str = Header(),
):
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
    id = str(uuid.uuid4())
    suggestion = RadioSuggestion(
        id=id,
        username=account_session.username,
        description=description,
        youtube_id=youtube_id,
        name=name,
        status="WAITING FOR REVIEW",
        reviewed_by="",
        last_status_update=int(time.time()),
        submitted_on=int(time.time()),
        declined_reason="",
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
        suggestions = (await session.execute(select(RadioSuggestion))).all()
    suggestions_json = []

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

        if account_session.username not in RADIO_ADMINS and i.username != account_session.username:
            continue

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
    return suggestions_json


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
