import argparse
from pathlib import Path
import sys
import traceback

from .common import ROOT, Client, read, utc
from .dataset import prepare
from .runner import Run, environment, initialize
from . import analysis


def main():
    parser=argparse.ArgumentParser(description='MergeTree study: explicit phases, no implicit data deletion')
    parser.add_argument('--protocol',default=str(ROOT/'configs/protocol.json'))
    parser.add_argument('--client-config',help='Private external ClickHouse client.xml; alternatively CH_CONFIG')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('status')
    d=sub.add_parser('dataset')
    d.add_argument('--data',default=str(ROOT/'data'))
    d.add_argument('--shards',type=int,choices=[1,3,10,30],default=30)
    d.add_argument('--reuse-dir')
    d.add_argument('--lock',help='Shared curator manifest to verify all files')
    d.add_argument('--publish-lock',help='Create a new shared manifest after verified preparation')
    for name in ['init','build','queries','ingest','summarize','fit','forecast','compare','plot','package','export-latex']:
        p=sub.add_parser(name)
        p.add_argument('--member',required=True,choices=['ha','tuan','tai'])
        p.add_argument('--machine',required=True,help='Stable anonymous machine tag, e.g. laptop1')
        p.add_argument('--run',required=True,help='New ID per protocol or failed-run replacement')
        if name=='init':
            p.add_argument('--data',default=str(ROOT/'data'))
        if name in ('build','queries'):
            p.add_argument('--experiment',required=True,choices=['keys','granularity'])
        if name in ('build','queries','ingest'):
            p.add_argument('--scale',required=True,choices=['1m','3m','10m','30m'])
    args=parser.parse_args()
    protocol=read(args.protocol)
    run=None
    try:
        if args.command=='dataset':
            prepare(args,protocol)
        elif args.command=='status':
            import json
            print(json.dumps(environment(Client(protocol['settings'],args.client_config)),indent=2))
        elif args.command=='init':
            initialize(args,protocol)
        else:
            run=Run(args)
            if args.command in ('build','queries'):
                getattr(run,args.command)(args.experiment,args.scale)
            elif args.command=='ingest':
                run.ingest(args.scale)
            else:
                function={'fit':analysis.calibrate, 'forecast':analysis.forecast,
                          'compare':analysis.compare, 'summarize':analysis.summarize,
                          'plot':analysis.plot,'package':analysis.package,
                          'export-latex':analysis.export_latex}[args.command]
                function(run)
    except Exception as exc:
        if run:
            import json
            with run.path('errors.jsonl').open('a',encoding='utf-8') as f:
                f.write(json.dumps(dict(at=utc(),phase=args.command,error=str(exc)))+'\n')
        print(f'ERROR: {exc}',file=sys.stderr)
        sys.exit(1)


if __name__=='__main__':
    main()
