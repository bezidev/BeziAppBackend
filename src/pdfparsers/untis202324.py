import re


def parse(lines, all_classes, classes_archive: dict[int, dict], classes: dict[int, dict], i: int):
    for csv_values in lines:
        if not csv_values[2] in all_classes:
            continue
        if " - " in csv_values[1]:
            h = csv_values[1].split(" - ")
            hours = range(int(h[0]), int(h[1]) + 1)
        else:
            hours = [int(csv_values[1])]
        # print(hours)
        for n in classes[i].keys():
            try:
                sharepoint_gimsis_name = re.findall(r'\((.*?)\)', classes[i][n].ime)[0]
            except Exception as e:
                print(f"[E] {e} {classes[i][n].ime}")
                classes[i][n].opozori = True
                continue

            if classes[i][n].ura in hours:
                if "vaje" in sharepoint_gimsis_name:
                    if sharepoint_gimsis_name not in csv_values[7] and (
                            classes[i][n].opozori is None or classes[i][n].opozori):
                        print(sharepoint_gimsis_name, classes[i][n].ime, csv_values)
                        classes[i][n].opozori = True
                        continue
                    else:
                        classes[i][n].opozori = False
                if not (csv_values[3] in classes[i][n].profesor or csv_values[4] in classes[i][n].profesor):
                    classes[i][n].opozori = True
                if not (csv_values[7] in classes[i][n].ime or csv_values[8] in classes[i][n].ime):
                    classes[i][n].opozori = True
                classes[i][n].gimsis_kratko_ime = classes_archive[i][n].kratko_ime
                classes[i][n].gimsis_ime = classes_archive[i][n].ime
                if csv_values[7] != csv_values[8]:
                    classes[i][n].kratko_ime = csv_values[8]
                classes[i][n].profesor = csv_values[4]
                classes[i][n].odpade = "---" in classes[i][n].profesor
                try:
                    classes[i][n].ucilnica = f"Učilnica {int(csv_values[6])}"
                except:
                    classes[i][n].ucilnica = csv_values[6]
                if classes[i][n].kratko_ime == csv_values[8]:
                    classes[i][n].ime = csv_values[8]
                else:
                    classes[i][n].ime = f"{classes[i][n].kratko_ime} ({csv_values[8]})"
                if csv_values[9] != "":
                    classes[i][n].opis = f"{csv_values[0]}, {csv_values[9]}"
                else:
                    classes[i][n].opis = csv_values[0]
                classes[i][n].tip_izostanka = "Tip izostanka ni dan"
                classes[i][n].fixed_by_sharepoint = True

    return classes