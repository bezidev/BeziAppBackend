import asyncio
import base64
import copy
import csv
import os
import re
import io

import aiofiles as aiofiles
from fastapi import status, Header, Response, Form, FastAPI, APIRouter
from fastapi.responses import StreamingResponse
from gimsisapi.formtagparser import GimSisUra
from ics import Calendar, Event
from datetime import datetime

from gimsisapi import GimSisAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.api import api

from src.endpoints.consts import engine, Base, sessions
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


@app.get("/timetable", status_code=status.HTTP_200_OK)
async def get_timetable(response: Response, date: str | None, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    gimsis_session = sessions[authorization]
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

    for i, day in enumerate(days):
        for grading in gradings:
            if day not in grading.datum:
                continue
            for n in classes[i].keys():
                if grading.predmet.lower() in classes[i][n].kratko_ime.lower():
                    classes[i][n].ocenjevanje = True
                    classes[i][n].ocenjevanje_details = grading
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
            f"substitutions/nadomescanje_{day}_intranet.csv"
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
    absences = await gimsis_session.fetch_absences(from_date, to_date=to_date, ni_obdelano=ni_obdelano, opraviceno=opraviceno, neopraviceno=neopraviceno, ne_steje=ne_steje, type=type)

    return {"absences": absences, "type": type}


@app.get("/gradings", status_code=status.HTTP_200_OK)
async def get_gradings(response: Response, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    gimsis_session = sessions[authorization]
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
    grades = await gimsis_session.fetch_grades()
    if len(grades) == 0:
        await gimsis_session.login()
        grades = await gimsis_session.fetch_grades()
    return {"grades": grades}


@app.post("/gimsis/login", status_code=status.HTTP_200_OK)
async def login(username: str = Form(), password: str = Form()):
    global sessions

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
