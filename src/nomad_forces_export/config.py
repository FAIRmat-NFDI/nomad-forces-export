VALID_FORMATS = {"ase_db", "extxyz"}
VALID_PROPERTIES = {"energy", "forces", "stress"}

NOMAD_BASE_URL = "https://nomad-lab.eu/prod/v1/api/v1"

WORKFLOWS = [
    "SinglePoint",
    "single_point",
    "GeometryOptimization",
    "geometry_optimization",
]

REQUIRED_METADATA = ["entry_id", "upload_id"]
REQUIRED_ARCHIVE_DATA = {
    "results": {
        "method": "*",
    },
    "workflow2": {"results": {"is_converged_geometry": "*"}},
    "run": {
        "program": "*",
        "method": "*",
        "system": {"atoms": "*", "is_representative": "*"},
        "calculation": {
            "energy": "*",
            "forces": "*",
            "stress": "*",
            "system_ref": "*",
        },
    },
}

BASE_QUERY = {
    "results.method.method_name:any": ["DFT"],
    "results.method.workflow_name:any": WORKFLOWS,
    "quantities:all": ["run.calculation", "run.system"],
}
