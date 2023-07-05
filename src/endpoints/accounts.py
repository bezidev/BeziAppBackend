import base64
import os
import bcrypt

from fastapi import APIRouter, Header, Form
from gimsisapi import GimSisAPI
from sqlalchemy import select
from starlette import status
from starlette.responses import Response

from src.endpoints import async_session
from src.endpoints.consts import User, encrypt, decrypt, sessions, Session, TEST_USERNAME, TEST_PASSWORD

accounts = APIRouter()


@accounts.post("/account/login", status_code=status.HTTP_200_OK)
async def login(response: Response, username: str = Form(), password: str = Form()):
    username = username.lower()

    if username == TEST_USERNAME:
        if password != TEST_PASSWORD:
            response.status_code = status.HTTP_403_FORBIDDEN
            return {
                "type": "invalid_password",
                "data": "Invalid password.",
                "session": None,
                "error": None,
            }
        while True:
            login_session = base64.b64encode(os.urandom(64)).decode()
            if sessions.get(login_session) is not None:
                continue
            sessions[login_session] = Session(
                username=username,
                gimsis_password=password,
                lopolis_username=None,
                lopolis_password=None,
                oauth2_session=False,
                permissions=None,
            )
            break
        return {
            "type": "login_success",
            "data": "OK",
            "session": login_session,
            "error": None,
        }
    async with async_session() as session:
        user = (await session.execute(select(User).filter_by(username=username))).first()
        if user is None or user[0] is None:
            # uporabnik še ne obstaja kot BežiApp uporabnik.
            # avtomatično ga registrirajmo z uporabo GimSIS-a
            gimsis = GimSisAPI(username, password)

            try:
                await gimsis.login()
            except Exception as e:
                response.status_code = status.HTTP_403_FORBIDDEN
                print(f"[REGISTRATION FAILED] GimSIS error: {e}")
                return {
                    "type": "reg_fail",
                    "data": "GimSIS session verification failed",
                    "session": None,
                    "error": str(e),
                }

            try:
                password_bytes = password.encode('utf-8')
                salt = bcrypt.gensalt()
                bcrypt_password = bcrypt.hashpw(password_bytes, salt)
            except Exception as e:
                response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                return {
                    "type": "reg_fail",
                    "data": "Password hashing failed. Aborted.",
                    "session": None,
                    "error": str(e),
                }

            try:
                encrypted_gimsis_password = encrypt(password, password)
            except Exception as e:
                response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                return {
                    "type": "reg_fail",
                    "data": "Password encryption failed. Aborted.",
                    "session": None,
                    "error": str(e),
                }

            user = User(
                username=username,
                gimsis_password=encrypted_gimsis_password.decode("utf-8"),
                salt=salt.decode("utf-8"),
                password=bcrypt_password.decode("utf-8"),
                lopolis_username="",
                lopolis_password="",
            )

            session.add(user)
            await session.commit()

            while True:
                login_session = base64.b64encode(os.urandom(64)).decode()
                if sessions.get(login_session) is not None:
                    continue
                sessions[login_session] = Session(
                    username=username,
                    gimsis_password=password,
                    lopolis_username=None,
                    lopolis_password=None,
                    oauth2_session=False,
                    permissions=None,
                )
                try:
                    await sessions[login_session].login()
                except Exception as e:
                    response.status_code = status.HTTP_403_FORBIDDEN
                    return {
                        "type": "login_fail",
                        "data": "Session login failed.",
                        "session": None,
                        "error": str(e),
                    }

                break

            return {
                "type": "reg_login_success",
                "data": "OK",
                "session": login_session,
                "error": None,
            }

        user = user[0]
        bcrypt_password = bcrypt.hashpw(password.encode(), user.salt.encode()).decode()
        if bcrypt_password != user.password:
            response.status_code = status.HTTP_403_FORBIDDEN
            return {
                "type": "login_fail",
                "data": "Invalid password.",
                "session": None,
                "error": "Password mismatch.",
            }

        try:
            gimsis_password = decrypt(user.gimsis_password, password)
        except Exception as e:
            response.status_code = status.HTTP_409_CONFLICT
            return {
                "type": "login_fail",
                "data": "Could not decrypt GimSIS password.",
                "session": None,
                "error": str(e),
            }

        try:
            lopolis_password = None
            if user.lopolis_password != "":
                lopolis_password = decrypt(user.lopolis_password, password)
        except Exception as e:
            response.status_code = status.HTTP_409_CONFLICT
            return {
                "type": "login_fail",
                "data": "Could not decrypt Lo.Polis password.",
                "session": None,
                "error": str(e),
            }

        while True:
            login_session = base64.b64encode(os.urandom(64)).decode()
            if sessions.get(login_session) is not None:
                continue
            sessions[login_session] = Session(
                username=username,
                gimsis_password=gimsis_password,
                lopolis_username=user.lopolis_username,
                lopolis_password=lopolis_password,
                oauth2_session=False,
                permissions=None,
            )
            break

        # Trik je v tem, da lahko dostopamo do BežiApp računa tudi, ko nimamo GimSIS-a, če smo se predhodno registrirali z GimSIS-om,
        # zato tega ne preverjamo ob prijavah, ampak to preveri API, ki ga kliče ta oseba **PO** prijavi
        #
        #try:
        #    await sessions[login_session].login()
        #except Exception as e:
        #    response.status_code = status.HTTP_403_FORBIDDEN
        #    return {
        #        "type": "login_fail",
        #        "data": "Session login failed.",
        #        "session": None,
        #        "error": str(e),
        #    }

        return {
            "type": "login_success",
            "data": "OK",
            "session": login_session,
            "error": None,
        }

@accounts.post("/account/password", status_code=status.HTTP_200_OK)
async def change_password(response: Response, pass_type: str = Form(), current_password: str = Form(), new_password: str = Form(), username: str = Form(""), authorization: str = Header()):
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
        user = (await session.execute(select(User).filter_by(username=account_session.username))).first()
        if user is None or user[0] is None:
            response.status_code = status.HTTP_403_FORBIDDEN
            return
        user = user[0]

        bcrypt_password = bcrypt.hashpw(current_password.encode(), user.salt.encode()).decode()
        if bcrypt_password != user.password:
            response.status_code = status.HTTP_403_FORBIDDEN
            return {
                "type": "password_verification_fail",
                "data": "Invalid password.",
                "session": None,
                "error": "Password mismatch.",
            }

        if current_password == "" or new_password == "":
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                "type": "invalid_password",
                "data": "Invalid password.",
                "session": None,
                "error": "Password too short.",
            }

        if pass_type == "gimsis":
            user.gimsis_password = encrypt(new_password, current_password).decode()
            del sessions[authorization]
            await session.commit()
        elif pass_type == "lopolis":
            if username == "":
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {
                    "type": "invalid_username",
                    "data": "Invalid username.",
                    "session": None,
                    "error": "No Lo.Polis username was provided.",
                }
            user.lopolis_password = encrypt(new_password, current_password).decode()
            user.lopolis_username = username
            del sessions[authorization]
            await session.commit()
        elif pass_type == "beziapp":
            new_bcrypt_password = bcrypt.hashpw(new_password.encode(), user.salt.encode()).decode()
            if user.lopolis_password != "":
                decrypted_lopolis = decrypt(user.lopolis_password, current_password)
                user.lopolis_password = encrypt(decrypted_lopolis, new_password).decode()
            decrypted_gimsis = decrypt(user.gimsis_password, current_password)
            user.gimsis_password = encrypt(decrypted_gimsis, new_password).decode()
            user.password = new_bcrypt_password
            del sessions[authorization]
            await session.commit()
        else:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                "type": "bad_request",
                "data": "Invalid pass_type.",
                "session": None,
                "error": None,
            }

        return {
            "type": "change_success",
            "data": "OK",
            "session": None,
            "error": None,
        }
