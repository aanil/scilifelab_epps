#!/usr/bin/env python

import logging
import re
from argparse import ArgumentParser
from datetime import datetime as dt

from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.entities import Artifact, Process
from genologics.lims import Lims

from scilifelab_epps.utils.formula import (
    ng_ul_to_nM,
    nM_to_ng_ul,
)
from scilifelab_epps.utils.udf_tools import fetch_last, get_art_tuples
from scilifelab_epps.wrapper import epp_decorator

DESC = """Script to perform UDF calculations on input-output level by reading
equations with special syntax UDF placeholders from a step UDF.

The whole idea is to have a single calculation script whose behavior can be customized on a
step-by-step basis in the front-end configuration.

Syntax examples:

- UDF placeholders
    A special string referencing a UDF in an artifact or step, and whether to fetch it recursively.

    E.g.
        in['foo']      step input artifact UDF 'foo'
        _out['bar']    artifact UDF 'bar', fetched recursively from step output artifact
        step['mm']     step UDF 'mm'

- Formulas
    A string containing an equation with UDF placeholders. The left hand side needs to be an isolated UDF placeholder,
    which is the one to be assigned, and the right hand side will be evaluated after translating UDF placeholders
    into their corresponding values.

    E.g.
        outp['Eluted Amount (fmol)'] = nM(outp['Eluted Concentration (ng/ul)'], 'ng/ul', _outp['Size (bp)']) * outp['Eluted Volume (ul)']

"""

TIMESTAMP = dt.now().strftime("%y%m%d_%H%M%S")


def ng_ul(conc: float, conc_units: str, size: float) -> float:
    """Force a concentration to be in ng/ul."""
    if conc_units == "ng/ul":
        return conc
    elif conc_units == "nM":
        return nM_to_ng_ul(conc, size)
    else:
        raise AssertionError(f"Concentration units '{conc_units}' not recognized")


def nM(conc: float, conc_units: str, size: float) -> float:
    """Force a concentration to be in nM."""
    if conc_units == "nM":
        return conc
    elif conc_units == "ng/ul":
        return ng_ul_to_nM(conc, size)
    else:
        raise AssertionError(f"Concentration units '{conc_units}' not recognized")


def assign_val_to_placeholder(
    val: str | float, placeholder: str, art_tuple: tuple, step: Process
) -> None:
    """Assign a value to a UDF placeholder for a given artifact tuple and step."""
    udf_name = re.search(r"\['(.*?)'\]", placeholder).groups()[0]

    # Where to assign UDF
    if "inp" in placeholder:
        obj = art_tuple[0]["uri"]
    elif "outp" in placeholder:
        obj = art_tuple[1]["uri"]
    elif "step" in placeholder:
        obj = step

    if type(val) is float:
        val = round(val, 2)

    obj.udf[udf_name] = val
    obj.put()


def get_val_from_placeholder(
    placeholder: str, art_tuple: tuple, step: Process
) -> str | float:
    """Fetch a value from a UDF placeholder for a given artifact tuple and step."""
    recursive = True if placeholder[0] == "_" else False
    udf_name = re.search(r"\['(.*?)'\]", placeholder).groups()[0]

    # Where to fetch UDF
    if "inp" in placeholder:
        obj = art_tuple[0]["uri"]
    elif "outp" in placeholder:
        obj = art_tuple[1]["uri"]
    elif "step" in placeholder:
        obj = step

    # How to fetch UDF
    if recursive:
        assert type(obj) is Artifact, (
            "Recursive UDF references only allowed for artifacts"
        )
        val = fetch_last(obj, udf_name, include_current=True, on_fail=None)
    else:
        val = obj.udf.get(udf_name)

    if val is None:
        logging.warning(f"Could not resolve UDF {placeholder} for {obj}")
        raise SkipCalculation()

    return val


class SkipCalculation(Exception):
    """Custom exception for skipping calculations."""

    pass


def parse_formula(formula: str) -> tuple[str, list[str]]:
    """From a formula string, extract UDF placeholders.

    Return the formula string with placeholders replaced by curly brackets,
    as well as a list of the placeholders.

    Also perform various assertions to sanity check the input and prevent code injection.
    """
    logging.info(f"Parsing formula:\n\t{formula}")

    # Explicate non-placeholders allowed in formula, to prevent code injection
    allowed_functions = ["ng_ul", "nM"]
    allowed_strings = ["'ng/ul'", "'nM'"]

    # Patterns
    placeholder_pattern = r"_?((inp)|(outp)|(step))\[.*?\]"
    allowed_functions_pattern = "|".join([f"({f})" for f in allowed_functions])
    allowed_strings_pattern = "|".join([f"({s})" for s in allowed_strings])
    pure_math_pattern = r"[=\d\+\-\*\/\(\)\{\}\s]+"

    # Collect UDF references from formula
    placeholders: list[str] = [
        match[0] for match in re.finditer(placeholder_pattern, formula)
    ]

    # Replace UDF references with curly brackets
    formula_fstring: str = re.sub(placeholder_pattern, r"{}", formula)

    # Sanity check matching number of UDF references and placeholders
    assert formula_fstring.count(r"{}") == len(placeholders), (
        f"Number of extracted UDF references ({len(placeholders)})"
        + f"do not match number of format placeholders ({formula_fstring.count(r'{}}')})"
    )

    # Assert only pure math remains after removing allowed functions, strings and commas
    formula_pure = formula_fstring
    formula_pure = re.sub(allowed_functions_pattern, "", formula_pure)
    formula_pure = re.sub(allowed_strings_pattern, "", formula_pure)
    formula_pure = re.sub(r",", "", formula_pure)

    assert re.fullmatch(pure_math_pattern, formula_pure), (
        f"Formula '{formula}' appears to contain disallowed characters."
    )

    return formula_fstring, placeholders


def eval_rh(
    formula_fstring: str, placeholders: list[str], art_tuple: tuple, process: Process
) -> str | float:
    """Evaluate the right-hand side of the formula, with placeholders replaced by values."""
    # Translate placeholders to values
    placeholder2val = {}
    for placeholder in placeholders[1:]:  # First placeholder is the one to be assigned
        val = get_val_from_placeholder(placeholder, art_tuple, process)
        placeholder2val[placeholder] = val

    # Evaluate right-hand side of equation
    formula_fstring_rh = formula_fstring.split("=")[1].strip()
    formula_eval_str_rh = formula_fstring_rh.format(*placeholder2val.values())
    rh_val = eval(formula_eval_str_rh)

    # Print equations with placeholders and populated values
    formula_eval_str_rh_2f = formula_fstring_rh.format(
        *[f"{i:.2f}" for i in placeholder2val.values()]
    )
    logging.info(f"Formula:     {formula_fstring.format(*placeholders)}")
    logging.info(f"Calculation: {rh_val:.2f} = {formula_eval_str_rh_2f}")

    return rh_val


@epp_decorator(script_path=__file__, timestamp=TIMESTAMP)
def main(args):
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    process = Process(lims, id=args.pid)

    # Read field containing formulas
    formula_field_contents = process.udf.get(args.formula_field)
    assert formula_field_contents, f"Step UDF '{args.formula_field}' is empty"
    formulas = formula_field_contents.split("\n")

    for formula in formulas:
        formula_fstring, placeholders = parse_formula(formula)

        # Iterate across artifacts
        # TODO check for no-output steps and resultsfile linkages
        for art_tuple in get_art_tuples(process):
            art_in = art_tuple[0]["uri"]
            art_out = art_tuple[1]["uri"]
            logging.info(
                f"Calculations for input-output '{art_in.name}' ({art_in.id}) --> '{art_out.name}' ({art_out.id})"
            )
            try:
                val = eval_rh(
                    formula_fstring,
                    placeholders,
                    art_tuple,
                    process,
                )
                assign_val_to_placeholder(val, placeholders[0], art_tuple, process)
            except SkipCalculation as e:
                logging.warning(f"Skipping calculation\n{e}")
                continue


if __name__ == "__main__":
    # Parse args
    parser = ArgumentParser(description=DESC)
    parser.add_argument(
        "--pid",
        required=True,
        type=str,
        help="Lims ID for current Process",
    )
    parser.add_argument(
        "--log",
        required=True,
        type=str,
        help="Which log file slot to use",
    )
    parser.add_argument(
        "--formula_field",
        type=str,
        default="UDF formulas",
        help="Which step UDF containing UDF formulas",
    )
    args = parser.parse_args()

    main(args)
