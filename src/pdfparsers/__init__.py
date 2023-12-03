from main import TIPI_NADOMESCANJ
import src.pdfparsers.untis202223 as untis2223
import src.pdfparsers.untis202324 as untis2324
import src.pdfparsers.untis202324v2 as untis2324v2

def select_parser(lines, all_classes, classes_archive, classes, i):
    untis = "2023"
    for csv_values in lines:
        tip = csv_values[0]
        if tip == "Št.ure" or tip == "Štev.ure":
            untis = "2024v2"
        if tip in TIPI_NADOMESCANJ:
            untis = "2024"
        break

    if untis == "2023":
        print(f"[SUBSTITUTION PARSER] Parsing using the Untis 2022/2023 format. Now deprecated.")
        return untis2223.parse(lines, all_classes, classes_archive, classes, i)

    if untis == "2024":
        print(f"[SUBSTITUTION PARSER] Parsing using the Untis 2023/2024 format.")
        return untis2324.parse(lines, all_classes, classes_archive, classes, i)

    print(f"[SUBSTITUTION PARSER] Parsing using the Untis 2023/2024 v2 format.")
    classes = untis2324v2.parse(lines, all_classes, classes_archive, classes, i)

    return classes