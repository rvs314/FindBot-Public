
import logging

logging.basicConfig(filename='logs', level=logging.DEBUG)

from datetime import datetime
from functools import singledispatchmethod
from time import sleep

import gspread

from utils import panic

def stamp() -> str:
    return datetime.now().strftime("%c")

class Notes:
    gc = gspread.service_account(filename="./sheets-account.json")
    sheet = gc.open("FindBot Spreadsheet")
    summary = sheet.sheet1

    @classmethod
    def count(cls):
        inums = cls.summary.get("A2:A", major_dimension="COLUMNS")[0]
        if not inums: return 0
        return max(map(int, inums)) + 1

    @classmethod
    def from_id(cls, id: int) -> "Notes":
        blank_note = Notes.__new__(cls)

        blank_note.number = id
        blank_note.log_sheet = cls.sheet.worksheet(f"Interview #{id}")
        blank_note.backlog = []

        return blank_note

    def __init__(self):
        self.number = self.count()
        self.log_sheet = self.sheet.add_worksheet(f"Interview #{self.number}", 0, 10)
        self.backlog = []

        self.log_sheet.insert_row(["Timestamp", "Event"])
        self.summary.insert_row(index=2, values=[self.number, stamp(), "STARTUP"])

    def status(self, new):
        entry = self.summary.find(str(self.number), in_column=1) or panic("Invalid interview!")

        if entry.value == new: return

        self.summary.update_cell(entry.row, 3, new)
        self.log(new)

        self.flush()

    def flush(self):
        self.backlog.reverse()
        while True:
            try:
                self.log_sheet.insert_rows(row=2, values=self.backlog)
                self.backlog.clear()
                return
            except gspread.exceptions.APIError:
                sleep(3)

    @singledispatchmethod
    def log(self, st):
        self.log([st])

    @log.register
    def _(self, msg: dict):
        role, content = msg['role'], msg['content']
        self.log(f"{role}: {content}")

    @log.register
    def _(self, lst: list):
        stmp = stamp()
        self.backlog.extend([[stmp, str(l)] for l in lst])
        logging.info(stmp)
        for l in lst:
            logging.info(l)

        if len(self.backlog) > 20:
            self.flush()
