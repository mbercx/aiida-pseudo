# -*- coding: utf-8 -*-
"""Commands to inspect or modify the contents of pseudo potential families."""
import json

import click

from aiida.cmdline.params import options as options_core
from aiida.cmdline.utils import decorators, echo

from ..groups.mixins import RecommendedCutoffMixin
from .params import arguments, options
from .root import cmd_root


@cmd_root.group('family')
def cmd_family():
    """Command group to inspect or modify the contents of pseudo potential families."""


@cmd_family.command('show')
@arguments.PSEUDO_POTENTIAL_FAMILY()
@options.STRINGENCY()
@options_core.RAW()
@decorators.with_dbenv()
def cmd_family_show(family, stringency, raw):
    """Show details of pseudo potential family."""
    from tabulate import tabulate

    if isinstance(family, RecommendedCutoffMixin):

        if stringency is not None and stringency not in family.get_cutoff_stringencies():
            raise click.BadParameter(f'`{stringency}` is not defined for family `{family}`.', param_hint='stringency')

        headers = ['Element', 'Pseudo', 'MD5', 'Wavefunction (eV)', 'Charge density (eV)']
        rows = [[
            pseudo.element, pseudo.filename, pseudo.md5,
            *family.get_recommended_cutoffs(elements=pseudo.element, stringency=stringency)
        ] for pseudo in family.nodes]
    else:
        headers = ['Element', 'Pseudo', 'MD5']
        rows = [[pseudo.element, pseudo.filename, pseudo.md5] for pseudo in family.nodes]

    if raw:
        echo.echo(tabulate(sorted(rows), tablefmt='plain', floatfmt='.1f'))
    else:
        echo.echo(tabulate(sorted(rows), headers=headers, floatfmt='.1f'))


@cmd_family.group('cutoffs')
def cmd_family_cutoffs():
    """Command group to inspect or modify the recommended cutoffs of pseudo potential families."""


@cmd_family_cutoffs.command('set')
@arguments.PSEUDO_POTENTIAL_FAMILY()
@click.argument('cutoffs', type=click.File(mode='rb'))
@options.STRINGENCY(required=True)
@options.UNIT()
@decorators.with_dbenv()
def cmd_family_cutoffs_set(family, cutoffs, stringency, unit):  # noqa: D301
    """Set the recommended cutoffs for a pseudo potential family and a specified stringency.

    The cutoffs should be provided as a JSON file through the argument `CUTOFFS` which should have the structure:

    \b
        {
            "Ag": {
                "cutoff_wfc": 50.0,
                "cutoff_rho": 200.0
            },
            ...
        }

    where the cutoffs are expected to be in electronvolt by default.
    """
    if not isinstance(family, RecommendedCutoffMixin):
        raise click.BadParameter(f'family `{family}` does not support recommended cutoffs to be set.')

    try:
        family.validate_cutoffs_unit(unit)
    except ValueError as exception:
        raise click.BadParameter(f'{exception}', param_hint='UNIT')

    try:
        data = json.load(cutoffs)
    except ValueError as exception:
        raise click.BadParameter(f'`{cutoffs.name}` contains invalid JSON: {exception}', param_hint='CUTOFFS')

    try:
        family.set_cutoffs(data, stringency, unit=unit)
    except ValueError as exception:
        raise click.BadParameter(f'`{cutoffs.name}` contains invalid cutoffs: {exception}', param_hint='CUTOFFS')

    echo.echo_success(f'set cutoffs for `{family}` with the stringency `{stringency}`.')
