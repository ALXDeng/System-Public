"""Build mockup/evidence-map.html from grid/grid_data.json + mockup/studies.json + mockup/template.html.
Run from the project root: python3 mockup/build.py
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(ROOT, "grid/grid_data.json")))
studies = json.load(open(os.path.join(ROOT, "mockup/studies.json")))

D, H, M, S = "Dose adjustment", "Substitute or hold", "Closer monitoring", "Storage and stability"

GROUPS = {
    "Heart, blood pressure and kidney": ["Diuretics", "ACE inhibitors / ARBs", "Beta blockers", "Calcium channel blockers"],
    "Mental health and neurology": ["Antipsychotics", "Lithium", "Antidepressants", "Benzodiazepines / sedatives", "Topiramate / zonisamide", "Stimulants"],
    "Diabetes": ["Insulin", "SGLT2 inhibitors", "Metformin and sulfonylureas"],
    "Pain": ["Opioids", "NSAIDs"],
    "Other": ["Anticholinergics", "Heat-labile emergency products"],
}

# DRAFT review prompts: [prompt, trigger, who, reassess/restart]. Demonstration wording; needs clinical sign-off.
SICK = "Vomiting, diarrhoea or unable to keep fluids down"
RESTART = "Restart once eating and drinking normally for 24 to 48 hours."
P = {
 "Diuretics": {
  D: ["Review the diuretic dose if the patient is drinking less or losing weight.", "Low intake, falling weight, dizziness or rising creatinine during sustained heat", "Prescriber (primary care, cardiology or nephrology)", "Return to the usual dose when intake, weight and symptoms are back to baseline. In heart failure, follow the existing fluid and weight plan."],
  H: ["Agree a sick-day plan: when to pause the diuretic and who to call.", SICK, "Prescriber sets the plan; pharmacist reinforces it", RESTART + " In heart failure, confirm with the treating team before pausing."],
  M: ["Consider checking sodium, potassium and creatinine; ask about dizziness and daily weight.", "Prolonged heat plus older age, heart failure or kidney disease", "Prescriber orders; nurse or pharmacist follows up", "Repeat after any dose change or new symptoms."]},
 "ACE inhibitors / ARBs": {
  D: ["Review the dose if blood pressure runs low through the summer.", "Symptoms of low blood pressure, or home readings below target", "Prescriber (primary care or cardiology)", "Recheck blood pressure in 2 to 4 weeks and again when the weather cools."],
  H: ["Agree a sick-day plan, and check for a diuretic or NSAID taken alongside.", SICK, "Prescriber sets the plan; pharmacist checks for the combination", RESTART],
  M: ["Consider checking creatinine and potassium; ask about dizziness on standing.", "Prolonged heat plus kidney disease, older age or a diuretic", "Prescriber orders; nurse or pharmacist follows up", "Repeat after illness or a dose change."]},
 "Beta blockers": {
  H: ["Do not stop abruptly. Reassess only where the indication is weak.", "Poor heat tolerance and no strong indication for the drug", "Prescriber (cardiology input if prescribed for heart disease)", "Any change is tapered and reviewed by the prescriber."],
  M: ["Ask about dizziness and reduced exercise tolerance in the heat.", "Outdoor work or exercise in hot weather; older age", "Primary care; pharmacist counselling", "Reassess if symptoms appear."]},
 "Calcium channel blockers": {
  D: ["Review the dose if low blood pressure causes symptoms in hot weather.", "Light-headedness, falls or low home readings", "Prescriber", "Recheck blood pressure in 2 to 4 weeks."],
  M: ["Ask about light-headedness, falls and ankle swelling.", "Older adult during prolonged heat", "Primary care; pharmacist counselling", "Reassess if symptoms appear."]},
 "Anticholinergics": {
  H: ["Review whether the medication is still needed or has a lower-risk alternative.", "Older adult, several anticholinergic medications, or past heat illness", "Prescriber; pharmacist medication review", "Reassess symptoms after any switch."],
  M: ["Counsel on reduced sweating; watch for confusion and hot, dry skin.", "A heat alert for a patient on these medications", "Pharmacist or nurse counselling; carers", "Seek urgent care for confusion or a high temperature."]},
 "Antipsychotics": {
  H: ["Do not stop abruptly. Where a choice exists, discuss agents with lower anticholinergic effect.", "Past heat illness or high anticholinergic load", "Psychiatry", "Any change is planned and monitored by the prescriber."],
  M: ["Check hydration and temperature; watch for confusion, rigidity and low blood pressure.", "A heat alert, above all with limited access to cooling", "Psychiatry and community mental health team; carers", "Seek urgent care for a high temperature with rigidity or confusion."]},
 "Lithium": {
  D: ["Base any dose review on a serum level, not on the forecast.", "Signs of dehydration or toxicity, or a raised level", "Psychiatry (nephrology if kidney function falls)", "Recheck the level after any dose change."],
  H: ["Agree a sick-day plan: when to pause lithium and get a level.", SICK, "Psychiatry sets the plan; pharmacist reinforces it", "Restart on the prescriber's advice once a level is known."],
  M: ["Consider a serum lithium level and creatinine during prolonged heat; teach the signs of toxicity.", "Prolonged heat, heavy sweating, or a new diuretic, ACE inhibitor or NSAID", "Psychiatry or primary care orders; pharmacist checks interactions", "Repeat if symptoms appear or interacting drugs change."]},
 "Antidepressants": {
  H: ["In older adults on a tricyclic, review whether an alternative suits.", "Older adult on a tricyclic with poor heat tolerance", "Prescriber (psychiatry or primary care)", "Any switch is planned; do not stop abruptly."],
  M: ["SSRIs: consider a sodium check in older adults. Tricyclics: watch for overheating.", "Older adult during prolonged heat; confusion or falls", "Primary care; pharmacist counselling", "Repeat sodium if symptoms appear."]},
 "Benzodiazepines / sedatives": {
  H: ["Review the need for long-term use. Taper; do not stop suddenly.", "Falls, confusion or daytime sedation", "Prescriber", "Follow a taper plan with review."],
  M: ["Ask about falls and fluid intake; sedation can dull thirst.", "Older adult during a heat alert", "Primary care; carers", "Reassess after any fall."]},
 "Opioids": {
  M: ["Offer naloxone and plan check-ins on hot days.", "A heat alert for a patient on long-term opioids or opioid agonist treatment", "Prescriber, pharmacist and addiction services", "Review after the heat event."],
  S: ["Fentanyl patch: counsel to keep heat sources and direct sun off the patch.", "Any patient using a transdermal fentanyl patch; fever", "Pharmacist at dispensing; prescriber", "Seek advice if drowsiness or slow breathing appears."]},
 "Insulin": {
  D: ["Review doses if low glucose readings appear in hot weather.", "Unexplained low readings during heat", "Diabetes team or primary care", "Adjust on glucose readings; review again when the weather changes."],
  M: ["Advise more frequent glucose checks in hot weather.", "A heat alert; outdoor activity; reduced appetite", "Diabetes educator, nurse or pharmacist", "Return to usual checks when readings are stable."],
  S: ["Counsel on storage: keep insulin cool and out of hot cars.", "Travel, power cuts or no reliable refrigeration", "Pharmacist", "Replace insulin exposed to high heat or that looks changed."]},
 "SGLT2 inhibitors": {
  H: ["Agree a sick-day plan: pause when dehydrated or not eating.", "Vomiting, diarrhoea, not eating or unable to keep fluids down", "Prescriber sets the plan; pharmacist reinforces it", RESTART],
  M: ["Ask about fluid intake; advise a ketone check if unwell.", "Unwell during heat, even with normal glucose", "Diabetes team or primary care", "Seek same-day review if ketones are raised."]},
 "Metformin and sulfonylureas": {
  D: ["Sulfonylureas: review the dose if eating less and low readings occur.", "Reduced appetite with low glucose readings", "Prescriber", "Review again when intake returns to normal."],
  H: ["Metformin: include in the sick-day plan when dehydrated.", SICK, "Prescriber sets the plan; pharmacist reinforces it", RESTART],
  M: ["Advise more frequent glucose checks; consider kidney function.", "Prolonged heat plus kidney disease or older age", "Primary care; pharmacist", "Repeat after illness."]},
 "NSAIDs": {
  H: ["Review NSAID use during heat, including over-the-counter use, above all with a diuretic and an ACE inhibitor or ARB.", "Dehydration risk, kidney disease, or the three-drug combination", "Pharmacist (over-the-counter sales); prescriber", "Reassess the need for pain relief and the alternatives."],
  M: ["Consider a creatinine check if NSAIDs continue through prolonged heat.", "Regular NSAID use plus older age, kidney disease or a diuretic", "Prescriber", "Repeat if NSAIDs continue."]},
 "Topiramate / zonisamide": {
  M: ["Counsel on reduced sweating, mainly in children; limit exertion in the heat.", "Child or teenager active outdoors in hot weather", "Neurology or pediatrics; parents and schools", "Seek care for a high temperature with little sweating."]},
 "Stimulants": {
  M: ["Counsel on fluids during sport in the heat; appetite and thirst may be reduced.", "Child or teenager exercising in hot weather", "Pediatrics or psychiatry; parents and coaches", "Reassess if heat symptoms occur."]},
 "Heat-labile emergency products": {
  S: ["Counsel on storage: keep out of hot cars and direct sun; check the product after heat exposure.", "Summer, travel, school or sports bags", "Pharmacist", "Replace if discoloured, past expiry or exposed to high heat."]},
}

# What each direct study does and does not show. Written from the study's own variables and population.
DIRECT_NOTE = {
 "17698677": "Antihypertensives as a group; the study does not separate drug classes. All patients already had heatstroke; the outcome is death.",
 "36418530": "Study drug: irbesartan/hydrochlorothiazide. Compares blood-pressure response by season of starting treatment. It does not measure heat illness.",
 "37897873": "Outcomes are opioid overdose and emergency visits for opioid use, not limited to prescribed opioids.",
 "15101888": "Transdermal fentanyl patch only. Heat was applied to the skin over the patch, not ambient heat. Measures drug exposure, not a clinical outcome.",
}
QUAL = {"17698677": "drug group", "36418530": "one product", "15101888": "one formulation"}

DRUGS = {
 "Diuretics": "furosemide bumetanide torsemide hydrochlorothiazide chlorthalidone indapamide spironolactone",
 "ACE inhibitors / ARBs": "lisinopril ramipril enalapril perindopril losartan valsartan irbesartan candesartan",
 "Beta blockers": "metoprolol atenolol propranolol bisoprolol carvedilol",
 "Calcium channel blockers": "amlodipine diltiazem verapamil nifedipine",
 "Anticholinergics": "oxybutynin diphenhydramine benztropine tolterodine solifenacin hydroxyzine",
 "Antipsychotics": "olanzapine clozapine haloperidol quetiapine risperidone aripiprazole",
 "Lithium": "lithium",
 "Antidepressants": "sertraline fluoxetine citalopram escitalopram paroxetine amitriptyline nortriptyline venlafaxine",
 "Benzodiazepines / sedatives": "diazepam lorazepam alprazolam clonazepam zolpidem",
 "Opioids": "morphine oxycodone fentanyl_patch methadone hydrocodone tramadol buprenorphine",
 "Insulin": "insulin insulin_glargine insulin_lispro insulin_aspart",
 "SGLT2 inhibitors": "empagliflozin dapagliflozin canagliflozin",
 "Metformin and sulfonylureas": "metformin gliclazide glyburide glipizide glimepiride",
 "NSAIDs": "ibuprofen naproxen diclofenac celecoxib",
 "Topiramate / zonisamide": "topiramate zonisamide",
 "Stimulants": "methylphenidate amphetamine lisdexamfetamine",
 "Heat-labile emergency products": "epinephrine_auto-injector salbutamol_inhaler albuterol_inhaler nitroglycerin",
}

def finding(e):
    st = studies.get(e["pmid"], {})
    res = f"{(e.get('stat') or '').strip()} {e.get('value') or ''}".strip()
    ci = e.get("ci") or ["", ""]
    if ci[0] and ci[1]:
        res += f" (CI {ci[0]} to {ci[1]})"
    if e.get("p"):
        res += f", p {e['p']}"
    return {"pmid": e["pmid"], "a": e.get("a"), "b": e.get("b"), "res": res, "trial": st.get("type") == "Experimental Trial",
            "pop": st.get("pop") or e.get("pop") or "", "doi": st.get("doi") or ""}

group_of = {c: g for g, cs in GROUPS.items() for c in cs}
order = [c for cs in GROUPS.values() for c in cs]
rows, claims = [], {}
for r in sorted(d["rows"], key=lambda r: order.index(r["class"])):
    rows.append({"cls": r["class"], "ex": r["examples"], "specs": r["specialties"], "group": group_of[r["class"]]})
    for b, c in r["cells"].items():
        if c["tier"] == "none":
            continue
        mechs = [{"name": m["mechanism"], "d": m["drug_studies"], "h": m["heat_studies"],
                  "dex": [finding(e) for e in m.get("drug_examples", [])[:3]],
                  "hex": [finding(e) for e in m.get("heat_examples", [])[:3]]} for m in c.get("mechanisms", [])]
        direct = []
        for x in c.get("direct") or []:
            st = studies.get(x["pmid"], {})
            direct.append({"pmid": x["pmid"], "a": x["a"], "b": x["b"], "res": x["summary"], "trial": st.get("type") == "Experimental Trial",
                           "pop": st.get("pop", ""), "doi": st.get("doi", ""), "note": DIRECT_NOTE.get(x["pmid"], "")})
        if c["tier"] == "direct":
            level = "direct"
        elif c["tier"] == "bridged":
            level = "indirect"
        elif c["tier"] == "partial" or any(m["d"] or m["h"] for m in mechs):
            level = "incomplete"
        else:
            level = "none"
        quals = [QUAL.get(x["pmid"]) for x in direct]
        qual = quals[0] if quals and all(quals) else ""
        p = P[r["class"]][b]
        claims[f"{r['class']}|{b}"] = {"cls": r["class"], "b": b, "level": level, "qual": qual, "q": p[0], "trig": p[1], "who": p[2], "re": p[3],
                                       "basis": c.get("note", ""), "direct": direct, "mechs": mechs}

gen = d["general"][0]
gst = studies.get(gen["pmid"], {})
out = {"buckets": d["buckets"], "rows": rows, "claims": claims, "source": d["source"], "built": d["built"],
       "general": {"pmid": gen["pmid"], "res": gen["summary"], "pop": gst.get("pop", ""), "doi": gst.get("doi", "")},
       "drugs": {k: [x.replace("_", " ") for x in v.split()] for k, v in DRUGS.items()}}
js = json.dumps(out, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
t = open(os.path.join(ROOT, "mockup/template.html")).read()
open(os.path.join(ROOT, "mockup/evidence-map.html"), "w").write(t.replace("/*DATA*/", js, 1))
from collections import Counter
print(len(claims), "claims", Counter(c["level"] for c in claims.values()), len(js), "bytes of data")
