"""Small transparent nonnegative model; no target-scale measurements in fitting."""
import statistics


def fit(rows, times):
    if len(rows) < 3 or len(set(rows)) < 2:
        return {'identifiable': False, 'reason': 'Need >=3 scales and >=2 distinct estimated-row counts'}
    xbar, ybar = statistics.mean(rows), statistics.mean(times)
    xx = sum((x-xbar)**2 for x in rows)
    beta = sum((x-xbar)*(y-ybar) for x,y in zip(rows,times)) / xx
    alpha = ybar - beta*xbar
    candidates = [(max(0, ybar), 0)]
    if beta >= 0 and alpha >= 0:
        candidates.append((alpha,beta))
    candidates.append((0,max(0,sum(x*y for x,y in zip(rows,times))/sum(x*x for x in rows))))
    alpha,beta = min(candidates, key=lambda ab:sum((y-ab[0]-ab[1]*x)**2 for x,y in zip(rows,times)))
    fitted = [alpha+beta*x for x in rows]
    ss = sum((y-ybar)**2 for y in times)
    return dict(identifiable=True, alpha_ms=alpha, beta_ms_per_row=beta,
                calibration_r2=None if ss==0 else 1-sum((y-yh)**2 for y,yh in zip(times,fitted))/ss,
                boundary_fit=alpha==0 or beta==0, calibration_points=len(rows),
                x_min=min(rows), x_max=max(rows))


def predict(model, rows):
    if not model['identifiable']:
        return None
    return model['alpha_ms'] + model['beta_ms_per_row'] * rows
