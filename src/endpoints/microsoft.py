import asyncio
import os

import aiofiles
import httpx
import tabula
from fastapi import status, APIRouter
from fastapi.responses import RedirectResponse

from .consts import MS_OAUTH_ID, SCOPE, MS_OAUTH_SECRET


microsoft = APIRouter()


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


def find_base_class(classes):
    all_classes = []
    for day in classes.values():
        for i in day.values():
            if i.razred.replace(".", "") not in all_classes:
                all_classes.append(i.razred.replace(".", ""))

    return all_classes
