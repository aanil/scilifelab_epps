#!/usr/bin/env python

import logging
import re
from argparse import ArgumentParser
from datetime import datetime as dt

from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.entities import Artifact, Process
from genologics.lims import Lims

from scilifelab_epps.utils.formula import (
    fmol_to_ng,
    ng_to_fmol,
    ng_ul_to_nM,
    nM_to_ng_ul,
)
from scilifelab_epps.utils.udf_tools import fetch_last, get_art_tuples
from scilifelab_epps.wrapper import epp_decorator

DESC = """Script to perform UDF calculations on input-output level by reading equations
with special syntax from a step UDF text field.

The whole idea is to have a single calculation script whose behavior can be customized
on a step-by-step basis in the front-end configuration.

The text field can contain multiple equations on one line each. Lines prefixed with '#'
will be ignored as comments.

Syntax explained:

    - UDF placeholders

        A special string referencing a UDF in an artifact or step, and whether to fetch
        it recursively.

        E.g.
            inp['foo']      step input artifact UDF 'foo'
            _outp['bar']    artifact UDF 'bar', fetched recursively from step output
                            artifact
            step['mm']      step UDF 'mm'

    - Formulas

        A string containing an equation with UDF placeholders.

        The left-hand side needs to be an isolated UDF placeholder, which is the one to
        be assigned, and the right-hand side will be evaluated using eval() after
        replacing UDF placeholders with their corresponding values.

        The separator between the left and right hand side can be either '=' or '==',
        where the former will overwrite existing UDFs and the latter will silently pass
        them. The latter case is useful for making sure multiple formulas do not
        overwrite one another, i.e. the first calculation to write to the field will be
        the one to stick.

        Right-hand side placeholders that can't be resolved will result in skipping the
        calculation. The silent skipping allows us to have multiple formulas targeting
        the same UDF that can be run in priority order without raising errors or
        warnings.

Examples:

    1) Calculate the ng and fmol amount from a given concentration, volume and size of
       an output artifact.

        outp['Amount (ng)'] = ng_ul(outp['Concentration'], outp['Conc. Units'], outp['Size (bp)']) * outp['Volume (ul)']
        outp['Amount (fmol)'] = ng_to_fmol(outp['Amount (ng)'], outp['Size (bp)'])

    2) Prioritized calculations! Populate three UDFs, based on the supplied value of one
       of them, in priority order.

        # Calculate from 'Amount for prep (fmol)'
        outp['Amount for prep (ng)'] == fmol_to_ng(outp['Amount for prep (fmol)'], _outp['Size (bp)'])
        outp['Volume to take (uL)'] == fmol_to_ng(outp['Amount for prep (fmol)'], _outp['Size (bp)']) / ng_ul(inp['Concentration'], inp['Conc. Units'], _outp['Size (bp)'])

        # Calculate from 'Amount for prep (ng)'
        outp['Amount for prep (fmol)'] == ng_to_fmol(outp['Amount for prep (ng)'], _outp['Size (bp)'])
        outp['Volume to take (uL)'] == ng_to_fmol(outp['Amount for prep (ng)'], _outp['Size (bp)']) / nM(inp['Concentration'], inp['Conc. Units'], _outp['Size (bp)'])

        # Calculate from 'Volume to take (uL)'
        outp['Amount for prep (fmol)'] == outp['Volume to take (uL)'] * nM(inp['Concentration'], inp['Conc. Units'], _outp['Size (bp)'])
        outp['Amount for prep (ng)'] == outp['Volume to take (uL)'] * ng_ul(inp['Concentration'], inp['Conc. Units'], _outp['Size (bp)'])
"""

TIMESTAMP = dt.now().strftime("%y%m%d_%H%M%S")


def ng_ul(conc: float, conc_units: str, size: float | None = None) -> float:
    """Force a concentration to be in ng/ul."""
    if conc_units == "ng/ul":
        return conc
    elif conc_units == "nM":
        assert size, "Size not provided for conversion to ng"
        return nM_to_ng_ul(conc, size)
    else:
        raise AssertionError(f"Concentration units '{conc_units}' not recognized")


def nM(conc: float, conc_units: str, size: float | None = None) -> float:
    """Force a concentration to be in nM."""
    if conc_units == "nM":
        return conc
    elif conc_units == "ng/ul":
        assert size, "Size not provided for conversion to nM"
        return ng_ul_to_nM(conc, size)
    else:
        raise AssertionError(f"Concentration units '{conc_units}' not recognized")


def assign_val_to_placeholder(
    val: str | float,
    placeholder: str,
    art_in: Artifact | None = None,
    art_out: Artifact | None = None,
    step: Process | None = None,
    overwrite: bool = True,
) -> None:
    """Assign a value to a UDF placeholder."""
    udf_name = re.search(r"\['(.*?)'\]", placeholder).groups()[0]

    # Where to assign UDF
    if "inp" in placeholder:
        assert art_in, "Input artifact not provided"
        obj = art_in
    elif "outp" in placeholder:
        assert art_out, "Output artifact not provided"
        obj = art_out
    elif "step" in placeholder:
        assert step, "Step not provided"
        obj = step

    if type(val) is float:
        val = round(val, 2)

    if obj.udf.get(udf_name) and not overwrite:
        logging.info(
            f"UDF {placeholder} for {obj} already exists and overwrite is False, skipping."
        )
        raise SkipCalculation()
    else:
        obj.udf[udf_name] = val
        obj.put()


def get_val_from_placeholder(
    placeholder: str,
    art_in: Artifact | None = None,
    art_out: Artifact | None = None,
    step: Process | None = None,
) -> str | float:
    """Fetch a value from a UDF placeholder."""
    recursive = True if placeholder[0] == "_" else False
    udf_name = re.search(r"\['(.*?)'\]", placeholder).groups()[0]

    # Where to fetch UDF
    if "inp" in placeholder:
        assert art_in, "Input artifact not provided"
        obj = art_in
    elif "outp" in placeholder:
        assert art_out, "Output artifact not provided"
        obj = art_out
    elif "step" in placeholder:
        assert step, "Step not provided"
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
        logging.info(f"Could not resolve UDF {placeholder} for {obj}")
        raise SkipCalculation()

    # Returned values will pass through eval, so strings need
    # to be escaped to not be interpreted as variables
    if type(val) is str:
        val = f"'{val}'"

    return val


class SkipCalculation(Exception):
    """Custom exception for skipping calculations."""

    def __init__(self, message="Skipping calculation"):
        super().__init__(message)
        logging.info(message)


def parse_formula(formula: str) -> tuple[str, list[str]]:
    """From a formula string, extract UDF placeholders.

    Return the formula string with placeholders replaced by curly brackets,
    as well as a list of the placeholders.

    Also perform various assertions to sanity check the input and prevent code injection.
    """
    logging.info(f"Parsing formula:\n\t{formula}")

    # Explicate non-placeholders allowed in formula, to prevent code injection
    allowed_functions = [
        ng_ul,
        nM,
        fmol_to_ng,
        ng_to_fmol,
        ng_ul_to_nM,
        nM_to_ng_ul,
    ]
    allowed_strings = [
        "'ng/ul'",
        "'nM'",
    ]

    # Patterns
    placeholder_pattern = r"_?((inp)|(outp)|(step))\[.*?\]"
    allowed_functions_pattern = "|".join([f"({f.__name__})" for f in allowed_functions])
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
    formula_fstring: str,
    placeholders: list[str],
    art_in: Artifact | None = None,
    art_out: Artifact | None = None,
    step: Process | None = None,
) -> str | float:
    """Evaluate the right-hand side of the formula, with placeholders replaced by values."""
    # Translate right-hand placeholders to values
    rh_values = []
    for placeholder in placeholders[1:]:  # First placeholder to be assigned, not read
        rh_val = get_val_from_placeholder(placeholder, art_in, art_out, step)
        rh_values.append(rh_val)

    # Evaluate right-hand side of equation
    sep = "==" if "==" in formula_fstring else "="
    formula_fstring_rh = formula_fstring.split(sep)[1].strip()
    formula_eval_str_rh = formula_fstring_rh.format(*rh_values)

    # Solve for x :)
    lh_val = eval(formula_eval_str_rh)

    # Print equations with placeholders and populated values
    rh_values_2f = [f"{i:.2f}" if type(i) in [float, int] else i for i in rh_values]
    formula_fstring_rh_2f = formula_fstring_rh.format(*rh_values_2f)
    logging.info(f"        Formula:  {formula_fstring.format(*placeholders)}")
    logging.info(f"    Calculation:  {rh_val:.2f} = {formula_fstring_rh_2f}")

    return lh_val


def apply_formula(process, formula_fstring, placeholders):
    """This function takes the parsed formula and applies it.

    The application will differ depending on the type of step.
    """

    overwrite = False if "==" in formula_fstring else True

    # Iterate across artifacts
    # TODO resultsfile linkages
    io_tuples = get_art_tuples(process)
    if io_tuples:
        logging.info("Step type: Standard input-ouput")
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
                    art_in=art_in,
                    art_out=art_out,
                    step=process,
                )
                assign_val_to_placeholder(
                    val, placeholders[0], art_in, art_out, process, overwrite
                )
            except SkipCalculation:
                continue
    else:
        logging.info("Step type: No-output")
        for art_in in [i for i in process.all_inputs() if i.type == "Analyte"]:
            logging.info(f"Calculations for input '{art_in.name}' ({art_in.id})")
            try:
                val = eval_rh(
                    formula_fstring,
                    placeholders,
                    art_in=art_in,
                    step=process,
                )
                assign_val_to_placeholder(
                    val, placeholders[0], art_in, process, overwrite
                )
            except SkipCalculation:
                continue


def get_formulas(step, formula_field):
    """Extract formulas from a step UDF text field. Skip empty lines and comments."""
    formula_field_contents = step.udf.get(formula_field)
    assert formula_field_contents, f"Step UDF '{formula_field}' is empty"
    rows = formula_field_contents.split("\n")

    formulas = []
    for row in rows:
        if row == "":
            continue
        if row[0] == "#":
            continue
        formulas.append(row)

    return formulas


@epp_decorator(script_path=__file__, timestamp=TIMESTAMP)
def main(args):
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    process = Process(lims, id=args.pid)

    formulas = get_formulas(process, args.formula_field)
    for formula in formulas:
        formula_fstring, placeholders = parse_formula(formula)
        apply_formula(process, formula_fstring, placeholders)


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
