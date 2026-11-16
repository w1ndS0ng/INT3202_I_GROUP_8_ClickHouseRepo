from collections import defaultdict
from pathlib import Path
import statistics

from .common import csv_read, csv_write, distribution, read, save, sha, utc
from .model import fit, predict


def summarize(run):
    summary=[]
    storage=[]
    for path in sorted(run.path('queries').glob('*.csv')):
        groups=defaultdict(list)
        for row in csv_read(path):
            groups[(row['experiment'],row['scale'],row['variant'],row['case'])].append(row)
        for (experiment,scale,variant,case),rows in groups.items():
            if len(rows)!=run.p['query_rounds']:
                raise RuntimeError('Incomplete query cell; do not summarize as a completed benchmark')
            explain=next(x for x in read(run.path('explain',f'{experiment}_{scale}_{variant}.json')) if x['case']==case)
            item=dict(experiment=experiment,scale=scale,variant=variant,case=case)
            for field in ['client_ms','server_ms','read_rows','read_bytes','memory_bytes']:
                for key,value in distribution([float(r[field]) for r in rows]).items():
                    item[field+'_'+key]=value
            item.update(estimated_rows=explain['estimated_rows'],selected_marks=explain['selected_marks'],
                        total_marks=explain['total_marks'],
                        pruning_ratio=None if not explain['total_marks'] else 1-explain['selected_marks']/explain['total_marks'])
            summary.append(item)
    by_key={(r['experiment'],r['scale'],r['variant'],r['case']):r for r in summary}
    for row in summary:
        base='k0' if row['experiment']=='keys' else 'g8192'
        baseline=by_key.get((row['experiment'],row['scale'],base,row['case']))
        row['speedup_client']=baseline['client_ms_median']/row['client_ms_median'] if baseline and row['client_ms_median'] else None
        row['server_resolution_note']='zero_ms_do_not_compute_server_speedup' if row['server_ms_median']==0 else ''
    if summary:
        csv_write(run.path('summary','queries.csv'),summary)
    for path in run.path('checks').glob('*_built.json'):
        data=read(path)
        parts=data['parts']
        item=dict(table=data['table'],rows=data['n'],parts=len(parts))
        for field in ['bytes_on_disk','data_compressed_bytes','data_uncompressed_bytes','marks_bytes','primary_key_bytes_in_memory']:
            item[field]=sum(int(p[field]) for p in parts)
        item['compressed_fraction']=item['data_compressed_bytes']/item['data_uncompressed_bytes'] if item['data_uncompressed_bytes'] else None
        storage.append(item)
    if storage:
        csv_write(run.path('summary','storage.csv'),storage)
        granularity_cost=[]
        for item in storage:
            label=item['table'].split('.')[-1]
            experiment,scale,variant=label.split('_')
            if experiment!='granularity':
                continue
            g=int(variant[1:])
            expected_marks=(item['rows']+g-1)//g
            granularity_cost.append(dict(scale=scale,variant=variant,rows=item['rows'],
                expected_marks=expected_marks,actual_marks=sum(int(p['marks']) for p in
                    read(run.path('checks',f'{label}_built.json'))['parts']),
                estimated_primary_key_bytes=expected_marks*6,
                primary_key_bytes_in_memory=item['primary_key_bytes_in_memory'],
                marks_bytes=item['marks_bytes'],data_compressed_bytes=item['data_compressed_bytes'],
                bytes_on_disk=item['bytes_on_disk']))
        if granularity_cost:
            csv_write(run.path('summary','granularity_cost.csv'),
                      sorted(granularity_cost,key=lambda r:int(r['variant'][1:])))
    for path in run.path('ingest').glob('*.csv'):
        complete=run.path('ingest',path.stem+'_complete.json')
        if not complete.exists():
            print(f'Not summarizing incomplete ingestion: {path.name}')
            continue
        groups=defaultdict(list)
        for row in csv_read(path):
            groups[row['batch_rows']].append(row)
        output=[]
        for batch,rows in groups.items():
            if len(rows)!=run.p['ingest_rounds']:
                raise RuntimeError('Incomplete ingestion case')
            item={'batch_rows':int(batch),'scale':path.stem}
            for metric in ['ingest_ack_s','throughput_rows_s','active_bytes_stable','parts_stable',
                           'observed_stable_wait_s','merge_row_amplification','merge_duration_sum_ms']:
                for k,v in distribution([float(r[metric]) for r in rows]).items():
                    item[f'{metric}_{k}']=v
            output.append(item)
        csv_write(run.path('summary','ingest_'+path.stem+'.csv'),output)
    return summary


def calibrate(run):
    target=run.path('model','model.json')
    if target.exists() or run.path('queries','keys_30m_journal.jsonl').exists():
        raise RuntimeError('Fit must occur once, before any 30M measurements')
    rows=summarize(run)
    models=[]
    for variant,_,_ in run.variants('keys'):
        for case in ['w0','w1','w2','w3','w4']:
            points=[]
            for scale in ['1m','3m','10m']:
                match=[r for r in rows if (r['experiment'],r['scale'],r['variant'],r['case'])==('keys',scale,variant,case)]
                if len(match)!=1:
                    raise RuntimeError(f'Complete 1M/3M/10M keys query matrix before fitting: {variant}/{case}/{scale}')
                points.append(match[0])
            m=fit([r['estimated_rows'] for r in points],[r['client_ms_median'] for r in points])
            m.update(variant=variant,case=case,points=[dict(scale=r['scale'],rows=r['estimated_rows'],
                         client_ms=r['client_ms_median'],iqr_ms=r['client_ms_iqr']) for r in points])
            models.append(m)
    save(target,dict(frozen_at=utc(),protocol_hash=run.c['protocol_hash'],
         measurement='client_elapsed_ms',formula='T_hat_ms = alpha_ms + beta_ms_per_row * estimated_rows',
         constraint='alpha>=0,beta>=0; boundary solutions allowed',models=models,
         calibration_csv_sha256={s:sha(run.path('queries','keys_'+s+'.csv')) for s in ['1m','3m','10m']}))
    print('Model frozen before holdout measurement. Boundary/weak fits must be discussed.')


def forecast(run):
    path=run.path('model','forecast.json')
    if path.exists() or run.path('queries','keys_30m_journal.jsonl').exists():
        raise RuntimeError('Forecast must be frozen once before 30M measurement')
    model_path=run.path('model','model.json')
    model=read(model_path)
    if model['protocol_hash']!=run.c['protocol_hash']:
        raise RuntimeError('Protocol changed after fitting')
    for scale,digest in model['calibration_csv_sha256'].items():
        if sha(run.path('queries','keys_'+scale+'.csv'))!=digest:
            raise RuntimeError('Calibration observations changed')
    rows=[]
    explain_hashes={}
    for variant,_,_ in run.variants('keys'):
        ep=run.path('explain',f'keys_30m_{variant}.json')
        estimates=read(ep)
        explain_hashes[variant]=sha(ep)
        for estimate in estimates:
            m=next(x for x in model['models'] if x['variant']==variant and x['case']==estimate['case'])
            point=m['points'][-1]
            naive=point['client_ms']*estimate['estimated_rows']/point['rows'] if point['rows'] else None
            rows.append(dict(variant=variant,case=estimate['case'],estimated_rows=estimate['estimated_rows'],
                             predicted_client_ms=predict(m,estimate['estimated_rows']),naive_client_ms=naive,
                             identifiable=m['identifiable'],boundary_fit=m.get('boundary_fit'),
                             is_extrapolation=estimate['estimated_rows']>m.get('x_max',0)))
    save(path,dict(frozen_at=utc(),protocol_hash=run.c['protocol_hash'],model_sha256=sha(model_path),
                  explain_sha256=explain_hashes,predictions=rows))
    print('30M forecasts frozen; now run queries --experiment keys --scale 30m.')


def compare(run):
    forecast_path=run.path('model','forecast.json')
    forecast=read(forecast_path)
    if sha(run.path('model','model.json'))!=forecast['model_sha256']:
        raise RuntimeError('Frozen model was edited')
    for variant,digest in forecast['explain_sha256'].items():
        if sha(run.path('explain',f'keys_30m_{variant}.json'))!=digest:
            raise RuntimeError('Target EXPLAIN changed after forecast')
    measured=summarize(run)
    rows=[]
    for prediction in forecast['predictions']:
        match=[r for r in measured if (r['experiment'],r['scale'],r['variant'],r['case'])==
               ('keys','30m',prediction['variant'],prediction['case'])]
        if len(match)!=1:
            raise RuntimeError('Complete 30M query matrix before comparison')
        actual=match[0]
        est=prediction['predicted_client_ms']
        value=actual['client_ms_median']
        row=dict(**prediction,actual_client_ms=value,actual_client_q1=actual['client_ms_q1'],
                 actual_client_q3=actual['client_ms_q3'],actual_server_ms=actual['server_ms_median'],
                 actual_read_rows=actual['read_rows_median'],
                 absolute_error_ms=None if est is None else abs(est-value),
                 absolute_percentage_error=None if est is None or value==0 else abs(est-value)/value*100,
                 signed_error_ms=None if est is None else est-value,
                 naive_absolute_error_ms=None if prediction['naive_client_ms'] is None else abs(prediction['naive_client_ms']-value))
        rows.append(row)
    csv_write(run.path('summary','estimated_vs_actual.csv'),rows)
    valid=[r for r in rows if r['absolute_error_ms'] is not None]
    save(run.path('summary','model_accuracy.json'),dict(cases=len(valid),
         mae_ms=statistics.mean(r['absolute_error_ms'] for r in valid) if valid else None,
         median_ape=statistics.median(r['absolute_percentage_error'] for r in valid) if valid else None,
         forecast_sha256=sha(forecast_path)))


def plot(run):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.lines import Line2D
    # Use the user's installed Windows font under WSL; font files are never
    # copied into this repository or redistributed with experiment outputs.
    windows_fonts=Path('/mnt/c/Windows/Fonts')
    if windows_fonts.exists():
        for path in windows_fonts.glob('times*.ttf'):
            font_manager.fontManager.addfont(str(path))
    try:
        font_manager.findfont('Times New Roman',fallback_to_default=False)
    except ValueError as exc:
        raise RuntimeError('Times New Roman is required for report figures; install it on this machine before plotting') from exc
    plt.rcParams.update({'font.family':'Times New Roman','font.size':13,
                         'axes.titlesize':13,'axes.labelsize':13,'legend.fontsize':13,
                         'xtick.labelsize':13,'ytick.labelsize':13,'svg.fonttype':'none'})
    folder=run.path('figures')
    folder.mkdir(parents=True,exist_ok=True)
    save(folder/'plot_environment.json',dict(matplotlib=matplotlib.__version__,font='Times New Roman',font_size=13))
    def export(fig,name,rect=None):
        fig.tight_layout(rect=rect)
        for suffix in ['png','svg']:
            fig.savefig(folder/(name+'.'+suffix),dpi=180,bbox_inches='tight')
        plt.close(fig)
    qpath=run.path('summary','queries.csv')
    if qpath.exists():
        rows=csv_read(qpath)
        for exp,scale in sorted({(r['experiment'],r['scale']) for r in rows}):
            fig,axes=plt.subplots(1,3,figsize=(13,4))
            selected=[r for r in rows if r['experiment']==exp and r['scale']==scale]
            for variant in sorted({r['variant'] for r in selected}):
                group=sorted((r for r in selected if r['variant']==variant),key=lambda r:r['case'])
                x=[r['case'] for r in group]
                med=[float(r['client_ms_median']) for r in group]
                axes[0].errorbar(x,med,yerr=[[v-float(r['client_ms_q1']) for r,v in zip(group,med)],
                    [float(r['client_ms_q3'])-v for r,v in zip(group,med)]],marker='o',capsize=3,label=variant)
                axes[1].plot(x,[float(r['read_rows_median']) for r in group],marker='o',label=variant)
                axes[2].plot(x,[float(r['pruning_ratio']) for r in group],marker='o',label=variant)
            for ax,title in zip(axes,['Client time (ms), median / IQR','Rows read, median','Pruned marks / total marks']):
                ax.set_title(title)
                ax.legend()
                ax.grid(alpha=.2)
            fig.suptitle(f'{exp} / {scale} / {run.c["member"]} / {run.c["machine"]}')
            export(fig,f'{exp}_{scale}')
    sp=run.path('summary','storage.csv')
    if sp.exists():
        groups=defaultdict(list)
        for row in csv_read(sp):
            label=row['table'].split('.')[-1]
            experiment,scale,variant=label.split('_')
            groups[(experiment,scale)].append(dict(**row,variant=variant))
        for (experiment,scale),group in groups.items():
            group=sorted(group,key=lambda r:int(r['variant'][1:]))
            fig,axes=plt.subplots(1,3,figsize=(13,4))
            for ax,metric,label,factor in zip(axes,
                ['primary_key_bytes_in_memory','marks_bytes','bytes_on_disk'],
                ['Primary key in memory (KiB)','Column marks (KiB)','Active table storage (MiB)'],[1024,1024,2**20]):
                ax.bar([r['variant'] for r in group],[float(r[metric])/factor for r in group])
                ax.set(title=label)
            export(fig,f'{experiment}_{scale}_storage')
    cost_path=run.path('summary','granularity_cost.csv')
    if cost_path.exists() and qpath.exists():
        costs=[r for r in csv_read(cost_path) if r['scale']=='30m']
        query_rows=[r for r in csv_read(qpath) if r['experiment']=='granularity' and r['scale']=='30m']
        if costs and query_rows:
            # Match the report's usable A4 width so 13 pt labels remain legible
            # when the image is inserted without shrinking its typography.
            fig,grid_axes=plt.subplots(2,2,figsize=(6.5,5.8))
            axes=list(grid_axes.flat)
            variants=[r['variant'] for r in costs]
            x=list(range(len(variants)))
            case_styles=[('w1','o','-'),('w2','s','--'),('w3','^',':')]
            for case,marker,linestyle in case_styles:
                group=[next(r for r in query_rows if r['variant']==variant and r['case']==case)
                       for variant in variants]
                med=[float(r['client_ms_median']) for r in group]
                # Dodge the three series within each discrete configuration so
                # overlapping quartile intervals remain individually visible.
                offset={'w1':-.10,'w2':0,'w3':.10}[case]
                positions=[position+offset for position in x]
                axes[0].errorbar(positions,med,
                    yerr=[[v-float(r['client_ms_q1']) for r,v in zip(group,med)],
                          [float(r['client_ms_q3'])-v for r,v in zip(group,med)]],
                    marker=marker,markerfacecolor='white',linestyle=linestyle,
                    color='black',capsize=3,label=case.upper())
                pruning=[100*float(r['pruning_ratio']) for r in group]
                target=axes[2] if case=='w2' else axes[1]
                target.plot(x,pruning,marker=marker,markerfacecolor='white',
                            linestyle=linestyle,color='black',label=case.upper())
                if case=='w2':
                    for position,value in zip(x,pruning):
                        target.annotate(f'{value:.1f}'.replace('.',','),(position,value),
                                        xytext=(0,8),textcoords='offset points',ha='center')
            axes[0].set(title='(a) Latency (ms, log)',yscale='log',yticks=[3,10,40])
            axes[0].set_yticklabels(['3','10','40'])
            axes[0].minorticks_off()
            # ErrorbarContainer's default legend adds stems/caps around the
            # marker. Show clean line/marker keys; retain intervals in the plot.
            legend_keys=[Line2D([],[],color='black',marker=marker,
                markerfacecolor='white',linestyle=linestyle,label=case.upper())
                for case,marker,linestyle in case_styles]
            axes[0].legend(handles=legend_keys,loc='center left',frameon=False,
                           numpoints=1,handlelength=2.2,handletextpad=.7)
            axes[1].set(title='(b) Pruning W1/W3 (%)',ylim=(99.6,100.02),yticks=[99.6,99.8,100])
            axes[1].set_yticklabels(['99,6','99,8','100,0'])
            axes[1].legend(loc='lower left',frameon=False)
            axes[2].set(title='(c) Pruning W2 (%)',ylim=(0,100),yticks=[0,50,100])
            axes[3].bar([v-.18 for v in x],
                [float(r['primary_key_bytes_in_memory'])/1024 for r in costs],
                width=.36,color='white',edgecolor='black',hatch='///',label='PK (RAM)')
            axes[3].bar([v+.18 for v in x],
                [float(r['marks_bytes'])/1024 for r in costs],
                width=.36,color='white',edgecolor='black',hatch='...',label='Marks (đĩa)')
            axes[3].set(title='(d) Dung lượng (KiB)',yticks=[0,125,250])
            axes[3].legend(loc='upper right')
            for ax in axes:
                ax.set_xticks(x,[v[1:] for v in variants])
                ax.set_xlim(-.5,len(variants)-.5)
                ax.grid(axis='y',alpha=.2)
                ax.set_xlabel('g (cấu hình)')
            export(fig,'e2_granularity_tradeoff_v3')
    ep=run.path('summary','estimated_vs_actual.csv')
    if ep.exists():
        rows=[r for r in csv_read(ep) if r['predicted_client_ms']]
        if rows:
            fig,ax=plt.subplots(figsize=(8,6))
            predicted=[float(r['predicted_client_ms']) for r in rows]
            actual=[float(r['actual_client_ms']) for r in rows]
            ax.scatter(predicted,actual)
            hi=max(predicted+actual)*1.1
            ax.plot([0,hi],[0,hi],'--',color='gray',label='Perfect prediction')
            for r,x,y in zip(rows,predicted,actual):
                ax.annotate(r['variant']+'/'+r['case'],(x,y),fontsize=13)
            ax.set(xlabel='Estimated client time (ms)',ylabel='Actual median client time (ms)')
            ax.legend()
            export(fig,'estimated_vs_actual')
    for path in run.path('summary').glob('ingest_*.csv'):
        rows=sorted(csv_read(path),key=lambda r:int(r['batch_rows']))
        fig,axes=plt.subplots(1,3,figsize=(13,4))
        for ax,metric,label,factor in zip(axes,['throughput_rows_s','active_bytes_stable','merge_row_amplification'],
               ['Ingestion throughput (rows/s)','Active storage (MiB)','Merge rows read / input rows'],[1,2**20,1]):
            med=[float(r[metric+'_median'])/factor for r in rows]
            err=[[v-float(r[metric+'_q1'])/factor for r,v in zip(rows,med)],
                 [float(r[metric+'_q3'])/factor-v for r,v in zip(rows,med)]]
            ax.bar([r['batch_rows'] for r in rows],med,yerr=err,capsize=4)
            ax.set(xlabel='Rows / batch',title=label)
        export(fig,path.stem)
    for path in run.path('ingest').glob('*_timeline.json'):
        rows=[r for r in read(path) if 'parts' in r]
        if rows:
            fig,ax=plt.subplots(figsize=(7,4))
            ax.plot([float(r['elapsed_s']) for r in rows],[int(r['parts']) for r in rows],marker='.')
            ax.set(xlabel='Observed elapsed time (s)',ylabel='Active parts',title=path.stem)
            export(fig,path.stem)


def package(run):
    """Only reproducibility outputs, never credentials or input payloads."""
    import shutil
    destination=run.path('share')
    if destination.exists():
        raise RuntimeError('Share package already exists; do not overwrite an archived run')
    destination.mkdir()
    for name in ['config.json','input_manifest.json','environment.json','effective_settings.json']:
        value=read(run.out/name)
        if name=='config.json':
            value['data_dir']='<local input directory>'
        if name=='environment.json':
            for disk in value['disks']:
                disk['path']='<local ClickHouse disk>'
        save(destination/name,value)
    for name in ['errors.jsonl','reproducibility.json']:
        source=run.out/name
        if source.exists():
            shutil.copy2(source,destination/name)
    for name in ['ddl','sql','explain','checks','queries','ingest','model','summary','figures','setup']:
        source=run.out/name
        if source.exists():
            shutil.copytree(source,destination/name)
    archive=shutil.make_archive(str(run.out/'share_results'),'zip',destination)
    print(f'Share {archive}; results stay isolated by member/machine/run.')
