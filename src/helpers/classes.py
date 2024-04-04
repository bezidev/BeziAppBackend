import re
from typing import List


def parse_base_class(all_classes: List[str]) -> (int, str):
    try:
        for f in all_classes:
            # seveda obstajajo tudi izjeme, oz. po domače mm, qa, qb
            if not (len(f) == 2 or (len(f) == 3 and (
                    f == "4MM" or f == "4QA" or f == "4QA" or f == "3MM" or f == "3QA" or f == "3QB" or f == "2QA" or f == "2QB" or f == "1QA" or f == "1QB"))):
                continue
            return int(f[0]), f[1:].upper()
    except Exception as e:
        print(f"Could not obtain class level: {e}, skipping")
        return 0, ""
    return 0, ""


def match_class(c, class_level, base_class) -> str:
    try:
        regex_match = f"{class_level}[A-HŠ]*\.\.|{class_level}[A-HŠ]*{base_class}[A-HŠ]*"
    except Exception as e:
        print(f"[UNTIS 2023/24 v2] Could not find class_level and base_class")
        return ""

    try:
        class_match = re.findall(regex_match, c)[0]
        return class_match
    except Exception as e:
        # print(f"[UNTIS 2023/24 v2] No match found for {class_level}. {base_class} and regex {regex_match} with {csv_values[1]}: {e}")
        return ""
