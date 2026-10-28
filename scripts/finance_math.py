"""Independent, deterministic screening mathematics. Not verified project inputs."""

def annuity_factor(rate, years):
    if rate <= 0 or years <= 0:
        raise ValueError("Requires positive discount rate and year count")
    return sum(1 / (1 + rate) ** t for t in range(1, years + 1))

def annual_contribution(teu, teu_margin, general_tonnes, general_margin,
                        fish_tonnes, fish_margin, capex, fixed_opex_fraction):
    return (teu * teu_margin + general_tonnes * general_margin
            + fish_tonnes * fish_margin - capex * fixed_opex_fraction)

def flat_npv(capex, annual_cm, rate, years):
    return -capex + annual_cm * annuity_factor(rate, years)

def ramp_npv(capex, teu, teu_margin, general_tonnes, general_margin,
             fish_tonnes, fish_margin, fixed_opex_fraction, rate, ramps):
    fixed = capex * fixed_opex_fraction
    annual_gross = teu * teu_margin + general_tonnes * general_margin + fish_tonnes * fish_margin
    return -capex + sum((annual_gross * ramp - fixed) / ((1 + rate) ** t)
                        for t, ramp in enumerate(ramps, 1))

def break_even_teu_margin(capex, teu, general_tonnes, general_margin,
                          fish_tonnes, fish_margin, fixed_opex_fraction, rate, ramps):
    if teu <= 0 or not ramps:
        raise ValueError("Require positive TEU and at least one year")
    factor = sum(1 / (1 + rate) ** t for t in range(1, len(ramps) + 1))
    weighted = sum(ramp / (1 + rate) ** t for t, ramp in enumerate(ramps, 1))
    if weighted <= 0:
        raise ValueError("No positive discounted operating capacity")
    other = general_tonnes * general_margin + fish_tonnes * fish_margin
    fixed = capex * fixed_opex_fraction
    return (capex + fixed * factor - other * weighted) / (teu * weighted)

def incremental_group_margin(contracted, diverted, duplicated, new_unit_margin,
                             incumbent_unit_margin, incremental_fixed, additional_risk):
    if any(x < 0 for x in (contracted, diverted, duplicated,
                           incremental_fixed, additional_risk)):
        raise ValueError("Negative volume or cost")
    if diverted + duplicated > contracted:
        raise ValueError("Diverted plus duplicate exceeds contracted")
    net_new = contracted - diverted - duplicated
    cm = (net_new * new_unit_margin
          + diverted * (new_unit_margin - incumbent_unit_margin)
          - incremental_fixed - additional_risk)
    return net_new, cm
