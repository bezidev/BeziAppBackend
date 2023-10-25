import re


def parse(lines, all_classes, classes_archive: dict[int, dict], classes: dict[int, dict], i: int):
    for csv_values in lines:
        try:
            for f in all_classes:
                # seveda obstajajo tudi izjeme, oz. po domače mm, qa, qb
                if not (len(f) == 2 or (len(f) == 3 and (f == "4MM" or f == "4QA" or f == "4QA" or f == "3MM" or f == "3QA" or f == "3QB" or f == "2QA" or f == "2QB" or f == "1QA" or f == "1QB"))):
                    continue
                class_level = int(f[0])
                base_class = f[1:].upper()
                break
        except Exception as e:
            print(f"[UNTIS 2023/24 v2] Could not obtain class level: {e}, csv_values={csv_values}, skipping")
            continue
        #print(f"Found {class_level}. {base_class}")

        try:
            regex_match = f"{class_level}[A-HŠ]*\.\.|{class_level}[A-HŠ]*{base_class}[A-HŠ]*"
        except:
            print(f"[UNTIS 2023/24 v2] Could not find class_level and base_class")
        try:
            class_match = re.findall(regex_match, csv_values[1])[0]
        except Exception as e:
            #print(f"[UNTIS 2023/24 v2] No match found for {class_level}. {base_class} and regex {regex_match} with {csv_values[1]}: {e}")
            continue
        print(f"[UNTIS 2023/24 v2] Match found for {class_level}{base_class} and regex {regex_match} with {csv_values[1]}: {class_match}")
        if " - " in csv_values[0]:
            h = csv_values[0].split(" - ")
            hours = range(int(h[0]), int(h[1]) + 1)
        else:
            hours = [int(csv_values[0])]
        # print(hours)
        for n in classes[i].keys():
            if classes[i][n].ura not in hours:
                continue

            classes[i][n].gimsis_kratko_ime = classes_archive[i][n].kratko_ime
            classes[i][n].gimsis_ime = classes_archive[i][n].ime

            if classes[i][n].vpisano_nadomescanje:
                print(f"[UNTIS 2023/24 v2] Preskakujem že v GimSIS-u vpisano nadomeščanje {classes[i][n]} {csv_values} {class_match}.")
                continue
            try:
                if classes[i][n].fixed_by_sharepoint:
                    print(f"[UNTIS 2023/24 v2] Preskakujem že popravljeno nadomeščanje {classes[i][n]} {csv_values} {class_match}.")
                    continue
            except:
                pass

            print(f"[UNTIS 2023/24 v2] Najdeno nadomeščanje {classes[i][n]} {csv_values} {class_match}.")

            # naslednja dva primera dobro obrazložita situacijo:
            # gimsis_ime: ŠVZ-M (Športna vzgoja)
            # sharepoint ime: ŠVZ-M
            #
            # gimsis_kratko_ime: FIZv
            # sharepoint ime: FIZv2
            if not (csv_values[6] in classes[i][n].gimsis_kratko_ime or classes[i][n].gimsis_kratko_ime in csv_values[6]):
                # Maturitetni predmeti so posebni, saj so takrat skupine kombinirane
                # Maturitetni predmeti vedno vsebujejo številko letnika, če je pa ne, pa se maturitetni predmeti
                # pokažejo na nadomeščanjih v obliki 4AB.. (dve pikici na koncu), tako da lahko zanesljivo preskočimo.
                # Za maturitetne predmete ne potrebujemo opozoril, saj so pretežno false alarmi.
                # Seveda enako velja za športno vzgojo in vse laboratorijske vaje
                # -N nadaljevalni predmet
                # -Z začetni predmet
                if (f"{class_level}" in classes[i][n].gimsis_kratko_ime or
                        ".." in csv_values[1] or
                        "ŠVZ" in classes[i][n].gimsis_kratko_ime or
                        "-N" in classes[i][n].gimsis_kratko_ime or
                        "-Z" in classes[i][n].gimsis_kratko_ime or
                        "-vaje" in classes[i][n].gimsis_ime):
                    print(f"[UNTIS 2023/24 v2] Preskakujem maturitetni/kombinirani predmet oz. vaje {classes[i][n]} {csv_values} {class_match}")
                    continue

                print(f"[UNTIS 2023/24 v2] Opozarjam uporabnika na napako v urniku {classes[i][n]} {csv_values} {class_match}")
                classes[i][n].opozori = True
                # ne applyjaj sprememb, samo opozori
                continue
            p = csv_values[2].lower().replace("..", "")
            profesor = p.split(" ")[0]
            if profesor.lower() not in classes[i][n].profesor.lower():
                # Pač oprosti, ampak to pa res ne more biti napaka
                print(f"[UNTIS 2023/24 v2] Napaka v urniku glede profesorja {classes[i][n]} {profesor} {class_match}")
                #classes[i][n].opozori = True
                continue

            if classes[i][n].opozori:
                print(f"[UNTIS 2023/24 v2] Brišem opozorilo {classes[i][n]} {csv_values} {class_match}")
                classes[i][n].opozori = False

            classes[i][n].kratko_ime = csv_values[7]
            classes[i][n].profesor = csv_values[3]
            classes[i][n].odpade = "---" in classes[i][n].profesor

            try:
                classes[i][n].ucilnica = f"Učilnica {int(csv_values[5])}"
            except:
                classes[i][n].ucilnica = csv_values[5]

            if classes[i][n].gimsis_kratko_ime != csv_values[7]:
                classes[i][n].ime = csv_values[7]

            classes[i][n].opis = csv_values[8]
            try:
                classes[i][n].tip_izostanka = csv_values[9]
            except:
                classes[i][n].tip_izostanka = "Tip izostanka ni dan"
            classes[i][n].fixed_by_sharepoint = True

    return classes
