import asyncio
import csv
import datetime
import os
import re
from math import floor

import aiofiles


class Class:
    def __init__(self, name: str, teacher: str, group: str, classroom: str):
        self.name = name
        self.teacher = teacher
        self.group = group
        self.classroom = classroom
        self.repetitions = 0


async def main():
    d = 4
    hour = 4
    while True:
        ucilnica = input("Vpišite učilnico: ")
        if ucilnica == "":
            print("Nasvidenje!")
            break
        start = datetime.date(day=1, month=9, year=2023)
        now = datetime.date.today() + datetime.timedelta(weeks=1)
        if start.weekday() != d:
            start += datetime.timedelta(days=7 - start.weekday())  # damo na ponedeljek
            start += datetime.timedelta(days=d)  # damo na dan
            start += datetime.timedelta(weeks=-1)  # premaknemo za en teden nazaj

        classes: dict[str, dict[str, Class]] = {}

        while start <= now:
            day = f"{start.day}.{start.month}"
            sharepoint_filenames = [
                f"substitutions/nadomeščanje_{day}.csv",
                f"substitutions/nadomescanje_{day}.csv",
                f"substitutions/nadomeščenje_{day}.csv",
                f"substitutions/nadomescenje_{day}.csv",
            ]

            for sharepoint_filename in sharepoint_filenames:
                if not os.path.exists(sharepoint_filename):
                    continue
                async with aiofiles.open(sharepoint_filename, "r") as f:
                    ls = await f.readlines()
                    lines = csv.reader(ls, delimiter=',')

                    for csv_values in lines:
                        uc = csv_values[4]
                        if not (uc in ucilnica or ucilnica in uc):
                            continue
                        if csv_values[0] != str(hour):
                            continue

                        razred = csv_values[1]
                        predmet = csv_values[6]

                        if classes.get(razred) is None:
                            classes[razred] = {}
                        if classes[razred].get(predmet) is None:
                            c = Class(name=predmet, teacher=csv_values[2], group=razred, classroom=uc)
                            classes[razred][predmet] = c
                        classes[razred][predmet].repetitions += 1
                break

            start += datetime.timedelta(weeks=1)

        for razred, v in classes.items():
            for predmet, l in v.items():
                l: Class = l
                print(f"Najdenih {l.repetitions} ponovitev za {hour}. uro dne {d}. Učilnica {l.classroom}, skupina {l.group}, učitelj {l.teacher}, predmet {l.name}.")
        print("------------------------------")


asyncio.run(main())
