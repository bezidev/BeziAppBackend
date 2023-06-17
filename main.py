import asyncio
import base64
import copy
import csv
import json
import os
import re
import io
import time

import aiofiles as aiofiles
from fastapi import status, Header, Response, Form, FastAPI
from fastapi.responses import StreamingResponse
from gimsisapi.formtagparser import GimSisUra
from ics import Calendar, Event
from datetime import datetime

from gimsisapi import GimSisAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from routes.api import api

from src.endpoints.consts import engine, Base, sessions, TEST_USERNAME, async_session, SharepointNotification
from src.endpoints.microsoft import translate_days_into_sharepoint, find_base_class, background_sharepoint_job

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
    gimsis_session = sessions[authorization]
    new_notifications = []
    seen_notifications = []
    expired_notifications = []
    async with async_session() as session:
        db_objects = (await session.execute(select(SharepointNotification))).all()
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
            if gimsis_session.username in seen_by:
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
    gimsis_session = sessions[authorization]

    async with async_session() as session:
        notification = (await session.execute(select(SharepointNotification).filter_by(id=id))).first()
        if notification is None or notification[0] is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return
        notification = notification[0]
        seen_by = json.loads(notification.seen_by)
        if gimsis_session.username in seen_by:
            seen_by.remove(gimsis_session.username)
        else:
            seen_by.append(gimsis_session.username)
        notification.seen_by = json.dumps(seen_by)
        await session.commit()


@app.get("/timetable", status_code=status.HTTP_200_OK)
async def get_timetable(response: Response, date: str | None, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    gimsis_session = sessions[authorization]
    if gimsis_session.username == TEST_USERNAME:
        return {"classes":{"0":{"1":{"ura":1,"dan":0,"ime":"ZGO (Zgodovina)","kratko_ime":"ZGO","razred":"1.A","profesor":"Jernej Pirnat","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"2":{"ura":2,"dan":0,"ime":"MAT (Matematika)","kratko_ime":"MAT","razred":"1.A","profesor":"Urška Markun","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"3":{"ura":3,"dan":0,"ime":"LUM (Likovna umetnost)","kratko_ime":"LUM","razred":"1.A","profesor":"Tanja Mastnak","ucilnica":"Učilnica 402","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"4":{"ura":4,"dan":0,"ime":"SLO (Slovenščina)","kratko_ime":"SLO","razred":"1.A","profesor":"Mojca Osvald","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"5":{"ura":5,"dan":0,"ime":"KEMv (Kemija-vaje)","kratko_ime":"KEMv","razred":"1.As2","profesor":"Saša Cecowski","ucilnica":"Učilnica 104","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"6":{"ura":6,"dan":0,"ime":"ANG (Angleščina)","kratko_ime":"ANG","razred":"1.A","profesor":"Maja Petričić Štritof","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None}},"1":{"2":{"ura":2,"dan":1,"ime":"ANG (Angleščina)","kratko_ime":"ANG","razred":"1.A","profesor":"Maja Petričić Štritof","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"3":{"ura":3,"dan":1,"ime":"MAT (Matematika)","kratko_ime":"MAT","razred":"1.A","profesor":"Urška Markun","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"4":{"ura":4,"dan":1,"ime":"ZGO (Zgodovina)","kratko_ime":"ZGO","razred":"1.A","profesor":"Jernej Pirnat","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"5":{"ura":5,"dan":1,"ime":"SLO (Slovenščina)","kratko_ime":"SLO","razred":"1.A","profesor":"Mojca Osvald","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"6":{"ura":6,"dan":1,"ime":"NEM (Nemščina)","kratko_ime":"NEM","razred":"1.A","profesor":"Barbara Ovsenik Dolinar","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"7":{"ura":7,"dan":1,"ime":"GEO (Geografija)","kratko_ime":"GEO","razred":"1.A","profesor":"Veronika Lazarini","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None}},"2":{"1":{"ura":1,"dan":2,"ime":"NEM (Nemščina)","kratko_ime":"NEM","razred":"1.A","profesor":"Barbara Ovsenik Dolinar","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"2":{"ura":2,"dan":2,"ime":"GEO (Geografija)","kratko_ime":"GEO","razred":"1.A","profesor":"Veronika Lazarini","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"3":{"ura":3,"dan":2,"ime":"FIZ (Fizika)","kratko_ime":"FIZ","razred":"1.A","profesor":"Monika Vidmar","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"4":{"ura":4,"dan":2,"ime":"SLO (Slovenščina)","kratko_ime":"SLO","razred":"1.A","profesor":"Mojca Osvald","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"5":{"ura":5,"dan":2,"ime":"MAT (Matematika)","kratko_ime":"MAT","razred":"1.A","profesor":"Urška Markun","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"6":{"ura":6,"dan":2,"ime":"ANG (Angleščina)","kratko_ime":"ANG","razred":"1.A","profesor":"Maja Petričić Štritof","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"7":{"ura":7,"dan":2,"ime":"INF (Informatika)","kratko_ime":"INF","razred":"1.A","profesor":"Andrej Šuštaršič","ucilnica":"Učilnica 206","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None}},"3":{"1":{"ura":1,"dan":3,"ime":"INFv (Informatika - vaje)","kratko_ime":"INFv","razred":"1.As2","profesor":"Andrej Šuštaršič","ucilnica":"Učilnica 206","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"2":{"ura":2,"dan":3,"ime":"SLO (Slovenščina)","kratko_ime":"SLO","razred":"1.A","profesor":"Mojca Osvald","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"3":{"ura":3,"dan":3,"ime":"ŠVZ-M (Športna vzgoja)","kratko_ime":"ŠVZ-M","razred":"1.A_ŠVZ-M","profesor":"Peter Cizl","ucilnica":"Telovadnica","dnevniski_zapis":True,"vpisano_nadomescanje":True,"opozori":None},"4":{"ura":4,"dan":3,"ime":"BIOp (Biologija-pouk, cikli)","kratko_ime":"BIOp","razred":"1.A","profesor":"Polona Gros Remec","ucilnica":"Učilnica 306","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"5":{"ura":5,"dan":3,"ime":"KEM (Kemija)","kratko_ime":"KEM","razred":"1.A","profesor":"Saša Cecowski","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"6":{"ura":6,"dan":3,"ime":"NEM (Nemščina)","kratko_ime":"NEM","razred":"1.A","profesor":"Barbara Ovsenik Dolinar","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"7":{"ura":7,"dan":3,"ime":"RU (Razredna ura)","kratko_ime":"RU","razred":"1.A","profesor":"Saša Cecowski","ucilnica":"Učilnica 107","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None}},"4":{"1":{"ura":1,"dan":4,"ime":"ŠVZ-M (Športna vzgoja)","kratko_ime":"ŠVZ-M","razred":"1.A_ŠVZ-M","profesor":"Domen Hren","ucilnica":"Telovadnica","dnevniski_zapis":True,"vpisano_nadomescanje":True,"opozori":None},"2":{"ura":2,"dan":4,"ime":"ŠVZ-M (Športna vzgoja)","kratko_ime":"ŠVZ-M","razred":"1.A_ŠVZ-M","profesor":"Domen Hren","ucilnica":"Telovadnica","dnevniski_zapis":True,"vpisano_nadomescanje":True,"opozori":None},"3":{"ura":3,"dan":4,"ime":"KEMp (Kemija-pouk, cikli)","kratko_ime":"KEMp","razred":"1.A","profesor":"Saša Cecowski","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"4":{"ura":4,"dan":4,"ime":"MAT (Matematika)","kratko_ime":"MAT","razred":"1.A","profesor":"Urška Markun","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"5":{"ura":5,"dan":4,"ime":"BIO (Biologija)","kratko_ime":"BIO","razred":"1.A","profesor":"Polona Gros Remec","ucilnica":"Učilnica 105","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"6":{"ura":6,"dan":4,"ime":"GLA (Glasba)","kratko_ime":"GLA","razred":"1.A","profesor":"Kristina Drnovšek","ucilnica":"Učilnica 308","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None},"7":{"ura":7,"dan":4,"ime":"LUM (Likovna umetnost)","kratko_ime":"LUM","razred":"1.A","profesor":"Tanja Mastnak","ucilnica":"Učilnica 402","dnevniski_zapis":True,"vpisano_nadomescanje":False,"opozori":None}},"5":{},"6":{}},"days":["15.05.","16.05.","17.05.","18.05.","19.05.","20.05.","21.05."],"sharepoint_days":["15.5","16.5","17.5","18.5","19.5","20.5","21.5"]}
    classes, days = await gimsis_session.fetch_timetable(date)
    if len(days) == 0:
        # Session token has expired, new login is needed
        await gimsis_session.login()
        classes, days = await gimsis_session.fetch_timetable(date)

    try:
        gradings = await gimsis_session.fetch_gradings()
    except Exception as e:
        print(f"[ERROR] Error while fetching gradings: {e}")
        gradings = []

    classes_archive = copy.deepcopy(classes)

    sharepoint_days = translate_days_into_sharepoint(days)
    all_classes = find_base_class(classes)

    if "1A" in all_classes:
        # ročni popravki za 1.A
        if len(classes[0].keys()) != 0 and classes[0].get(6) is None:
            classes[0][6] = GimSisUra(6, 0, "ANG (Angleščina)", "ANG", "1.A", "Maja Petričić Štritof", "Učilnica 105", False, False)
            classes[0][6].rocno = True
        if "22.02." in days:
            for i in range(9):
                classes[2][i] = GimSisUra(i, 2, "ZD (Zdravniški pregled)", "ZD", "1.A", "ZD",
                                          "ZD Bežigrad", False, False)
                classes[2][i].rocno = True
        if "10.03." in days:
            classes[4][7] = GimSisUra(7, 4, "OIV (Likovna umetnost - obisk galerije)", "OIV-LUM", "1.A", "Tanja Mastnak",
                                      "Galerija", False, False)
            classes[4][7].rocno = True
        if "23.02." in days:
            classes[3][7] = GimSisUra(7, 3, "KIZ (Knjižnično-informacijska znanja - obisk knjižnice Bežigrad)", "KIZ", "1.A", "Savina Zwitter",
                                      "Galerija", False, False)
            classes[3][7].rocno = True
            classes[3][8] = GimSisUra(8, 3, "KIZ (Knjižnično-informacijska znanja - obisk knjižnice Bežigrad)", "KIZ",
                                      "1.A", "Savina Zwitter",
                                      "Galerija", False, False)
            classes[3][8].rocno = True

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
            f"substitutions/nadomeščanje_{day}..csv",
            f"substitutions/nadomeščanje_{day}.novo.csv",
            f"substitutions/nadomeščanje_{day}_intranet.csv",
            f"substitutions/nadomescanje_{day}.csv",
            f"substitutions/nadomescanje_{day}..csv",
            f"substitutions/nadomescanje_{day}.novo.csv",
            f"substitutions/nadomescanje_{day}_intranet.csv",
            
            f"substitutions/Nadomeščanje_{day}.csv",
            f"substitutions/Nadomeščanje_{day}..csv",
            f"substitutions/Nadomeščanje_{day}.novo.csv",
            f"substitutions/Nadomeščanje_{day}_intranet.csv",
            f"substitutions/Nadomescanje_{day}.csv",
            f"substitutions/Nadomescanje_{day}..csv",
            f"substitutions/Nadomescanje_{day}.novo.csv",
            f"substitutions/Nadomescanje_{day}_intranet.csv",
        ]
        for sharepoint_filename in sharepoint_filenames:
            if not os.path.exists(sharepoint_filename):
                print(f"[SHAREPOINT] Could not find a file {sharepoint_filename}")
                continue
            async with aiofiles.open(sharepoint_filename, "r") as f:
                print(f"[SHAREPOINT] File {sharepoint_filename} exists.")
                ls = await f.readlines()
                lines = csv.reader(ls, delimiter=',')
                if "ura,razred,učilnica,nadomešča,komentar\n" in ls:
                    print(f"[SUBSTITUTION PARSER] Parsing using the new PDF format.")
                    for csv_values in lines:
                        if csv_values[0] == "ura":
                            continue
                        print(csv_values[1].replace(". ", ""), all_classes)
                        if not csv_values[1].replace(". ", "") in all_classes:
                            continue
                        hours = [int(csv_values[0].replace(".", ""))]
                        print(hours)
                        for n in classes[i].keys():
                            try:
                                sharepoint_gimsis_name = re.findall(r'\((.*?)\)', classes[i][n].ime)[0]
                            except Exception as e:
                                print(f"[E] {e} {classes[i][n].ime}")
                            if classes[i][n].ura in hours:
                                if "vaje" in sharepoint_gimsis_name:
                                    if sharepoint_gimsis_name not in csv_values[6] and (
                                            classes[i][n].opozori is None or classes[i][n].opozori):
                                        print(sharepoint_gimsis_name, classes[i][n].ime, csv_values)
                                        classes[i][n].opozori = True
                                        continue
                                    else:
                                        classes[i][n].opozori = False
                                nadomesca = csv_values[3].split(" - ")
                                if len(nadomesca) == 1:
                                    nadomesca = csv_values[3].split(" – ")
                                classes[i][n].gimsis_kratko_ime = classes_archive[i][n].kratko_ime
                                classes[i][n].gimsis_ime = classes_archive[i][n].ime
                                classes[i][n].kratko_ime = nadomesca[-1]
                                classes[i][n].profesor = nadomesca[0]
                                classes[i][n].odpade = "/" in classes[i][n].profesor
                                try:
                                    classes[i][n].ucilnica = f"Učilnica {int(csv_values[2])}"
                                except:
                                    classes[i][n].ucilnica = csv_values[2]
                                classes[i][n].ime = nadomesca[-1]
                                classes[i][n].opis = csv_values[4]
                                classes[i][n].tip_izostanka = "Tip izostanka ni dan"
                                classes[i][n].fixed_by_sharepoint = True
                    continue

                for csv_values in lines:
                    if not csv_values[1] in all_classes:
                        continue
                    if " - " in csv_values[0]:
                        h = csv_values[0].split(" - ")
                        hours = range(int(h[0]), int(h[1]) + 1)
                    else:
                        hours = [int(csv_values[0])]
                    #print(hours)
                    for n in classes[i].keys():
                        try:
                            sharepoint_gimsis_name = re.findall(r'\((.*?)\)', classes[i][n].ime)[0]
                        except Exception as e:
                            print(f"[E] {e} {classes[i][n].ime}")
                        if classes[i][n].ura in hours:
                            if "vaje" in sharepoint_gimsis_name:
                                if sharepoint_gimsis_name not in csv_values[6] and (classes[i][n].opozori is None or classes[i][n].opozori):
                                    print(sharepoint_gimsis_name, classes[i][n].ime, csv_values)
                                    classes[i][n].opozori = True
                                    continue
                                else:
                                    classes[i][n].opozori = False
                            classes[i][n].gimsis_kratko_ime = classes_archive[i][n].kratko_ime
                            classes[i][n].gimsis_ime = classes_archive[i][n].ime
                            if csv_values[6] != csv_values[7]:
                                classes[i][n].kratko_ime = csv_values[7]
                            classes[i][n].profesor = csv_values[3]
                            classes[i][n].odpade = "---" in classes[i][n].profesor
                            try:
                                classes[i][n].ucilnica = f"Učilnica {int(csv_values[5])}"
                            except:
                                classes[i][n].ucilnica = csv_values[5]
                            if classes[i][n].kratko_ime == csv_values[7]:
                                classes[i][n].ime = csv_values[7]
                            else:
                                classes[i][n].ime = f"{classes[i][n].kratko_ime} ({csv_values[7]})"
                            classes[i][n].opis = csv_values[8]
                            try:
                                classes[i][n].tip_izostanka = csv_values[9]
                            except:
                                classes[i][n].tip_izostanka = "Tip izostanka ni dan"
                            classes[i][n].fixed_by_sharepoint = True

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
    gimsis_session = sessions[authorization]
    if gimsis_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    absences = await gimsis_session.fetch_absences(from_date, to_date=to_date, ni_obdelano=ni_obdelano, opraviceno=opraviceno, neopraviceno=neopraviceno, ne_steje=ne_steje, type=type)

    return {"absences": absences, "type": type}


@app.get("/gradings", status_code=status.HTTP_200_OK)
async def get_gradings(response: Response, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    gimsis_session = sessions[authorization]
    if gimsis_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    gradings = await gimsis_session.fetch_gradings()
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


@app.get("/grades", status_code=status.HTTP_200_OK)
async def get_grades(response: Response, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    gimsis_session = sessions[authorization]
    if gimsis_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    grades = await gimsis_session.fetch_grades()
    if len(grades) == 0:
        await gimsis_session.login()
        grades = await gimsis_session.fetch_grades()
    return {"grades": grades}


@app.post("/gimsis/login", status_code=status.HTTP_200_OK)
async def login(username: str = Form(), password: str = Form()):
    global sessions

    username = username.lower()
    if username == TEST_USERNAME: # Lutka account za Google
        session = base64.b64encode(os.urandom(64)).decode()
        sessions[session] = GimSisAPI(username, password) # ne prijavimo se v gimsis tho
        return {"session": session}

    gimsis = GimSisAPI(username, password)
    await gimsis.login()

    session = base64.b64encode(os.urandom(64)).decode()
    sessions[session] = gimsis

    return {"session": session}


@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    asyncio.ensure_future(background_sharepoint_job())
