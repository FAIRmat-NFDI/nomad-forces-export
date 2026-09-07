import math

from src.nomad_forces_export.units import (
    joule_to_ev,
    meter_to_angstrom,
    newton_to_ev_per_angstrom,
    pascal_to_ev_per_angstrom3,
)


def test_joule_to_ev():
    # 1 eV = 1.602176634e-19 J
    assert math.isclose(joule_to_ev(1.602176634e-19), 1.0, rel_tol=1e-6)


def test_meter_to_angstrom():
    assert math.isclose(meter_to_angstrom(1e-10), 1.0, rel_tol=1e-6)


def test_newton_to_ev_per_angstrom():
    # 1 eV/Angstrom = 1.602176634e-9 N
    assert math.isclose(newton_to_ev_per_angstrom(1.602176634e-9), 1.0, rel_tol=1e-6)


def test_pascal_to_ev_per_angstrom3():
    # 1 eV/Angstrom^3 = 1.602176634e11 Pa (approximately)
    assert math.isclose(pascal_to_ev_per_angstrom3(1.602176634e11), 1.0, rel_tol=1e-3)
