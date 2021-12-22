import datetime
import os

import pandas as pd


analytics_dir = os.path.join("analytics")
os.makedirs(analytics_dir, exist_ok=True)


class _Table:
    def __init__(self, storage_loc: str):
        self.storage_loc = storage_loc
        os.makedirs(self.storage_loc, exist_ok=True)
        self.filename = os.path.join(self.storage_loc, "data.pkl")
        if os.path.exists(self.filename):
            self.frame = pd.read_pickle(self.filename)
        else:
            self.frame = pd.DataFrame()
        self.num_uncommited_writes = 0
        self.last_save_time = datetime.datetime.now()

    def log(self, data: dict):
        row = pd.DataFrame(data, index=[datetime.datetime.now()])
        self.frame = self.frame.append(row)
        self.num_uncommited_writes += 1
        time_since_last_save = datetime.datetime.now() - self.last_save_time
        if (
            self.num_uncommited_writes >= 1
            or time_since_last_save.total_seconds() >= 5 * 60
        ):
            self.save()

    def save(self):
        self.frame.to_pickle(self.filename)
        self.num_uncommited_writes = 0
        self.last_save_time = datetime.datetime.now()


tables: list[_Table] = []


def get_table(name: str) -> _Table:
    table = _Table(os.path.join(analytics_dir, name))
    tables.append(table)
    return table


def save_all():
    for table in tables:
        table.save()
