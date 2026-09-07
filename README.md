# nomad-mlip-data

Fetch atomistic structures with energies/forces/stress from
[NOMAD](https://nomad-lab.eu/prod/v1/gui/search/entries) and package them as ASE-DB or
extxyz datasets for fine-tuning ASE-calculator-compatible MLIPs.

## Install

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Usage (Python)

```python
from nomad_forces_export import NomadQuery, fetch_dataset

query = NomadQuery(
    elements=["Si", "O"],
    exclude_datasets=["Alexandria PBEsol"],
)

fetch_dataset(
    query=query,
    properties={"energy", "forces"},
    output_format="ase_db",
    output_path="dataset.db",
    max_entries=5000,
)
```

## Usage (CLI)

```bash
nomad-mlip-data fetch \
  --elements Si O \
  --exclude-dataset "Alexandria PBEsol" \
  --properties energy forces \
  --format ase_db extxyz \
  --output dataset \
  --max-entries 5000
```

## Testing

```bash
pytest tests/ -v
```

All tests run against recorded NOMAD API fixtures in `tests/fixtures/` — no live
network access is required.

## Main contributors
| Name | E-mail     |
|------|------------|
| Sharat Patil | [patilsha@physik.hu-berlin.de](mailto:patilsha@physik.hu-berlin.de)
