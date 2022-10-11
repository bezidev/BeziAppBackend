import asyncio
import base64
import json
import os

import aiofiles as aiofiles
import httpx
from fastapi import FastAPI, status, Header, Response, Form
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from gimsisapi import GimSisAPI
from lopolis import LoPolisAPI

import tabula

from consts import MS_OAUTH_ID, SCOPE, MS_OAUTH_SECRET

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


sessions: dict[str, GimSisAPI] = {}
lopolis_sessions: dict[str, LoPolisAPI] = {}


async def get_sharepoint_files(access_token: str):
    async with httpx.AsyncClient() as client:
        client.headers = {"Authorization": f"Bearer {access_token}"}
        disk_contents = await client.get(
            "https://graph.microsoft.com/v1.0/sites/gimnazijabezigrad.sharepoint.com,"
            "3493a726-d514-4c8e-93f9-9badbb6463e8,"
            "0f8a293b-b0fb-4baf-83c1-3dcdfafd1969/drives/b!JqeTNBTVjkyT"
            "-Zutu2Rj6Dspig_7sK9Lg8E9zfr9GWnVpozUH7MwTKu8IAQRajCq/items/root/children",
        )

        for file in disk_contents.json()["value"]:
            name = file["name"]
            print(f"Parsing {name}.")
            csv_name = f'substitutions/{name.replace(".pdf", ".csv")}'
            if os.path.exists(csv_name):
                print("File already exists, deleting.")
                os.remove(csv_name)
            tabula.convert_into(file["@microsoft.graph.downloadUrl"], csv_name, output_format="csv", pages='all')
            f = await aiofiles.open(csv_name, mode='r')
            t = []
            for line in await f.readlines():
                if line[:8] == "Šol. ura":
                    continue
                t.append(line)
            await f.close()
            async with aiofiles.open(csv_name, mode='w+') as f:
                await f.write("".join(t))
            print(f"Done parsing {name}. Result is {csv_name}.")


async def background_sharepoint_job(run_only_once: bool = False):
    print("[SHAREPOINT] Starting background Sharepoint job")

    while True:
        try:
            if not os.path.exists("refresh_token.txt"):
                await (await aiofiles.open("refresh_token.txt", "w+")).close()
            token = ""
            async with aiofiles.open("refresh_token.txt", "r+") as f:
                token = await f.read()
            if token == "":
                print("[SHAREPOINT] No Microsoft refresh tokens were detected. Please sign into BežiApp Nadomeščanja to "
                      "access Sharepoint and retrieve OAUTH refresh token")
                await asyncio.sleep(30)
                continue

            body = {
                "client_id": MS_OAUTH_ID,
                "client_secret": MS_OAUTH_SECRET,
                "refresh_token": token,
                "scope": SCOPE,
                "grant_type": "refresh_token",
            }

            async with httpx.AsyncClient() as client:
                response = (await client.post("https://login.microsoftonline.com/organizations/oauth2/v2.0/token",
                                              data=body)).json()
                access_token = response["access_token"]
                refresh_token = response["refresh_token"]
                async with aiofiles.open("refresh_token.txt", "w+") as f:
                    await f.write(refresh_token)

                await get_sharepoint_files(access_token)

            if run_only_once:
                return

            await asyncio.sleep(3600)
        except Exception as e:
            print(f"[ERROR][SharePoint] Exception while fetching SharePoint files: {e}")


@app.get("/microsoft/oauth2/url")
async def ms_oauth_url():
    return RedirectResponse(f"https://login.microsoftonline.com/organizations/oauth2/v2.0/authorize?client_id={MS_OAUTH_ID}&response_type=code&response_mode=query&scope=offline_access%20{SCOPE}")


@app.get("/microsoft/oauth2/callback", status_code=status.HTTP_200_OK)
async def ms_oauth_callback(code: str):
    body = {
        "client_id": MS_OAUTH_ID,
        "client_secret": MS_OAUTH_SECRET,
        "code": code,
        "scope": SCOPE,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        response = (await client.post("https://login.microsoftonline.com/organizations/oauth2/v2.0/token", data=body)).json()
        refresh_token = response["refresh_token"]
        async with aiofiles.open("refresh_token.txt", "w+") as f:
            await f.write(refresh_token)
        await background_sharepoint_job(run_only_once=True)

    return "OK"


def translate_days_into_sharepoint(days: [str]):
    new_days = []
    for sharepoint_day in days:
        fmt = sharepoint_day.split(".")
        new_day = f'{fmt[0].lstrip("0")}.{fmt[1].lstrip("0")}'
        new_days.append(new_day)
    return new_days


def find_base_class(classes):
    all_classes = []
    for day in classes.values():
        for i in day.values():
            if i.razred.replace(".", "") not in all_classes:
                all_classes.append(i.razred.replace(".", ""))

    return all_classes


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

    sharepoint_days = translate_days_into_sharepoint(days)
    all_classes = find_base_class(classes)

    for i, day in enumerate(sharepoint_days):
        sharepoint_filenames = [
            f"substitutions/nadomeščanje_{day}.csv",
            f"substitutions/nadomeščanje_{day}_intranet.csv"
        ]
        for sharepoint_filename in sharepoint_filenames:
            if not os.path.exists(sharepoint_filename):
                print(f"[SHAREPOINT] Could not find a file {sharepoint_filename}")
                continue
            async with aiofiles.open(sharepoint_filename, "r") as f:
                for line in await f.readlines():
                    csv_values = line.split(",")
                    if not csv_values[1] in all_classes:
                        continue
                    if " - " in csv_values[0]:
                        h = csv_values[0].split(" - ")
                        hours = range(int(h[0]), int(h[1]) + 1)
                    else:
                        hours = [int(csv_values[0])]
                    print(hours)
                    for n in classes[i].keys():
                        if classes[i][n].ura in hours:
                            classes[i][n].profesor = csv_values[3]
                            classes[i][n].ucilnica = csv_values[5]
                            classes[i][n].kratko_ime = csv_values[7]
                            classes[i][n].ime = csv_values[7]
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


@app.post("/gimsis/login", status_code=status.HTTP_200_OK)
async def login(username: str = Form(), password: str = Form()):
    global sessions

    gimsis = GimSisAPI(username, password)
    await gimsis.login()

    session = base64.b64encode(os.urandom(64)).decode()
    sessions[session] = gimsis

    return {"session": session}


@app.post("/lopolis/login", status_code=status.HTTP_200_OK)
async def lopolis_login(response: Response, username: str = Form(), password: str = Form(), authorization: str = Header()):
    global lopolis_sessions

    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return

    lopolis = LoPolisAPI()
    await lopolis.get_token(username, password)
    session = base64.b64encode(os.urandom(64)).decode()
    lopolis_sessions[authorization] = lopolis

    return {"session": session}


@app.get("/lopolis/meals", status_code=status.HTTP_200_OK)
async def get_meals(response: Response, month: str, year: str, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None or lopolis_sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    lopolis_session = lopolis_sessions[authorization]
    return await lopolis_session.get_menus(year, month)


@app.post("/lopolis/meals", status_code=status.HTTP_200_OK)
async def set_meals(response: Response, month: str, year: str, authorization: str = Header(), lopolis_response: str = Form()):
    if authorization == "" or sessions.get(authorization) is None or lopolis_sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    lopolis_session = lopolis_sessions[authorization]
    # print(lopolis_response)
    return await lopolis_session.set_menus(year, month, json.loads(lopolis_response))


@app.get("/lopolis/checkouts", status_code=status.HTTP_200_OK)
async def get_meals(response: Response, month: str, year: str, authorization: str = Header()):
    if authorization == "" or sessions.get(authorization) is None or lopolis_sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    lopolis_session = lopolis_sessions[authorization]
    return await lopolis_session.get_checkouts(year, month)


@app.post("/lopolis/checkouts", status_code=status.HTTP_200_OK)
async def set_meals(response: Response, month: str, year: str, authorization: str = Header(), lopolis_response: str = Form()):
    if authorization == "" or sessions.get(authorization) is None or lopolis_sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    lopolis_session = lopolis_sessions[authorization]
    return await lopolis_session.set_checkouts(year, month, json.loads(lopolis_response))


@app.on_event("startup")
async def startup_event():
    asyncio.ensure_future(background_sharepoint_job())
