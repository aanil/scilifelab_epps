import json
import logging
from typing import Union

from genologics.entities import Artifact, Process
from requests.exceptions import HTTPError

DESC = """This is a submodule for defining reusable functions to handle artifact
UDFs in in the Genologics Clarity LIMS API.
"""


def put(target: Artifact | Process, target_udf: str, val, on_fail=AssertionError):
    """Try to put UDF on artifact or process, optionally without causing fatal error.
    Evaluates true on success and error (default) or on_fail param on failure.
    """

    target.udf[target_udf] = val

    try:
        target.put()
        return True

    except HTTPError:
        del target.udf[target_udf]
        if isinstance(on_fail, type) and issubclass(on_fail, Exception):
            raise on_fail(
                f"Can't put UDF '{target_udf}' on '{target.name if isinstance(target, Artifact) else target.type.name}'"
            )
        else:
            return on_fail


def is_filled(art: Artifact, target_udf: str) -> bool:
    """Check whether current UDF is populated for current article."""
    try:
        art.udf[target_udf]
        return True
    except KeyError:
        return False


def get_art_tuples(currentStep: Process) -> list:
    """Return I/O tuples whose elements are either
    1) both analytes
        or
    2) an analyte and None
    """

    art_tuples = []
    for art_tuple in currentStep.input_output_maps:
        if art_tuple[0] and art_tuple[1]:
            if art_tuple[0]["uri"].type == art_tuple[1]["uri"].type == "Analyte":
                art_tuples.append(art_tuple)
        elif art_tuple[0] and not art_tuple[1]:
            if art_tuple[0]["uri"].type == "Analyte":
                art_tuples.append(art_tuple)
        elif not art_tuple[0] and art_tuple[1]:
            if art_tuple[1]["uri"].type == "Analyte":
                art_tuples.append(art_tuple)

    # Sort
    art_tuples.sort(key=lambda t: t[1]["uri"].name if t[1] else t[0]["uri"].name)

    return art_tuples


def fetch_from_tuple(art_tuple: tuple, target_udfs: str | list, on_fail=AssertionError):
    """Try to fetch UDF based on input/output tuple of step that is missing either input or output artifacts,
    optionally without causing fatal error.

    Target UDF can be supplied as a string, or as a prioritized list of strings.
    """

    if isinstance(target_udfs, str):
        target_udfs = [target_udfs]

    for target_udf in target_udfs:
        try:
            return art_tuple[1]["uri"].udf[target_udf]
        except:
            try:
                return art_tuple[0]["uri"].udf[target_udf]
            except:
                continue

    if isinstance(on_fail, type) and issubclass(on_fail, Exception):
        raise on_fail(
            f"Could not find matching UDF(s) [{', '.join(target_udfs)}] for artifact tuple {art_tuple}"
        )
    else:
        return on_fail


def fetch(art: Artifact, target_udfs: Union[str, list], on_fail=AssertionError):
    """Try to fetch UDF from artifact, optionally without causing fatal error.

    Target UDF can be supplied as a string, or as a prioritized list of strings.
    """

    if isinstance(target_udfs, str):
        target_udfs = [target_udfs]

    for target_udf in target_udfs:
        try:
            return art.udf[target_udf]
        except KeyError:
            continue

    if isinstance(on_fail, type) and issubclass(on_fail, Exception):
        raise on_fail(
            f"Could not find matching UDF(s) [{', '.join(target_udfs)}] for artifact {art.name}"
        )
    else:
        return on_fail


def list_udfs(art: Artifact) -> list:
    return [item_tuple[0] for item_tuple in art.udf.items()]


def fetch_last(
    target_art: Artifact,
    target_udfs: str | list,
    log_traceback=False,
    return_traceback=False,
    on_fail=AssertionError,
) -> (str | int | float) | tuple[str | int | float, dict]:
    """Recursively look for target UDF.

    Arguments:

        target_art          Artifact to traceback and assign UDF value to.

        target_udfs         Can be supplied as a string, or as a prioritized
                            list of strings.

        log_traceback       If True, will log the full traceback.

        return_traceback    If True, will return the traceback too.

        on_fail             If not None, will return this value on failure.
    """

    # Convert to list, to enable iteration
    if isinstance(target_udfs, str):
        target_udfs = [target_udfs]

    # Instantiate traceback
    traceback = []
    steps_visited = []

    try:
        # First iteration, current artifact is the target artifact. Don't pull any UDF values.
        current_art = target_art
        pp = current_art.parent_process
        assert pp, f"Artifact '{current_art.name}' ({current_art.id}) has no parent process linked."
        steps_visited.append(f"'{pp.type.name}' ({pp.id})")

        traceback.append(
            {
                "Artifact": {
                    "Name": current_art.name,
                    "ID": current_art.id,
                    "UDFs": dict(current_art.udf.items()),
                    "Parent Step": {
                        "Name": pp.type.name if pp else None,
                        "ID": pp.id if pp else None,
                    },
                }
            }
        )

        # Start recursive search
        while True:
            pp_art_tuples = get_art_tuples(pp)

            # If parent process has valid input-output tuples, use for linkage
            if pp_art_tuples != []:
                for pp_tuple in pp_art_tuples:
                    if pp_tuple[1]["uri"].id == current_art.id:
                        current_art = pp_tuple[0]["uri"]
                        break
            # If not, TODO
            else:
                raise NotImplementedError()

            pp = current_art.parent_process
            if pp is not None:
                steps_visited.append(f"'{pp.type.name}' ({pp.id})")

            traceback.append(
                {
                    "Artifact": {
                        "Name": current_art.name,
                        "ID": current_art.id,
                        "UDFs": dict(current_art.udf.items()),
                        "Parent Step": {
                            "Name": pp.type.name if pp else None,
                            "ID": pp.id if pp else None,
                        },
                    }
                }
            )

            # Search for correct UDF
            for target_udf in target_udfs:
                if target_udf in list_udfs(current_art):
                    if log_traceback is True:
                        logging.info(f"Traceback:\n{json.dumps(traceback, indent=2)}")
                    logging.info(
                        f"Found target UDF '{target_udf}'"
                        + f" with value '{current_art.udf[target_udf]}'"
                        + f" in process {steps_visited[-1]}"
                        + f" {'output' if pp else 'input'}"
                        + f" artifact '{current_art.name}' ({current_art.id})"
                    )

                    if return_traceback:
                        return current_art.udf[target_udf], traceback
                    else:
                        return current_art.udf[target_udf]

            if pp is None:
                raise AssertionError(
                    f"Artifact '{current_art.name}' ({current_art.id}) has no parent process linked and can't be traced back further."
                )

    except AssertionError:
        if isinstance(on_fail, type) and issubclass(on_fail, Exception):
            raise on_fail(
                f"Could not find matching UDF(s) [{', '.join(target_udfs)}] for artifact {target_art}"
            )
        else:
            logging.warning(
                f"Failed traceback for artifact '{target_art.name}' ({target_art.id}), falling back to value '{on_fail}'"
            )
            return on_fail
