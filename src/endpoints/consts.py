import os
from typing import List

import emoji
from gimsisapi import GimSisAPI
from lopolis import LoPolisAPI
from sqlalchemy import Column, String, Boolean, Integer, Float
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

MS_OAUTH_ID = os.environ["MS_OAUTH_ID"]
MS_OAUTH_SECRET = os.environ["MS_OAUTH_SECRET"]
SCOPE = "https://graph.microsoft.com/Files.Read.All https://graph.microsoft.com/Sites.Read.All"

def no_emoji_text(text):
    return emoji.replace_emoji(text, replace='')

OAUTH2_VALID_PERMISSIONS = [
    "gimsis.timetable",
    "gimsis.absences",
    "gimsis.gradings",
    "gimsis.grades",
    "gimsis.user.read.usernameemail",
    "gimsis.user.read.namesurname",
    "gimsis.user.read.sex",
    "gimsis.user.read.role",
    "sharepoint.notifications.read",
    "sharepoint.notifications.write",
    "lopolis.meals.read",
    "lopolis.meals.write",
    "lopolis.checkouts.read",
    "lopolis.checkouts.write",
    "notes.read",
    "notes.delete",
    "notes.write",
    "radio.suggestion.read",
    "radio.suggestion.write",
    "radio.suggestion.delete",
    "radio.suggestion.status.change",
    "tarot.read",
    "tarot.game.write",
    "tarot.game.delete",
    "tarot.contests.write",
    "tarot.contests.delete",
]

class Session:
    def __init__(
            self,
            username: str,
            gimsis_password: str,
            lopolis_username: str | None,
            lopolis_password: str | None,
            oauth2_session: bool = False,
            permissions: List[str] | None = None,
    ):
        if permissions is None:
            permissions = []
        self.username = username
        self.lopolis_session: None | LoPolisAPI = None
        self.lopolis_username = lopolis_username
        self.lopolis_password = lopolis_password
        self.gimsis_session = GimSisAPI(username, gimsis_password)
        self.oauth2_session = oauth2_session
        self.permissions = permissions

    async def login(self):
        try:
            await self.gimsis_session.login()
        except Exception as e:
            print(f"[GIMSIS LOGIN] Failed: {e}")
            pass
        if self.lopolis_username is None or self.lopolis_password is None:
            return
        self.lopolis_session = LoPolisAPI()
        await self.lopolis_session.get_token(self.lopolis_username, self.lopolis_password)


sessions: dict[str, Session] = {}
gimsis_sessions: dict[str, GimSisAPI] = {}
lopolis_sessions: dict[str, LoPolisAPI] = {}

import base64
import hashlib
from Crypto import Random
from Crypto.Cipher import AES

BLOCK_SIZE = AES.block_size

def encrypt_key(password: str) -> bytes:
    return hashlib.sha256(password.encode()).digest()

def encrypt(raw, password):
    raw = _pad(raw)
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(encrypt_key(password), AES.MODE_CBC, iv)
    return base64.b64encode(iv + cipher.encrypt(raw.encode()))

def decrypt(enc, password):
    enc = base64.b64decode(enc)
    iv = enc[:AES.block_size]
    cipher = AES.new(encrypt_key(password), AES.MODE_CBC, iv)
    return _unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

def _pad(s):
    return s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(BLOCK_SIZE - len(s) % BLOCK_SIZE)

def _unpad(s):
    return s[:-ord(s[len(s)-1:])]


TEST_USERNAME = "test"
TEST_PASSWORD = "test"

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


class RadioSuggestion(Base):
    __tablename__ = 'suggestion'
    id = Column(String(60), primary_key=True)
    youtube_id = Column(String(20))
    username = Column(String(60))
    name = Column(String(100))
    description = Column(String(1000))
    status = Column(String(100))
    reviewed_by = Column(String(60))
    last_status_update = Column(Integer)
    submitted_on = Column(Integer)
    declined_reason = Column(String(1000))


class TarotGamePlayer(Base):
    __tablename__ = "tarot_game_player"
    id = Column(String(60), primary_key=True)
    game_id = Column(String(60))
    name = Column(String(100))
    difference = Column(Integer)
    playing = Column(Boolean)


class ErrorReport(Base):
    __tablename__ = "error_reports"
    id = Column(String(60), primary_key=True)
    message = Column(String(10_000))
    source = Column(String(10_000))
    line = Column(Integer)
    column = Column(Integer)
    error = Column(String(100_000))
    username = Column(String(1_000))
    password = Column(Boolean)
    session = Column(String(500))


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


class SharepointNotification(Base):
    __tablename__ = 'sharepoint_notification'
    id = Column(Integer, primary_key=True)
    name = Column(String(1000))
    description = Column(String(50_000))
    created_on = Column(Integer)
    modified_on = Column(Integer)
    modified_by = Column(String(1000))
    created_by = Column(String(1000))
    seen_by = Column(String(50_000))
    expires_on = Column(Integer)
    has_attachments = Column(Boolean)


class User(Base):
    __tablename__ = 'user'
    username = Column(String(1000), primary_key=True, unique=True)
    password = Column(String(1000))
    salt = Column(String(1000))
    gimsis_password = Column(String(1000))
    lopolis_username = Column(String(1000))
    lopolis_password = Column(String(1000))


class OAUTH2App(Base):
    __tablename__ = 'oauth2_apps'
    id = Column(String(60), primary_key=True)
    redirect_url = Column(String(200), unique=True)
    owner = Column(String(200))
    name = Column(String(100))
    description = Column(String(200))
    verified = Column(Boolean)
    created_on = Column(Float)
    modified_on = Column(Float)


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

