#!/usr/bin/env python

DESC = """EPP script to calculate molar concentration given the
weight concentration, in Clarity LIMS. Before updating the artifacts,
the script verifies that 'Concentration' and 'Size (bp)' udf:s are not blank,
 and that the 'Conc. units' field is 'ng/ul' for each artifact. Artifacts
that do not fulfill the requirements, will not be updated.

Written by Johannes Alneberg, Science for Life Laboratory, Stockholm, Sweden
"""
import logging
import sys
from argparse import ArgumentParser

from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.entities import Process
from genologics.lims import Lims

from scilifelab_epps.epp import EppLogger
from scilifelab_epps.utils.formula import ng_ul_to_nM


def apply_calculations(lims, artifacts, conc_udf, size_udf, unit_udf, epp_logger):
    for artifact in artifacts:
        logging.info(
            f"Updating: Artifact id: {artifact.id}, "
            f"Concentration: {artifact.udf[conc_udf]}, Size: {artifact.udf[size_udf]}, "
        )
        artifact.udf[conc_udf] = ng_ul_to_nM(
            artifact.udf[conc_udf], artifact.udf[size_udf]
        )
        artifact.udf[unit_udf] = "nM"
        artifact.put()
        logging.info(f"Updated {conc_udf} to {artifact.udf[conc_udf]}.")


def check_udf_is_defined(artifacts, udf):
    """Filter and Warn if udf is not defined for any of artifacts."""
    filtered_artifacts = []
    incorrect_artifacts = []
    for artifact in artifacts:
        if (udf in artifact.udf) and artifact.udf[udf] != 0:
            filtered_artifacts.append(artifact)
        else:
            logging.warning(
                f"Found artifact for sample {artifact.samples[0].name} with {udf} "
                "undefined/blank, skipping"
            )
            incorrect_artifacts.append(artifact)
    return filtered_artifacts, incorrect_artifacts


def check_udf_has_value(artifacts, udf, value):
    """Filter artifacts on undefined udf or if udf has wrong value."""
    filtered_artifacts = []
    incorrect_artifacts = []
    for artifact in artifacts:
        if udf in artifact.udf and (artifact.udf[udf] == value):
            filtered_artifacts.append(artifact)
        elif udf in artifact.udf:
            incorrect_artifacts.append(artifact)
            logging.warning(
                f"Filtered out artifact for sample: {artifact.samples[0].name}"
                f", due to wrong {udf}"
            )
        else:
            incorrect_artifacts.append(artifact)
            logging.warning(
                f"Filtered out artifact for sample: {artifact.samples[0].name}"
                f", due to undefined/blank {udf}"
            )

    return filtered_artifacts, incorrect_artifacts


def main(lims, args, epp_logger):
    p = Process(lims, id=args.pid)
    udf_check = "Conc. Units"
    value_check = "ng/ul"
    concentration_udf = "Concentration"
    size_udf = "Size (bp)"

    if args.aggregate:
        artifacts = p.all_inputs(unique=True)
    else:
        all_artifacts = p.all_outputs(unique=True)
        artifacts = [a for a in all_artifacts if a.output_type == "ResultFile"]

    correct_artifacts, no_concentration = check_udf_is_defined(
        artifacts, concentration_udf
    )
    correct_artifacts, no_size = check_udf_is_defined(correct_artifacts, size_udf)
    correct_artifacts, wrong_value = check_udf_has_value(
        correct_artifacts, udf_check, value_check
    )

    apply_calculations(
        lims, correct_artifacts, concentration_udf, size_udf, udf_check, epp_logger
    )

    d = {
        "ca": len(correct_artifacts),
        "ia": len(wrong_value) + len(no_size) + len(no_concentration),
    }

    abstract = (
        "Updated {ca} artifact(s), skipped {ia} artifact(s) with "
        "wrong and/or blank values for some udfs."
    ).format(**d)

    print(abstract, file=sys.stderr)  # stderr will be logged and printed in GUI


if __name__ == "__main__":
    # Initialize parser with standard arguments and description
    parser = ArgumentParser(description=DESC)
    parser.add_argument("--pid", help="Lims id for current Process")
    parser.add_argument(
        "--log",
        default=sys.stdout,
        help=("File name for standard log file, for runtime information and problems."),
    )
    parser.add_argument(
        "--aggregate",
        action="store_true",
        help=(
            "Use this tag if your process is aggregating "
            "results. The default behaviour assumes it is "
            "the output artifact of type analyte that is "
            "modified while this tag changes this to using "
            "input artifacts instead"
        ),
    )

    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    with EppLogger(args.log, lims=lims, prepend=True) as epp_logger:
        main(lims, args, epp_logger)
