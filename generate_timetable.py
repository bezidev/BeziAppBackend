import asyncio
import csv
import datetime
import os
import re
from math import floor

import aiofiles

class Class:
    def __init__(self, name: str, teacher: str, group: str):
        self.name = name
        self.teacher = teacher
        self.group = group


def levo_desno(data: str) -> (str, str):
    w = 30
    l = w - len(data)
    ll = int(l / 2)
    return (" "*ll, " "*ll) if ll == l / 2 else (" "*ll, " "*(ll+1))

async def main():
    razred = input("Vpišite razred: ")
    start = datetime.date(day=1, month=9, year=2023)
    now = datetime.date.today() + datetime.timedelta(weeks=1)

    classes = [
        [[], [], [], [], [], [], [], [], [], [], []],
        [[], [], [], [], [], [], [], [], [], [], []],
        [[], [], [], [], [], [], [], [], [], [], []],
        [[], [], [], [], [], [], [], [], [], [], []],
        [[], [], [], [], [], [], [], [], [], [], []],
    ]

    try:
        if len(razred) != 2:
            return
        class_level = int(razred[0])
        base_class = razred[1:].upper()
    except Exception as e:
        print(f"[TIMETABLE GENERATOR] Could not obtain class level: {e}.")
        return

    print(f"[TIMETABLE GENERATOR] Found {class_level}. {base_class}.")

    try:
        regex_match = f"{class_level}[A-HŠ]*\.\.|{class_level}[A-HŠ]*{base_class}[A-HŠ]*"
    except:
        print(f"[TIMETABLE GENERATOR] Could not find class_level and base_class")
        return

    while start <= now:
        wd = start.weekday()
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
                    try:
                        re.findall(regex_match, csv_values[1])[0]
                    except Exception as e:
                        #print(f"[UNTIS 2023/24 v2] No match found for {class_level}. {base_class} and regex {regex_match} with {csv_values[1]}: {e}")
                        continue
                    if " - " in csv_values[0]:
                        h = csv_values[0].split(" - ")
                        hours = range(int(h[0]), int(h[1]) + 1)
                    else:
                        hours = [int(csv_values[0])]
                    # print(hours)

                    c = Class(name=csv_values[6], teacher=csv_values[2], group=csv_values[1])

                    for hour in hours:
                        found = False
                        for i in classes[wd][hour]:
                            if i.teacher == c.teacher:
                                found = True
                                break
                        if found:
                            continue
                        classes[wd][hour].append(c)

        start += datetime.timedelta(days=1)

    for h in range(10):
        print(f"{h}. ura")
        m = 0
        for d in range(5):
            m = max(len(classes[d][h]), m)
        if m == 0:
            continue
        #vrstic = m*3+(m-1)
        for mv in range(m):
            for t in range(2):
                for d in range(5):
                    if len(classes[d][h]) <= mv:
                        data = ""
                    else:
                        if t == 0:
                            data = f"{classes[d][h][mv].name} ({classes[d][h][mv].group})"
                        else:
                            data = classes[d][h][mv].teacher
                    levo, desno = levo_desno(data)
                    print(f"|{levo}{data}{desno}", end="")
                print("|")
            for d in range(5):
                if len(classes[d][h]) <= mv:
                    print("|" + " " * 30, end="")
                else:
                    print("|" + "-" * 30, end="")
            print("|")
        print("-"*(31*5+1))

asyncio.run(main())
