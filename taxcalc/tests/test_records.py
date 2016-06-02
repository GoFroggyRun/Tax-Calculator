import os
import sys
import numpy as np
from numpy.testing import assert_array_equal
import pandas as pd
CUR_PATH = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(CUR_PATH, '..', '..'))
from taxcalc import Policy, Records, Calculator, Growth

# use 1991 PUF-like data to emulate current puf.csv, which is private
TAXDATA_PATH = os.path.join(CUR_PATH, '..', 'altdata', 'puf91taxdata.csv.gz')
TAXDATA = pd.read_csv(TAXDATA_PATH, compression='gzip')
WEIGHTS_PATH = os.path.join(CUR_PATH, '..', 'altdata', 'puf91weights.csv.gz')
WEIGHTS = pd.read_csv(WEIGHTS_PATH, compression='gzip')


def test_create_records():
    recs = Records(data=TAXDATA, weights=WEIGHTS, start_year=Records.PUF_YEAR)
    assert recs
    assert np.any(recs.MARS != 0)


def test_blow_up():
    tax_dta = pd.read_csv(TAXDATA_PATH, compression='gzip')
    parms = Policy()
    parms_start_year = parms.current_year
    recs = Records(data=tax_dta, start_year=Records.PUF_YEAR)
    assert recs.current_year == Records.PUF_YEAR
    # r.current_year == PUF_YEAR ==> Calculator ctor will call r.blowup()
    calc = Calculator(policy=parms, records=recs)
    assert calc.current_year == parms_start_year


def test_for_duplicate_names():
    varnames = set()
    for varname in Records.VALID_READ_VARS:
        assert varname not in varnames
        varnames.add(varname)
        assert varname not in Records.CALCULATED_VARS
    varnames = set()
    for varname in Records.CALCULATED_VARS:
        assert varname not in varnames
        varnames.add(varname)
        assert varname not in Records.VALID_READ_VARS
    varnames = set()
    for varname in Records.INTEGER_READ_VARS:
        assert varname not in varnames
        varnames.add(varname)
        assert varname in Records.VALID_READ_VARS


def test_default_rates_and_those_implied_by_blowup_factors():
    """
    Check that default GDP growth rates, default wage growth rates, and
    default price inflation rates, are consistent with the rates embedded
    in the Records blowup factors (BF).
    """
    record = Records(TAXDATA_PATH)  # contains the blowup factors
    policy = Policy()  # contains the default indexing rates
    syr = Policy.JSON_START_YEAR
    endyr = Policy.LAST_BUDGET_YEAR
    nyrs = endyr - syr

    # back out original stage I GDP growth rates from blowup factors
    record.BF.AGDPN[Records.PUF_YEAR] = 1
    for year in range(Records.PUF_YEAR + 1, endyr + 1):
        record.BF.AGDPN[year] = (record.BF.AGDPN[year] *
                                 record.BF.AGDPN[year - 1] *
                                 record.BF.APOPN[year])

    # calculate nominal GDP growth rates from original GDP growth rates
    nominal_rates = np.zeros(nyrs)
    for year in range(syr + 1, endyr):
        irate = policy._inflation_rates[year - syr]
        nominal_rates[year - syr] = (record.BF.AGDPN[year] /
                                     record.BF.AGDPN[year - 1] - 1 - irate)

    # check that nominal_rates are same as default GDP growth rates
    nominal_rates = np.round(nominal_rates, 4)
    assert_array_equal(nominal_rates[1:], Growth.REAL_GDP_GROWTH_RATES[1:-1])

    # back out stage I inflation rates from blowup factors
    cpi_u = np.zeros(nyrs)
    for year in range(syr, endyr):
        cpi_u[year - syr] = record.BF.ACPIU[year] - 1

    # check that blowup rates are same as default inflation rates
    cpi_u = np.round(cpi_u, 4)
    assert_array_equal(cpi_u, policy._inflation_rates[:-1])

    # back out original stage I wage growth rates from blowup factors
    record.BF.AWAGE[Records.PUF_YEAR] = 1
    for year in range(Records.PUF_YEAR + 1, endyr):
        record.BF.AWAGE[year] = (record.BF.AWAGE[year] *
                                 record.BF.AWAGE[year - 1] *
                                 record.BF.APOPN[year])

    # calculate nominal wage growth rates from original wage growth rates
    wage_growth_rates = np.zeros(nyrs)
    for year in range(syr + 1, endyr):
        wage_growth_rates[year - syr] = (record.BF.AWAGE[year] /
                                         record.BF.AWAGE[year - 1] - 1)

    # check that blowup rates are same as default wage growth rates
    wage_growth_rates = np.round(wage_growth_rates, 4)
    assert_array_equal(wage_growth_rates[1:], policy._wage_growth_rates[1:-1])


def test_var_labels_txt_contents():
    """
    Check that every Records variable used by taxcalc is in var_labels.txt
    and that all variables in var_labels.txt are used by taxcalc.
    """
    # read variables in var_labels.txt file (checking for duplicates)
    var_labels_path = os.path.join(CUR_PATH, '..', 'var_labels.txt')
    var_labels_set = set()
    with open(var_labels_path, 'r') as input:
        for line in input:
            var = (line.split())[0]
            if var in var_labels_set:
                msg = 'DUPLICATE_IN_VAR_LABELS.TXT: {}\n'.format(var)
                sys.stdout.write(msg)
                assert False
            else:
                var_labels_set.add(var)
    # change all VALID variables to uppercase
    var_used_set = set()
    for var in Records.VALID_READ_VARS:
        var_used_set.add(var.upper())
    # check for no extra var_used variables
    used_less_labels = var_used_set - var_labels_set
    assert len(used_less_labels) == 0
    # check for no extra var_labels variables
    labels_less_used = var_labels_set - var_used_set
    assert len(labels_less_used) == 0
