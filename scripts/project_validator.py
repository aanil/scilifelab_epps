#!/usr/bin/env python

import re
import smtplib
import sys
import warnings
from argparse import ArgumentParser
from email.message import Message
from email.mime.text import MIMEText
from io import BytesIO
from typing import TypedDict, cast

from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.entities import Project
from genologics.lims import Lims
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from scilifelab_epps.utils.get_epp_user import get_epp_user

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

DESC = """EPP used to validate a project including checking sample name format, index format and index distance in library pool.
"""

# Pre-compile regexes in global scope:
NGISAMPLE_PAT = re.compile("P[0-9]+_[0-9]+")
INDEX_PAT = re.compile(
    r"^([ATGC]{6,24}(-[ATGC]{6,12})?|SI-[A-Z0-9]{2,4}-[A-Z]\d{1,2}|NB\d{2}|BC\d{2}|NoIndex)$"
)


# Verify sample IDs
def verify_sample_ids(lims, project):
    """Validate project sample IDs for format, count, and sequence."""
    message = []

    # Get all samples in the project
    samples = lims.get_samples(projectname=project.name)

    if not samples:
        message.append(
            f"SAMPLE COUNT WARNING: No samples found for project {project.id}"
        )
        return message

    ngi_ids = []
    customer_names = []

    # Validate sample name format and collect data
    for sample in sorted(samples, key=lambda s: s.name):
        sample_id = sample.name
        customer_name = sample.udf.get("Customer Name")

        ngi_ids.append(sample_id)
        if customer_name:
            customer_names.append(customer_name)

        # Validate format and prefix match
        if not NGISAMPLE_PAT.search(sample_id):
            message.append(f"SAMPLE NAME WARNING: Bad sample ID format {sample_id}")
        elif sample_id.split("_")[0] != project.id:
            message.append(
                f"SAMPLE NAME WARNING: Sample ID {sample_id} does not match "
                f"project ID {project.id}"
            )

    # Check count consistency
    if len(ngi_ids) != len(customer_names):
        message.append(
            f"SAMPLE COUNT WARNING: Mismatch between NGI Sample IDs ({len(ngi_ids)}) "
            f"and customer sample names ({len(customer_names)})"
        )

    # Validate sample numbering: group by plate digit, check first sample and gaps
    if ngi_ids:
        try:
            # Group samples by plate digit (first digit of suffix: _1XXX, _2XXX, etc.)
            plates = {}
            for sample_id in ngi_ids:
                sample_suffix = sample_id.split("_")[1] if "_" in sample_id else None
                if sample_suffix:
                    plate_digit = sample_suffix[0]
                    suffix_num = int(sample_suffix)
                    if plate_digit not in plates:
                        plates[plate_digit] = []
                    plates[plate_digit].append(suffix_num)

            # Validate each plate: first sample must be X001 or X01, check gaps
            for plate_digit in sorted(plates.keys()):
                plate_suffixes = sorted(plates[plate_digit])

                # Check first sample starts with X001 or X01
                expected_values = (
                    int(f"{plate_digit}001"),
                    int(f"{plate_digit}01"),
                )
                if plate_suffixes[0] not in expected_values:
                    message.append(
                        f"SAMPLE SEQUENCE WARNING: Plate {plate_digit} first "
                        f"sample should be _{plate_digit}001 or _{plate_digit}01, "
                        f"but got _{plate_suffixes[0]}"
                    )

                # Check gaps within plate
                for curr, next_val in zip(plate_suffixes, plate_suffixes[1:]):
                    if next_val - curr != 1:
                        message.append(
                            f"SAMPLE SEQUENCE WARNING: Gap detected in plate "
                            f"{plate_digit} numbering between {curr} and "
                            f"{next_val}. Verify missing samples in the "
                            f"uploaded CSV file."
                        )
        except (ValueError, IndexError):
            pass  # Skip validation if suffix extraction fails

    return message


def verify_indexes(lims, project):
    """Validate that all 4-digit samples have valid index formats."""
    message = []

    samples = lims.get_samples(projectname=project.name)
    for sample in samples:
        # Only validate 4-digit suffix samples (finished libraries)
        suffix = sample.name.split("_")[1] if "_" in sample.name else ""
        if len(suffix) == 4:
            # Check if index exists and is valid
            if not sample.artifact.reagent_labels:
                message.append(f"INDEX WARNING: Sample {sample.name} has no index")
            else:
                index = sample.artifact.reagent_labels[0].strip()
                if not index:
                    message.append(f"INDEX WARNING: Sample {sample.name} has no index")
                elif not INDEX_PAT.match(index):
                    message.append(
                        f"INDEX WARNING: Sample {sample.name} has invalid index '{index}'"
                    )
IDX_PAT = re.compile("([ATCG]{4,}N*)-?([ATCG]*)")
VALIDBASES_PAT = re.compile(r"^[ATCG\-]+$")
TENX_SINGLE_PAT = re.compile("SI-(?:GA|NA)-[A-H][1-9][0-2]?")
TENX_DUAL_PAT = re.compile("SI-(?:TT|NT|NN|TN|TS)-[A-H][1-9][0-2]?")
SMARTSEQ_PAT = re.compile("SMARTSEQ[1-9]?-[1-9][0-9]?[A-P]")


class IndexPair(TypedDict):
    idx1: str
    idx2: str


class WellData(TypedDict):
    count: int
    indexes: list[IndexPair]
    index_length: set[int]


def get_header_columns(worksheet: Worksheet) -> dict[str, int]:
    header_row = list(worksheet.iter_rows(min_row=17, max_row=17, values_only=True))[0]
    return {header: idx for idx, header in enumerate(header_row) if header is not None}


def get_index_format_error(index: str) -> str | None:
    if TENX_SINGLE_PAT.fullmatch(index):
        return None
    if TENX_DUAL_PAT.fullmatch(index):
        return None
    if SMARTSEQ_PAT.fullmatch(index):
        return None

    if not IDX_PAT.fullmatch(index):
        return "does not match known index patterns"
    parts = index.split("-")
    if len(parts) > 2:
        return "too many parts (expected single or dual index)"
    if any(part == "" for part in parts):
        return "empty part around '-'"

    if not VALIDBASES_PAT.fullmatch(index):
        return "contains invalid characters (allowed: A, T, C, G, -)"

    return None


def email_responsible(
    message: str,
    resp_email: str,
    subject: str,
) -> None:
    msg: Message
    body = "Samplesheet validation Errors: \n" + message
    body += "\n\n--\nThis is an automatically generated error notification"
    msg = MIMEText(body)
    msg["Subject"] = subject

    msg["From"] = "Lims_monitor"
    msg["To"] = resp_email

    with smtplib.SMTP("localhost") as s:
        s.sendmail("genologics-lims@scilifelab.se", msg["To"], msg.as_string())


def verify_samplename(sample_name: str, proj_id: str) -> set[str]:
    message = set()
    if not NGISAMPLE_PAT.findall(sample_name):
        message.add(f"SAMPLE NAME WARNING: Bad sample name format {sample_name}")
    else:
        if sample_name.split("_")[0] != proj_id:
            message.add(
                f"SAMPLE NAME WARNING: Sample name {sample_name} does not match project ID {proj_id}"
            )
    return message


def main(lims, pid):
    """Validate a project and exit with appropriate status code."""
def my_distance(idx_a: str, idx_b: str) -> int:
    diffs = 0
    short = min((idx_a, idx_b), key=len)
    lon = idx_a if short == idx_b else idx_b
    for i, c in enumerate(short):
        if c != lon[i]:
            diffs += 1
    return diffs


def parse_library_info_sheet(
    worksheet: Worksheet, proj_id: str
) -> tuple[dict[str, WellData], set[str]]:
    data: dict[str, WellData] = {}
    message: set[str] = set()
    headers = get_header_columns(worksheet)
    sample_name_col = headers.get("Sample/Name")
    well_col = headers.get("UDF/Pooling")
    index_col = headers.get("Sample/Reagent Label")
    for row in worksheet.iter_rows(min_row=20, values_only=True):
        sample_name = cast(str | None, row[sample_name_col])
        well = cast(str | None, row[well_col])
        index = cast(str | None, row[index_col])
        if sample_name is None or well is None:
            continue
        message.update(verify_samplename(sample_name, proj_id))
        if well not in data:
            data[well] = {"count": 1, "indexes": [], "index_length": set()}
            # Initialize WellData TypedDict correctly
        else:
            data[well]["count"] += 1
            if index is not None:
                data[well]["index_length"].add(len(index))
                if (
                    len(data[well]["index_length"]) > 1
                ):  # Assuming first index has the correct length
                    data[well]["index_length"].remove(
                        len(index)
                    )  # Remove the different length to avoid multiple warnings for the same issue
                    common_index = data[well]["index_length"].pop()
                    message.add(
                        f"INDEX LENGTH WARNING: Multiple index lengths noticed in pool {well} for Sample {sample_name}, length {len(index)} is different from {common_index}"
                    )
                    data[well]["index_length"].add(common_index)

        if index == "" or index is None:
            message.add(
                f"EMPTY INDEX: Sample {sample_name} in well {well} has an empty index"
            )
        else:
            if index == "NoIndex":
                if data[well]["count"] > 1:
                    message.add(
                        f"NOINDEX ERROR: Well {well} has NoIndex but but contains more than one sample"
                    )
            else:
                reason = get_index_format_error(index)
                if reason:
                    message.add(
                        f"INDEX FORMAT ERROR: Sample {sample_name} with index '{index}' has a bad format: {reason}"
                    )
                else:
                    idxs = (
                        TENX_SINGLE_PAT.findall(index)
                        or TENX_DUAL_PAT.findall(index)
                        or SMARTSEQ_PAT.findall(index)
                    )
                    if idxs:
                        # Skip TENX and SMARTSEQ indexes for now
                        pass
                    else:
                        try:
                            idxs = IDX_PAT.findall(index)[0]
                            curr_idx: IndexPair = {
                                "idx1": idxs[0],
                                "idx2": idxs[1] if len(idxs) > 1 else "",
                            }
                            data[well]["indexes"].append(curr_idx)
                            for prev_idx in data[well]["indexes"][:-1]:
                                dist = 0
                                dist += my_distance(prev_idx["idx1"], curr_idx["idx1"])
                                if prev_idx.get("idx2", "") and curr_idx.get(
                                    "idx2", ""
                                ):
                                    dist += my_distance(
                                        prev_idx["idx2"], curr_idx["idx2"]
                                    )
                                if dist < 2:
                                    idx_a = (
                                        prev_idx.get("idx1", "")
                                        + "-"
                                        + prev_idx.get("idx2", "")
                                    )
                                    idx_b = (
                                        curr_idx.get("idx1", "")
                                        + "-"
                                        + curr_idx.get("idx2", "")
                                    )
                                    if dist == 0:
                                        message.add(
                                            f"INDEX COLLISION ERROR: Index {idx_a} and Index {idx_b} (for sample {sample_name}) in pool {well}"
                                        )
                                    else:
                                        message.add(
                                            f"SIMILAR INDEX WARNING: Index {idx_a} and Index {idx_b} (for sample {sample_name}) in pool {well}"
                                        )
                        except IndexError:
                            # try:
                            # we only have the reagent label name.
                            pass
                            # rt = lims.get_reagent_types(name=reagent_label_name)[0]
                            # idxs = IDX_PAT.findall(rt.sequence)[0]
                            # sample_idxs.add(idxs)
                            # except:
                            #    sample_idxs.add(("NoIndex", ""))
    return data, message


def main(lims: Lims, pid: str, auto: bool) -> None:
    message = []
    project = Project(lims, id=pid)
    if not project.files:
        sys.stderr.write("No samplesheet file found for the project.\n")
        sys.exit(1)
    for samplesheet_file in project.files:
        stream = lims.get_file_contents(uri=samplesheet_file.uri)
        data = stream.read()
        workbooks = load_workbook(BytesIO(data), read_only=True, data_only=True)
        worksheet = workbooks.active
        file_name = samplesheet_file.original_location
        library_information = (
            "Library_information"
            in list(worksheet.iter_rows(min_row=3, max_row=3, values_only=True))[0][12]
        )
        # sample_information = 'Sample_information' in list(worksheet.iter_rows(min_row=4, max_row=4, values_only=True))[0][8]

    # Validate sample IDs
    message += verify_sample_ids(lims, project)

    # Validate indexes for finished libraries
    message += verify_indexes(lims, project)

    if not message:
        print(f"No issue detected for project {pid}")
        if library_information:
            data, lib_info_message = parse_library_info_sheet(worksheet, pid)
            if lib_info_message:
                message.extend(
                    [f"\n\nFile: {file_name} \n" + "\n".join(lib_info_message)]
                )
    if message:
        resp_email = get_epp_user(lims, project_id=pid).email
        if auto:
            if not resp_email:
                print(
                    "**Errors exist in the samplesheet: **\n"
                    "Email with the error could not be sent as no email address was found for the EPP user.\n"
                    + "\n".join(message),
                    file=sys.stderr,
                )
            else:
                print(
                    "**Errors exist in the samplesheet: **\n"
                    f"Email with the error has been sent to {resp_email}.\n"
                )
                email_responsible(
                    message="\n".join(message),
                    resp_email=resp_email,
                    subject=f"[Error] Project {pid} failed sample sheet validation",
                )
        else:
            sys.stderr.write("; ".join(message))
    else:
        print("No issue detected with indexes or placement")

    with open("index_checker.log", "w") as logContext:
        logContext.write("\n".join(message))
    # Throw red warning message when it is not automatically run
    if not auto and not message:
        sys.exit(0)


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument("--pid", help="Project ID for current Project")
    parser.add_argument(
        "--log",
        dest="log",
        help=("File name for standard log file, for runtime information and problems."),
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help=("Used when the script is running automatically in LIMS."),
    )
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args.pid, args.auto)
