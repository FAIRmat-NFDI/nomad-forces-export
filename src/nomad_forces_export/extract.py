"""Convert a NOMAD archive entry into one ase.Atoms object per calculation frame."""

import logging
from collections.abc import Iterator

import numpy as np
from ase import Atoms
from ase.calculators.singlepoint import SinglePointCalculator

from nomad_forces_export.config import VALID_PROPERTIES
from nomad_forces_export.units import (
    joule_to_ev,
    meter_to_angstrom,
    newton_to_ev_per_angstrom,
    pascal_to_ev_per_angstrom3,
)

logger = logging.getLogger(__name__)


def _parse_system_ref(system_ref: str) -> tuple[int, int] | None:
    # system_ref looks like "/run/0/system/3" (leading slash optional) ->
    # extract both the run index and system index.
    parts = system_ref.rstrip('/').split('/')
    try:
        run_index = int(parts[parts.index('run') + 1])
        system_index = int(parts[parts.index('system') + 1])
    except (ValueError, IndexError):
        return None
    return run_index, system_index


def _build_atoms_from_system(system: dict) -> Atoms:
    atoms_data = system['atoms']
    species = atoms_data['species']
    positions_m = np.array(atoms_data['positions'])
    positions_ang = meter_to_angstrom(positions_m)
    magmoms = system.get('magmoms')

    lattice_vectors_m = atoms_data.get('lattice_vectors')
    periodic = atoms_data.get('periodic', [False, False, False])

    cell = None
    if lattice_vectors_m is not None:
        cell = meter_to_angstrom(np.array(lattice_vectors_m))

    return Atoms(
        numbers=species,
        positions=positions_ang,
        cell=cell,
        pbc=periodic,
        magmoms=magmoms,
    )


def _extract_energy_ev(calculation: dict) -> float | None:
    energy = calculation.get('energy')
    if not energy:
        return None
    if 'total_t0' in energy:
        return joule_to_ev(energy['total_t0']['value'])
    if 'total' in energy:
        return joule_to_ev(energy['total']['value'])
    if 'free' in energy:
        return joule_to_ev(energy['free']['value'])
    return None


def _extract_forces_ev_per_ang(calculation: dict) -> np.ndarray | None:
    forces = calculation.get('forces')
    if not forces or 'total' not in forces:
        return None
    forces_n = np.array(forces['total']['value'])
    return newton_to_ev_per_angstrom(forces_n)


def _extract_stress_ev_per_ang3(calculation: dict) -> np.ndarray | None:
    stress = calculation.get('stress')
    if not stress or 'total' not in stress:
        return None
    stress_pa = np.array(stress['total']['value'])
    return pascal_to_ev_per_angstrom3(stress_pa)


def to_atoms(archive_entry: dict, properties: set | list[str]) -> Iterator[Atoms]:
    """Yield one `ase.Atoms` per calculation frame in a NOMAD archive entry.

    `properties` is a subset of {"energy", "forces", "stress"}; frames missing any
    requested property are skipped (and logged) rather than raising.
    """
    unknown = set(properties) - VALID_PROPERTIES
    if unknown:
        raise ValueError(f'Unknown properties requested: {sorted(unknown)}')

    entry_id = archive_entry.get('entry_id')
    upload_id = archive_entry.get('upload_id')
    runs = archive_entry.get('archive', {}).get('run', [])

    for run_index, run in enumerate(runs):
        systems = run.get('system', [])
        calculations = run.get('calculation', [])
        method = run.get('method', [{}])[0]

        for calc_index, calculation in enumerate(calculations):
            system_ref = calculation.get('system_ref')
            if system_ref is not None:
                parsed = _parse_system_ref(system_ref)
                if parsed is None:
                    logger.warning(
                        f'entry {entry_id}: calculation {calc_index} has an unparseable system_ref {system_ref}, skipping'
                    )
                    continue
                ref_run_index, system_index = parsed
                if ref_run_index != run_index:
                    logger.warning(
                        f'entry {entry_id}: calculation {calc_index} has system_ref pointing to a '
                        f'different run ({ref_run_index}) than its own run ({run_index}), skipping',
                    )
                    continue
            else:
                system_index = calc_index

            if system_index < 0 or system_index >= len(systems):
                logger.warning(
                    'entry %s: calculation %d references missing system %d, skipping',
                    entry_id,
                    calc_index,
                    system_index,
                )
                continue

            if method.get('x_vasp_incar_in'):
                magmom = method['x_vasp_incar_in'].get('MAGMOM')
                if magmom:
                    systems[system_index]['magmoms'] = np.array(magmom)
            results: dict = {}
            skip = ''

            if 'energy' in properties:
                energy_ev = _extract_energy_ev(calculation)
                if energy_ev is None:
                    skip = 'energy'
                else:
                    results['energy'] = energy_ev

            if not skip and 'forces' in properties:
                forces = _extract_forces_ev_per_ang(calculation)
                if forces is None:
                    skip = 'forces'
                else:
                    results['forces'] = forces

            if not skip and 'stress' in properties:
                stress = _extract_stress_ev_per_ang3(calculation)
                if stress is None:
                    skip = 'stress'
                else:
                    results['stress'] = stress

            if skip:
                logger.debug(
                    f'entry {entry_id}: calculation {calc_index} missing {skip}, skipping'
                )
                continue

            atoms = _build_atoms_from_system(systems[system_index])
            atoms.calc = SinglePointCalculator(atoms, **results)
            atoms.info['nomad_entry_id'] = entry_id
            atoms.info['nomad_upload_id'] = upload_id
            atoms.info['is_representative'] = systems[system_index].get(
                'is_representative', False
            )
            atoms.info['is_converged_geometry'] = run.get('workflow2', {}).get(
                'results', {}
            ).get('is_converged_geometry', False) or run.get('workflow', {}).get(
                'geometry_optimization', {}
            ).get('is_converged_geometry', False)
            yield atoms
