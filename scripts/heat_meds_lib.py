"""Shared matching rules for heat terms and medication classes."""
import collections
import re

I = re.IGNORECASE
# Direct heat exposure / heat illness terms
HEAT_DIRECT = re.compile(
    r"heat[\s-]?waves?|heat[\s-]?stroke|heat[\s-]?(related|illness|stress|strain|exhaustion|exposure|injur|disorder|index|"
    r"toleran|intoleran|acclimat|event|day|season|warning|alert|vulnerab|mortality|death|morbidity)|extreme heat|"
    r"\bhot (weather|day|climate|temperature|environment|season|condition|spell|night|ambient|summer|humid)|"
    r"(ambient|air|outdoor|high|higher|extreme|daily|mean|maximum|apparent|environmental|wet[\s-]?bulb)[\w\s-]{0,20}temperature|"
    r"temperature (increase|rise|above|exposure|variab)|\bsummer|heat exposure|exertional heat|\bin the heat\b|"
    r"passive heat|heat load|thermal stress|hyperthermi|global warming|climate change|urban heat",
    I,
)
HEAT_EXCLUDE = re.compile(
    r"heat[\s-]?shock|heat pain|heated tobacco|heat[\s-]?map|wheat|heat therapy|heat treat|heat[\s-]?inactivat|"
    r"malignant hyperthermia|hyperthermic|hyperthermia (therapy|treatment)|hipec|heat capacity|"
    r"heat[\s-]?not[\s-]?burn|heat sensitiv|heat applic|heat wrap|heat pack|moist heat|heating|heat pad",
    I,
)
# Physiological proxies for heat vulnerability
HEAT_PROXY = re.compile(
    r"dehydrat|hypohydrat|\bsweat|thermoregulat|(core|body|rectal|skin|tympanic|oesophageal|esophageal)[\s-]?temperature|"
    r"hyponatr|volume depletion|hypovol",
    I,
)

DRUGS = collections.OrderedDict(
    [
        ("Diuretics", r"diuretic|furosemide|frusemide|thiazide|spironolactone|bumetanide|torsemide|torasemide|chlort?halidone|indapamide|amiloride"),
        ("Beta blockers", r"beta[\s-]?(adrenergic )?(receptor )?block|β[\s-]?block|metoprolol|atenolol|propranolol|bisoprolol|carvedilol|nebivolol"),
        ("ACE inhibitors / ARBs", r"ace[\s-]?inhibitor|angiotensin[\s-]converting enzyme inhib|angiotensin (ii )?receptor (block|antag)|\barbs?\b|\bacei\b|lisinopril|enalapril|ramipril|perindopril|captopril|losartan|valsartan|candesartan|telmisartan|irbesartan|renin[\s-]angiotensin[\w\s-]*(inhib|block)|raas inhib|ras inhib"),
        ("Calcium channel blockers", r"calcium[\s-]channel block|calcium antagonist|amlodipine|nifedipine|diltiazem|verapamil"),
        ("Antihypertensives (unspecified)", r"antihypertensive|anti-hypertensive|blood pressure (medication|lowering drug|drug)|cardiovascular (medication|drug)"),
        ("Anticholinergics", r"anticholinergic|antimuscarinic|oxybutynin|atropine|scopolamine|hyoscine|tolterodine|solifenacin|benz?tropine|trihexyphenidyl|glycopyrr"),
        ("Antipsychotics", r"antipsychotic|neuroleptic|haloperidol|olanzapine|clozapine|risperidone|quetiapine|aripiprazole|chlorpromazine|phenothiazine"),
        ("Antidepressants", r"antidepressant|\bssris?\b|\bsnris?\b|serotonin reuptake|tricyclic|sertraline|fluoxetine|paroxetine|citalopram|venlafaxine|duloxetine|amitriptyline|mirtazapine|bupropion"),
        ("Lithium", r"\blithium"),
        ("Psychotropics (unspecified)", r"psychotropic|psychiatric (medication|drug)|psychoactive (medication|drug)"),
        ("Insulin (as therapy)", r"insulin"),
        ("SGLT2 inhibitors", r"sglt[\s-]?2|gliflozin|sodium[\s-]glucose co"),
        ("Other diabetes drugs", r"metformin|sulfonylurea|glipizide|gliclazide|glimepiride|glp[\s-]?1|antidiabetic|hypoglycemic agent|diabetes medication"),
        ("Stimulants", r"stimulant|methylphenidate|amphetamine|mdma|ecstasy|cocaine|ephedrine|pseudoephedrine"),
        ("Antihistamines", r"antihistamine|diphenhydramine|promethazine|cetirizine|loratadine|chlorphen"),
        ("Opioids / sedatives", r"opioid|benzodiazepine|sedative|hypnotic|morphine|fentanyl|oxycodone|tramadol|diazepam|lorazepam|zolpidem"),
        ("NSAIDs / analgesics", r"\bnsaids?\b|non-?steroidal anti|ibuprofen|naproxen|diclofenac|aspirin|acetaminophen|paracetamol"),
        ("Anticonvulsants", r"anticonvulsant|antiepileptic|anti-epileptic|topiramate|zonisamide|carbamazepine|oxcarbazepine|valproate|valproic"),
        ("Antiparkinson / dementia drugs", r"levodopa|dopamine agonist|antiparkinson|cholinesterase inhib|donepezil|rivastigmine|memantine"),
        ("Statins", r"\bstatins?\b|atorvastatin|simvastatin|rosuvastatin|pravastatin"),
        ("Anticoagulants / antiplatelets", r"anticoagulant|warfarin|antiplatelet|clopidogrel|\bdoacs?\b|apixaban|rivaroxaban"),
        ("Inhalers / epinephrine", r"inhaler|salbutamol|albuterol|epinephrine|adrenaline|bronchodilator|\bepipen"),
        ("Laxatives / PPIs / other", r"laxative|proton pump|\bppis?\b|thyroxine|levothyroxine|alcohol"),
        ("Medication use (generic)", r"polypharmacy|\bmedications?\b|\bdrugs?\b|prescri|pharmac"),
    ]
)
DRUG_RE = collections.OrderedDict((k, re.compile(v, I)) for k, v in DRUGS.items())
INSULIN_BIOMARKER = re.compile(
    r"insulin[\s-]?(resist|sensitiv|like|level|concentrat|secret|respon|receptor|signal|growth|index|auc|clearance|action)|"
    r"(fasting|serum|plasma|circulating|basal|postprandial|hyper|hypo|pro|endogenous|blood)[\s-]?insulin|homa|igf|"
    r"non[\s-]?insulin|insulinemi|insulin[\s-]?depend",
    I,
)
STORAGE = re.compile(r"storage|stored|stabilit|shelf|degrad|potency|refriger|room temperature|freez|cold chain", I)


def heat_tier(name):
    if HEAT_DIRECT.search(name) and not HEAT_EXCLUDE.search(name):
        return "direct"
    if HEAT_PROXY.search(name):
        return "proxy"
    return None


def drug_classes(name):
    hits = []
    for k, rx in DRUG_RE.items():
        if rx.search(name):
            if k == "Insulin (as therapy)" and INSULIN_BIOMARKER.search(name):
                continue
            hits.append(k)
    # only keep the generic bucket if nothing specific matched
    if len(hits) > 1 and "Medication use (generic)" in hits:
        hits.remove("Medication use (generic)")
    return hits
