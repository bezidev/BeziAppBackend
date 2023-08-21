import httpx
import asyncio
from bs4 import BeautifulSoup

async def main():
    async with httpx.AsyncClient() as client:
        r = await client.get("https://www.gimb.org/?page_id=485")
        text = r.text
    soup = BeautifulSoup(text, "html.parser")
    table = soup.find("table")
    trs = table.find_all("tr")
    print("const teachers = [")
    for tr in trs:
        td = tr.find("td")
        span = td.find("span")
        if span is None:
            t = td.text
        else:
            t = span.text
        t.strip()
        k: str = t.split(",")[0]
        k = k.replace("Mag. ", "")
        k = k.replace("Dr. ", "")
        print(f'    "{k}",')
    print("];")

asyncio.run(main())
