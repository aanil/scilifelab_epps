#!/usr/bin/env python
import datetime
import logging
import subprocess
import sys
from argparse import ArgumentParser

from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.entities import Process
from genologics.lims import Lims

from scilifelab_epps.epp import EppLogger


def makeContainerBarcode(plateid, copies=1):
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
    # height 70, no interpreation line.
    lines.append("^FO70,10^BCN,70,N,N^FN2^FS")
    lines.append("^XZ")  # end format

    for copy in range(copies):
        lines.append("^XA")  # start of label format
        lines.append("^XFFORMAT^FS")  # label home position
        lines.append("^FN1^FD" + plateid + "^FS")  # this is readable
        lines.append("^FN2^FD" + plateid + "^FS")  # this is also readable
        lines.append("^XZ")
    return lines


def makeContainerNameBarcode(plate_name, copies=1):
    """Constrcut label with container name as human readable"""
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

    for copy in range(copies):
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
    for copy in range(copies):
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

    for copy in range(copies):
        lines.append("^XA")  # start of label format
        lines.append("^XFFORMAT^FS")  # label home position
        lines.append("^FN1^FD" + process_name + "^FS")  # this is readable
        lines.append("^XZ")
    return lines


def getArgs():
    desc = (
        " Print barcodes on zebra barcode printer, "
        " different label types available. Information "
        " is fetched from Clarity LIMS."
    )
    parser = ArgumentParser(description=desc)
    parser.add_argument(
        "--container_id",
        action="store_true",
        help=(
            "Print output container id label in both barcode format and human readable."
        ),
    )
    parser.add_argument(
        "--operator_and_date",
        action="store_true",
        help=("Print label with both operator and todays date."),
    )
    parser.add_argument(
        "--container_name",
        action="store_true",
        help=("Print label with human readablecontainer name (user defined)"),
    )
    parser.add_argument(
        "--process_name",
        action="store_true",
        help=("Print label with human readableprocess name"),
    )
    parser.add_argument(
        "--copies",
        default=1,
        type=int,
        help=(
            "Number of printout copies, only used"
            " if neither container_name nor container_id"
            " type labels are printed. In that case, print"
            " one label of each type for each container."
        ),
    )
    parser.add_argument("--pid", help="The process LIMS id.")
    parser.add_argument("--log", help="File name to use as log file")
    parser.add_argument(
        "--use_printer",
        action="store_true",
        help=("Print file on default or supplied printer using lp command."),
    )
    parser.add_argument("--hostname", help="Hostname for lp CUPS server.")
    parser.add_argument("--destination", help="Name of printer.")
    parser.add_argument(
        "--no_prepend",
        action="store_true",
        help="Do not prepend old log, useful when ran locally",
    )
    return parser.parse_args()


def main(args, lims, epp_logger):
    p = Process(lims, id=args.pid)
    lines = []
    cs = []
    if args.container_id:
        cs = p.output_containers()
        for c in cs:
            logging.info(f"Constructing barcode for container {c.id}.")
            lines += makeContainerBarcode(c.id, copies=1)
    if args.container_name:
        cs = p.output_containers()
        for c in cs:
            logging.info(f"Constructing name label for container {c.id}.")
            lines += makeContainerNameBarcode(c.name, copies=1)
    if args.operator_and_date:
        op = p.technician.name
        date = str(datetime.date.today())
        if cs:  # list of containers
            copies = len(cs)
        else:
            copies = args.copies
        lines += makeOperatorAndDateBarcode(op, date, copies=copies)
    if args.process_name:
        pn = p.type.name
        if cs:  # list of containers
            copies = len(cs)
        else:
            copies = args.copies
        lines += makeProcessNameBarcode(pn, copies=copies)
    if not (
        args.container_id
        or args.container_name
        or args.operator_and_date
        or args.process_name
    ):
        logging.info("No recognized label type given, exiting.")
        sys.exit(-1)
    if not args.use_printer:
        logging.info("Writing to stdout.")
        epp_logger.saved_stdout.write("\n".join(lines) + "\n")
    elif lines:  # Avoid printing empty files
        lp_args = ["lp"]
        if args.hostname:
            # remove that when all the calls to this script have been updated
            if args.hostname == "homer.scilifelab.se:631":
                args.hostname = "homer2.scilifelab.se:631"
            lp_args += ["-h", args.hostname]
        if args.destination:
            lp_args += ["-d", args.destination]
        lp_args.append("-")  # lp accepts stdin if '-' is given as filename
        logging.info("Ready to call lp for printing.")
        sp = subprocess.Popen(
            lp_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf8",
        )
        sp.stdin.write(str("\n".join(lines)))
        logging.info("lp command is called for printing.")
        stdout, stderr = sp.communicate()  # Will wait for sp to finish
        logging.info(f"lp stdout: {stdout}")
        logging.info(f"lp stderr: {stderr}")
        logging.info("lp command finished")
        sp.stdin.close()


if __name__ == "__main__":
    arguments = getArgs()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    prepend = not arguments.no_prepend
    with EppLogger(arguments.log, lims=lims, prepend=prepend) as epp_logger:
        main(arguments, lims, epp_logger)
