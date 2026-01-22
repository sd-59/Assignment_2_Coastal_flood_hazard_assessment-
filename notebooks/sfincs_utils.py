"""
HydroMT-SFINCS utilities functions
"""

import platform
import subprocess
import zipfile
from pathlib import Path
from typing import Literal, Optional

from hydromt_sfincs.sfincs_input import SfincsInput


def run_sfincs(
    sfincs_inp: Path,
    run_method: Literal["exe", "docker", "apptainer"],
    sfincs_exe: Optional[Path] = None,
    docker_tag: str = "sfincs-v2.1.1-Dollerup-Release",
    verbose: bool = True,
) -> None:
    """Run the SfincsRun method.

    Parameters
    ----------
    sfincs_inp : Path
        The path to the SFINCS model configuration (inp) file.
    run_method : Literal["exe", "docker", "apptainer"]
        How to run the SFINCS model. The default is "exe", which runs the Windows executable.
        If 'docker' or 'aptainer' is specified, the model is run in a Docker or Apptainer container.
    sfincs_exe : Optional[Path], optional
        The path to SFINCS executable, by default None.
        Required if run_method == "exe".
    docker_tag : str, optional
        The Docker tag to specify the version of the Docker image to use, by default "sfincs-v2.1.1-Dollerup-Release".
    verbose : bool, optional
        Print output to screen, by default True.
    """
    # check run_method is supported
    if run_method not in ["exe", "docker", "apptainer"]:
        raise ValueError(f"run_method {run_method} not supported")
    # make sure model_root is an absolute path and sfincs_inp exists
    sfincs_inp = Path(sfincs_inp)
    if not sfincs_inp.is_file():
        raise FileNotFoundError(f"sfincs_inp not found: {sfincs_inp}")
    model_root = sfincs_inp.parent.resolve()
    base_folder = get_sfincs_basemodel_root(model_root / "sfincs.inp")

    # set command to run depending on run_method
    if run_method == "exe":
        if platform.system() != "Windows":
            raise ValueError("sfince_exe only supported on Windows")
        sfincs_exe = Path(sfincs_exe).resolve()
        if not sfincs_exe.is_file():
            raise FileNotFoundError(f"sfincs_exe not found: {sfincs_exe}")
        cmd = [str(sfincs_exe)]
    elif run_method == "docker":
        if subprocess.run(["docker", "stats", "--no-stream"]).returncode != 0:
            raise RuntimeError(
                "Docker not running. Make sure Docker is installed and running."
            )
        cmd = [
            "docker",
            "run",
            f"-v{base_folder}://data",
            "-w",
            f"/data/{model_root.relative_to(base_folder).as_posix()}",
            f"deltares/sfincs-cpu:{docker_tag}",
        ]
    elif run_method == "apptainer":
        if subprocess.run(["apptainer", "version"]).returncode != 0:
            raise RuntimeError(
                "Apptainer not found. Make sure it is installed, running and added to PATH."
            )
        cmd = [
            "apptainer",
            "run",
            f"-B{base_folder}:/data",
            "--pwd",
            f"/data/{model_root.relative_to(base_folder).as_posix()}",
            f"docker://deltares/sfincs-cpu:{docker_tag}",
        ]

    # run & write log file
    print(f"Running SFINCS model in {model_root} with command:")
    print(f">> {' '.join(cmd)}\n")
    log_file = model_root / "sfincs_log.txt"
    # run & write log file
    print_log = False
    with subprocess.Popen(
        cmd,
        cwd=model_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,  # get string output instead of bytes
    ) as proc:
        with open(log_file, "w") as f:
            for line in proc.stdout:
                if verbose and not print_log:
                    # start printing log after first line with only "-"
                    print_log = set(line.strip()) == set(["-"])
                if print_log:
                    print(line.rstrip("\n"))
                f.write(line)
            for line in proc.stderr:
                if verbose:
                    print(line.rstrip("\n"))
                f.write(line)
        proc.wait()
        return_code = proc.returncode

    # check return code
    if return_code == 127:
        raise RuntimeError(
            f"{run_method} not found. Make sure it is installed, running and added to PATH."
        )
    elif return_code != 0:
        raise RuntimeError(f"SFINCS run failed with return code {return_code}")

    # check if "Simulation stopped" in log file
    with open(log_file, "r") as f:
        log = f.read()
        if "Simulation stopped" in log:
            raise RuntimeError(
                f"SFINCS run failed. Check log file for details: {log_file}"
            )

    return None


def get_sfincs_basemodel_root(sfincs_inp: Path) -> Path:
    """Get folder with SFINCS static files.

    Parameters
    ----------
    sfincs_inp : Path
        Path to event sfincs.inp file.

    Returns
    -------
    Path
        Path to parent directory with static files.
    """
    inp = SfincsInput.from_file(sfincs_inp)
    config = inp.to_dict()
    n = 0
    for key, value in config.items():
        if "file" in key and "../" in value:
            n = max(n, value.count("../"))

    return sfincs_inp.parents[n]


def create_sfincs_model_archive(
    sfincs_inp: Path, zip_filename: Path | str = "sfincs.zip"
) -> Path:
    """Create a zip archive with the SFINCS model.

    Parameters
    ----------
    sfincs_inp : Path
        Path to event sfincs.inp file.
    zip_filename : Path, str, optional
        Name of the zip archive, by default "sfincs.zip".

    Returns
    -------
    Path
        zip archive file path.
    """
    sfincs_inp = Path(sfincs_inp).resolve()
    zip_filename = Path(zip_filename)
    if zip_filename.suffix != ".zip":
        zip_filename = zip_filename.with_suffix(".zip")
    if not zip_filename.is_absolute():
        zip_filename = sfincs_inp.parent / zip_filename
    if zip_filename.exists():
        try:
            zip_filename.unlink()
        except Exception:
            raise FileExistsError(f"Could not remove existing zipfile: {zip_filename}")

    files = [sfincs_inp]
    base_folder = get_sfincs_basemodel_root(sfincs_inp)
    inp = SfincsInput.from_file(sfincs_inp)
    config = inp.to_dict()
    for key, value in config.items():
        if "file" in key:
            file_path = Path(sfincs_inp.parent, value).resolve()
            if file_path.exists():
                files.append(file_path)
            else:
                # raise FileNotFoundError(f"Could not find file: {key} = {value}")
                print(f"WARNING: Could not find file: {key} = {value}")
    # create zip archive with base_folder as root
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            zipf.write(file, arcname=file.relative_to(base_folder))

    return zip_filename
