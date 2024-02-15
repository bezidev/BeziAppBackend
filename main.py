import asyncio
import copy
import csv
import json
import os
import io
import time

from gimsisapi.formtagparser import GimSisUra

import src.pdfparsers.temppdf as temppdf

import aiofiles as aiofiles
from fastapi import status, Header, Response, FastAPI
from fastapi.responses import StreamingResponse
from ics import Calendar, Event
from datetime import datetime, timedelta

from gimsisapi import GimSisAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from routes.api import api

from src.endpoints.consts import engine, Base, TEST_USERNAME, async_session, SharepointNotification, sessions, analytics
from src.endpoints.microsoft import translate_days_into_sharepoint, find_base_class, background_sharepoint_job
from src.pdfparsers import select_parser

app = FastAPI()

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api)

@app.get("/notifications", status_code=status.HTTP_200_OK)
async def get_my_notifications(response: Response, only_new: bool = False, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "sharepoint.notifications.read" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    new_notifications = []
    seen_notifications = []
    expired_notifications = []
    async with async_session() as session:
        db_objects = (await session.execute(select(SharepointNotification).order_by(SharepointNotification.modified_on))).all()
        for notification in db_objects:
            notification = notification[0]
            if notification.expires_on < time.time():
                # notifikacija je potekla
                expired_notifications.append(
                    {
                        "id": notification.id,
                        "name": notification.name,
                        "description": notification.description,
                        "created_on": notification.created_on,
                        "created_by": notification.created_by,
                        "modified_on": notification.modified_on,
                        "modified_by": notification.modified_by,
                        "expires_on": notification.expires_on,
                        "has_attachments": notification.has_attachments,
                    }
                )
                continue
            seen_by = json.loads(notification.seen_by)
            if account_session.username in seen_by:
                # uporabnik je to že videl, ni treba, da mu kažemo še enkrat
                seen_notifications.append(
                    {
                        "id": notification.id,
                        "name": notification.name,
                        "description": notification.description,
                        "created_on": notification.created_on,
                        "created_by": notification.created_by,
                        "modified_on": notification.modified_on,
                        "modified_by": notification.modified_by,
                        "expires_on": notification.expires_on,
                        "has_attachments": notification.has_attachments,
                    }
                )
                continue
            new_notifications.append(
                {
                    "id": notification.id,
                    "name": notification.name,
                    "description": notification.description,
                    "created_on": notification.created_on,
                    "created_by": notification.created_by,
                    "modified_on": notification.modified_on,
                    "modified_by": notification.modified_by,
                    "expires_on": notification.expires_on,
                    "has_attachments": notification.has_attachments,
                }
            )

    #new_notifications.reverse()
    #seen_notifications.reverse()
    #expired_notifications.reverse()

    if only_new:
        return new_notifications

    return {
        "new_notifications": new_notifications,
        "seen_notifications": seen_notifications,
        "expired_notifications": expired_notifications,
    }


@app.post("/notifications/{id}", status_code=status.HTTP_200_OK)
async def update_visibility(
        response: Response,
        id: int,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "sharepoint.notifications.write" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        notification = (await session.execute(select(SharepointNotification).filter_by(id=id))).first()
        if notification is None or notification[0] is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return
        notification = notification[0]
        seen_by = json.loads(notification.seen_by)
        if account_session.username in seen_by:
            seen_by.remove(account_session.username)
        else:
            seen_by.append(account_session.username)
        notification.seen_by = json.dumps(seen_by)
        await session.commit()


@app.get("/timetable", status_code=status.HTTP_200_OK)
async def get_timetable(response: Response, date: str | None, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "gimsis.timetable" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        return {"classes":{"0":{"1":{"ura":1,"dan":0,"ime":"ZGO (Zgodovina)","kratko_ime":"ZGO","razred":"1.A","profesor":"Jernej Pirnat","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"2":{"ura":2,"dan":0,"ime":"MAT (Matematika)","kratko_ime":"MAT","razred":"1.A","profesor":"Urška Markun","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"3":{"ura":3,"dan":0,"ime":"LUM (Likovna umetnost)","kratko_ime":"LUM","razred":"1.A","profesor":"Tanja Mastnak","ucilnica":"Učilnica 402","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"4":{"ura":4,"dan":0,"ime":"SLO (Slovenščina)","kratko_ime":"SLO","razred":"1.A","profesor":"Mojca Osvald","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"5":{"ura":5,"dan":0,"ime":"KEMv (Kemija-vaje)","kratko_ime":"KEMv","razred":"1.As2","profesor":"Saša Cecowski","ucilnica":"Učilnica 104","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"6":{"ura":6,"dan":0,"ime":"ANG (Angleščina)","kratko_ime":"ANG","razred":"1.A","profesor":"Maja Petričić Štritof","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None}},"1":{"2":{"ura":2,"dan":1,"ime":"ANG (Angleščina)","kratko_ime":"ANG","razred":"1.A","profesor":"Maja Petričić Štritof","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"3":{"ura":3,"dan":1,"ime":"MAT (Matematika)","kratko_ime":"MAT","razred":"1.A","profesor":"Urška Markun","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"4":{"ura":4,"dan":1,"ime":"ZGO (Zgodovina)","kratko_ime":"ZGO","razred":"1.A","profesor":"Jernej Pirnat","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"5":{"ura":5,"dan":1,"ime":"SLO (Slovenščina)","kratko_ime":"SLO","razred":"1.A","profesor":"Mojca Osvald","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"6":{"ura":6,"dan":1,"ime":"NEM (Nemščina)","kratko_ime":"NEM","razred":"1.A","profesor":"Barbara Ovsenik Dolinar","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"7":{"ura":7,"dan":1,"ime":"GEO (Geografija)","kratko_ime":"GEO","razred":"1.A","profesor":"Veronika Lazarini","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None}},"2":{"1":{"ura":1,"dan":2,"ime":"NEM (Nemščina)","kratko_ime":"NEM","razred":"1.A","profesor":"Barbara Ovsenik Dolinar","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"2":{"ura":2,"dan":2,"ime":"GEO (Geografija)","kratko_ime":"GEO","razred":"1.A","profesor":"Veronika Lazarini","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"3":{"ura":3,"dan":2,"ime":"FIZ (Fizika)","kratko_ime":"FIZ","razred":"1.A","profesor":"Monika Vidmar","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"4":{"ura":4,"dan":2,"ime":"SLO (Slovenščina)","kratko_ime":"SLO","razred":"1.A","profesor":"Mojca Osvald","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"5":{"ura":5,"dan":2,"ime":"MAT (Matematika)","kratko_ime":"MAT","razred":"1.A","profesor":"Urška Markun","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"6":{"ura":6,"dan":2,"ime":"ANG (Angleščina)","kratko_ime":"ANG","razred":"1.A","profesor":"Maja Petričić Štritof","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"7":{"ura":7,"dan":2,"ime":"INF (Informatika)","kratko_ime":"INF","razred":"1.A","profesor":"Andrej Šuštaršič","ucilnica":"Učilnica 206","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None}},"3":{"1":{"ura":1,"dan":3,"ime":"INFv (Informatika - vaje)","kratko_ime":"INFv","razred":"1.As2","profesor":"Andrej Šuštaršič","ucilnica":"Učilnica 206","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"2":{"ura":2,"dan":3,"ime":"SLO (Slovenščina)","kratko_ime":"SLO","razred":"1.A","profesor":"Mojca Osvald","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"3":{"ura":3,"dan":3,"ime":"ŠVZ-M (Športna vzgoja)","kratko_ime":"ŠVZ-M","razred":"1.A_ŠVZ-M","profesor":"Peter Cizl","ucilnica":"Telovadnica","dnevniski_zapis":True,"vpisano_nadomescanje":True,"opozori":None},"4":{"ura":4,"dan":3,"ime":"BIOp (Biologija-pouk, cikli)","kratko_ime":"BIOp","razred":"1.A","profesor":"Polona Gros Remec","ucilnica":"Učilnica 306","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"5":{"ura":5,"dan":3,"ime":"KEM (Kemija)","kratko_ime":"KEM","razred":"1.A","profesor":"Saša Cecowski","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"6":{"ura":6,"dan":3,"ime":"NEM (Nemščina)","kratko_ime":"NEM","razred":"1.A","profesor":"Barbara Ovsenik Dolinar","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"7":{"ura":7,"dan":3,"ime":"RU (Razredna ura)","kratko_ime":"RU","razred":"1.A","profesor":"Saša Cecowski","ucilnica":"Učilnica 107","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None}},"4":{"1":{"ura":1,"dan":4,"ime":"ŠVZ-M (Športna vzgoja)","kratko_ime":"ŠVZ-M","razred":"1.A_ŠVZ-M","profesor":"Domen Hren","ucilnica":"Telovadnica","dnevniski_zapis":True,"vpisano_nadomescanje":True,"opozori":None},"2":{"ura":2,"dan":4,"ime":"ŠVZ-M (Športna vzgoja)","kratko_ime":"ŠVZ-M","razred":"1.A_ŠVZ-M","profesor":"Domen Hren","ucilnica":"Telovadnica","dnevniski_zapis":True,"vpisano_nadomescanje":True,"opozori":None},"3":{"ura":3,"dan":4,"ime":"KEMp (Kemija-pouk, cikli)","kratko_ime":"KEMp","razred":"1.A","profesor":"Saša Cecowski","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"4":{"ura":4,"dan":4,"ime":"MAT (Matematika)","kratko_ime":"MAT","razred":"1.A","profesor":"Urška Markun","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"5":{"ura":5,"dan":4,"ime":"BIO (Biologija)","kratko_ime":"BIO","razred":"1.A","profesor":"Polona Gros Remec","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"6":{"ura":6,"dan":4,"ime":"GLA (Glasba)","kratko_ime":"GLA","razred":"1.A","profesor":"Kristina Drnovšek","ucilnica":"Učilnica 308","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"7":{"ura":7,"dan":4,"ime":"LUM (Likovna umetnost)","kratko_ime":"LUM","razred":"1.A","profesor":"Tanja Mastnak","ucilnica":"Učilnica 402","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None}},"5":{},"6":{}},"days":["15.05.","16.05.","17.05.","18.05.","19.05.","20.05.","21.05."],"sharepoint_days":["15.5","16.5","17.5","18.5","19.5","20.5","21.5"]}
    try:
        classes, days = await account_session.gimsis_session.fetch_timetable(date)
        if len(days) == 0:
            # Session token has expired, new login is needed
            await account_session.login()
            classes, days = await account_session.gimsis_session.fetch_timetable(date)
            if len(days) == 0:
                raise Exception("len(days) is 0")
    except Exception as e:
        print(f"[TIMETABLE] GimSIS login failed: {e}")
        response.status_code = status.HTTP_403_FORBIDDEN
        return {
            "type": "gimsis_login_fail",
            "data": "GimSIS login failed",
        }

    current = datetime.now()
    if current.day != analytics["reset"]:
        prev = current - timedelta(days=1)
        print("[ANALITIKA] ----------------------------------------------")
        print("[ANALITIKA] BežiApp analitika")
        print(f"[ANALITIKA] Analitika izpisana ob {current.minute}.{current.hour} na dan {prev.day}. {prev.month}. {prev.year}")
        print(f"[ANALITIKA] Dan: {prev.day}. {prev.month}. {prev.year}")
        print(f"[ANALITIKA] Število edinstvenih obiskovalcev: {len(analytics.keys()) - 1}")
        print(f"[ANALITIKA] Obiskovalci: {analytics}")
        print("----------------------------------------------")
        analytics.clear()
        analytics["reset"] = current.day
    if analytics.get(account_session.username) is None:
        print(f"[ANALYTICS DEBUG] Dodajam v analitiko: {current.day} {analytics['reset']}")
        analytics[account_session.username] = 0
    analytics[account_session.username] += 1

    try:
        gradings = await account_session.gimsis_session.fetch_gradings()
    except Exception as e:
        print(f"[ERROR] Error while fetching gradings: {e}")
        gradings = []

    classes_archive = copy.deepcopy(classes)

    sharepoint_days = translate_days_into_sharepoint(days)
    all_classes = find_base_class(classes)

    e = "" if len(all_classes) == 0 else all_classes[0]

    print(f"[INFO] Parsing timetable for user {account_session.username} {e}")

    for i, day in enumerate(days):
        for grading in gradings:
            if day not in grading.datum:
                continue
            for n in classes[i].keys():
                if grading.predmet.lower() in classes[i][n].kratko_ime.lower():
                    classes[i][n].ocenjevanje = True
                    classes[i][n].ocenjevanje_details = grading

    for i, day in enumerate(sharepoint_days):
        for n in classes[i].keys():
            classes[i][n].opozori = None

        sharepoint_filenames = [
            f"substitutions/nadomeščanje_{day}.csv",
            f"substitutions/nadomescanje_{day}.csv",
            f"substitutions/nadomeščenje_{day}.csv",
            f"substitutions/nadomescenje_{day}.csv",
        ]
        for sharepoint_filename in sharepoint_filenames:
            if not os.path.exists(sharepoint_filename):
                #print(f"[SHAREPOINT] Could not find a file {sharepoint_filename}")
                continue
            async with aiofiles.open(sharepoint_filename, "r") as f:
                print(f"[SHAREPOINT] File {sharepoint_filename} exists.")
                ls = await f.readlines()
                lines = csv.reader(ls, delimiter=',')
                if "ura,razred,učilnica,nadomešča,komentar\n" in ls:
                    print(f"[SUBSTITUTION PARSER] Parsing using the temporary PDF format. Now deprecated.")
                    classes = temppdf.parse(lines, all_classes, classes_archive, classes, i)
                    continue
                classes = select_parser(lines, all_classes, classes_archive, classes, i)

    return {"classes": classes, "days": days, "sharepoint_days": sharepoint_days}


@app.get("/absences", status_code=status.HTTP_200_OK)
async def get_absences(
    response: Response,
    from_date: str,
    to_date: str = None,
    ni_obdelano: bool = True,
    opraviceno: bool = True,
    neopraviceno: bool = True,
    ne_steje: bool = True,
    type: int = 1,
    authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "gimsis.absences" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    try:
        absences = await account_session.gimsis_session.fetch_absences(from_date, to_date=to_date, ni_obdelano=ni_obdelano, opraviceno=opraviceno, neopraviceno=neopraviceno, ne_steje=ne_steje, type=type)
    except Exception as e:
        await account_session.login()
        absences = await account_session.gimsis_session.fetch_absences(from_date, to_date=to_date,
                                                                       ni_obdelano=ni_obdelano, opraviceno=opraviceno,
                                                                       neopraviceno=neopraviceno, ne_steje=ne_steje,
                                                                       type=type)

    if len(absences) == 0:
        absences = await account_session.gimsis_session.fetch_absences(from_date, to_date=to_date, ni_obdelano=ni_obdelano, opraviceno=opraviceno, neopraviceno=neopraviceno, ne_steje=ne_steje, type=type)
        await account_session.login()

    return {"absences": absences, "type": type}


@app.get("/gradings", status_code=status.HTTP_200_OK)
async def get_gradings(response: Response, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "gimsis.gradings" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    try:
        gradings = await account_session.gimsis_session.fetch_gradings()
    except Exception as e:
        await account_session.login()
        gradings = await account_session.gimsis_session.fetch_gradings()
    return {"gradings": gradings}


@app.get("/gradings/calendar", status_code=status.HTTP_200_OK)
async def get_gradings_ical(username: str, password: str):
    gimsis = GimSisAPI(username, password)
    await gimsis.login()
    gradings = await gimsis.fetch_gradings()
    c = Calendar()
    c.creator = "BežiApp/GimSIS"
    for grading in gradings:
        e = Event()
        e.name = grading.predmet
        desc = grading.opis.split("\r\n")
        e.description = f"{desc[0].strip()}\n{desc[1].strip()}"
        e.begin = datetime.strptime(grading.datum, '%d.%m.%Y').strftime("%Y.%m.%d 060000.00")
        e.location = "46.064167;14.511667"
        c.events.add(e)
    return StreamingResponse(io.StringIO(c.serialize()), media_type="text/calendar")


@app.get("/teachers", status_code=status.HTTP_200_OK)
async def get_teachers(response: Response, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "gimsis.teachers" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    teachers = await account_session.gimsis_session.fetch_teachers()
    if len(teachers) == 0:
        await account_session.login()
        teachers = await account_session.gimsis_session.fetch_teachers()
    return {"teachers": teachers}


@app.get("/grades", status_code=status.HTTP_200_OK)
async def get_grades(response: Response, year: str | None, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "gimsis.grades" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    year = "" if year is None else year
    try:
        grades = await account_session.gimsis_session.fetch_grades(year=year)
    except Exception as e:
        await account_session.login()
        grades = await account_session.gimsis_session.fetch_grades(year=year)
    if len(grades) == 0:
        await account_session.login()
        grades = await account_session.gimsis_session.fetch_grades(year=year)
    return {"grades": grades["grades"], "school_years": grades["school_years"]}


@app.get("/user/info", status_code=status.HTTP_200_OK)
async def get_user_info(response: Response, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    filtered_profile = {}

    try:
        profile = await account_session.gimsis_session.my_profile()
        if not account_session.oauth2_session or "gimsis.user.read.usernameemail" in account_session.permissions:
            filtered_profile["username"] = profile["username"]
            filtered_profile["email"] = profile["email"]
        if not account_session.oauth2_session or "gimsis.user.read.namesurname" in account_session.permissions:
            filtered_profile["name"] = profile["name"]
            filtered_profile["surname"] = profile["surname"]
        if not account_session.oauth2_session or "gimsis.user.read.sex" in account_session.permissions:
            filtered_profile["sex"] = profile["sex"]
        if not account_session.oauth2_session or "gimsis.user.read.role" in account_session.permissions:
            filtered_profile["user_role"] = profile["user_role"]
    except Exception as e:
        print(f"Failed while requesting from GimSIS. Falling back to local knowledge. Exception: {e}")
        if not account_session.oauth2_session or "gimsis.user.read.usernameemail" in account_session.permissions:
            filtered_profile["username"] = account_session.username
            filtered_profile["email"] = ""

    return filtered_profile


@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    asyncio.ensure_future(background_sharepoint_job())
