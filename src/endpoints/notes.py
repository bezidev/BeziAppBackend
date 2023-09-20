import os
import uuid

import aiofiles
from fastapi import Header, Form, UploadFile, status, APIRouter
from sqlalchemy import delete, select
from fastapi.responses import FileResponse, Response

from .consts import async_session, Upload, UploadJSON, ALLOWED_EXTENSIONS, TEST_USERNAME, sessions

notes = APIRouter()


@notes.post("/notes/upload", status_code=status.HTTP_201_CREATED)
async def upload_new_note(
        response: Response,
        file: UploadFile,
        description: str = Form(""),
        subject: str = Form(),
        teacher: str = Form(),
        class_name: str = Form(),
        class_year: str = Form(),
        type: str = Form(),
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "notes.write" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    id = str(uuid.uuid4())
    extension = file.filename.split(".")[-1]
    if extension not in ALLOWED_EXTENSIONS:
        return "Extension isn't allowed. Please contact system administrators if you think it's a mistake."
    file_path = f"uploads/{id}.{extension}"
    contents = await file.read()
    async with aiofiles.open(file_path, "wb+") as f:
        await f.write(contents)
    upload = Upload(
        id=id,
        filename=file.filename,
        username=account_session.username,
        description=description,
        filepath=file_path,
        subject=subject,
        teacher=teacher,
        class_name=class_name,
        class_year=class_year,
        pending_moderation=False,
        type=type,
    )
    async with async_session() as session:
        session.add(upload)
        await session.commit()


@notes.get("/notes", status_code=status.HTTP_200_OK)
async def get_notes(response: Response, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "notes.read" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    async with async_session() as session:
        uploads = (await session.execute(select(Upload))).all()
    uploads_json = []
    for i in uploads:
        i = i[0]
        uploads_json.append(UploadJSON(i.id, i.filename, i.description, i.subject, i.teacher,  i.class_name, i.class_year, i.type, i.username == account_session.username))
    return uploads_json


@notes.delete("/notes", status_code=status.HTTP_200_OK)
async def delete_note(response: Response, id: str = Form(), authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "notes.delete" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    async with async_session() as session:
        upload = (await session.execute(select(Upload).filter_by(id=id))).first()
        if upload is None or upload[0] is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return

        upload = upload[0]

        if upload.username != account_session.username:
            response.status_code = status.HTTP_403_FORBIDDEN
            return
        try:
            os.remove(upload.filepath)
        except:
            pass

        await session.execute(delete(Upload).where(Upload.id == id))
        await session.commit()


@notes.get("/notes/get", status_code=status.HTTP_200_OK)
async def get_note(response: Response, id: str, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "notes.read" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    async with async_session() as session:
        upload = (await session.execute(select(Upload).filter_by(id=id))).first()
        if upload is None or upload[0] is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return
        upload = upload[0]
        return FileResponse(upload.filepath)
