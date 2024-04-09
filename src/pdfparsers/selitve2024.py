import csv
import re
import aiofiles


# S tem, da upoštevajmo, dragi guspudje, da je to najmanj standardiziran format na svetu
# Katerega seveda menjajo vsak mesec.
# Zakaj?
# Ker lahko.
async def process_migrations():
    async with aiofiles.open("substitutions/selitve_raw.csv", mode='r') as f:
        print(f"[MIGRATIONS 2024 PARSER] Attempting to parse current file.")
        ls = await f.readlines()
        lines = csv.reader(ls, delimiter=',')
        nf = None
        w = None
        day = 0
        month = 0
        days = []
        for line in lines:
            ok = False
            for p in line:
                r = re.search("(ponedeljek|torek|sreda|[cč]etrtek|petek|sobota|nedelja)[, ][ ]?(\d+)[. ][ ]?(\d+)[.]?[ ]?", p.lower())
                if r is None:
                    continue
                print(f"[MIGRATIONS 2024 PARSER] Matched {p.lower()} to day description.")
                try:
                    day = int(r.group(2))
                    month = int(r.group(3))
                except Exception as e:
                    print(f"[MIGRATIONS 2024 PARSER] Couldn't extract day and month from {p.lower()}. Error: {e}")
                    continue

                if nf is not None:
                    # trust me bro, to dela
                    # ps. jebeš type anotacije v pythonu
                    await nf.close()

                # Vodstvo očitno ni spretno z Wordom, zato se kar odločijo, da bodo dali nov odstavek, kadarkoli jim
                # srce poželi
                nf = await aiofiles.open(f"substitutions/selitve_{day}.{month}.csv", "a" if day in days else "w+", newline="")
                w = csv.writer(nf)
                ok = True

                days.append(day)

                break

            if ok:
                continue

            if day == 0 or month == 0 or w is None or nf is None:
                continue

            if len(line) != 10:
                print(f"[MIGRATIONS 2024 PARSER] Invalid parser selection: {line}")
                continue

            for i in range(2):
                k = i * 5  # zamik

                h = line[k]
                if h == "":
                    continue

                raz = line[k+1].lower()
                if "q" in raz or "mm" in raz:
                    continue  # Žal (ali pa tudi ne) GimSIS-a ne servirajo mednarodni šoli

                h = h.replace(".", "")

                try:
                    h = int(h)
                except Exception as e:
                    print(f"[MIGRATIONS 2024 PARSER] Failure while parsing hour. Error: {e}. Line: {line}/{i}")
                    continue

                predmet = line[k+2].upper()
                ucitelj = line[k+3].lower()
                nova_ucilnica = line[k+4].upper() # baje ne smemo pretvoriti v int, saj je vrednost lahko tudi ČIT

                # sej ne, da v nadomeščanjih uporabljajo format 4A, tukaj pa 4. a also, kadar so maturitetne zadeve,
                # je edino logično, da ne uporabijo 4AB..., kot to delajo na jebenih nadomeščanjih, temveč napišejo
                # "Priprave"
                # TODO: In more recent news, včasih napišejo FI4 (Filozofija 4) kot razred.
                # na kakšnem svetu živimo jao bože
                raz = raz.upper()
                r = re.search("([1-4])[.]?[ ]?([A-H|Š])", raz)
                if r is not None:
                    raz = [f"{r.group(1)}{r.group(2)}"]
                else:
                    raz = ["3ABC..", "4ABC.."] # za zdaj ni boljšega načina, kot da naspammamo shit za oba letnika

                for r in raz:
                    await w.writerow([h, r, predmet, ucitelj, nova_ucilnica])

        if nf is not None:
            await nf.close()

