"""Unit conversions from NOMAD's SI-based archive units to ASE's units.

ASE's internal unit system uses electron-volt (eV) for energy, Angstrom (Ang) for
length, eV/Ang for force, and eV/Ang^3 for stress/pressure. NOMAD archives store
raw SI values (Joule, meter, Newton, Pascal). These helpers convert one direction:
NOMAD (SI) -> ASE units.
"""
from ase import units as ase_units


def joule_to_ev(value: float) -> float:
    """Convert an energy value in Joules to electron-volts."""
    # ase_units.J is the number of eV in one Joule.
    return value * ase_units.J


def meter_to_angstrom(value: float) -> float:
    """Convert a length value in meters to Angstrom."""
    # ase_units.m is the number of Angstrom in one meter.
    return value * ase_units.m


def newton_to_ev_per_angstrom(value: float) -> float:
    """Convert a force value in Newtons to eV/Angstrom."""
    # 1 N = 1 J/m, so N -> eV/Ang is ase_units.J / ase_units.m
    return value * ase_units.J / ase_units.m


def pascal_to_ev_per_angstrom3(value: float) -> float:
    """Convert a stress/pressure value in Pascals to eV/Angstrom^3."""
    # 1 Pa = 1 J/m^3, so Pa -> eV/Ang^3 is ase_units.J / ase_units.m**3
    return value * ase_units.J / (ase_units.m ** 3)
