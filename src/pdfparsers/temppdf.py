import re


def parse(lines, all_classes, classes_archive: dict[int, dict], classes: dict[int, dict], i: int):
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
                classes[i][n].opozori = True
                continue
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

    return classes