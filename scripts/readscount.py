#!/usr/bin/env python
DESC = """EPP script to aggregate the number of reads from different demultiplexing runs,
based on the flag 'include reads' located at the same level as '# reads'

Denis Moreno, Science for Life Laboratory, Stockholm, Sweden
"""
import logging
import os
from argparse import ArgumentParser

from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.entities import Process
from genologics.lims import Lims

from scilifelab_epps.epp import EppLogger, attach_file

DEMULTIPLEX = {
    "13": "Bcl Conversion & Demultiplexing (Illumina SBS) 4.0",
    "3205": "ONT Finish Sequencing v3",  # TODO Update this to reflect prod
    # TODO Add AVITI
}
SUMMARY = {
    "356": "Project Summary 1.3",
}
SEQUENCING = {
    "38": "Illumina Sequencing (Illumina SBS) 4.0",
    "46": "MiSeq Run (MiSeq) 4.0",
    "714": "Illumina Sequencing (HiSeq X) 1.0",
    "1454": "AUTOMATED - NovaSeq Run (NovaSeq 6000 v2.0)",
    "1908": "Illumina Sequencing (NextSeq) v1.0",
    "2612": "NovaSeqXPlus Run v1.0",
    "2955": "ONT Start Sequencing v3.0",  # TODO Update this to reflect prod
}


def main(lims, args, logger):
    """This should be run at project summary level"""
    process = Process(lims, id=args.pid)
    sample_counter = 0
    error_counter = 0

    summary = {}  # { sample_name : { flowcell : { lane1, lane2, ... } } }  # dict -> dict -> set
    log_artifact = [
        art
        for art in process.all_outputs()
        if art.type == "ResultFile" and art.name == "AggregationLog"
    ][0]

    for art_out in [art for art in process.all_outputs() if art.type == "Analyte"]:
        assert (
            len(art_out.samples) == 1
        ), f"Found {len(art_out.samples)} samples for the output analyte {art_out.id}, that should not happen"

        sample = art_out.samples[0]
        sample_counter += 1

        # Update the total number of reads
        total_reads = sum_reads(sample, summary)
        sample.udf["Total Reads (M)"] = total_reads
        art_out.udf["Set Total Reads"] = total_reads
        logging.info(f"Total reads is {total_reads} for sample {sample.name}")

        # Set sample min reads UDF from project min reads UDF
        logging.info(
            f"Updating {sample.name} UDF 'Reads Min' to {sample.project.udf.get("Reads Min", 0)}"
        )
        sample.udf["Reads Min"] = sample.project.udf.get("Reads Min", 0) / 10e6

        # Set sample UDFs for status and sequencing QC based on min reads and total reads
        if sample.udf["Reads Min"] >= total_reads:
            sample.udf["Status (auto)"] = "In Progress"
            sample.udf["Passed Sequencing QC"] = "False"
        elif sample.udf["Reads Min"] < total_reads:
            sample.udf["Passed Sequencing QC"] = "True"
            sample.udf["Status (auto)"] = "Finished"

        # Commit changes to sample and sample artifact
        sample.put()
        art_out.put()

    # Write the csv file, separated by pipes, no cell delimiter
    with open("AggregationLog.csv", "w") as f:
        f.write("sep=,\n")
        f.write(
            "sample name,number of flowcells,number of lanes,flowcell1:lane1|lane2;flowcell2:lane1|lane2|lane3 ...\n"
        )
        for sample in summary:
            view = []
            n_flowcells = len(summary[sample])
            n_lanes = 0
            for fc in summary[sample]:
                view.append("{}:{}".format(fc, "|".join(summary[sample][fc])))
                n_lanes += len(summary[sample][fc])
            f.write(
                "{},{},{},{}\n".format(sample, n_flowcells, n_lanes, ";".join(view))
            )

    # Upload the log file
    try:
        attach_file(os.path.join(os.getcwd(), "AggregationLog.csv"), log_artifact)
        logging.info(f"Updated {sample_counter} samples with {error_counter} errors")
    except AttributeError:
        # Happens if the log artifact does not exist, if the step has been started before the configuration changes
        logging.info("Could not upload the log file")


def dem_number(sample):
    """Returns the number of distinct demultiplexing processes tagged with "Include reads" for a given sample"""
    expected_name = f"{sample.name} (FASTQ reads)"
    demux_steps = set()
    arts = lims.get_artifacts(
        sample_name=sample.name,
        process_type=list(DEMULTIPLEX.values()),
        name=expected_name,
    )
    for art in arts:
        if art.udf["Include reads"] == "YES":
            demux_steps.add(art.parent_process.id)
    return len(demux_steps)


def sum_reads(sample, summary):
    # Append to summary
    if sample.name not in summary:
        summary[sample.name] = {}

    expected_name = f"{sample.name} (FASTQ reads)"
    # Look for artifacts matching the sample name and expected analyte name in the demultiplexing processes
    demux_arts = lims.get_artifacts(
        sample_name=sample.name,
        process_type=list(DEMULTIPLEX.values()),
        name=expected_name,
    )

    # Instantiate vars
    tot_reads = 0
    flowcell_lane_list = []
    filtered_arts = []
    base_art = None
    for demux_art in sorted(
        demux_arts, key=lambda art: art.parent_process.date_run, reverse=True
    ):
        logging.info(
            f"Looking at '{demux_art.name}' ({demux_art.id}) of step '{demux_art.parent_process.type.name}' ({demux_art.parent_process.id})..."
        )

        # Evaluate skip conditions
        if "# Reads" not in demux_art.udf:
            logging.info("Missing or unpopulated UDF '# Reads', skipping.")
            continue

        if "Include reads" not in demux_art.udf:
            logging.info("Missing or unpopulated UDF 'Include_reads' filled, skipping.")
            continue

        if "Include reads" not in demux_art.udf:
            logging.info("Missing or unpopulated UDF 'Include_reads' filled, skipping.")
            continue
        elif demux_art.udf["Include reads"] == "NO":
            logging.info("UDF 'Include reads' is set to 'NO', skipping.")
            continue

        # Look at parent samples
        parent_arts = get_parent_inputs(demux_art)
        for parent_art in parent_arts:
            if sample in parent_art.samples:
                # ONT
                if "ONT flow cell ID" in parent_art.udf:
                    ont_flowcell = parent_art.udf["ONT flow cell ID"]
                    if ont_flowcell not in flowcell_lane_list:
                        filtered_arts.append(demux_art)
                        flowcell_lane_list.append(ont_flowcell)
                    if ont_flowcell not in summary[sample.name]:
                        summary[sample.name][ont_flowcell] = set()

                # Illumina
                else:
                    flowcell_lane = "{}:{}".format(
                        parent_art.location[0].name,
                        parent_art.location[1].split(":")[0],
                    )
                    if flowcell_lane not in flowcell_lane_list:
                        filtered_arts.append(demux_art)
                        flowcell_lane_list.append(flowcell_lane)
                    if parent_art.location[0].name in summary[sample.name]:
                        summary[sample.name][parent_art.location[0].name].add(
                            parent_art.location[1].split(":")[0]
                        )
                    else:
                        summary[sample.name][parent_art.location[0].name] = set(
                            parent_art.location[1].split(":")[0]
                        )

    for i in range(0, len(filtered_arts)):
        demux_art = filtered_arts[i]
        if demux_art.udf["Include reads"] == "YES":
            base_art = demux_art
            tot_reads += float(demux_art.udf["# Reads"])

    # Grab the sequencing process associated
    # Find the correct input
    try:
        for art_in in base_art.parent_process.all_inputs():
            if sample.name in [s.name for s in art_in.samples]:
                try:
                    sq = lims.get_processes(
                        type=list(SEQUENCING.values()), inputartifactlimsid=art_in.id
                    )[0]
                except TypeError:
                    logging.error(
                        f"Did not manage to get sequencing process for artifact {art_in.id}"
                    )
                else:
                    if (
                        "Read 2 Cycles" in sq.udf
                        and sq.udf["Read 2 Cycles"] is not None
                    ):
                        tot_reads /= 2
                break
    except AttributeError as e:
        print(e)
        # Base_art is still None because no arts were found
        logging.info(f"No demultiplexing processes found for sample {sample.name}")

    # Total is displayed as millions
    tot_reads /= 10e6
    return tot_reads


def get_parent_inputs(art):
    input_arts = set()
    for input_output_tuple in art.parent_process.input_output_maps:
        if input_output_tuple[1]["uri"].id == art.id:
            input_arts.add(input_output_tuple[0]["uri"])

    return input_arts


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument("--pid", help="Lims id for current Process")
    parser.add_argument("--log", help="Log file for runtime info and errors.")
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    with EppLogger(args.log, lims=lims, prepend=True) as epp_logger:
        main(lims, args, epp_logger)
