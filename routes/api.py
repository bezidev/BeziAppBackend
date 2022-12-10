from fastapi import APIRouter

from src.endpoints import lopolis, microsoft, notes, tarot

api = APIRouter()
api.include_router(lopolis)
api.include_router(microsoft)
api.include_router(notes)
api.include_router(tarot)
