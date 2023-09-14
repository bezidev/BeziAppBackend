def parse(lines, all_classes, classes_archive: dict[int, dict], classes: dict[int, dict], i: int):
    for csv_values in lines:
        if not csv_values[1] in all_classes:
            continue
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

            if csv_values[6] != classes[i][n].gimsis_ime:
                classes[i][n].opozori = True
            if csv_values[2].lower() not in classes[i][n].profesor.lower():
                classes[i][n].opozori = True

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
