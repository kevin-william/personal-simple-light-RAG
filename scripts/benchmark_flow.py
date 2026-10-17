"""Compare real streaming paths with the same prompt; storage must be isolated."""
import argparse
import asyncio
from copy import deepcopy
from hashlib import sha256
import io
import importlib.metadata
import json
from pathlib import Path
import platform
import statistics
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.application import Application
from src.config import load_settings
from src.metrics import Metrics,hardware_details
from src.models.llm import LLM
from src.models.downloader import digest


def fingerprint(value):
    return sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus',type=Path,required=True)
    parser.add_argument('--data-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--profile',choices=['mixed','cpu','cuda'],default='mixed')
    parser.add_argument('--runs',type=int,default=5,help='Warm runs, in addition to one cold-model run')
    parser.add_argument('--routes',nargs='+',choices=['plain','direct','rich','tui'],default=['plain','direct','rich','tui'])
    parser.add_argument('--terminal',action='store_true',help='Render Rich/Textual in the current terminal instead of headless')
    parser.add_argument('--question',default='Explique em detalhes como funcionam as consultas independentes, a busca documental e as citações de fontes neste projeto.')
    args=parser.parse_args(argv)
    if args.runs < 1 or args.routes[0]!='plain' or len(set(args.routes))!=len(args.routes):
        parser.error('Use --runs positivo e rotas distintas começando por plain.')
    settings=load_settings(args.profile,chroma_persist_dir=args.data_dir.resolve()/'chroma')
    if settings.chroma_persist_dir==load_settings().chroma_persist_dir:
        parser.error('--data-dir deve ser uma base exclusiva de benchmark.')
    report={'hardware':hardware_details(),'python':platform.python_version(),
            'settings':settings.model_dump(mode='json'),'question_sha256':fingerprint(args.question),
            'corpus_sha256':sha256(args.corpus.read_bytes()).hexdigest(),
            'terminal':args.terminal,'cold_definition':'Models cold; storage initialized; OS cache not cleared.',
            'records':[],'prompt_hashes':[],'events':{},'document_sha256':[],
            'versions':{name:importlib.metadata.version(name) for name in
                        ('torch','llama-cpp-python','sentence-transformers','chromadb','textual','rich')}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    captured=[]

    def save():
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

    def add(route,run,metrics,elapsed,prompt_hash,ui_updates=None):
        row=dict(route=route,run=run,cold_start=run==0,wall_seconds=elapsed,
                 prompt_sha256=prompt_hash,metrics=metrics)
        if ui_updates is not None:
            row['ui_updates']=ui_updates
        report['records'].append(row)
        save()

    def rag_route(route):
        app=Application(settings)
        pipeline=app.pipeline
        original=app.llm.stream
        last_prompt=[]
        def observe(messages,**kwargs):
            last_prompt[:]=deepcopy(messages)
            if not captured:
                captured.extend(deepcopy(messages))
            yield from original(messages,**kwargs)
        app.llm.stream=observe
        try:
            if route=='tui':
                from src.ui.tui import RagTuiApp
                from textual.widgets import Input
                ui=RagTuiApp(app)
                updates=[]
                started=[None]
                update=ui.update_chat_message
                def on_update(widget,text):
                    update(widget,text)
                    if started[0] is not None:
                        updates.append(time.perf_counter()-started[0])
                ui.update_chat_message=on_update
                async def run_ui():
                    async with ui.run_test(headless=not args.terminal,size=(140,50)):
                        for run in range(args.runs+1):
                            updates.clear()
                            started[0]=time.perf_counter()
                            ui.query_one('#prompt-input',Input).value=args.question
                            ui.submit_prompt()
                            while ui.is_generating:
                                if time.perf_counter()-started[0]>240:
                                    ui.action_cancel_response()
                                    raise TimeoutError('Resposta da TUI excedeu 240s.')
                                await asyncio.sleep(.01)
                            add(route,run,pipeline.last_result.metrics,time.perf_counter()-started[0],
                                fingerprint(last_prompt),list(updates))
                        ui._monitor_running=False
                        ui._monitor_stop.set()
                asyncio.run(run_ui())
            else:
                for run in range(args.runs+1):
                    started=time.perf_counter()
                    if route=='rich':
                        from rich.console import Console
                        from src.ui.chat import respond
                        output=sys.stdout if args.terminal else io.StringIO()
                        respond(app,args.question,out=Console(file=output,width=140,force_terminal=True))
                    else:
                        list(pipeline.stream(args.question))
                    add(route,run,pipeline.last_result.metrics,time.perf_counter()-started,fingerprint(last_prompt))
            report['events'][route]=list(app.lifecycle.events)
            report['offload']=app.llm.offload_effective
        finally:
            app.close()

    def direct_route():
        llm=LLM(settings)
        metrics=Metrics()
        llm.metrics=metrics
        try:
            for run in range(args.runs+1):
                started=time.perf_counter()
                metrics.start()
                metrics.llm_calls=1
                metrics.generation_started=metrics.clock()
                text=''
                for fragment in llm.stream(captured):
                    metrics.mark_token()
                    metrics.mark_model_fragment(fragment)
                    text+=fragment
                metrics.generation_finished=metrics.clock()
                item=metrics.finish(llm.tokens(text),llm.tokens(metrics.first_model_fragment))
                item['llama_native']=dict(llm.native_timings)
                add('direct',run,item,time.perf_counter()-started,fingerprint(captured))
        finally:
            llm.unload()

    try:
        corpus=json.loads(args.corpus.read_text(encoding='utf-8'))
        prep=Application(settings)
        try:
            imports=[]
            for name in corpus['documents']:
                path=(args.corpus.resolve().parent/name).resolve()
                report['document_sha256'].append(digest(path))
                imports.extend(prep.ingestor.ingest_path(path))
            if any(item['status']=='failed' for item in imports):
                raise RuntimeError('Falha na ingestão do corpus de benchmark.')
        finally:
            prep.close()
        for route in args.routes:
            if route=='direct':
                direct_route()
            else:
                rag_route(route)
            if route=='plain' and not captured:
                raise RuntimeError('A consulta não produziu um prompt documental para comparação.')
            print(f'Concluído: {route}',flush=True)
        report['prompt_hashes']=sorted({row['prompt_sha256'] for row in report['records']})
        if len(report['prompt_hashes'])!=1:
            raise RuntimeError('Prompts divergentes: comparação inválida.')
        summary={}
        for route in args.routes:
            rows=[r for r in report['records'] if r['route']==route and not r['cold_start']]
            def median(key,native=False):
                sources=[r['metrics'].get('llama_native',{}) if native else r['metrics'] for r in rows]
                values=[source[key] for source in sources if source.get(key) is not None]
                return statistics.median(values) if values else None
            summary[route]={key:median(key) for key in ['ttft_seconds','generation_seconds','total_seconds','delivery_tokens_per_second_estimate']}
            summary[route]['decode_tokens_per_second']=median('decode_tokens_per_second',native=True)
            summary[route]['warm_model_events']=sum(len(r['metrics']['model_events']) for r in rows)
            summary[route]['llm_calls']=[r['metrics']['llm_calls'] for r in rows]
        report['summary']=summary
        if 'direct' in summary:
            baseline=summary['direct']['decode_tokens_per_second']
            report['acceptance']={route:{'decode_ratio':data['decode_tokens_per_second']/baseline,
                                         'resident':data['warm_model_events']==0,
                                         'single_generation':all(c==1 for c in data['llm_calls'])}
                                  for route,data in summary.items() if route!='direct'}
        if 'plain' in summary:
            for route in ('rich','tui'):
                if route in summary:
                    summary[route]['generation_ratio_vs_plain']=summary[route]['generation_seconds']/summary['plain']['generation_seconds']
        save()
        print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    except Exception as error:
        report['error']=str(error)
        save()
        raise
    return 0


if __name__=='__main__':
    raise SystemExit(main())
