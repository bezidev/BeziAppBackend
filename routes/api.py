from fastapi import APIRouter

from src.endpoints import lopolis, microsoft, notes, tarot, radio, accounts, error_handler, oauth2, notifications

api = APIRouter()
api.include_router(lopolis)
api.include_router(microsoft)
api.include_router(notes)
api.include_router(tarot)
api.include_router(radio)
api.include_router(accounts)
api.include_router(error_handler)
api.include_router(oauth2)
api.include_router(notifications)
