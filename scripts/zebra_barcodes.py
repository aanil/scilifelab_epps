#!/usr/bin/env python
import logging
import subprocess
from argparse import ArgumentParser
from datetime import datetime as dt

from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.entities import Process
from genologics.lims import Lims

from scilifelab_epps.wrapper import epp_decorator, upload_file

TIMESTAMP = dt.now().strftime("%y%m%d_%H%M%S")


def make_container_label(plateid, copies=1):
    """Construct label with container id as human readable and barcode"""
    lines = []
    lines.append("^XA")  # start of label
    # download and store format, name of format,
    # end of field data (FS = field stop)
    lines.append("^DFFORMAT^FS")
    lines.append("^LH0,0")  # label home position (label home = LH)
    # AF = assign font F, field number 1 (FN1),
    # print text at position field origin (FO) rel. to home
    lines.append("^FO360,30^AFN 78,39^FN1^FS")
    # BC=barcode 128, field number 2, Normal orientation,
    # height 70, no interpretation line.
    lines.append("^FO70,10^BCN,70,N,N^FN2^FS")
    lines.append("^XZ")  # end format

    for _ in range(copies):
        lines.append("^XA")  # start of label format
        lines.append("^XFFORMAT^FS")  # label home position
        lines.append("^FN1^FD" + plateid + "^FS")  # this is readable
        lines.append("^FN2^FD" + plateid + "^FS")  # this is also readable
        lines.append("^XZ")
    return lines


def makeContainerNameBarcode(plate_name, copies=1):
    """Construct label with container name as human readable"""
    lines = []
    lines.append("^XA")  # start of label
    # download and store format, name of format,
    # end of field data (FS = field stop)
    lines.append("^DFFORMAT^FS")
    lines.append("^LH0,0")  # label home position (label home = LH)
    # AF = assign font F, field number 1 (FN1),
    # print text at position field origin (FO) rel. to home
    if len(plate_name) > 21:
        # Use smaller font, fits 28 chars
        lines.append("^FO20,40^AFN 54,30^FN1^FS")
    else:
        # Use larger font, fits 21 chars
        lines.append("^FO20,30^AFN 78,39^FN1^FS")

    lines.append("^XZ")  # end format

    for _ in range(copies):
        lines.append("^XA")  # start of label format
        lines.append("^XFFORMAT^FS")  # label home position
        lines.append("^FN1^FD" + plate_name + "^FS")  # this is readable
        lines.append("^XZ")
    return lines


def makeOperatorAndDateBarcode(operator, date, copies=1):
    """Construct label with operator name and date in human readable format"""
    lines = []
    lines.append("^XA")  # start of label
    # Download and store format, name of format,
    # end of field data (FS = field stop)
    lines.append("^DFFORMAT^FS")
    lines.append("^LH0,0")  # label home position (label home = LH)
    # AF = assign font F, field number 1 (FN1),
    # print text at position field origin (FO) rel. to home
    lines.append("^FO420,35^ADN,36,20^FN1^FS")
    lines.append("^FO20,35^ADN,36,20^FN2^FS")
    lines.append("^XZ")  # end format

    if len(operator) > 19:
        operator = operator[:19]  # If string is longer, it would cover the date
    for _ in range(copies):
        lines.append("^XA")  # start of label format
        lines.append("^XFFORMAT^FS")  # label home position
        lines.append("^FN1^FD" + date + "^FS")  # this is readable
        lines.append("^FN2^FD" + operator + "^FS")  # this is also readable
        lines.append("^XZ")
    return lines


def makeProcessNameBarcode(process_name, copies=1):
    """Constrcut label with process name as human readable"""
    lines = []
    lines.append("^XA")  # start of label
    # download and store format, name of format,
    # end of field data (FS = field stop)
    lines.append("^DFFORMAT^FS")
    lines.append("^LH0,0")  # label home position (label home = LH)
    # AF = assign font F, field number 1 (FN1),
    # print text at position field origin (FO) rel. to home
    if len(process_name) > 21:
        # Use smaller font, fits 28 chars
        lines.append("^FO20,40^ADN 54,30^FN1^FS")
    else:
        # Use larger font, fits 21 chars
        lines.append("^FO20,30^AFN 78,39^FN1^FS")

    lines.append("^XZ")  # end format

    for _ in range(copies):
        lines.append("^XA")  # start of label format
        lines.append("^XFFORMAT^FS")  # label home position
        lines.append("^FN1^FD" + process_name + "^FS")  # this is readable
        lines.append("^XZ")
    return lines


@epp_decorator(script_path=__file__, timestamp=TIMESTAMP)
def main(args):
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    process = Process(lims, id=args.pid)

    # Build a list of ZPL (=Zebra Programming Language) lines, corresponding to 4 labels per output container
    zpl_code = []
    for container in process.output_containers():
        logging.info(
            f"Making label for container ID with barcode: <barcode> {container.id}"
        )
        zpl_code += make_container_label(container.id)

        logging.info(f"Making label for container ID: {container.id}.")
        zpl_code += makeContainerNameBarcode(container.name)

        logging.info(
            f"Making label for operator and date: {process.technician.name} {str(dt.date.today())}"
        )
        zpl_code += makeOperatorAndDateBarcode(
            process.technician.name, str(dt.date.today())
        )

        logging.info(f"Making label for step name: {process.type.name}")
        zpl_code += makeProcessNameBarcode(process.type.name)

    logging.info(f"Full ZPL contents: {'\n'.join(zpl_code)}")

    # Build args list to label printer command
    lp_args = ["lp"]
    lp_args += ["-h", "homer2.scilifelab.se:631"]
    lp_args += ["-d", "zebrabarcode"]
    lp_args.append("-")  # make lp command read from stdin
    logging.info(f"Using command: {' '.join(lp_args)}")

    # Call label printer command
    logging.info("Calling command...")
    lp_process = subprocess.Popen(
        lp_args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf8",
    )
    lp_process.stdin.write("\n".join(zpl_code))
    logging.info("Supplied ZPL contents.")
    stdout, stderr = lp_process.communicate()  # Will wait for subprocess to finish
    logging.info(f"lp stdout: {stdout}")
    logging.info(f"lp stderr: {stderr}")
    logging.info("Command finished, closing subprocess.")
    lp_process.stdin.close()

    # Upload barcode file (ZPL contents), will persist after finishing step, useful for re-prints and doing LIMS from home
    filename = f"labels_{process.id}_{TIMESTAMP}.txt"
    logging.info(f"Uploading ZPL contents as {filename}")

    with open(filename, "w") as f:
        f.write("\n".join(zpl_code))

    upload_file(filename, args.file, process, lims, remove=True)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--pid", help="The process LIMS id.")
    parser.add_argument("--file", help="LIMS file slot name to use for barcode file.")
    parser.add_argument("--log", help="LIMS file slot name to use for log file.")
    args = parser.parse_args()

    main(args)
