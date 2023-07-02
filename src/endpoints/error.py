import uuid

from fastapi import APIRouter, Form
from starlette import status
from starlette.responses import Response

from src.endpoints import async_session
from src.endpoints.consts import ErrorReport

error_handler = APIRouter()

@error_handler.post("/report/error", status_code=status.HTTP_201_CREATED)
async def submit_report(
        message: str = Form(),
        source: str = Form(),
        line: int = Form(),
        col: int = Form(),
        error: str = Form(),
        username: str = Form(),
        password: bool = Form(),
        session: str = Form(),
):
    id = str(uuid.uuid4())

    report = ErrorReport(
        id=id,
        message=message,
        source=source,
        line=line,
        column=col,
        error=error,
        username=username,
        password=password,
        session=session,
    )

    async with async_session() as session:
        session.add(report)
        await session.commit()

    return f"Hvala za prijavo napake. Vaš enolični identifikator napake je {id}."
