import json
import time
import uuid

from fastapi import APIRouter, Header, Form
from sqlalchemy import select, delete
from starlette import status
from starlette.responses import Response

from src.endpoints import async_session
from src.endpoints.consts import User, sessions, TEST_USERNAME, Palette

palettes = APIRouter()


@palettes.get("/palettes", status_code=status.HTTP_200_OK)
async def get_palettes(response: Response, authorization: str = Header()):
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
        palettes = (await session.execute(select(Palette))).all()
        palettes_json = []
        for palette in palettes:
            palette = palette[0]

            try:
                p = json.loads(palette.palette)
            except:
                p = []

            palettes_json.append({
                "id": palette.id,
                "palette": p,
                "name": palette.name,
                "downloads": palette.downloads,
                "owner": "Anonimni uporabnik BežiApp-a" if palette.is_owner_private else palette.owner,
                "owned": palette.owner == account_session.username,
                "created_on": palette.created_on,
            })

        return palettes_json

@palettes.post("/palettes", status_code=status.HTTP_200_OK)
async def new_palette(response: Response, palette: str = Form(), is_owner_private: bool = Form(), name: str = Form(""), authorization: str = Header()):
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
        d = json.dumps(json.loads(palette))

        p = Palette(
            id=str(uuid.uuid4()),
            palette=d,
            name=name,
            downloads=0,
            owner=account_session.username,
            is_owner_private=is_owner_private,
            created_on=int(time.time()),
        )

        session.add(p)
        await session.commit()

        return "OK"

@palettes.patch("/palettes/set/{id}", status_code=status.HTTP_200_OK)
async def set_palette(response: Response, id: str, authorization: str = Header()):
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
        palette = (await session.execute(select(Palette).filter_by(id=id))).first()
        if palette is None or palette[0] is None:
            response.status_code = status.HTTP_403_FORBIDDEN
            return

        user = (await session.execute(select(User).filter_by(username=account_session.username))).first()
        if user is None or user[0] is None:
            response.status_code = status.HTTP_403_FORBIDDEN
            return

        user = user[0]
        palette = palette[0]

        try:
            p = json.loads(palette.palette)
            user.palette = json.dumps(p)
        except:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return

        palette.downloads += 1

        await session.commit()

        return "OK"


@palettes.delete("/palettes/set/{id}", status_code=status.HTTP_200_OK)
async def delete_palette(response: Response, id: str, authorization: str = Header()):
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
        palette = (await session.execute(select(Palette).filter_by(id=id))).first()
        if palette is None or palette[0] is None:
            response.status_code = status.HTTP_403_FORBIDDEN
            return

        palette = palette[0]

        if palette.owner != account_session.username:
            response.status_code = status.HTTP_403_FORBIDDEN
            return

        await session.execute(delete(Palette).where(Palette.id == id))
        await session.commit()

        return "OK"

@palettes.patch("/palettes/anon/{id}", status_code=status.HTTP_200_OK)
async def delete_palette(response: Response, id: str, authorization: str = Header()):
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
        palette = (await session.execute(select(Palette).filter_by(id=id))).first()
        if palette is None or palette[0] is None:
            response.status_code = status.HTTP_403_FORBIDDEN
            return

        palette = palette[0]

        if palette.owner != account_session.username:
            response.status_code = status.HTTP_403_FORBIDDEN
            return

        palette.is_owner_private = not palette.is_owner_private

        await session.commit()

        return "OK"

