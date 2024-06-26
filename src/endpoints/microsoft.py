import asyncio
import datetime
import os
import re
import time

import aiofiles
import httpx
import tabula
from fastapi import status, APIRouter
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from .consts import MS_OAUTH_ID, SCOPE, MS_OAUTH_SECRET, async_session, SharepointNotification
from ..pdfparsers import selitve2024

microsoft = APIRouter()


async def get_sharepoint_notifications(access_token: str):
    async with httpx.AsyncClient() as client:
        client.headers = {"Authorization": f"Bearer {access_token}"}
        next_link = "https://graph.microsoft.com/v1.0/sites/root/lists/54521912-06dd-4ccc-8edb-8173c9629fd8/items"
        while next_link is not None:
            print("[SHAREPOINT NOTIFICATIONS] Got a new page link.")
            disk_contents = await client.get(
                next_link,
            )
            j = disk_contents.json()
            async with async_session() as session:
                for sharepoint_object in j["value"]:
                    id = int(sharepoint_object["id"])
                    db_object = (await session.execute(select(SharepointNotification).filter_by(id=id))).first()
                    if db_object is None:
                        object_detailed = (await client.get(
                            f"https://graph.microsoft.com/v1.0/sites/root/lists/54521912-06dd-4ccc-8edb-8173c9629fd8/items/{id}",
                        )).json()
                        modified_on = int(time.mktime(datetime.datetime.strptime(object_detailed["fields"]["Modified"], "%Y-%m-%dT%H:%M:%SZ").timetuple()))
                        created_on = int(time.mktime(datetime.datetime.strptime(object_detailed["fields"]["Created"], "%Y-%m-%dT%H:%M:%SZ").timetuple()))
                        if object_detailed["fields"].get("Expires"):
                            expires_on = int(time.mktime(datetime.datetime.strptime(object_detailed["fields"]["Expires"],
                                                                                    "%Y-%m-%dT%H:%M:%SZ").timetuple()))
                        else:
                            expires_on = 0

                        obj = SharepointNotification(
                            id=id,
                            name=object_detailed["fields"]["Title"],
                            description=(object_detailed["fields"].get("Body") or "").replace("&#58;", ":"),
                            created_on=created_on,
                            modified_on=modified_on,
                            modified_by=object_detailed["lastModifiedBy"]["user"]["displayName"],
                            created_by=object_detailed["createdBy"]["user"]["displayName"],
                            has_attachments=object_detailed["fields"]["Attachments"],
                            expires_on=expires_on,
                            seen_by="[]",
                        )
                        session.add(obj)
                        print(f"[SHAREPOINT NOTIFICATIONS] Session added for ID {id}")
                        continue

                    db_object = db_object[0]
                    modified_on = int(time.mktime(datetime.datetime.strptime(sharepoint_object["lastModifiedDateTime"],
                                                                             "%Y-%m-%dT%H:%M:%SZ").timetuple()))
                    if db_object.modified_on != modified_on:
                        print(f"[SHAREPOINT NOTIFICATIONS] Change detected on ID {id}")
                        object_detailed = (await client.get(
                            f"https://graph.microsoft.com/v1.0/sites/root/lists/54521912-06dd-4ccc-8edb-8173c9629fd8/items/{id}",
                        )).json()
                        modified_on = int(time.mktime(datetime.datetime.strptime(object_detailed["fields"]["Modified"],
                                                                                 "%Y-%m-%dT%H:%M:%SZ").timetuple()))
                        if object_detailed["fields"].get("Expires"):
                            expires_on = int(time.mktime(datetime.datetime.strptime(object_detailed["fields"]["Expires"],
                                                                                     "%Y-%m-%dT%H:%M:%SZ").timetuple()))
                        else:
                            expires_on = 0

                        db_object.name = object_detailed["fields"]["Title"]
                        db_object.description = (object_detailed["fields"].get("Body") or "").replace("&#58;", ":")
                        db_object.modified_on = modified_on
                        db_object.modified_by = object_detailed["lastModifiedBy"]["user"]["displayName"]
                        db_object.has_attachments = object_detailed["fields"]["Attachments"]
                        db_object.seen_by = "[]"
                        db_object.expires_on = expires_on

                await session.commit()
            next_link = j.get("@odata.nextLink")
        print("[SHAREPOINT NOTIFICATIONS] Done.")


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
            name = file["name"].lower()
            z = re.search("nadome[sš][cč]anj[ea][_ ](3[01]|[12][0-9]|[1-9])\.[ ]*(1[0-2]|[1-9]).*\.pdf", name)
            sel = re.search("selit[ev][ev]?[_ ].*\.pdf", name)

            t = (0 if z is not None else (1 if sel is not None else -1))

            if t == -1:
                print(f"[SHAREPOINT] Failure while matching substitutions or migrations: {name}")
                csv_name = f'substitutions/{name.lower().replace(".pdf", ".csv")}'
            elif t == 0:
                # Nadomeščanja
                try:
                    dan = int(z[1])
                    try:
                        mesec = int(z[2])
                        csv_name = f'substitutions/nadomescanje_{dan}.{mesec}.csv'
                    except:
                        print(f"[SHAREPOINT] Failure while parsing month: {name}")
                        csv_name = f'substitutions/{name.lower().replace(".pdf", ".csv")}'
                except:
                    print(f"[SHAREPOINT] Failure while parsing day: {name}")
                    csv_name = f'substitutions/{name.lower().replace(".pdf", ".csv")}'
            elif t == 1:
                print(f"[SHAREPOINT] Parsing migrations: {name}")
                csv_name = f'substitutions/selitve_raw.csv'

            print(f"Parsing {name} as {csv_name}.")
            if os.path.exists(csv_name):
                print("File already exists, deleting.")
                os.remove(csv_name)
            tabula.convert_into(file["@microsoft.graph.downloadUrl"], csv_name, output_format="csv", pages='all')

            if t == -1:
                continue

            if t == 1:
                await selitve2024.process_migrations()
                print(f"Done parsing {name} as migration. Result is {csv_name}.")

            f = await aiofiles.open(csv_name, mode='r')
            t = []
            for line in await f.readlines():
                if line[:8] == "Šol. ura" or line[:5] == "Vrsta":
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
                await get_sharepoint_notifications(access_token)

            if run_only_once:
                return

            await asyncio.sleep(3600)
        except Exception as e:
            print(f"[ERROR][SharePoint] Exception while fetching SharePoint files: {e}")


@microsoft.get("/microsoft/oauth2/url")
async def ms_oauth_url():
    return RedirectResponse(f"https://login.microsoftonline.com/organizations/oauth2/v2.0/authorize?client_id={MS_OAUTH_ID}&response_type=code&response_mode=query&scope=offline_access%20{SCOPE}")


@microsoft.get("/microsoft/oauth2/callback", status_code=status.HTTP_200_OK)
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


# Tole vrže ven something in "4A" ali "4MM" style
def find_base_class(classes):
    all_classes = []
    for day in classes.values():
        for i in day.values():
            if i.razred.replace(".", "") not in all_classes:
                all_classes.append(i.razred.replace(".", ""))

    return all_classes
