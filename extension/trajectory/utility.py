import csv
import os
class CsvReader:
    def __init__(self, name, path) -> None:
        self._file = os.path.join(path, name)
        self._name = name
        self._path = path
    
    def _read(self) -> list:
        data = []
        with(open(self._file)) as csvFile:
            reader = csv.DictReader(csvFile)
            for row in reader:
                line_data = []
                for item in row.values():
                    ditem = float(item)
                    line_data.append(ditem)
                data.append(line_data)
        return data

    def _data_sanity_check(self, data) -> None:
        """ 
        THE CSV HEADER MUST BE:
            1) Duration from previous waypoint
            2) x
            3) y
            4) z
            5) yaw
        """
        for line in data:
            if(len(line) != 5):
                raise Exception("Invalid csv headers (5 required)")
            if(line[0] < 0 ):
                raise Exception("Duration must be always positive")

    def csv_to_trajectory(self) -> list:
        data = self._read()
        self._data_sanity_check(data)
        return data
