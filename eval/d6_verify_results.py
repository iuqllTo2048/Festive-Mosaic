"""Validate preserved D6 evidence, budgets, source integrity and git exclusions. No model calls."""
import hashlib
import json
import subprocess
from collections import Counter
import httpx
from d6_diagnose import ROOT, OUT, RESULTS, BASE, corpus, norm, save, record
from scripts.evaluate_d5 import verify


def main():
    settings, store, docs, chunks, readers = corpus()
    cases=json.loads((OUT/'d6_cases.json').read_text(encoding='utf-8'))
    rows=[json.loads(line) for line in RESULTS.read_text(encoding='utf-8').splitlines()]
    expected={'fact_numeric':3,'multi_condition':2,'cross_paper':2,'chinese_paraphrase':2,'unanswerable':2,'negation_comparison_trap':1}
    assert dict(Counter(c['category'] for c in cases))==expected
    page_cache={}
    refs=0
    for case in cases:
        assert not case['human_verified'] and case['label_status']=='provisional'
        for ref in case['references']:
            key=(ref['paper_id'],ref['page'])
            if key not in page_cache:
                page_cache[key]=norm(readers[key[0]].pages[key[1]-1].extract_text() or '')
            assert norm(ref['quote']) in page_cache[key]
            assert norm(ref['quote']) in norm(store.get_chunk(ref['chunk_id']).text)
            assert not ref['human_verified'] and ref['semantic_label']=='provisional'
            refs+=1
    a=[r for r in rows if r['test']=='A']; b=[r for r in rows if r['test']=='B']; c=[r for r in rows if r['test']=='C']
    assert len(a)==12 and len({r['id'] for r in a})==12
    assert len(b)==9 and len({r['id'] for r in b})==9
    assert len(c)<=6 and sum(r['actual_requests'] for r in c)<=24
    assert sum(r['total_tokens'] or 0 for r in c)<=50000
    for row in c:
        assert row['actual_requests']==len(row['sdk_calls'])==row['raw_result']['stats']['llm_requests']
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=20) as client:
        for row in c:
            verify(client,row['raw_result'],row['repair'])
    diff=subprocess.run(['git','diff','--exit-code',BASE,'--','backend/app','frontend/src'],cwd=ROOT,capture_output=True,text=True)
    assert diff.returncode==0,'Production source changed'
    exclusions={}
    for path in ('backend/.env','backend/data/evidence.sqlite3',f'backend/data/pdfs/{docs["kg2rag"].sha256}.pdf'):
        checked=subprocess.run(['git','check-ignore','-v',path],cwd=ROOT,capture_output=True,text=True)
        assert checked.returncode==0
        exclusions[path]=checked.stdout.strip()
    tracked=subprocess.run(['git','ls-files','--','*.pdf','*.sqlite3','*.db','.env','backend/.env'],cwd=ROOT,capture_output=True,text=True)
    assert tracked.returncode==0 and not tracked.stdout.strip()
    if not any(r['test']=='E' for r in rows):
        regression=json.loads((OUT/'d6_regression.json').read_text(encoding='utf-8'))
        record('E','regression',**{k:v for k,v in regression.items() if k!='test'},recorded_from_prior_exec=True)
    output={'reference_location_checks':refs,'independent_human_verified':0,'case_categories':expected,
        'online_runs':len(c),'actual_online_requests':sum(r['actual_requests'] for r in c),
        'source_integrity_checked_online_runs':len(c),'production_source_unchanged':True,
        'git_exclusions':exclusions,'tracked_private_data_files':[],
        'results_sha256':hashlib.sha256(RESULTS.read_text(encoding='utf-8').encode('utf-8')).hexdigest(),
        'results_sha256_normalization':'UTF-8 text with CRLF normalized to LF',
        'meaning':'Completed source/budget/git checks; not semantic gold or scientific accuracy'}
    save(OUT/'d6_integrity.json',output)
    print(json.dumps(output,ensure_ascii=False))


if __name__=='__main__':
    main()
