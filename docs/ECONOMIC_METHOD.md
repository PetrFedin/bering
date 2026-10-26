# Modeling standards and known scenarios

## Do not collapse cost perimeters
Historical project-initiator full-corridor capital estimate **USD 249.915bn** is *not an approved feasibility estimate*, and the reported USD 35bn submarine segment must not be added again if already included. This scope is not the standalone Magadan hub.

V7 illustrates construction delay: test inputs of 12 years build, 50 years operations, 5% real discount rate, OPEX 1.5% CAPEX and recurring reinvestment 0.5% CAPEX, hypothetic freight 30m tonnes/year and net contribution USD 100/tonne and 98% availability. An indicated USD ~23.156bn/year hurdle and ~USD 787.63 per available tonne are **screening assumptions**, not a project tariff, forecast or proven debt service capacity.

## Individual route comparison
```
D2D_route = pickup + freight + customs + terminal_not_included + handling_not_included
          + storage + insurance + last_mile + equipment + risk_cost
          +/- tax_cash_flow_impacts
```
`value_of_time = goods_value * cost_of_capital * days_saved / 365`.
This is shipper's value of working capital, NOT additional tunnel company revenue.

`max_affordable_new_route_premium = comparator_D2D - new_route_D2D_without_premium + value_of_time + validated_risk_delta`.

## Standalone hub comparison
Reconcile net-new cargo against 24-month shipper/receiver baseline and all incumbent terminals controlled by the same group. Contribution margin is incremental at group level, not gross port revenue. Analyze at least base, low demand, CAPEX overrun, delayed opening, maintenance ramp, currency/tax, severe disruption and no-tunnel scenarios.

## Evidence requirements
Workbook formulas should use reference cells, have independent QA and source comments, and leave missing input cells empty instead of imputing fake contract rates. Avoid reporting IRR of an investor proposal as independently proven without underlying operating projections.

## Risk and accounting
Separate unlevered FCFF from interest, repayments and financing fees; interest during construction is not added a second time to unlevered NPV. Social CBA and project-finance NPV have different discount rates and beneficiaries.
