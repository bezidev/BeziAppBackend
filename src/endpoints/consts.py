import os

from gimsisapi import GimSisAPI
from lopolis import LoPolisAPI
from sqlalchemy import Column, String, Boolean, Integer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

MS_OAUTH_ID = os.environ["MS_OAUTH_ID"]
MS_OAUTH_SECRET = os.environ["MS_OAUTH_SECRET"]
SCOPE = "https://graph.microsoft.com/Files.Read.All"

sessions: dict[str, GimSisAPI] = {}
lopolis_sessions: dict[str, LoPolisAPI] = {}

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


class TarotGamePlayer(Base):
    __tablename__ = "tarot_game_player"
    id = Column(String(60), primary_key=True)
    game_id = Column(String(60))
    name = Column(String(100))
    difference = Column(Integer)
    playing = Column(Boolean)


# 0: Tri                      10
# 1: Dva                      20
# 2: Ena                      30
# 3: Pikolo                   35 [Žiga me je zbullyjal, da pikolo ne obstaja, zato do nadaljnjega ni podprt]
# 4: Solo tri                 40
# 5: Solo dva                 50
# 6: Solo ena                 60
# 7: Berač                    70
# 8: Solo brez                80
# 9: Odprti berač             90
# 10: Valat                   500
# 11: Barvni valat            125
# 12: Klop                    [posebna igra]
# 13: Renons                  -70
# 14: Ročni vpis              0
# 15: Ročni vpis z radlcem    0
GAMEMODES = {
    0: 10,
    1: 20,
    2: 30,
    3: 35,
    4: 40,
    5: 50,
    6: 60,
    7: 70,
    8: 80,
    9: 90,
    10: 500,
    11: 125,
    12: 0,
    13: -70,
    14: 0,
    15: 0,
}


class TarotGame(Base):
    __tablename__ = "tarot_game"
    id = Column(String(60), primary_key=True)
    contest_id = Column(String(60))
    gamemode = Column(Integer)
    igra_kontre = Column(Integer)
    trulo_napovedal = Column(String(100))
    trulo_zbral = Column(String(100))
    trula_kontre = Column(Integer)
    kralji_napovedal = Column(String(100))
    kralji_zbral = Column(String(100))
    kralji_kontre = Column(Integer)
    pagat_napovedal = Column(String(100))
    pagat_zbral = Column(String(100))
    pagat_kontre = Column(Integer)
    kralj_napovedal = Column(String(100))
    kralj_zbral = Column(String(100))
    kralj_kontre = Column(Integer)
    valat_napovedal = Column(String(100))
    valat_zbral = Column(String(100))
    valat_kontre = Column(Integer)
    barvni_valat_napovedal = Column(String(100))
    barvni_valat_zbral = Column(String(100))
    izgubil_monda = Column(String(100))

    # Defaulta na v 4
    v_tri = Column(Boolean)
    initializer = Column(String(60))
    played_at = Column(Integer)


class TarotContest(Base):
    __tablename__ = 'tarot_contest'
    id = Column(String(60), primary_key=True)
    contestants = Column(String(1000))
    name = Column(String(50))
    description = Column(String(200))
    is_private = Column(Boolean)
    has_ended = Column(Boolean)

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

