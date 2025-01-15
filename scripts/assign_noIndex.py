#!/usr/bin/env python
import logging
from argparse import ArgumentParser
from datetime import datetime as dt
from xml.etree import ElementTree as ET

from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.entities import Process
from genologics.lims import Lims

from scilifelab_epps.wrapper import epp_decorator

DESC = """Script to automatically assign the 'noIndex' reagent label
to all unlabeled input samples of a step.
"""

TIMESTAMP: str = dt.now().strftime("%y%m%d_%H%M%S")


@epp_decorator(script_path=__file__, timestamp=TIMESTAMP)
def main(args):
    # Set up LIMS
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    process = Process(lims, id=args.pid)

    unlabeled_input_arts = [
        art
        for art in process.all_inputs()
        if not art.reagent_labels and art.type == "Analyte"
    ]

    xml_element_noIndex = ET.Element("reagent-label", name="NoIndex")
    failed_arts = []
    for art in unlabeled_input_arts:
        try:
            art.root.append(xml_element_noIndex)
            art.put()
        except Exception as e:
            logging.error(e)
            failed_arts.append(art)

    if failed_arts:
        logging.error(
            f"Failed to assign 'noIndex' reagent label to the following artifacts: {', '.join(art.name for art in failed_arts)}"
        )


if __name__ == "__main__":
    # Parse args
    parser = ArgumentParser(description=DESC)
    parser.add_argument("--pid", type=str, help="Lims ID for current Process")
    parser.add_argument("--log", type=str, help="Which log file slot to use")

    args = parser.parse_args()

    main(args)
