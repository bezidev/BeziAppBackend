import os

from sqlalchemy import Column, String, Boolean, Integer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

MS_OAUTH_ID = os.environ["MS_OAUTH_ID"]
MS_OAUTH_SECRET = os.environ["MS_OAUTH_SECRET"]
SCOPE = "https://graph.microsoft.com/Files.Read.All"

ALLOWED_EXTENSIONS = [
    "pdf",  # Portable Document Format
    "pptx",  # PowerPoint format
    "ppt",  # Old PowerPoint document format
    "md",  # Markdown & Mayura Draw (*cough* pls no)
    "doc",
    "docx",
    "xls",
    "xlsx",
    "txt",
    "png",
    "jpg",
    "jpeg",
    "bmp",
    "gif",
    "svg",
    "webm",  # Only movie format allowed, as it's very small
    "odt",  # LibreOffice Writer
    "ods",  # LibreOffice Calc
    "odp",  # LibreOffice Impress
    "odg",  # LibreOffice Draw
    "odf",  # LibreOffice Math
]

DATABASE_USER = os.environ["POSTGRES_USER"]
DATABASE_PASSWORD = os.environ["POSTGRES_PASSWORD"]
DATABASE = os.environ["POSTGRES"]
DATABASE_CONNECTION = f"postgresql+asyncpg://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE}/BeziAppDB"

engine = create_async_engine(DATABASE_CONNECTION)
async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

Base = declarative_base()


class Upload(Base):
    __tablename__ = 'upload'
    id = Column(String(60), primary_key=True)
    filename = Column(String(100), unique=True)
    username = Column(String(60))
    description = Column(String(200))
    filepath = Column(String(150))
    subject = Column(String(60))
    teacher = Column(String(60))
    class_name = Column(String(60))
    class_year = Column(String(12))
    pending_moderation = Column(Boolean)
    type = Column(String(30))


class UploadJSON:
    def __init__(self, id: str, filename: str, description: str, subject: str, teacher: str, class_name: str, class_year: str, type: str,
                 uploaded_by_me: bool):
        self.id = id
        self.filename = filename
        self.description = description
        self.subject = subject
        self.teacher = teacher
        self.class_name = class_name
        self.class_year = class_year
        self.type = type
        self.uploaded_by_me = uploaded_by_me
