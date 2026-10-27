# GulfTrade five-minute demo script

## Before presenting

1. Create the environment and install dependencies as described in `README.md`.
2. Run `python make_data.py`, then `python build_sqlite.py`.
3. Run `streamlit run app.py`.
4. Leave API keys unset for an offline demo, or configure `.env` if demonstrating the optional Assistant tab.

## 1. Establish the planning context — 30 seconds

Open the sidebar and state that GulfTrade is a fictional UAE B2B distributor with 20 SKUs, three locations, about 5,000 available units, 90 days of history and a 30-day horizon. Point out the planning cutoff and that the application is decision support only.

## 2. Review data quality and censored demand — 45 seconds

Open **Forecast**. Select `SKU01` and `Abu Dhabi`. Show P10, P50 and P90 together. Expand **See how distorted sales were corrected** and explain that stockout zeros and missing rows are not treated as proof of zero demand. State that the cleaned values are model assumptions, while observed values remain visible.

## 3. Identify the core imbalance — 45 seconds

Open **Stock overview** and filter to `SKU01`. Show the planted position: Dubai has 500 available, Abu Dhabi has 100 and Sharjah has 300. Then open **Imbalances** and filter/read the `SKU01` Abu Dhabi position. Explain that stock, demand, safety stock and inbound timing are evaluated together.

## 4. Review a feasible transfer — 60 seconds

Open **Recommendations**. Select the `SKU01` Dubai-to-Abu Dhabi proposal. Expand **Why this transfer?** and **Recommendation evidence and timestamps**. Explain that it was admitted only because it preserves source surplus after forecast and safety stock, arrives before projected stockout and has positive estimated net benefit after route costs. Emphasise that estimated benefit is not guaranteed savings.

Click **Open human review**. Explain that the approval gate pauses for an explicit planner decision. Choose **Reject** for the demo or **Approve** only as a demonstration of the audit trail. Point out that no stock is moved in either case.

## 5. Show an uneconomic alternative — 30 seconds

In **Why not? Rejected transfer candidates**, find `SKU05` to Abu Dhabi. Explain that a shortage alone does not justify a transfer: the fixed route cost exceeds recoverable margin/benefit for this low-margin case.

## 6. Explain impact and ageing — 30 seconds

Open **Impact**. Explain the distinction between baseline, before and after. “After” assumes all listed proposals, not just approved proposals. Note that ageing savings only credit consumption of the initially old cohort; moving stock alone is not credited as an ageing reduction.

## 7. Demonstrate difficult disruption scope — 45 seconds

In the sidebar select **component_shortage**. Show the explicit affected-SKU list and its assumed inbound delay. Explain that it changes only listed semiconductor-dependent SKUs; semiconductor dependency alone is insufficient. Switch to **shipping_delay** and show its additional route restriction. Return to **None**.

## 8. Show transparent corrections and close — 15 seconds

Open **Edit records**, select a dataset and show that changes are session-local, preserve row identity/source metadata and recompute the entire plan. Close by stating that production use would require governed integrations, capacity data, permissions, monitoring and calibration on real demand.

## Optional assistant demonstration

If configured, ask: “Explain the SKU01 Abu Dhabi forecast and proposed transfer.” Show tool evidence. Do not ask the assistant to approve, buy, book or move stock; it has no execution capability.
