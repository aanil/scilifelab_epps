#!/usr/bin/env python
import glob
import logging
import os
from argparse import ArgumentParser, Namespace
from datetime import datetime as dt

import pandas as pd
from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.entities import Artifact, Process
from genologics.lims import Lims

from scilifelab_epps.utils import udf_tools
from scilifelab_epps.wrapper import epp_decorator

TIMESTAMP: str = dt.now().strftime("%y%m%d_%H%M%S")


def find_run(process: Process) -> str:
    """From the current step, use the ONT run info from previous step to find the run path."""

    assert len(process.all_inputs()) == 1, "Expected exactly one input artifact"

    run_name = process.all_inputs()[0].udf["ONT run name"]

    # Slap the ONT run name and GenStat link onto the LIMS step for good measure
    process.udf["ONT run name"] = os.path.basename(run_name)
    process.udf["GenStat link"] = (
        f"https://genomics-status.scilifelab.se/flowcells_ont/{run_name}"
    )
    process.put()

    run_query = f"/srv/ngi-nas-ns/minion_data/qc/{run_name}"
    logging.info(f"Looking for path {run_query}")

    run_glob = glob.glob(run_query)
    assert len(run_glob) != 0, f"Path {run_query} doesn't exist"
    assert len(run_glob) == 1, f"Multiple paths found for query {run_query}"

    run_path = run_glob[0]
    logging.info(f"Using run path {run_path}")

    return run_path


def find_latest_anglerfish_run(run_path: str) -> str:
    anglerfish_query = f"{run_path}/**/anglerfish_run*"
    logging.info(f"Looking for Anglerfish runs with query {anglerfish_query}")
    anglerfish_glob = glob.glob(anglerfish_query, recursive=True)

    assert len(anglerfish_glob) != 0, (
        f"No Anglerfish runs found for query {anglerfish_query}"
    )

    if len(anglerfish_glob) > 1:
        runs_list = "\n".join(anglerfish_glob)
        logging.warning(f"Multiple Anglerfish runs detected:\n{runs_list}")
    latest_anglerfish_run_path = max(anglerfish_glob, key=os.path.getctime)
    logging.info(f"Using latest Anglerfish run {latest_anglerfish_run_path}")

    return latest_anglerfish_run_path


def get_anglerfish_text_results(
    lims: Lims,
    process: Process,
    args: Namespace,
    latest_anglerfish_run_path: str,
):
    logging.info("Fetching Anglerfish results .txt-file...")

    txt_file_slot: Artifact = [
        outart for outart in process.all_outputs() if outart.name == args.txt_file
    ][0]

    file_name = "anglerfish_stats.txt"
    file_path = os.path.join(latest_anglerfish_run_path, file_name)
    assert os.path.exists(file_path), f"File {file_path} does not exist"

    # Upload results to LIMS
    lims.upload_new_file(txt_file_slot, file_path)


def get_anglerfish_dataframe(
    lims: Lims,
    process: Process,
    args: Namespace,
    latest_anglerfish_run_path: str,
) -> pd.DataFrame:
    logging.info("Fetching Anglerfish results .csv-file...")

    csv_file_slot: Artifact = [
        outart for outart in process.all_outputs() if outart.name == args.csv_file
    ][0]

    file_name = "anglerfish_dataframe.csv"
    file_path = os.path.join(latest_anglerfish_run_path, file_name)
    assert os.path.exists(file_path), f"File {file_path} does not exist"

    # Upload results to LIMS
    lims.upload_new_file(csv_file_slot, file_path)

    df_raw = pd.read_csv(file_path)

    return df_raw


def parse_data(df_raw: pd.DataFrame):
    df = df_raw.copy()

    # Subset df to pre-defined samples
    df_samples = df[df["sample_name"].notna()].copy()

    # Calculate representation metrics across pre-defined samples
    df_samples["repr_total_pc"] = (
        df_samples["num_reads"] / df_samples["num_reads"].sum() * 100
    )
    df_samples["repr_within_barcode_pc"] = df_samples.apply(
        # Sample reads divided by sum of all sample reads w. the same barcode
        lambda row: row["num_reads"]
        / df_samples[df_samples["ont_barcode"] == row["ont_barcode"]]["num_reads"].sum()
        * 100
        if not pd.isna(row["ont_barcode"])
        else None,
        axis=1,
    )

    # Merge new columns back into working df
    df = df.merge(
        df_samples[["repr_total_pc", "repr_within_barcode_pc"]],
        left_index=True,
        right_index=True,
        how="left",
    )

    # Get barcode number from ID
    df["ont_barcode_id"] = df["ont_barcode"].apply(
        lambda x: int(str(x)[-2:]) if pd.notna(x) else None
    )

    return df


def fill_udfs(process: Process, df: pd.DataFrame):
    """Try to assign UDFs to samples in LIMS.

    Iterate across all samples and UDFs prior to raising errors.
    """

    errors = False

    # Get Illumina samples
    measurements = []
    ops = process.all_outputs()
    for op in ops:
        if op.name in list(df.sample_name) and len(op.samples) == 1:
            measurements.append(op)
    measurements.sort(key=lambda x: x.name)

    assert len(measurements) == len(
        df[df["sample_name"].isin([m.name for m in measurements])]
    ), (
        "Number of samples demultiplexed in LIMS does not correspond to number of sample rows in Anglerfish results."
    )

    # Relate UDF names to dataframe column names
    udf2col = {
        "# Reads": "num_reads",
        "Avg. Read Length": "mean_read_len",
        "Std. Read Length": "std_read_len",
        "Representation Within Run (%)": "repr_total_pc",
        "Representation Within Barcode (%)": "repr_within_barcode_pc",
        "ONT Barcode ID": "ont_barcode_id",
    }

    for measurement in measurements:
        sample_name = measurement.name
        sample_row = df[df["sample_name"] == sample_name]

        # Assign UDFs
        for udf, col in udf2col.items():
            if pd.notna(sample_row[col].values[0]):
                value = float(sample_row[col].values[0])

                try:
                    udf_tools.put(measurement, udf, value)
                except AssertionError:
                    errors = True
                    logging.error(
                        f"Could not set UDF '{udf}' to '{value}' for sample '{sample_name}'"
                    )
                    continue

    if errors:
        raise AssertionError("Errors when populating sample UDFs.")


def parse_anglerfish_results(process, lims):
    run_path = find_run(process)

    latest_anglerfish_run_path = find_latest_anglerfish_run(run_path)

    # Upload Anglerfish files and load dataframe
    get_anglerfish_text_results(
        lims,
        process,
        args,
        latest_anglerfish_run_path,
    )

    df_raw: pd.DataFrame = get_anglerfish_dataframe(
        lims,
        process,
        args,
        latest_anglerfish_run_path,
    )

    # Parse the Anglerfish output
    df_parsed: pd.DataFrame = parse_data(df_raw)

    # Populate sample fields with Anglerfish results
    fill_udfs(process, df_parsed)


@epp_decorator(script_path=__file__, timestamp=TIMESTAMP)
def main(args):
    # Set up LIMS
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    process = Process(lims, id=args.pid)

    parse_anglerfish_results(process, lims)


if __name__ == "__main__":
    # Parse args
    parser = ArgumentParser()
    parser.add_argument(
        "--pid", default="24-594126", dest="pid", help="Lims id for current Process"
    )
    parser.add_argument(
        "--log",
        required=True,
        type=str,
        help="Which log file slot to use",
    )
    parser.add_argument(
        "--txt_file",
        required=True,
        type=str,
        help="Which file slot to use for the Anglerfish results",
    )
    parser.add_argument(
        "--csv_file",
        required=True,
        type=str,
        help="Which file slot to use for the Anglerfish dataframe",
    )
    args = parser.parse_args()

    main(args)
