#!/usr/bin/env python

import sys
from argparse import ArgumentParser

from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.entities import Process
from genologics.lims import Lims

DESC = """EPP for checking the placement of sample indexes for lib prep
Author: Chuan Wang, Science for Life Laboratory, Stockholm, Sweden
"""


# get the index layout for each plate
def get_index_layout(process):
    data = {}
    for container in process.output_containers():
        data[container.id] = {"name": container.name}
        index_layout = {}
        for k, v in container.placements.items():
            row = k.split(":")[0]
            col = k.split(":")[1]
            new_k = "0" + col + row if len(col) == 1 else col + row
            index_layout[new_k] = v.reagent_labels[0]
        data[container.id]["index_layout"] = index_layout
    return data


# Very the placement of indexes
def verify_index_placement(data):
    message = []
    for container_id, container_info in data.items():
        sorted_wells = sorted(list(container_info["index_layout"].keys()))
        last_well = sorted_wells[-1]
        index_placement = [
            container_info["index_layout"][well] for well in sorted_wells
        ]
        sorted_indexes = sorted(list(container_info["index_layout"].values()))
        # Check if there is/are skipped wells in between of samples
        used_cols = sorted(list(set([well[:2] for well in sorted_wells])))
        full_plate_wells = sorted(
            [
                "0" + str(col) + row if len(str(col)) == 1 else str(col) + row
                for col in range(1, int(max(used_cols)) + 1)
                for row in ["A", "B", "C", "D", "E", "F", "G", "H"]
            ]
        )
        empty_wells = []
        for well in full_plate_wells:
            if well != last_well:
                if well not in sorted_wells:
                    empty_wells.append(well)
            else:
                break
        if empty_wells:
            message.append(
                "WARNING! Plate {}: Empty wells in between of samples detected!".format(
                    container_info["name"]
                )
            )
        # Check if indexes are placed by coloumn
        if index_placement != sorted_indexes:
            message.append(
                "WARNING! Plate {}: The orders of indexes and wells do NOT match!".format(
                    container_info["name"]
                )
            )
    return message


def main(lims, pid):
    process = Process(lims, id=pid)
    data = get_index_layout(process)
    message = verify_index_placement(data)

    if message:
        print("; ".join(message), file=sys.stderr)
        if not process.udf.get("Comments"):
            process.udf["Comments"] = (
                "**Warnings from Indexes Placement checker EPP: **\n"
                + "\n".join(message)
            )
        elif (
            "Warnings from Indexes Placement checker EPP" not in process.udf["Comments"]
        ):
            process.udf["Comments"] += "\n\n"
            process.udf["Comments"] += (
                "**Warnings from Indexes Placement checker EPP: **\n"
            )
            process.udf["Comments"] += "\n".join(message)
        process.put()
    else:
        print("No issue detected with indexes or placement", file=sys.stderr)


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument("--pid", help="Lims id for current Process")
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args.pid)
