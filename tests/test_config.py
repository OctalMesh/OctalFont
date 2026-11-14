import pytest

from octalfont.config import validate_family_name


@pytest.mark.parametrize("name", ["Octal Titan", "Octal Cuprum"])
def test_good_names(name):
    assert validate_family_name(name, ["Regular"]) == []


@pytest.mark.parametrize("name", ["OctalFont", "OctalFont-Titan", "Octal_Titan", "Océtal"])
def test_bad_names(name):
    assert validate_family_name(name, ["Regular"])


def test_length_limit():
    assert validate_family_name("A" * 30, ["Regular"])
