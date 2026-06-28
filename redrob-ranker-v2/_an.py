import sys
sys.path.insert(0,".")
from src.load import load_candidates
import src.features as F
REF=F.REFERENCE_DATE
RELEASE={"rag":2020,"peft":2021,"lora":2021,"qlora":2023,"llamaindex":2022,"langchain":2022,"langgraph":2023,
"qdrant":2021,"pinecone":2021,"milvus":2019,"weaviate":2019,"pgvector":2021,"chromadb":2022,"vllm":2023,
"haystack":2020,"sentence transformers":2019,"fine-tuning llms":2020,"llms":2020,"stable diffusion":2022,
"diffusion models":2020,"dspy":2023,"autogen":2023,"whisper":2022,"clip":2021,"segment anything":2023,
"gpt":2019,"bert":2018,"transformers":2018,"yolo":2016,"gans":2015,"object detection":2014}
def tech_impossible(skills, grace=0):
    for s in skills:
        d=float(s.get("duration_months") or 0)
        if d<=24: continue
        rel=RELEASE.get((s.get("name") or "").lower())
        if rel is None: continue
        implied=REF.year - round(d/12.0)
        if implied < rel - grace:
            return True
    return False
cands=load_candidates(r"../[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/candidates.jsonl")
import collections
cnt=collections.Counter()
sets=collections.defaultdict(set)
for c in cands:
    cid=c.get("candidate_id"); p=c.get("profile",{}) or {}; career=c.get("career_history") or []; skills=c.get("skills") or []
    yoe=float(p.get("years_of_experience") or 0.0)
    ez=sum(1 for s in skills if float(s.get("duration_months") or 0)==0 and F._lower(s.get("proficiency"))=="expert")
    for N in (3,4,5):
        if ez>=N: sets["ez>=%d"%N].add(cid)
    # role longer than entire career (genuinely impossible). test two buffers
    for r in career:
        dur=float(r.get("duration_months") or 0)
        if dur>yoe*12 and dur>24: sets["role>yoe"].add(cid)
        if dur>yoe*12+36 and dur>24: sets["role>yoe+36"].add(cid)
    # timeline contradictions
    for r in career:
        sd=F._parse_date(r.get("start_date")); ed=F._parse_date(r.get("end_date"))
        if sd and ed and sd>ed: sets["timeline"].add(cid)
        if sd and (sd-REF).days>60: sets["timeline"].add(cid)
    # tech-age impossible
    if tech_impossible(skills,grace=0): sets["techage_g0"].add(cid)
    if tech_impossible(skills,grace=1): sets["techage_g1"].add(cid)
print("individual rule counts:")
for k in ["ez>=3","ez>=4","ez>=5","role>yoe","role>yoe+36","timeline","techage_g0","techage_g1"]:
    print("  %-14s %d"%(k,len(sets[k])))
def union(*keys):
    u=set()
    for k in keys: u|=sets[k]
    return u
print()
print("PROPOSED A (ez>=5, role>yoe+36, timeline, techage_g0):", len(union("ez>=5","role>yoe+36","timeline","techage_g0")))
print("PROPOSED B (ez>=4, role>yoe+36, timeline, techage_g0):", len(union("ez>=4","role>yoe+36","timeline","techage_g0")))
print("PROPOSED C (ez>=3, role>yoe,    timeline, techage_g0):", len(union("ez>=3","role>yoe","timeline","techage_g0")))
print("PROPOSED D (ez>=4, role>yoe,    timeline, techage_g0):", len(union("ez>=4","role>yoe","timeline","techage_g0")))
# check the 3 false positives are NOT in proposed A
fp=["CAND_0042506","CAND_0075439","CAND_0079284"]
uA=union("ez>=5","role>yoe+36","timeline","techage_g0")
print("false-positive trio still flagged under A:", [x for x in fp if x in uA])
# 5 impossible top100 entrants
imp5=["CAND_0093547","CAND_0001610","CAND_0030348","CAND_0022812","CAND_0037000"]
print("impossible top100 still flagged under A:", [x for x in imp5 if x in uA])
