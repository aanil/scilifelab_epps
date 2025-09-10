#!/usr/bin/env python

from argparse import ArgumentParser, Namespace
from datetime import datetime as dt

from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.entities import Process
from genologics.lims import Lims

from scilifelab_epps.wrapper import epp_decorator

TIMESTAMP = dt.now().strftime("%y%m%d_%H%M%S")


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
    file_id = matching_file_slot.files[0].id
    manifest_file_name = matching_file_slot.files[0].original_location
    manifest_file_contents = lims.get_file_contents(id=file_id)

    # Write and zip manifest(s)
    zip_file = manifest_file_name.replace(".csv", ".zip")


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
