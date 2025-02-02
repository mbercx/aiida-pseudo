# -*- coding: utf-8 -*-
# pylint: disable=unused-argument,redefined-outer-name
"""Tests for the command `aiida-pseudo family`."""
import json

from numpy.testing import assert_almost_equal
import pytest

from aiida.orm import Group

from aiida_pseudo.cli.family import cmd_family_cutoffs_set, cmd_family_show
from aiida_pseudo.groups.family import PseudoPotentialFamily, CutoffsFamily


@pytest.mark.usefixtures('clear_db')
def test_family_cutoffs_set(run_cli_command, get_pseudo_family, generate_cutoffs_dict, tmp_path):
    """Test the `aiida-pseudo family cutoffs set` command."""
    family = get_pseudo_family(cls=CutoffsFamily)
    stringencies = ('low', 'normal', 'high')
    cutoffs_dict = generate_cutoffs_dict(family, stringencies=stringencies)

    # Set two stringencies
    for stringency in ('low', 'normal'):
        family.set_cutoffs(cutoffs_dict[stringency], stringency)
    assert sorted(family.get_cutoff_stringencies()) == sorted(['low', 'normal'])

    filepath = tmp_path / 'cutoffs.json'

    # Invalid JSON
    filepath.write_text('invalid content')
    result = run_cli_command(cmd_family_cutoffs_set, [family.label, str(filepath)], raises=True)
    assert "Error: Missing option '-s' / '--stringency'" in result.output
    assert sorted(family.get_cutoff_stringencies()) == sorted(['low', 'normal'])

    # Invalid cutoffs structure
    filepath.write_text(json.dumps({'Ar': {'cutoff_rho': 300}}))
    result = run_cli_command(cmd_family_cutoffs_set, [family.label, str(filepath), '-s', 'high'], raises=True)
    assert 'Error: Invalid value for CUTOFFS:' in result.output
    assert sorted(family.get_cutoff_stringencies()) == sorted(['low', 'normal'])

    # Set correct stringency
    stringency = 'high'
    filepath.write_text(json.dumps(cutoffs_dict['high']))
    result = run_cli_command(cmd_family_cutoffs_set, [family.label, str(filepath), '-s', stringency])
    assert 'Success: set cutoffs for' in result.output
    assert stringency in family.get_cutoff_stringencies()
    assert sorted(family.get_cutoff_stringencies()) == sorted(['low', 'normal', 'high'])
    assert family.get_cutoffs(stringency) == cutoffs_dict[stringency]


@pytest.mark.usefixtures('clear_db')
def test_family_cutoffs_set_unit(run_cli_command, get_pseudo_family, generate_cutoffs, tmp_path):
    """Test the `aiida-pseudo family cutoffs set` command with the ``--unit`` flag."""
    family = get_pseudo_family(cls=CutoffsFamily)
    stringency = 'normal'
    cutoffs = generate_cutoffs(family)

    # We explicitly set the unit to the default (eV) in case this is changed in the future to hartree.
    family.set_cutoffs(cutoffs, stringency, 'eV')

    filepath = tmp_path / 'cutoffs.json'
    filepath.write_text(json.dumps(cutoffs))

    # Invalid unit
    unit = 'GME stock'
    result = run_cli_command(
        cmd_family_cutoffs_set, [family.label, str(filepath), '-s', stringency, '-u', unit], raises=True
    )
    assert 'Error: Invalid value for UNIT:' in result.output

    # Correct unit
    unit = 'hartree'
    result = run_cli_command(cmd_family_cutoffs_set, [family.label, str(filepath), '-s', stringency, '-u', unit])
    assert family.get_cutoffs_unit() == unit


def test_family_show(clear_db, run_cli_command, get_pseudo_family):
    """Test the `aiida-pseudo show` command."""
    family = get_pseudo_family()
    result = run_cli_command(cmd_family_show, [family.label])
    for node in family.nodes:
        assert node.md5 in result.output
        assert node.element in result.output
        assert node.filename in result.output


def test_family_show_recommended_cutoffs(clear_db, run_cli_command, get_pseudo_family, generate_cutoffs_dict):
    """Test the `aiida-pseudo show` command for a family with recommended cutoffs."""
    family = get_pseudo_family(cls=CutoffsFamily)
    stringencies = ('normal', 'high')
    cutoffs_dict = generate_cutoffs_dict(family, stringencies=stringencies)

    for stringency, cutoffs in cutoffs_dict.items():
        family.set_cutoffs(cutoffs, stringency)

    # Test the command prints an error for a non-existing stringency
    result = run_cli_command(cmd_family_show, [family.label, '--stringency', 'non-existing'], raises=True)
    assert 'Invalid value for stringency: `non-existing` is not defined' in result.output

    # Test the command for default and explicit stringency
    for stringency in [None, 'high']:

        if stringency is not None:
            result = run_cli_command(cmd_family_show, [family.label, '--stringency', stringency, '--raw'])
        else:
            result = run_cli_command(cmd_family_show, [family.label, '--raw'])

        for index, node in enumerate(sorted(family.nodes, key=lambda pseudo: pseudo.element)):
            fields = result.output_lines[index].split()
            cutoffs = family.get_recommended_cutoffs(elements=node.element, stringency=stringency)
            assert node.element in fields[0]
            assert node.filename in fields[1]
            assert node.md5 in fields[2]
            assert_almost_equal(cutoffs[0], float(fields[3]))
            assert_almost_equal(cutoffs[1], float(fields[4]))


def test_family_show_argument_type(clear_db, run_cli_command, get_pseudo_family):
    """Test that `aiida-pseudo show` only accepts instances of `PseudoPotentialFamily` or subclasses as argument."""
    pseudo_family = get_pseudo_family(label='pseudo-family', cls=PseudoPotentialFamily)
    normal_group = Group('normal-group').store()

    run_cli_command(cmd_family_show, [pseudo_family.label])
    run_cli_command(cmd_family_show, [normal_group.label], raises=SystemExit)


def test_family_show_raw(clear_db, run_cli_command, get_pseudo_family):
    """Test the `-r/--raw` option."""
    family = get_pseudo_family()

    for option in ['-r', '--raw']:
        result = run_cli_command(cmd_family_show, [option, family.label])
        assert len(result.output_lines) == len(family.nodes)
