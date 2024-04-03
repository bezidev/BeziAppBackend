import re

from src.helpers.classes import parse_base_class, match_class


def parse(lines, all_classes, classes_archive: dict[int, dict], classes: dict[int, dict], i: int):
    for csv_values in lines:
        class_level, base_class = parse_base_class(all_classes)
        if class_level == 0:
            continue

        #print(f"Found {class_level}. {base_class}")

        class_match = match_class(csv_values[1], class_level, base_class)
        if class_match == "":
            continue

        print(f"[UNTIS 2023/24 v2] Match found for {class_level}{base_class} with {csv_values[1]}: {class_match}")
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

            # menjavo ure vpišemo ne glede na to ali je ura že vpisana v gumsisu
            p = re.search(r"nam[.]? ([1-9]). ure", csv_values[8], re.IGNORECASE)
            if p:
                try:
                    ura = int(p.group(1))
                    classes[i][ura].odpade = True
                    classes[i][ura].implicitno_odpade = True
                    print(f"[UNTIS 2023/24 v2] Applied implicit hour: {csv_values[8]}")
                except Exception as e:
                    print(f"[UNTIS 2023/24 v2] Failure while applying replaced hour: {e}")

            if classes[i][n].vpisano_nadomescanje:
                # Če je nadomeščanje že vpisano v gimsisu, potem ta ura ne more biti odpadla
                # Right?
                classes[i][n].odpade = False
                classes[i][n].implicitno_odpade = False
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
                        "vaje" in classes[i][n].gimsis_ime):
                    print(f"[UNTIS 2023/24 v2] Preskakujem maturitetni/kombinirani predmet oz. vaje {classes[i][n]} {csv_values} {class_match}")
                    continue

                print(f"[UNTIS 2023/24 v2] Opozarjam uporabnika na napako v urniku {classes[i][n]} {csv_values} {class_match}")
                classes[i][n].opozori = True
                # ne applyjaj sprememb, samo opozori
                continue
            p = csv_values[2].lower().replace("..", "")
            profesor = p.replace("-", " ").split(" ")[0]
            if profesor.lower() not in classes[i][n].profesor.lower():
                # Pač oprosti, ampak to pa res ne more biti napaka
                #
                # To je ful neumno narejeno
                # Retardirano per se
                # Ampak G-jevci in drugi razredi imajo očitno informatiko deljeno med prof. Šuštaršiča in prof. Železnika.
                # In to isto uro. Posledično se predmeta čisto ujemata, profesor pa ne.
                # Pol pa pride še do tega, da na GIMB-u ne znajo vpisati nadomestnega profesorja v nadomeščanja.
                # VPISUJEJO JEBENE PROFESORJE, KI SO NA BOLNIŠKI IN JIH 3 JEBENE MESECE NE BO!!!
                # kaj to pomeni?
                # DA MAM JST TLE PROBLEME!!!
                # EDIT: tudi športna si zasluži skip

                if profesor.lower() == "železnik" or profesor.lower() == "šuštaršič":
                    # pač res, bog ne daj
                    continue
                if "ŠVZ" in classes[i][n].gimsis_kratko_ime:
                    continue

                print(f"[UNTIS 2023/24 v2] Napaka v urniku glede profesorja {classes[i][n]} {profesor} {class_match}")
                classes[i][n].opozori = True
                continue

            # koji kurac?
            # Kok zadet sem bil, ko sem to pisal
            # Anyhow, če dela, dela
            if classes[i][n].opozori:
                print(f"[UNTIS 2023/24 v2] Brišem opozorilo {classes[i][n]} {csv_values} {class_match}")
                classes[i][n].opozori = False

            classes[i][n].odpade = "---" in csv_values[3]

            # Tole se ne triggera pri implicitnih urah [needs reverification]
            if classes[i][n].odpade:
                classes[i][n].fixed_by_sharepoint = True
                continue

            # Če pridemo do sem, lahko rečemo, da implicitna ura ne odpade
            # Primer:
            # nam. 4. ure; 3. ura; Ovsenik -> Markun; NEM -> MAT
            # nam. 1. ure; 4. ura; Markun -> Lazarini; MAT -> GEO
            # Primer nespremenjenega urnika, da bo sploh imela kaj smisel:
            # 1. GEO
            # 2. PSI
            # 3. NEM
            # 4. MAT
            # 5. ZGO
            # ...
            # Prvo se označi 4. ura kot implicitno odpadla, saj je matematičarka zamenjala uro z nemcistko
            # Nato pa probamo spremeniti implicitno odpadlo v neko uro, saj je geografinja šla malo bolj gor po urniku
            # Zdaj označimo še 1. uro kot implicitno odpadlo, medtem ko je 4. ura še vedno implicitno označena.
            # To ni v redu, zato tukaj to.
            #
            # Naši urniki so na desetih dimenzijah razmišljanja ffs
            classes[i][n].odpade = False
            classes[i][n].implicitno_odpade = False

            classes[i][n].kratko_ime = csv_values[7]
            classes[i][n].profesor = csv_values[3]

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
