import os
import time
import uuid

import aiofiles
from fastapi import Header, Form, UploadFile, status, APIRouter
from sqlalchemy import delete, select
from fastapi.responses import FileResponse, Response

from .consts import async_session, Upload, UploadJSON, ALLOWED_EXTENSIONS, TEST_USERNAME, sessions, \
    DeveloperNotification

notifications = APIRouter()


NOTIFICATION_ADMINS = [
    "mitja.severkar"
]

NOTIFICATION_TYPES = [
    "general",
    "gimsis_closed",
    "login",
]


@notifications.post("/developers/notifications", status_code=status.HTTP_201_CREATED)
async def new_notification(
        response: Response,
        name: str = Form(),
        description: str = Form(),
        notification_type: str = Form(),
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "notifications.write" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username not in NOTIFICATION_ADMINS:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if notification_type not in NOTIFICATION_TYPES:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    id = str(uuid.uuid4())
    t = int(time.time())
    upload = DeveloperNotification(
        id=id,
        name=name,
        description=description,
        created_on=t,
        created_by=account_session.username,
        notification_type=notification_type,
    )
    async with async_session() as session:
        session.add(upload)
        await session.commit()


# Public API
@notifications.get("/developers/notifications", status_code=status.HTTP_200_OK)
async def get_notifications():
    async with async_session() as session:
        uploads = (await session.execute(select(DeveloperNotification).order_by(DeveloperNotification.created_on.desc()))).all()
    uploads_json = []
    for i in uploads:
        i = i[0]
        uploads_json.append(
            {
                "id": i.id,
                "name": i.name,
                "description": i.description,
                "created_by": i.created_by,
                "created_on": i.created_on,
                "notification_type": i.notification_type,
            }
        )
    return uploads_json


@notifications.delete("/developers/notification/{id}", status_code=status.HTTP_200_OK)
async def delete_notification(response: Response, id: str, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "notifications.delete" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username not in NOTIFICATION_ADMINS:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    async with async_session() as session:
        upload = (await session.execute(select(DeveloperNotification).filter_by(id=id))).first()
        if upload is None or upload[0] is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return

        await session.execute(delete(DeveloperNotification).where(DeveloperNotification.id == id))
        await session.commit()

