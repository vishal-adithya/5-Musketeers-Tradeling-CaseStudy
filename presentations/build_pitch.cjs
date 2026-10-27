const pptxgen = require('pptxgenjs');
const fs = require('node:fs');
const path = require('node:path');

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'GulfTrade project';
pptx.subject = 'Investor discussion: evidence-backed inventory planning prototype';
pptx.title = 'GulfTrade — Make existing stock work harder';
pptx.company = 'GulfTrade — prototype venture concept';
pptx.lang = 'en-GB';
pptx.theme = {
  headFontFace: 'Avenir Next',
  bodyFontFace: 'Avenir Next',
  lang: 'en-GB',
};

const C = {
  navy: '102A43', dark: '0A2032', teal: '007F78', mint: '65D9BE',
  cream: 'F6F4EF', white: 'FFFFFF', ink: '16354A', muted: '526574',
  light: 'E5EEE9', line: 'D5DFDB', gold: 'C4913E', red: 'A7443C',
  paleRed: 'F6E9E5', paleGold: 'F1E8D6', paleTeal: 'DDEEE8', steel: 'A9C1CC',
};
const W = 13.333333;
const H = 7.5;
const records = [];
let count = 0;

function box(slide, x, y, w, h, fill, radius = false, stroke) {
  slide.addShape(radius ? pptx.ShapeType.roundRect : pptx.ShapeType.rect, {
    x, y, w, h, radius: 0.12, rectRadius: 0.12,
    line: { color: stroke || fill, width: stroke ? 0.7 : 0 },
    fill: { color: fill },
  });
}
function text(slide, value, x, y, w, h, size = 16, color = C.ink, bold = false, extra = {}) {
  const item = { text: value, x, y, w, h, size };
  records[count - 1].elements.push(item);
  slide.addText(value, {
    x, y, w, h, fontFace: 'Avenir Next', fontSize: size,
    color, bold, margin: 0, breakLine: false, valign: 'mid',
    paraSpaceAfterPt: 0, ...extra,
  });
}
function line(slide, x, y, w, h = 0, color = C.line, width = 1.2, extra = {}) {
  slide.addShape(pptx.ShapeType.line, { x, y, w, h, line: { color, width, ...extra } });
}
function pill(slide, label, x, y, w, fill = C.paleTeal, color = C.teal) {
  box(slide, x, y, w, 0.34, fill, true);
  text(slide, label, x + 0.12, y, w - 0.24, 0.34, 10.5, color, true);
}
function circle(slide, x, y, size, fill) {
  slide.addShape(pptx.ShapeType.ellipse, { x, y, w: size, h: size, fill: { color: fill }, line: { color: fill, width: 0 } });
}
function arrow(slide, x, y, w, h, fill = C.teal) {
  slide.addShape(pptx.ShapeType.rightArrow, { x, y, w, h, fill: { color: fill }, line: { color: fill, width: 0 } });
}
function base(section, title, subtitle = '', dark = false, source = '') {
  const slide = pptx.addSlide();
  count += 1;
  records.push({ slide: count, title, elements: [] });
  slide.background = { color: dark ? C.dark : C.cream };
  const ink = dark ? C.white : C.ink;
  text(slide, 'GULFTRADE', 0.62, 0.31, 2.1, 0.28, 12, dark ? C.mint : C.teal, true, { charSpacing: 2.2 });
  text(slide, section.toUpperCase(), 8.7, 0.31, 4.0, 0.28, 10.5, dark ? C.steel : C.muted, true, { align: 'right', charSpacing: 1.3 });
  if (title) text(slide, title, 0.62, 1.01, 12.05, 1.02, 36, ink, true, { valign: 'top', breakLine: false });
  if (subtitle) text(slide, subtitle, 0.65, 2.10, 11.8, 0.56, 15.5, dark ? C.steel : C.muted);
  text(slide, source || 'Investor discussion  |  Prototype concept  |  27 October 2026', 0.64, 6.98, 11.45, 0.27, 11, dark ? C.steel : C.muted);
  text(slide, String(count).padStart(2, '0'), 12.10, 6.98, 0.58, 0.25, 11, dark ? C.mint : C.teal, true, { align: 'right' });
  return slide;
}
function notes(slide, body, sources) {
  slide.addNotes(`${body}\n\nEVIDENCE AND CLAIM STATUS\n${sources}`);
}
function card(slide, x, y, w, h, number, title, body, fill = C.white) {
  box(slide, x, y, w, h, fill, true);
  circle(slide, x + 0.25, y + 0.27, 0.46, C.teal);
  text(slide, number, x + 0.25, y + 0.27, 0.46, 0.46, 14, C.white, true, { align: 'center' });
  text(slide, title, x + 0.25, y + 0.98, w - 0.5, 0.65, 22, C.ink, true, { valign: 'top' });
  text(slide, body, x + 0.25, y + 1.81, w - 0.5, h - 2.04, 16, C.muted, false, { valign: 'top' });
}

{
  const s = base('Investor introduction', '', '', true);
  pill(s, 'PROTOTYPE VENTURE CONCEPT', 0.65, 1.27, 3.02, '18463F', C.mint);
  text(s, 'Make existing\nstock work\nharder.', 0.65, 1.91, 7.0, 2.55, 49, C.white, true, { breakLine: false, valign: 'top' });
  text(s, 'Decision intelligence for B2B distributors.', 0.68, 4.84, 6.6, 0.57, 23, C.mint, true);
  text(s, 'Spot misplaced inventory. Compare the economics.\nKeep every decision in human hands.', 0.68, 5.63, 6.5, 0.85, 18, C.steel);
  box(s, 8.16, 1.65, 4.53, 4.95, '123349', true);
  text(s, 'ONE NETWORK. BETTER DECISIONS.', 8.48, 1.97, 3.85, 0.40, 11.5, C.mint, true);
  const nodes = [
    { y: 2.67, city: 'DUBAI', value: '500', label: 'available units' },
    { y: 3.89, city: 'ABU DHABI', value: '100', label: 'available units' },
    { y: 5.11, city: 'SHARJAH', value: '300', label: 'available units' },
  ];
  line(s, 8.70, 3.20, 0, 2.28, C.mint, 2.5);
  nodes.forEach(n => {
    circle(s, 8.55, n.y + 0.30, 0.3, C.mint);
    text(s, n.city, 9.11, n.y + 0.02, 2.90, 0.27, 10.5, C.steel, true, { charSpacing: 1.4 });
    text(s, n.value, 9.08, n.y + 0.32, 1.08, 0.50, 30, C.white, true);
    text(s, n.label, 10.40, n.y + 0.45, 1.78, 0.24, 11, C.steel);
  });
  notes(s, 'Opening (35 seconds). GulfTrade is a proposed software venture built from a fictional UAE distributor case study, not an operating distributor presented as a funded company. The product makes fragmented inventory decisions visible, economically accountable and reviewable. Introduce the three-location example; these are synthetic SKU01 available-stock values, not customer traction.', 'Current data/inventory.csv: SKU01 Dubai 500, Abu Dhabi 100, Sharjah 300. Branding is the project concept. No commercial traction, team credentials or fundraising terms have been supplied.');
}
{
  const s = base('The problem', 'Stock can be plentiful. Availability can still fail.', 'The planner needs a decision—not another disconnected spreadsheet.');
  card(s, 0.65, 2.98, 3.83, 3.54, '01', 'Demand gets hidden', 'Stockout zeros and missing sales rows can make an active market look quiet.');
  card(s, 4.76, 2.98, 3.83, 3.54, '02', 'Capital sits idle', 'One location carries ageing stock while another cannot meet demand.');
  card(s, 8.86, 2.98, 3.83, 3.54, '03', 'The cure can cost more', 'A rushed transfer may arrive late—or consume more margin than it saves.');
  notes(s, 'Problem (40 seconds). Walk through the three decision failures, not a broad unsourced market claim. These patterns are deliberately represented in the synthetic pack. The commercial hypothesis is that a planner will pay for an auditable, repeatable workflow that connects these decisions.', 'data/README.md; make_data.py; engine/quality.py; engine/optimizer.py. The problem frequency and willingness to pay have not been validated with real customers.');
}
{
  const s = base('Customer & opportunity', 'Start with one urgent buyer.', 'Proposed beachhead: multi-location UAE B2B electronics distributors.');
  box(s, 0.65, 2.96, 4.19, 3.62, C.navy, true);
  text(s, 'THE BUYER', 0.94, 3.23, 3.56, 0.25, 12, C.mint, true);
  text(s, 'Head of operations\nor inventory planning', 0.94, 3.90, 3.51, 1.0, 26, C.white, true);
  text(s, 'Owns availability, working capital\nand inter-warehouse decisions.', 0.96, 5.32, 3.45, 0.72, 16, C.steel);
  const rows = [
    ['LAND', 'A single distributor network', 'Use familiar CSV exports; prove one repeatable planning workflow.'],
    ['EXPAND', 'More locations and product lines', 'Reuse mappings and decision history once value is demonstrated.'],
    ['VALIDATE', 'Size the reachable market bottom-up', 'Qualified accounts × validated annual price. No TAM claim yet.'],
  ];
  rows.forEach((r, i) => {
    const y = 3.03 + i * 1.21;
    pill(s, r[0], 5.24, y + 0.05, 1.32);
    text(s, r[1], 6.82, y, 5.63, 0.44, 21, C.ink, true);
    text(s, r[2], 6.84, y + 0.54, 5.56, 0.52, 15, C.muted);
  });
  notes(s, 'Customer and market (45 seconds). We deliberately start with a narrow buyer and operational job. This is a go-to-market hypothesis, not market research or an existing customer list. There is no externally validated TAM, SAM, SOM or competitor market-share estimate in this deck. A first commercial milestone is to enumerate reachable accounts and test willingness to pay.', 'Proposed strategy derived from the case-study domain. No market sizing, buyer interviews or account pipeline supplied.');
}
{
  const s = base('The product', 'One workspace. Seven steps to a defensible plan.', 'Working Streamlit interface with deterministic calculations and optional tool-grounded chat.');
  const groups = [
    { x: 0.65, title: '01 / UNDERSTAND', fill: C.navy, items: [['Stock overview', 'Available, reserved, inbound + sources'], ['Forecast', 'P10 / P50 / P90 demand + data quality']] },
    { x: 4.76, title: '02 / DECIDE', fill: C.teal, items: [['Imbalances', 'Shortage, excess and ageing exceptions'], ['Recommendations', 'Feasible quantities, routes and economics'], ['Impact', 'Before / after outcomes on one forecast']] },
    { x: 8.86, title: '03 / CONTROL', fill: C.navy, items: [['Edit records', 'Correct once; recompute the whole plan'], ['Assistant', 'Explain evidence; stage changes for review']] },
  ];
  groups.forEach(g => {
    box(s, g.x, 2.99, 3.83, 0.62, g.fill, true);
    text(s, g.title, g.x + 0.23, 3.00, 3.37, 0.59, 14, C.white, true);
    g.items.forEach((item, i) => {
      const y = 3.81 + i * 0.82;
      box(s, g.x, y, 3.83, 0.72, C.white, true);
      text(s, item[0], g.x + 0.20, y + 0.06, 3.41, 0.27, 16, C.ink, true);
      text(s, item[1], g.x + 0.20, y + 0.39, 3.41, 0.24, 11.5, C.muted);
    });
  });
  box(s, 0.66, 6.52, 12.02, 0.35, C.paleTeal, true);
  text(s, 'Human review required. No stock movement executes.', 0.83, 6.54, 11.66, 0.30, 13, C.teal, true);
  notes(s, 'Product (50 seconds). This is a workflow diagram of the implemented seven-tab application, not a fabricated customer screenshot. Explain that calculations run without a model API key. The optional assistant retrieves typed tool evidence; it does not invent quantities or execute transactions. Corrections remain session-local and approvals are local intent logs. Offer to switch to the live demo after the pitch.', 'app.py; agent/assistant.py; agent/approval.py; engine/state.py. SQL is a derived read model; the current planning app reads the canonical CSV pack.');
}
{
  const s = base('Synthetic demonstration', 'The right stock exists. It is in the wrong place.', 'SKU01 charger | Current prototype snapshot: 26 October 2026 | Forecast: next 30 days', false, 'Source: current seed-42 pipeline. Synthetic data; fitted forecasts are uncertain, not customer demand commitments.');
  const cols = [
    { x: 0.65, city: 'DUBAI', qty: '500', tag: 'Source surplus', p50: '191.50', range: 'P10 175.46 / P90 207.54' },
    { x: 4.76, city: 'ABU DHABI', qty: '100', tag: 'Shortage risk', p50: '353.06', range: 'P10 334.21 / P90 371.90' },
    { x: 8.86, city: 'SHARJAH', qty: '300', tag: 'Network alternative', p50: '159.75', range: 'P10 147.50 / P90 172.00' },
  ];
  cols.forEach((c, i) => {
    box(s, c.x, 2.92, 3.83, 2.76, C.white, true);
    text(s, c.city, c.x + 0.25, 3.13, 2.9, 0.28, 12, C.teal, true, { charSpacing: 1.1 });
    text(s, c.qty, c.x + 0.23, 3.58, 1.94, 0.79, 49, i === 1 ? C.red : C.ink, true);
    text(s, 'available units', c.x + 1.96, 3.99, 1.61, 0.27, 12, C.muted);
    text(s, `P50 demand ${c.p50}`, c.x + 0.26, 4.67, 3.24, 0.32, 20, C.ink, true);
    text(s, c.range, c.x + 0.27, 5.13, 3.24, 0.24, 11, C.muted);
  });
  box(s, 0.65, 5.98, 12.04, 0.66, C.teal, true);
  text(s, '234 units', 0.90, 6.10, 1.95, 0.35, 23, C.white, true);
  arrow(s, 3.0, 6.22, 0.70, 0.19, C.mint);
  text(s, 'Dubai to Abu Dhabi', 3.99, 6.13, 3.11, 0.31, 19, C.white, true);
  text(s, '2-day lead | AED 171.80 transfer cost', 7.31, 6.16, 5.08, 0.26, 14, C.white);
  notes(s, 'Demonstration (60 seconds). Dubai has 500 available; Abu Dhabi has 100. Present all three forecast values as ranges, not just P50. The current implementation proposes 234 units from Dubai to Abu Dhabi at two days lead and AED 171.80 cost. It accounts for a 20-unit source buffer and a 40-unit Abu Dhabi inbound receipt on day 5. This is the CURRENT seed-42 app result, not the original drafting request for 150–180 units. It is synthetic and has not been executed. Do not generalize this one example into customer traction.', 'Computed with run_pipeline(load_data()), scenario None, on 27 October 2026. SKU01 fitted forecasts: Dubai 175.459260 / 191.5 / 207.540740; Abu Dhabi 334.208460 / 353.056439 / 371.904419; Sharjah 147.498683 / 159.75 / 172.001317. Current source dates differ from the earlier database draft; this deck consistently uses the current app pack.');
}
{
  const s = base('Illustrative value', 'A measurable case for better allocation.', 'Synthetic 30-day simulation | Same cleaned forecast, before and after all proposed transfers', false, 'Source: eval_report.md, normal-plan impact. Proposals are not executed; these are modeled estimates, not realised savings.');
  box(s, 0.65, 2.99, 7.01, 3.65, C.white, true);
  text(s, 'PROJECTED SHORTAGE UNITS', 0.96, 3.25, 5.57, 0.27, 12, C.muted, true);
  text(s, 'No transfers', 0.98, 3.98, 1.75, 0.31, 15, C.ink, true);
  box(s, 2.94, 3.95, 3.61, 0.43, C.navy);
  text(s, '452.16', 6.70, 4.00, 0.70, 0.25, 12, C.ink, true);
  text(s, 'With proposals', 0.98, 4.81, 1.84, 0.31, 15, C.ink, true);
  box(s, 2.94, 4.78, 3.61 * 96.50 / 452.16, 0.43, C.teal);
  text(s, '96.50', 3.94, 4.83, 0.90, 0.25, 12, C.teal, true);
  text(s, 'Same network. Same demand model. Different allocation.', 0.98, 5.82, 6.15, 0.33, 14, C.muted);
  box(s, 8.00, 2.99, 4.69, 1.64, C.teal, true);
  text(s, '78.7%', 8.31, 3.14, 3.76, 0.79, 47, C.white, true);
  text(s, 'fewer projected shortage units', 8.34, 4.08, 3.96, 0.27, 15, C.white);
  box(s, 8.00, 4.95, 4.69, 1.69, C.navy, true);
  text(s, 'AED 5,911.64', 8.31, 5.14, 4.05, 0.62, 31, C.white, true);
  text(s, 'Net benefit after transfer costs', 8.33, 5.91, 4.02, 0.27, 13, C.white);
  text(s, 'MODELLED, NOT REALISED', 8.33, 6.28, 4.02, 0.23, 11.5, C.mint, true);
  notes(s, 'Value (50 seconds). The model reduces projected network shortage from 452.16 to 96.50 units, or 78.7 percent, assuming every proposal occurs. Net benefit is AED 5,911.64 after AED 370.30 in transfer costs. Avoided lost-sales margin is the main modeled driver. This is NOT revenue, ARR, booked savings or a proven ROI. Do not annualise this tiny synthetic network or compare the raw-demand baseline to the cleaned forecast as if that difference were causal. Ageing exposure is unchanged in this run, so do not claim an ageing improvement.', 'eval_report.md rows Before and After. Percentage calculated as (452.16 - 96.50) / 452.16 × 100. Both rows use the same cleaned P50 demand. FEFO, constant margin, execution friction excluded and all-proposal execution are modeling assumptions.');
}
{
  const s = base('Trust & differentiation', 'Designed to say “no” when the economics do.', 'The product is an accountable decision layer—not an autonomous stock-moving agent.');
  box(s, 0.65, 2.98, 5.02, 3.62, C.paleRed, true);
  pill(s, 'REJECTED / LOW-MARGIN TRANSFER', 0.92, 3.24, 3.96, 'EDD1CA', C.red);
  text(s, 'AED 19.06', 0.97, 3.94, 2.77, 0.59, 31, C.ink, true);
  text(s, 'expected benefit', 3.61, 4.15, 1.70, 0.26, 12, C.muted);
  text(s, 'AED 231.80', 0.97, 4.80, 2.94, 0.57, 31, C.red, true);
  text(s, 'transfer cost', 3.87, 5.00, 1.45, 0.26, 12, C.muted);
  text(s, 'Net: AED −212.74. Reject transfer.', 0.98, 5.87, 4.27, 0.39, 17, C.red, true);
  const controls = [
    ['Scoped events', 'Only listed products and matching inbound routes are affected.'],
    ['Traceable calculations', 'Source rows, timestamps, assumptions and cost breakdowns.'],
    ['Explicit human approval', 'A dated intent log. No purchasing or stock movement executes.'],
  ];
  controls.forEach((v, i) => {
    const y = 3.03 + i * 1.25;
    circle(s, 6.05, y + 0.10, 0.43, C.teal);
    text(s, String(i + 1), 6.05, y + 0.10, 0.43, 0.43, 13, C.white, true, { align: 'center' });
    text(s, v[0], 6.77, y, 5.49, 0.45, 22, C.ink, true);
    text(s, v[1], 6.80, y + 0.61, 5.42, 0.52, 15, C.muted);
  });
  notes(s, 'Trust (45 seconds). One SKU05 candidate in the current test pack offers AED 19.06 expected benefit but costs AED 231.80, so the system rejects it. These are deliberately planted synthetic values, not customer economics. Emphasise specificity: component events require an explicit whitelist; shipping also requires route matching. The current approval log is not enterprise access control, and governance still needs production work.', 'eval_report.md, uneconomic case; engine/scenarios.py; agent/approval.py. Negative net is 19.06 - 231.80 = -212.74. No claim of patented, unique or independently benchmarked differentiation.');
}
{
  const s = base('Business model hypothesis', 'Sell the decision workflow. Price the network.', 'Proposed commercial model—not current revenue, signed contracts or validated pricing.');
  card(s, 0.65, 2.98, 3.83, 3.29, '01', 'Paid pilot', 'Fixed-scope onboarding, baseline measurement and a planner-reviewed trial.');
  card(s, 4.76, 2.98, 3.83, 3.29, '02', 'Annual subscription', 'Platform fee with location or SKU-volume tiers. Price to be tested with buyers.');
  card(s, 8.86, 2.98, 3.83, 3.29, '03', 'Integration services', 'ERP/WMS mapping and connectors, priced separately.');
  text(s, 'Commercial gate: validate willingness to pay and delivery cost before forecasting ARR or margin.', 0.73, 6.49, 11.85, 0.31, 16, C.teal, true);
  notes(s, 'Business model (40 seconds). This is a recommended initial model for investor discussion. No pricing, contracts, recurring revenue or margins are evidenced by the repository. Test price against attributable realized benefit and integration/support costs. There is no success fee on synthetic savings. Avoid an ARR forecast until account conversion and retention assumptions are supported.', 'Commercial hypothesis proposed for this presentation. No supplied revenue, pricing research, signed pilot or customer counts.');
}
{
  const s = base('Positioning', 'Add decision intelligence. Keep the ERP.', 'Compete for the planner’s daily decision workflow before expanding the product surface.');
  const stack = [
    { x: 0.65, label: 'SYSTEMS OF RECORD', title: 'Stock & sales data', body: 'CSV exports today\nERP / WMS connections later', fill: C.white, ink: C.ink },
    { x: 4.76, label: 'GULFTRADE', title: 'Decision intelligence', body: 'Forecast + feasibility + economics\nEvidence attached to each action', fill: C.navy, ink: C.white },
    { x: 8.86, label: 'PLANNER', title: 'Review & learn', body: 'Approve / reject intent today\nOutcome feedback in a pilot', fill: C.white, ink: C.ink },
  ];
  stack.forEach((v, i) => {
    box(s, v.x, 3.08, 3.83, 2.75, v.fill, true);
    text(s, v.label, v.x + 0.26, 3.34, 3.30, 0.27, 12, i === 1 ? C.mint : C.teal, true);
    text(s, v.title, v.x + 0.26, 4.08, 3.35, 0.50, 23, v.ink, true);
    text(s, v.body, v.x + 0.26, 4.97, 3.33, 0.59, 14, i === 1 ? C.steel : C.muted);
  });
  arrow(s, 4.48, 4.14, 0.25, 0.29);
  arrow(s, 8.58, 4.14, 0.25, 0.29);
  text(s, 'Potential defensibility: reusable data mappings, operational constraints and measured decision outcomes.', 0.73, 6.19, 11.80, 0.64, 17, C.teal, true);
  notes(s, 'Positioning (40 seconds). Alternatives include manual spreadsheets, existing ERP reports and dedicated planning software. This deck does not present an unresearched competitor feature matrix or claim that competitors cannot perform these tasks. GulfTrade aims to differentiate with a focused combination of evidence and economically feasible network decisions. Future data mappings and outcome history could create retention value, but this is not an existing moat. Production integrations and feedback loops are roadmap, not current capability.', 'app.py; engine/optimizer.py; build_sqlite.py; SUPPORT_NOTE.md. Positioning and potential defensibility are hypotheses, not verified competitive research.');
}
{
  const s = base('Go-to-market proposal', 'Prove a paid deployment. Then scale.', 'Founder-led distribution discovery, followed by a tightly measured pilot.');
  const stages = [
    ['01', 'Recruit design partners', 'Target three qualified distributor teams. Confirm data access and a named planner owner.'],
    ['02', 'Run in shadow mode', 'Record current decisions and measure recommendations without executing movements.'],
    ['03', 'Convert on evidence', 'Offer paid deployment only after buyer-agreed value and adoption gates are met.'],
  ];
  stages.forEach((v, i) => {
    const x = 0.65 + i * 4.105;
    circle(s, x + 0.05, 3.09, 0.64, i === 1 ? C.teal : C.navy);
    text(s, v[0], x + 0.05, 3.09, 0.64, 0.64, 19, C.white, true, { align: 'center' });
    if (i < 2) line(s, x + 1.02, 3.40, 2.66, 0, C.line, 2.5);
    text(s, v[1], x + 0.05, 4.11, 3.68, 0.85, 25, C.ink, true, { valign: 'top' });
    text(s, v[2], x + 0.06, 5.23, 3.54, 0.99, 17, C.muted, false, { valign: 'top' });
  });
  pill(s, 'TARGETS, NOT SIGNED PARTNERS. NO CUSTOMER TRACTION IS CLAIMED.', 0.71, 6.55, 8.56, C.paleGold, '76541E');
  notes(s, 'Go to market (45 seconds). Three design partners is a proposed target, not a signed pipeline. Begin with direct introductions to distribution operators. Agree a baseline and success criteria before offering a paid pilot. Track time-to-first-plan, planner acceptance, exceptions, data reconciliation and measured contribution net of execution costs. A future channel route could involve ERP implementers once onboarding is repeatable; no partner agreements are claimed.', 'Proposed go-to-market strategy. Repository contains synthetic inputs only, not customer pipeline evidence.');
}
{
  const s = base('Proposed 90-day pilot', 'De-risk data, trust and value—in that order.', 'Milestone sequence begins after partner access, staffing and scope are agreed.');
  const stages = [
    { x: 0.65, period: 'DAYS 01–30', title: 'Reliable inputs', deliver: 'Map sources. Reconcile inventory.\nEstablish the baseline and permissions.', gate: 'Gate: trusted source data' },
    { x: 4.76, period: 'DAYS 31–60', title: 'Safe decisions', deliver: 'Add capacity and transport constraints.\nCalibrate forecasts in shadow mode.', gate: 'Gate: feasible, reviewable plans' },
    { x: 8.86, period: 'DAYS 61–90', title: 'Measured value', deliver: 'Track actual decisions and outcomes.\nTest adoption, pricing and delivery cost.', gate: 'Gate: paid-deployment decision' },
  ];
  stages.forEach((v, i) => {
    box(s, v.x, 3.02, 3.83, 3.48, i === 1 ? C.paleTeal : C.white, true);
    pill(s, v.period, v.x + 0.23, 3.27, 1.74, i === 1 ? C.teal : C.light, i === 1 ? C.white : C.teal);
    text(s, v.title, v.x + 0.24, 4.00, 3.31, 0.56, 25, C.ink, true);
    text(s, v.deliver, v.x + 0.25, 4.95, 3.29, 0.73, 14.3, C.muted);
    text(s, v.gate, v.x + 0.25, 5.97, 3.27, 0.26, 12, C.teal, true);
  });
  notes(s, 'Pilot roadmap (45 seconds). These are proposed milestones, not delivery commitments or work already completed. Production needs include authenticated roles, durable audit/correction storage, scoped ERP access, observability, forecast calibration and capacity constraints. Agree metric thresholds with the partner rather than fabricate target savings. Assign accountable product, data-engineering and distributor-operations owners before work starts; no team bios or staffing claims were supplied.', 'SUPPORT_NOTE.md; eval_report.md limitations. Timeline, resourcing and gates are proposed.');
}
{
  const s = base('The investment conversation', '', '', true);
  text(s, 'Back a disciplined path\nfrom prototype to paid pilot.', 0.65, 1.39, 11.96, 1.65, 43, C.white, true, { valign: 'top' });
  text(s, 'The next milestone is commercial proof—not more demo features.', 0.70, 3.44, 11.71, 0.56, 22, C.mint, true);
  const cells = [
    ['CAPITAL FOR', 'Trusted data, a safer product\nand a measured pilot.'],
    ['INTRODUCTIONS TO', 'Design partners and operators\nwho own inventory decisions.'],
    ['TERMS TO DEFINE', 'Raise size, valuation and runway\nafter the pilot budget is agreed.'],
  ];
  cells.forEach((v, i) => {
    const x = 0.68 + i * 4.09;
    box(s, x, 4.68, 3.78, 1.70, '123349', true);
    text(s, v[0], x + 0.23, 4.92, 3.29, 0.29, 11.8, C.mint, true);
    text(s, v[1], x + 0.24, 5.51, 3.28, 0.65, 15, C.white, false, { valign: 'top' });
  });
  notes(s, 'Close (40 seconds). Ask for a follow-up pilot-scoping conversation and introductions to relevant operators. Capital is sought conceptually to reach commercial proof, but no amount, valuation, terms, use-of-funds percentages or runway are asserted. The founders must supply their names, roles, track record, contact details and approved financing terms before using this as a formal fundraising offer. The project name originated with a fictional case study. Do not imply that GulfTrade is an incorporated or operating business.', 'Proposed investor call to action. No fundraising amount, founder bios, contact details or financing terms were provided.');
}
{
  const s = base('Appendix / evidence & limitations', 'Working software. Transparent evidence.', 'Engineering evidence is not customer traction, and one synthetic backtest is not validation at scale.', false, 'Sources: eval_report.md; pytest run in the project virtual environment (49 passed, 27 October 2026).');
  box(s, 0.65, 2.93, 3.83, 3.68, C.navy, true);
  text(s, '49 / 49', 0.94, 3.14, 3.17, 0.72, 45, C.white, true);
  text(s, 'automated tests passed', 0.98, 4.00, 3.16, 0.31, 17, C.steel);
  text(s, '30 / 30', 0.94, 4.65, 3.17, 0.72, 45, C.mint, true);
  text(s, 'planted-case checks passed', 0.98, 5.52, 3.17, 0.53, 17, C.steel);
  const metrics = [
    ['30-day total WAPE', '14.48% model / 15.16% baseline', 'A small aggregate improvement on this split.'],
    ['Daily-demand WAPE', '62.37% model / 60.00% baseline', 'The model does not beat the daily baseline.'],
    ['P10–P90 coverage', '56.67% observed / 80% nominal', 'Intervals need calibration before a real pilot.'],
  ];
  metrics.forEach((v, i) => {
    const y = 2.97 + i * 1.24;
    text(s, v[0], 4.91, y, 7.47, 0.27, 12, C.teal, true);
    text(s, v[1], 4.91, y + 0.38, 7.46, 0.39, 21, C.ink, true);
    text(s, v[2], 4.93, y + 0.89, 7.35, 0.28, 14, C.muted);
  });
  notes(s, 'Diligence appendix. The software test run passed 49 tests; one third-party LangChain pending-deprecation warning was present. The 30 evaluation checks are deterministic planted cases, not independent customer outcomes. Fixed training is 60 days with a 30-day holdout. WAPE means sum of absolute errors divided by total actual demand, so lower is better. The model has slightly better 30-day aggregate WAPE but worse daily WAPE. Approximate 80-percent intervals cover only 56.67 percent of held-out totals. This makes calibration and repeated real-data evaluation an explicit pilot gate, not an optional improvement.', 'eval_report.md metrics, nominal coverage and limitations; full pytest output from prior UI verification: 49 passed, 1 warning. No live provider accuracy, customer ROI or production-readiness claims.');
}
{
  const s = base('Appendix / diligence map', 'Evidence today. Hypotheses to validate.', 'A clean boundary between a working case study and an investable operating business.');
  const rows = [
    ['PRODUCT', 'Seven tabs, source traceability, human review', 'app.py; agent/; engine/'],
    ['DATA', '20 SKUs, 3 locations, 5,000 available units; synthetic', 'data/README.md; make_data.py'],
    ['VALUE', 'Modeled before/after impact; no realised savings', 'eval_report.md; simulation.py'],
    ['COMMERCIAL', 'Pricing, customers, market size and moat unvalidated', 'Proposed strategy in this deck'],
    ['FUNDRAISING', 'Team credentials, raise size and terms not provided', 'Founders to define before raising'],
  ];
  rows.forEach((v, i) => {
    const y = 2.99 + i * 0.69;
    box(s, 0.65, y, 12.04, 0.57, i % 2 === 0 ? C.white : 'ECEFE9', true);
    text(s, v[0], 0.86, y + 0.13, 1.77, 0.27, 11, C.teal, true);
    text(s, v[1], 2.70, y + 0.12, 5.65, 0.30, 13.1, C.ink);
    text(s, v[2], 8.77, y + 0.12, 3.65, 0.30, 12, C.ink);
  });
  text(s, 'Use the final two slides for Q&A. The main pitch is slides 1–12; detailed sources are in speaker notes.', 0.72, 6.58, 11.79, 0.26, 13.5, C.teal, true);
  notes(s, 'Source appendix. All product and model assertions come from the current repository and tool-verified runtime. The canonical pack currently runs from 29 July through 26 October 2026, with forecast 27 October through 25 November. Sales contain 5,292 observed records and 108 omitted grid dates. Available inventory is net of reservations; it is not the same as on-hand. GulfTrade here is a product concept developed from a fictional distributor case. Existing market size, pilots, revenue, customer logos, team backgrounds, incorporation and fundraising terms have not been supplied and must not be invented. Rebuild the source with npm install then npm run build inside presentations. The PowerPoint is editable and includes these notes; the PDF is the shareable slide-only version.', 'Internal sources: README.md, data/README.md, app.py, make_data.py, evaluate.py, eval_report.md, engine/, agent/, tests/, SUPPORT_NOTE.md. No external market statistics are used.');
}

for (const slide of records) {
  for (const e of slide.elements) {
    if (e.x < 0.49 || e.y < 0.25 || e.x + e.w > W - 0.49 || e.y + e.h > H - 0.25) {
      throw new Error(`Text exceeds safe slide bounds: slide ${slide.slide}: ${e.text}`);
    }
  }
}
fs.mkdirSync(path.join(__dirname, '.qa'), { recursive: true });
fs.writeFileSync(path.join(__dirname, '.qa', 'layout.json'), JSON.stringify(records, null, 2));
pptx.writeFile({ fileName: path.join(__dirname, 'GulfTrade_Investor_Pitch.pptx') });
