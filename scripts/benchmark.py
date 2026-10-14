"""Opt-in local benchmark. Never labels synthetic/mocked results as model validation."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
from hashlib import sha256
import json
import platform
import importlib.metadata
from src.config import load_settings
from src.application import Application


def record(question,answer,expected=(),include_text=False):
    item = {'question_sha256':sha256(question.encode()).hexdigest(),
            'answer_sha256':sha256(answer.text.encode()).hexdigest(),
            'metrics':answer.metrics,'mode':answer.mode,
            'citations':len(answer.cited),'warnings':list(answer.warnings),
            'expected_phrases_present':all(p.lower() in answer.text.lower() for p in expected) if expected else None,
            'grounding_review':'pending human review'}
    if include_text:
        item.update(question=question,answer=answer.text,
                    sources=[{'path':h.metadata.get('source'),'text':h.text} for h in answer.cited])
    return item


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus',type=Path,required=True,help='JSON: documents, questions; paths relativos ao manifesto')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--profile',choices=['cuda','cpu'],default='cuda')
    parser.add_argument('--mode',choices=['resident','alternating'],default='resident')
    parser.add_argument('--runs',type=int,default=2)
    parser.add_argument('--data-dir',type=Path,required=True,help='Base exclusiva do benchmark')
    parser.add_argument('--include-text',action='store_true',help='Inclui perguntas, respostas e evidências nos logs locais')
    args = parser.parse_args(argv)
    if args.runs < 1:
        parser.error('--runs deve ser positivo')
    manifest = json.loads(args.corpus.read_text(encoding='utf-8'))
    s = load_settings(args.profile,memory_mode=args.mode,chroma_persist_dir=args.data_dir.resolve()/'chroma')
    app = Application(s)
    report = {'hardware':platform.platform(),'python':platform.python_version(),
              'settings':s.model_dump(mode='json'),'corpus_sha256':sha256(args.corpus.read_bytes()).hexdigest(),
              'versions':{},'quality_review':'pending','records':[]}
    for package in ('torch','llama-cpp-python','sentence-transformers','chromadb'):
        try:
            report['versions'][package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            report['versions'][package] = None
    try:
        app.metrics.start()
        imports = []
        for name in manifest['documents']:
            path = (args.corpus.resolve().parent/name).resolve()
            imports.extend(app.ingestor.ingest_path(path))
        report['indexing'] = app.metrics.finish()
        report['import_statuses'] = [r['status'] for r in imports]
        if any(r['status']=='failed' for r in imports):
            raise RuntimeError('Ingestão do corpus falhou; benchmark inválido.')
        for run in range(args.runs):
            app.pipeline.memory.clear()
            for number,query in enumerate(manifest['questions']):
                list(app.pipeline.stream(query['question']))
                item = record(query['question'],app.pipeline.last_result,query.get('expected_substrings',()),args.include_text)
                item.update(run=run+1,question_index=number,cold_start=run==0 and number==0)
                report['records'].append(item)
        report['offload_observed'] = app.llm.offload_effective
    except Exception as error:
        report['error'] = str(error)
    finally:
        app.close()
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return 1 if 'error' in report else 0


if __name__ == '__main__':
    raise SystemExit(main())
