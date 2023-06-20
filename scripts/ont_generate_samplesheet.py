#!/usr/bin/env python

from __future__ import division
from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process
from datetime import datetime as dt
import pandas as pd
import re
import sys
import shutil
from datetime import datetime as dt

DESC = """ Script for EPP "Generate ONT Sample Sheet" and file slot "ONT sample sheet".
Used to generate MinKNOW samplesheets.
"""


def main(lims, args):
    """
    === Sample sheet columns ===

    flow_cell_id                e.g. PAM96489
    position_id                 [1-3A-G] for PromethION, else None
    sample_id                   - For single samples:       e.g. P12345_101,
                                - For pools:                e.g. P12345_lims-pool-id
                                - For multi-project pools:  lims-pool-id
    experiment_id               lims-step-id
    flow_cell_product_code      e.g. FLO-MIN106D
    kit                         Product codes separated by spaces, e.g. SQK-LSK109 EXP-NBD196
    alias                       Only included for barcoded pools, sample name e.g. P12345_101
    barcode                     barcode01, barcode02, etc, fetched from LIMS

    === Constraints ===

    Must be the same across sheet:
    - kit
    - flow_cell_product_code
    - experiment_id

    Must be unique within sheet:
    - flow_cell_id
    - position_id
    - sample_id (TODO check if enforced by MinKNOW)

    Must be unique within the same flowcell
    - alias (TODO check if enforced by MinKNOW)
    - barcode (TODO check if enforced by MinKNOW)

    === Flowcell product codes ===

    FLO-PRO002 (PromethION R9.4.1)
    FLO-MIN106D (MinION R9.4.1)
    FLO-FLG001 (Flongle R9.4.1)
    FLO-PRO114M (PromethION R10.4.1)
    FLO-MIN114 (MinION R10.4.1)
    FLO-FLG114 (Flongle R10.4.1)

    === Outputs ===

    ONT_samplesheet_lims-step_yymmdd_hhmmss.csv
    """
    try:
        currentStep = Process(lims, id=args.pid)

        file_name = make_samplesheet(currentStep)
        upload_file(file_name, currentStep, lims)
        shutil.move(
            file_name, f"/srv/ngi-nas-ns/samplesheets/nanopore/{dt.now().year}/"
        )

    except AssertionError as e:
        sys.stderr.write(str(e))
        sys.exit(2)


def make_samplesheet(currentStep):
    arts = [art for art in currentStep.all_outputs() if art.type == "Analyte"]
    arts.sort(key=lambda art: art.id)

    rows = []
    for art in arts:
        row = {
            "flow_cell_id": art.udf.get("ONT flow cell ID"),
            "position_id": art.udf.get("ONT flow cell position"),
            "sample_id": get_minknow_sample_id(art),
            "experiment_id": f"{currentStep.id}",
            "flow_cell_product_code": currentStep.udf["ONT flow cell type"].split(" ")[
                0
            ],
            "flow_cell_type": currentStep.udf["ONT flow cell type"]
            .split(" ")[1]
            .strip("()"),
            "kit": get_kit_string(currentStep),
        }

        if "PromethION" in row["flow_cell_type"]:
            assert (
                row["position_id"] != "None"
            ), "Positions must be specified for PromethION flow cells."

        # Add extra columns for barcodes
        if len(art.reagent_labels) > 0:
            assert (
                currentStep.udf.get("ONT expansion kit") != "None"
            ), f"Barcodes found in pool {art.name}, but no barcode kit specified."
        if currentStep.udf.get("ONT expansion kit") != "None":
            assert (
                len(art.reagent_labels) > 0
            ), f"No barcodes found within pool {art.name}"
            label_tuples = [(e[0], e[1]) for e in zip(art.samples, art.reagent_labels)]
            label_tuples.sort(key=str)
            for sample, label in label_tuples:
                row["alias"] = strip_characters(sample.name)
                row["barcode"] = strip_characters(
                    "barcode" + label[0:2]
                )  # TODO double check extraction of barcode number
                rows.append(row.copy())
        else:
            rows.append(row)

        assert "" not in row.values(), "All fields must be populated."

    df = pd.DataFrame(rows)

    if len(arts) > 1:
        assert all(
            ["PromethION" in fc_type for fc_type in df.flow_cell_type.unique()]
        ), "Only PromethION flowcells can be grouped together in the same sample sheet."
        assert (
            len(arts) <= 24
        ), "Only up to 24 PromethION flowcells may be started at once."
    elif len(arts) == 1 and "MinION" in df.flow_cell_type[0]:
        assert (
            df.position_id[0] == "None"
        ), "MinION flow cells should not have a position assigned."

    assert (
        len(df.flow_cell_product_code.unique()) == len(df.kit.unique()) == 1
    ), "All rows must have the same flow cell type and kits"
    assert (
        len(df.position_id.unique()) == len(df.flow_cell_id.unique()) == len(arts)
    ), "All rows must have different flow cell positions and IDs"

    file_name = write_csv(df)

    return file_name


def upload_file(file_name, currentStep, lims):
    for out in currentStep.all_outputs():
        if out.name == "ONT sample sheet":
            for f in out.files:
                lims.request_session.delete(f.uri)
            lims.upload_new_file(out, file_name)


def write_csv(df):
    timestamp = dt.now().strftime("%y%m%d_%H%M%S")
    file_name = f"ONT_samplesheet_{df.experiment_id.unique()[0]}_{timestamp}.csv"

    columns = [
        "flow_cell_id",
        "position_id",
        "sample_id",
        "experiment_id",
        "flow_cell_product_code",
        "kit",
    ]

    if df.position_id[0] == "None":
        columns.remove("position_id")

    if "alias" in df.columns and "barcode" in df.columns:
        columns.append("alias")
        columns.append("barcode")

    df_csv = df.loc[:, columns]

    df_csv.to_csv(file_name, index=False)

    return file_name


def get_minknow_sample_id(art):
    """
    Assigns a MinKNOW sample ID based on the nature of the input artifact.
    Single samples, single-project pools and multi-project pools are treated differently.

    === Examples ===
    Type                    Contains                ID          Returns MinKNOW sample ID

    Single sample           PAAAAA_101              12-345678   PAAAAA_101
    Single project pool     PAAAAA_101, PAAAAA_102  23-456789   PAAAAA_23-456789
    Multi project pool      PAAAAA_101, PBBBBB_101  34-567890   34-567890
    """

    sample_id_pattern = re.compile("(P\d{5})_(\d+)")

    # Single sample
    if len(art.samples) == 1:
        re_match = re.match(sample_id_pattern, art.samples[0].name)
        if re_match:
            return re_match.group()
        else:
            return None

    # Pool
    else:
        # Look at the name of the first sample in the pool
        re_match = re.match(sample_id_pattern, art.samples[0].name)
        # If all samples in the pool have the same project
        if all(
            [
                re.match(sample_id_pattern, sample.name).groups()[0]
                == re_match.groups()[0]
                for sample in art.samples
            ]
        ):
            return f"{re_match.groups()[0]}_{art.id}"
        else:
            return art.id


def strip_characters(input_string):
    """Remove potentially problematic characters from string."""

    allowed_characters = re.compile("[^a-zA-Z0-9_-]")
    subbed_string = allowed_characters.sub("_", input_string)

    string_to_shorten = re.compile("__+")
    shortened_string = string_to_shorten.sub("_", subbed_string)

    return shortened_string


def get_kit_string(currentStep):
    """Combine prep kit and expansion kit UDFs (if any) into space-separated string"""
    kit_string = currentStep.udf.get("ONT prep kit")

    if currentStep.udf.get("ONT expansion kit") != "None":
        kit_string += f" {currentStep.udf.get('ONT expansion kit')}"

    return kit_string


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument("--pid", help="Lims id for current Process")
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)