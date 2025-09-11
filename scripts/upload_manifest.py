#!/usr/bin/env python

from argparse import ArgumentParser, Namespace
from datetime import datetime as dt
from zipfile import ZipFile
import os
import logging


from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.entities import Process
from genologics.lims import Lims

from scilifelab_epps.wrapper import epp_decorator

TIMESTAMP = dt.now().strftime("%y%m%d_%H%M%S")


def get_flowcell_id(process: Process) -> str:
    """Get the Element flowcell ID from the process."""
    flowcell_ids = [
        op.container.name for op in process.all_outputs() if op.type == "Analyte"
    ]

    assert len(set(flowcell_ids)) == 1, "Expected one flowcell ID."
    flowcell_id = flowcell_ids[0]

    if "-" in flowcell_id:
        logging.warning(
            f"Container name {flowcell_id} contains a dash, did you forget to set the name of the LIMS container to the flowcell ID?"
        )

    return flowcell_id


@epp_decorator(script_path=__file__, timestamp=TIMESTAMP)
def main(args: Namespace):
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    process = Process(lims, id=args.pid)

    matching_file_slots = [
        art
        for art in process.all_outputs()
        if art.name == args.file and art.type == "ResultFile"
    ]

    assert (
        len(matching_file_slots) == 1
    ), f"Could not find single file slot matching to '{args.file}'."
    matching_file_slot = matching_file_slots[0]
    assert matching_file_slot.files, f"'{matching_file_slot.name}' file slot is empty."
    manifest_file_name = matching_file_slot.files[0].original_location
    file_id = matching_file_slot.files[0].id
    manifest_file_contents = lims.get_file_contents(id=file_id)
    manifest_file_contents_list = manifest_file_contents.split("\n")

    # for line in manifest_file_contents_list:
    for keyname_index, line in enumerate(manifest_file_contents_list):
        if "KeyName" in line and "Value" in line:
            break
    manifest_file_contents_list.insert(
        keyname_index + 1, f"copy from original file,{manifest_file_name}"
    )
    manifest_file_contents_altered = "\n".join(manifest_file_contents_list)

    # Write and zip manifest(s)
    flowcell_id = get_flowcell_id(process)
    new_root_manifest_file_name = f"AVITI_run_manifest_{flowcell_id}_{process.id}_{TIMESTAMP}_{process.technician.name.replace(' ', '')}"
    new_manifest_csv_file_name = f"{new_root_manifest_file_name}.csv"
    new_manifest_zip_file_name = f"{new_root_manifest_file_name}.zip"

    with ZipFile(new_manifest_zip_file_name, "w") as zip_stream:
        open(new_manifest_csv_file_name, "w").write(manifest_file_contents_altered)
        zip_stream.write(new_manifest_csv_file_name)
        os.remove(new_manifest_csv_file_name)
    logging.info(
        f".csv file '{manifest_file_name}' has been saved as .zip file '{new_manifest_zip_file_name}'"
    )


if __name__ == "__main__":
    # Parse args
    parser = ArgumentParser()
    parser.add_argument(
        "--pid",
        required=True,
        type=str,
        help="Lims ID for current Process.",
    )
    parser.add_argument(
        "--log",
        required=True,
        type=str,
        help="Which file slot to use for the script log.",
    )
    parser.add_argument(
        "--file",
        required=True,
        type=str,
        help="Which file slot to take the run manifest from.",
    )
    args = parser.parse_args()

    main(args)
