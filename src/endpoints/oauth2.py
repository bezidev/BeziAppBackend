import base64
import json
import os
import time
import uuid
import urllib.parse

from fastapi import APIRouter, Form, Header
from sqlalchemy import select, delete
from starlette import status
from starlette.responses import Response

from src.endpoints import async_session
from src.endpoints.consts import sessions, Session, TEST_USERNAME, OAUTH2_VALID_PERMISSIONS, OAUTH2App, no_emoji_text

oauth2 = APIRouter()


@oauth2.post("/oauth2/auth", status_code=status.HTTP_200_OK)
async def oauth2_login(
        response: Response,
        app_id: str = Form(),
        scope: str = Form(),
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    username = account_session.username

    async with async_session() as session:
        oauth2_app = (await session.execute(select(OAUTH2App).filter_by(id=app_id))).first()
        if oauth2_app is None or oauth2_app[0] is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return {
                "type": "app_not_found",
                "data": "OAUTH2 app hasn't been found in the database",
                "error": "No such app was found in the database.",
            }
        oauth2_app = oauth2_app[0]

        scope = json.loads(scope)
        for request in scope:
            if request not in OAUTH2_VALID_PERMISSIONS:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {
                    "type": "invalid_request",
                    "data": "A scope wasn't found in OAUTH2_VALID_PERMISSIONS.",
                    "error": f"{request} wasn't found in list of valid permissions: {json.dumps(OAUTH2_VALID_PERMISSIONS)}",
                }

        while True:
            login_session = base64.b64encode(os.urandom(64)).decode()
            if sessions.get(login_session) is not None:
                continue
            sessions[login_session] = Session(
                username=username,
                gimsis_password=account_session.gimsis_session.password,
                lopolis_username=account_session.lopolis_username,
                lopolis_password=account_session.lopolis_password,
                oauth2_session=True,
                permissions=scope,
                ringo_url=None,
            )
            break

        f = {"session": login_session}
        query = urllib.parse.urlencode(f)

        return {
            "type": "login_success",
            "data": f"{oauth2_app.redirect_url}?{query}",
            "error": None,
        }


@oauth2.post("/oauth2/apps", status_code=status.HTTP_201_CREATED)
async def new_oauth2_app(
        response: Response,
        redirect_url: str = Form(),
        name: str = Form(),
        description: str = Form(),
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    async with async_session() as session:
        id = str(uuid.uuid4())
        t = time.time()
        app = OAUTH2App(
            id=id,
            redirect_url=redirect_url,
            owner=account_session.username,
            name=no_emoji_text(name),
            description=description,
            verified=False,
            created_on=t,
            modified_on=t,
        )
        session.add(app)
        await session.commit()


@oauth2.get("/oauth2/apps", status_code=status.HTTP_200_OK)
async def get_oauth2_apps(
        response: Response,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    k = []
    async with async_session() as session:
        oauth2_apps = (await session.execute(select(OAUTH2App).filter_by(owner=account_session.username))).all()
        for i in oauth2_apps:
            i = i[0]
            k.append({
                "id": i.id,
                "redirect_url": i.redirect_url,
                "owner": i.owner,
                "name": i.name,
                "description": i.description,
                "verified": i.verified,
            })
    return k


@oauth2.patch("/oauth2/apps/{id}", status_code=status.HTTP_200_OK)
async def patch_oauth2_app(
        response: Response,
        id: str,
        redirect_url: str = Form(),
        name: str = Form(),
        description: str = Form(),
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    async with async_session() as session:
        oauth2_app = (await session.execute(select(OAUTH2App).filter_by(id=id))).first()
        if oauth2_app is None or oauth2_app[0] is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return
        oauth2_app = oauth2_app[0]
        if oauth2_app.owner != account_session.username:
            response.status_code = status.HTTP_403_FORBIDDEN
            return
        oauth2_app.name = no_emoji_text(name)
        oauth2_app.description = description
        oauth2_app.redirect_url = redirect_url
        oauth2_app.modified_on = time.time()
        oauth2_app.verified = False
        await session.commit()


@oauth2.delete("/oauth2/apps/{id}", status_code=status.HTTP_200_OK)
async def delete_oauth2_app(
        response: Response,
        id: str,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        oauth2_app = (await session.execute(select(OAUTH2App).filter_by(id=id))).first()
        if oauth2_app is None or oauth2_app[0] is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return

        oauth2_app = oauth2_app[0]
        if oauth2_app.owner != account_session.username:
            response.status_code = status.HTTP_403_FORBIDDEN
            return

        await session.execute(delete(OAUTH2App).where(OAUTH2App.id == id))
        await session.commit()


@oauth2.get("/oauth2/apps/{id}", status_code=status.HTTP_200_OK)
async def get_oauth2_app(
        response: Response,
        id: str,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    async with async_session() as session:
        oauth2_app = (await session.execute(select(OAUTH2App).filter_by(id=id))).first()
        if oauth2_app is None or oauth2_app[0] is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return
        oauth2_app = oauth2_app[0]
        return {
            "id": oauth2_app.id,
            "redirect_url": oauth2_app.redirect_url,
            "owner": oauth2_app.owner,
            "name": oauth2_app.name,
            "description": oauth2_app.description,
            "verified": oauth2_app.verified,
            "created_on": oauth2_app.created_on,
            "modified_on": oauth2_app.modified_on,
        }
