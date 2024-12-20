#!/usr/bin/env python
import logging
from argparse import ArgumentParser
from datetime import datetime as dt

from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.entities import Process
from genologics.lims import Lims

from scilifelab_epps.utils import udf_tools
from scilifelab_epps.wrapper import epp_decorator

TIMESTAMP = dt.now().strftime("%y%m%d_%H%M%S")


@epp_decorator(script_path=__file__, timestamp=TIMESTAMP)
def main(args):
    """This script will get the name of an artifact UDF from a master step field,
    and for every sample artifact in the current step:

    - Use API calls to recursively back-trace the sample history using
        input-output links until it finds an artifact with the specified UDF
    - Copy the value of the specified UDF from the found artifact to the
        artifact of the current step

    Example use-case:
    - For Nanopore libraries in the Aggregate QC step of the Library Validation protocol,
        fetch the last recorded artifact UDF "Size (bp)" from the library prep for all samples.
    """
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    process = Process(lims, id=args.pid)

    target_udf = process.udf.get(args.step_udf, None)
    if target_udf is None or target_udf == "None":
        logging.error(f"No target UDF supplied from step field '{args.step_udf}'")

    no_outputs = udf_tools.no_outputs(process)

    if no_outputs:
        logging.info("Step has no output artifacts. Assigning to input artifact.")

    # TODO need to tweak this script and possible the traceback function to handle both
    # TODO  aggregate QC and regular steps
    art_tuples = udf_tools.get_art_tuples(process)  # TODO this returns []
    for art_tuple in art_tuples:
        target_artifact = art_tuple[0]["uri"] if no_outputs else art_tuple[1]["uri"]
        logging.info(
            f"Looking for last recorded UDF '{target_udf}' of sample '{target_artifact.name}'..."
        )
        udf_value, udf_history = udf_tools.fetch_last(
            currentStep=process,
            art_tuple=art_tuple,
            target_udfs=target_udf,
            use_current=False,
            print_history=True,
            on_fail=None,
        )
        if udf_value:
            logging.info(f"Traceback:\n{udf_history}")
            target_artifact.udf[target_udf] = udf_value
            target_artifact.put()
            logging.info(
                f"Updated UDF '{target_udf}' for '{art_tuple[1]['uri'].name}' to '{udf_value}'"
            )
        else:
            logging.warning(
                f"Could not traceback UDF '{target_udf}' for '{art_tuple[1]['uri'].name}'"
            )
            logging.info(f"Traceback:\n{udf_history}")


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
        "--step_udf",
        required=True,
        type=str,
        help="The name of the step UDF listing the target artifact UDF.",
    )
    args = parser.parse_args()

    main(args)
