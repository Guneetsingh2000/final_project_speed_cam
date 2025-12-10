import csv
from .config import PLATE_DB_PATH

def lookup_owner(plate):
    plate = (plate or "").replace(" ", "").upper()

    try:
        with open(PLATE_DB_PATH) as f:
            for row in csv.DictReader(f):
                if row["plate"].upper() == plate:
                    return row
    except FileNotFoundError:
        return None

    return None
