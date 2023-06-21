from fastapi import APIRouter

from src.endpoints import lopolis, microsoft, notes, tarot, radio, accounts

api = APIRouter()
api.include_router(lopolis)
api.include_router(microsoft)
api.include_router(notes)
api.include_router(tarot)
api.include_router(radio)
api.include_router(accounts)
