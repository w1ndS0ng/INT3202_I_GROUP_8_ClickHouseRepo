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
    from matplotlib.collections import LineCollection
    from matplotlib.container import ErrorbarContainer
    from matplotlib.lines import Line2D
    from matplotlib.patches import FancyBboxPatch, Patch
    # Use the user's installed Windows font under WSL or Windows; font files are never
    # copied into this repository or redistributed with experiment outputs.
    for font_dir in [Path('/mnt/c/Windows/Fonts'), Path('C:/Windows/Fonts')]:
        if font_dir.exists():
            for path in font_dir.glob('times*.ttf'):
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
            # Match usable A4 text width (6.5 in = 468 pt) at 450 DPI with broken y-axis in (a) and shared legend.
            fig=plt.figure(figsize=(6.5,6.55))
            gs=fig.add_gridspec(3,2,height_ratios=[0.42,1.08,1.0],hspace=0.44,wspace=0.28,
                                left=0.095,right=0.98,top=0.975,bottom=0.085)
            leg_ax=fig.add_subplot(gs[0,:])
            leg_ax.axis('off')
            top_ratio,bot_ratio=0.85,1.15
            gs_a=gs[1,0].subgridspec(2,1,height_ratios=[top_ratio,bot_ratio],hspace=0.15)
            ax_a_top=fig.add_subplot(gs_a[0])
            ax_a_bot=fig.add_subplot(gs_a[1],sharex=ax_a_top)
            ax_b=fig.add_subplot(gs[1,1])
            ax_c=fig.add_subplot(gs[2,0])
            ax_d=fig.add_subplot(gs[2,1])
            variants=[r['variant'] for r in costs]
            x=list(range(len(variants)))
            styles={
                'w1':{'marker':'o','ls':'-','color':'#1B4F72','ms':5.0,'label':'W1'},
                'w2':{'marker':'s','ls':'--','color':'#A93226','ms':5.0,'label':'W2'},
                'w3':{'marker':'^','ls':':','color':'#117864','ms':5.2,'label':'W3'},
            }
            q_gray='#64748B'
            halo=dict(boxstyle='round,pad=0.08',facecolor='white',edgecolor='none',alpha=0.88)
            st_w2=styles['w2']
            g_w2=[next(r for r in query_rows if r['variant']==v and r['case']=='w2') for v in variants]
            med_w2=[float(r['client_ms_median']) for r in g_w2]
            err_w2=[[m-float(r['client_ms_q1']) for r,m in zip(g_w2,med_w2)],
                    [float(r['client_ms_q3'])-m for r,m in zip(g_w2,med_w2)]]
            ax_a_top.plot(x,med_w2,linestyle=st_w2['ls'],linewidth=1.25,color=st_w2['color'],alpha=0.85,zorder=2)
            ax_a_top.errorbar(x,med_w2,yerr=err_w2,fmt='none',ecolor=q_gray,
                              elinewidth=1.5,capsize=4.0,capthick=1.35,zorder=3.5)
            ax_a_top.plot(x,med_w2,linestyle='none',marker=st_w2['marker'],markersize=st_w2['ms'],
                          markerfacecolor='white',markeredgecolor=st_w2['color'],markeredgewidth=1.55,zorder=4)
            ax_a_top.set(ylim=(29.0,44.0),yticks=[30,36,42])
            ax_a_top.set_yticklabels(['30','36','42'])
            ax_a_top.spines['bottom'].set_visible(False)
            ax_a_top.tick_params(axis='x',which='both',bottom=False,top=False,labelbottom=False)
            ax_a_top.set_title('(a) Độ trễ client_ms W1–W3 (ms)',pad=8,fontweight='bold')
            offsets={'w1':-0.13,'w3':0.13}
            for case in ['w1','w3']:
                st=styles[case]
                group=[next(r for r in query_rows if r['variant']==variant and r['case']==case)
                       for variant in variants]
                med=[float(r['client_ms_median']) for r in group]
                err=[[m-float(r['client_ms_q1']) for r,m in zip(group,med)],
                     [float(r['client_ms_q3'])-m for r,m in zip(group,med)]]
                pos=[position+offsets[case] for position in x]
                ax_a_bot.plot(pos,med,linestyle=st['ls'],linewidth=1.25,color=st['color'],alpha=0.85,zorder=2)
                ax_a_bot.errorbar(pos,med,yerr=err,fmt='none',ecolor=q_gray,
                                  elinewidth=1.5,capsize=4.0,capthick=1.35,zorder=3.5)
                ax_a_bot.plot(pos,med,linestyle='none',marker=st['marker'],markersize=st['ms'],
                              markerfacecolor='white',markeredgecolor=st['color'],markeredgewidth=1.55,zorder=4)
            ax_a_bot.set(ylim=(2.50,4.85),yticks=[2.8,3.6,4.4])
            ax_a_bot.set_yticklabels(['2,8','3,6','4,4'])
            ax_a_bot.spines['top'].set_visible(False)
            dx,dy_base=0.024,0.032
            dy_top=dy_base*(bot_ratio/top_ratio)
            dy_bot=dy_base
            kb=dict(color='black',linewidth=0.95,clip_on=False,zorder=10)
            for x0 in (0.0,1.0):
                for shift in (-0.014,0.014):
                    ax_a_top.plot((x0-dx,x0+dx),(shift-dy_top,shift+dy_top),transform=ax_a_top.transAxes,**kb)
                    ax_a_bot.plot((x0-dx,x0+dx),(1.0+shift-dy_bot,1.0+shift+dy_bot),transform=ax_a_bot.transAxes,**kb)
            for case in ['w1','w3']:
                st=styles[case]
                group=[next(r for r in query_rows if r['variant']==variant and r['case']==case)
                       for variant in variants]
                pruning=[100*float(r['pruning_ratio']) for r in group]
                ax_b.plot(x,pruning,linestyle=st['ls'],linewidth=1.6,color=st['color'],
                          marker=st['marker'],markersize=7.0 if case=='w1' else 7.4,
                          markerfacecolor='white',markeredgecolor=st['color'],markeredgewidth=1.65,zorder=4)
                for position,value in zip(x,pruning):
                    dy=8 if case=='w3' else -15
                    ax_b.annotate(f'{value:.2f}'.replace('.',','),(position,value),
                                  xytext=(0,dy),textcoords='offset points',ha='center',
                                  fontsize=10.5,color=st['color'],bbox=halo,zorder=5)
            ax_b.set(ylim=(99.58,100.09),yticks=[99.6,99.8,100.0])
            ax_b.set_yticklabels(['99,6','99,8','100,0'])
            ax_b.set_title('(b) Pruning W1, W3 (%)',pad=8,fontweight='bold')
            pruning_w2=[100*float(r['pruning_ratio']) for r in g_w2]
            ax_c.plot(x,pruning_w2,linestyle=st_w2['ls'],linewidth=1.6,color=st_w2['color'],
                      marker=st_w2['marker'],markersize=6.6,markerfacecolor='white',
                      markeredgecolor=st_w2['color'],markeredgewidth=1.65,zorder=4)
            for position,value in zip(x,pruning_w2):
                ax_c.annotate(f'{value:.1f}'.replace('.',','),(position,value),
                              xytext=(0,8),textcoords='offset points',ha='center',
                              fontsize=11,color=st_w2['color'],bbox=halo,zorder=5)
            ax_c.set(ylim=(0,100),yticks=[0,50,100])
            ax_c.set_yticklabels(['0','50','100'])
            ax_c.set_title('(c) Pruning W2 (%)',pad=8,fontweight='bold')
            ax_c.set_xlabel('index_granularity (g)')
            pk_kib=[float(r['primary_key_bytes_in_memory'])/1024 for r in costs]
            mk_kib=[float(r['marks_bytes'])/1024 for r in costs]
            bars_pk=ax_d.bar([v-.175 for v in x],pk_kib,width=.35,facecolor='#D6E6F4',
                             edgecolor='#1B4F72',linewidth=1.1,hatch='///',zorder=3)
            bars_mk=ax_d.bar([v+.175 for v in x],mk_kib,width=.35,facecolor='#FAE5D3',
                             edgecolor='#873600',linewidth=1.1,hatch='..',zorder=3)
            for bar,val,col in [(b,v,'#1B4F72') for b,v in zip(bars_pk,pk_kib)]+[(b,v,'#873600') for b,v in zip(bars_mk,mk_kib)]:
                ax_d.annotate(f'{val:.1f}'.replace('.',','),(bar.get_x()+bar.get_width()/2,val),
                              xytext=(0,3),textcoords='offset points',ha='center',va='bottom',
                              fontsize=10.5,color=col,bbox=halo,zorder=5)
            ax_d.set(ylim=(0,288),yticks=[0,125,250])
            ax_d.set_yticklabels(['0','125','250'])
            ax_d.set_title('(d) Chỉ mục & marks (KiB)',pad=8,fontweight='bold')
            ax_d.set_xlabel('index_granularity (g)')
            for ax in [ax_a_top,ax_a_bot,ax_b,ax_c,ax_d]:
                ax.set_xlim(-.52,len(variants)-.48)
                ax.grid(axis='y',color='#D5D8DC',linewidth=0.7,alpha=.85,zorder=0)
            for ax in [ax_a_bot,ax_b,ax_c,ax_d]:
                ax.set_xticks(x,[v[1:] for v in variants])
            row1=[Line2D([],[],color=styles[c]['color'],linestyle=styles[c]['ls'],linewidth=1.6,
                         marker=styles[c]['marker'],markersize=6.6 if c=='w2' else 7.0,markerfacecolor='white',
                         markeredgecolor=styles[c]['color'],markeredgewidth=1.65,label=styles[c]['label'])
                  for c in ['w1','w2','w3']]
            eb_handle=ErrorbarContainer(
                (Line2D([0],[0],linestyle='none',marker='none'),
                 (Line2D([0],[0],color=q_gray,marker='_',markersize=8.0,markeredgewidth=1.4,linestyle='none'),
                  Line2D([0],[0],color=q_gray,marker='_',markersize=8.0,markeredgewidth=1.4,linestyle='none')),
                 (LineCollection([[(0,0),(0,1)]],colors=[q_gray],linewidths=1.5),)),
                has_xerr=False,has_yerr=True)
            row1.append(eb_handle)
            row2=[Patch(facecolor='#D6E6F4',edgecolor='#1B4F72',linewidth=1.1,hatch='///',label='Primary index (RAM)'),
                  Patch(facecolor='#FAE5D3',edgecolor='#873600',linewidth=1.1,hatch='..',label='Marks (đĩa)')]
            leg1=leg_ax.legend(row1,['W1','W2','W3','Khoảng Q1–Q3'],loc='center',bbox_to_anchor=(0.5,0.73),ncol=4,
                               frameon=False,columnspacing=1.8,handlelength=2.1,handletextpad=0.5,fontsize=12)
            leg_ax.add_artist(leg1)
            leg_ax.legend(handles=row2,loc='center',bbox_to_anchor=(0.5,0.27),ncol=2,
                          frameon=False,columnspacing=2.4,handlelength=2.0,handletextpad=0.55,fontsize=12)
            leg_ax.add_patch(FancyBboxPatch((0.01,0.04),0.98,0.92,transform=leg_ax.transAxes,
                             boxstyle='round,pad=0.015,rounding_size=0.03',facecolor='#F8FAFC',
                             edgecolor='#CBD5E1',linewidth=0.9,zorder=-1,clip_on=False))
            for suffix,dpi_val in [('png',450),('svg',None),('pdf',None)]:
                fig.savefig(folder/('e2_granularity_tradeoff_v7.'+suffix),
                            dpi=dpi_val,bbox_inches='tight',pad_inches=0.06)
            plt.close(fig)
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
        raw_path=run.path('ingest',rows[0]['scale']+'.csv')
        raw=csv_read(raw_path) if raw_path.exists() else []
        fig,axes=plt.subplots(1,3,figsize=(13,4))
        for ax,metric,label,factor in zip(axes,['throughput_rows_s','active_bytes_stable','merge_row_amplification'],
               ['Ingestion throughput (rows/s)','Active storage (MiB)','Merge rows read / input rows'],[1,2**20,1]):
            med=[float(r[metric+'_median'])/factor for r in rows]
            err=[[v-float(r[metric+'_q1'])/factor for r,v in zip(rows,med)],
                 [float(r[metric+'_q3'])/factor-v for r,v in zip(rows,med)]]
            ax.bar(range(len(rows)),med,yerr=err,capsize=4,alpha=.65)
            ax.set_xticks(range(len(rows)),[r['batch_rows'] for r in rows])
            for j,r in enumerate(rows):
                observations=[v for v in raw if v['batch_rows']==r['batch_rows']]
                if observations:
                    ax.scatter([j+(int(v['repeat'])-1)*.12 for v in observations],
                               [float(v[metric])/factor for v in observations],color='black',s=22,zorder=3)
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
