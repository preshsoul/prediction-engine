"""
Dashboard V2 — Multi-Market
============================
Replaces generate_dashboard() in prediction_engine.py.
Shows: Moneyline, Spread, Totals, BTTS with tab navigation.
Each game is an expandable card showing all available markets.
"""

import json
from datetime import datetime
from collections import defaultdict


def generate_dashboard_v2(bt_pure, bt_mkt, mc, multi_predictions):
    """
    Generate the HTML dashboard with multi-market support.

    multi_predictions: list of dicts from predict_all_markets(), each with:
        { moneyline: {...}, spread: {...}, totals: {...}, btts: {...}|None }
    """
    # ── Prep chart data (same as v1) ────────────────────────────
    cal_labels = json.dumps([f"{c['bucket']*100:.0f}%" for c in mc["calibration"]])
    cal_predicted = json.dumps([round(c["predicted"]*100,1) for c in mc["calibration"]])
    cal_actual = json.dumps([round(c["actual"]*100,1) for c in mc["calibration"]])
    league_names = json.dumps(list(bt_pure["by_league"].keys()))
    league_pure = json.dumps([bt_pure["by_league"][k]["accuracy"]*100 for k in bt_pure["by_league"]])
    league_mkt = json.dumps([bt_mkt["by_league"][k]["accuracy"]*100 for k in bt_mkt["by_league"]])

    bt_details = []
    for league, data in bt_pure["by_league"].items():
        for d in data["details"]:
            bt_details.append({**d, "league": league})
    bt_details_json = json.dumps(bt_details)

    # Moneyline-level predictions for charts
    ml_preds = [p["moneyline"] for p in multi_predictions if p]
    pred_json = json.dumps(ml_preds)

    tier_counts = defaultdict(int)
    for p in ml_preds:
        tier_counts[p["tier"]] += 1
    tier_labels = json.dumps(list(tier_counts.keys()))
    tier_values = json.dumps(list(tier_counts.values()))
    mc_acc = json.dumps({k: v["accuracy"]*100 for k, v in mc["league_accuracy"].items()})

    # Full multi-market data for JS
    mm_json = json.dumps(multi_predictions)

    now = datetime.now().strftime("%B %d, %Y %H:%M")

    # Count market predictions
    n_spreads = sum(1 for p in multi_predictions if p and p.get("spread"))
    n_totals = sum(1 for p in multi_predictions if p and p.get("totals"))
    n_btts = sum(1 for p in multi_predictions if p and p.get("btts"))

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Prediction Engine v2 — Multi-Market Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
:root{{--bg:#fafaf8;--sf:#fff;--bd:#e5e4df;--tx:#1a1a18;--mt:#6b6a65;--ht:#9c9b96;
--red:#E24B4A;--blue:#378ADD;--green:#1D9E75;--coral:#D85A30;--amber:#EF9F27;--purple:#7F77DD;
--lk-bg:#E1F5EE;--lk-tx:#085041;--lk-bd:#5DCAA5;--st-bg:#E6F1FB;--st-tx:#0C447C;--st-bd:#85B7EB;
--ln-bg:#FAEEDA;--ln-tx:#633806;--ln-bd:#FAC775;--tu-bg:#F1EFE8;--tu-tx:#444441;--tu-bd:#B4B2A9;
--card-hover:rgba(0,0,0,0.02)}}
@media(prefers-color-scheme:dark){{:root{{--bg:#1a1a18;--sf:#242421;--bd:#3a3a36;--tx:#e8e7e3;--mt:#9c9b96;--ht:#6b6a65;
--lk-bg:#04342C;--lk-tx:#9FE1CB;--lk-bd:#0F6E56;--st-bg:#042C53;--st-tx:#85B7EB;--st-bd:#185FA5;
--ln-bg:#412402;--ln-tx:#FAC775;--ln-bd:#854F0B;--tu-bg:#2C2C2A;--tu-tx:#B4B2A9;--tu-bd:#5F5E5A;
--card-hover:rgba(255,255,255,0.02)}}}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--tx);line-height:1.6;padding:2rem;max-width:1200px;margin:0 auto}}
h1{{font-size:22px;font-weight:500;margin-bottom:4px}}
h2{{font-size:18px;font-weight:500;margin:2rem 0 1rem}}
h3{{font-size:16px;font-weight:500;margin:0 0 12px}}
.sub{{font-size:14px;color:var(--mt);margin-bottom:2rem}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px;margin-bottom:2rem}}
.m{{background:var(--sf);border:.5px solid var(--bd);border-radius:12px;padding:16px;text-align:center}}
.m-l{{font-size:12px;color:var(--mt);margin-bottom:4px}}.m-v{{font-size:24px;font-weight:500}}.m-s{{font-size:11px;color:var(--ht);margin-top:2px}}
.row{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:2rem}}
@media(max-width:768px){{.row{{grid-template-columns:1fr}}}}
.box{{background:var(--sf);border:.5px solid var(--bd);border-radius:12px;padding:20px}}
.cw{{position:relative;height:280px}}

/* Filter & market tabs */
.fb{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}}
.fb button{{padding:6px 14px;border-radius:8px;border:.5px solid var(--bd);background:transparent;cursor:pointer;font-size:13px;color:var(--tx);transition:all .15s}}
.fb button.a{{background:var(--sf);border-color:var(--tx);font-weight:500}}.fb button:hover{{background:var(--sf)}}
.mtabs{{display:flex;gap:6px;margin-bottom:20px;border-bottom:1.5px solid var(--bd);padding-bottom:0}}
.mtabs button{{padding:8px 16px;border:none;background:transparent;cursor:pointer;font-size:13px;font-weight:500;color:var(--mt);
  border-bottom:2px solid transparent;margin-bottom:-1.5px;transition:all .15s}}
.mtabs button.a{{color:var(--tx);border-bottom-color:var(--blue)}}
.mtabs button:hover{{color:var(--tx)}}

/* Game cards */
.games{{display:flex;flex-direction:column;gap:12px}}
.game-card{{background:var(--sf);border:.5px solid var(--bd);border-radius:12px;overflow:hidden;transition:border-color .15s}}
.game-card:hover{{border-color:var(--mt)}}
.gc-head{{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:14px;padding:16px 20px;cursor:pointer}}
.gc-league{{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--mt);font-weight:500;min-width:70px}}
.gc-matchup{{font-size:15px;font-weight:500}}
.gc-matchup span{{color:var(--mt);font-weight:400;font-size:13px;margin:0 8px}}
.gc-pick{{text-align:right}}
.gc-pick-name{{font-size:14px;font-weight:500}}
.gc-pick-conf{{font-size:12px;color:var(--mt)}}

/* Expanded market rows */
.gc-markets{{display:none;border-top:.5px solid var(--bd);padding:0}}
.game-card.open .gc-markets{{display:block}}
.mkt-row{{display:grid;grid-template-columns:100px 1fr 80px 70px;align-items:center;padding:10px 20px;border-bottom:.5px solid var(--bd);font-size:13px}}
.mkt-row:last-child{{border-bottom:none}}
.mkt-label{{font-weight:500;font-size:12px;color:var(--mt);text-transform:uppercase;letter-spacing:.03em}}
.mkt-pick{{font-weight:500}}
.mkt-conf{{text-align:right;color:var(--mt)}}

/* Over/under bar */
.ou-bar{{display:flex;height:6px;border-radius:3px;overflow:hidden;width:100%;max-width:120px}}
.ou-over{{background:var(--green)}}.ou-under{{background:var(--red)}}

/* BTTS indicator */
.btts-dot{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px}}
.btts-yes{{background:var(--green)}}.btts-no{{background:var(--red)}}

/* Badges */
.p{{display:inline-block;padding:2px 10px;border-radius:8px;font-size:11px;font-weight:500;letter-spacing:.03em}}
.p-LOCK{{background:var(--lk-bg);color:var(--lk-tx);border:.5px solid var(--lk-bd)}}
.p-STRONG{{background:var(--st-bg);color:var(--st-tx);border:.5px solid var(--st-bd)}}
.p-LEAN{{background:var(--ln-bg);color:var(--ln-tx);border:.5px solid var(--ln-bd)}}
.p-TOSS-UP{{background:var(--tu-bg);color:var(--tu-tx);border:.5px solid var(--tu-bd)}}
.ok{{color:var(--green)}}.no{{color:var(--red)}}.ep{{color:var(--green)}}.en{{color:var(--red)}}
.dot{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}}
.d-NBA{{background:var(--red)}}.d-NHL{{background:var(--blue)}}.d-EPL{{background:var(--green)}}.d-LL{{background:var(--coral)}}

/* Backtest table */
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{text-align:left;padding:8px 10px;border-bottom:1.5px solid var(--bd);color:var(--mt);font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:.04em}}
td{{padding:7px 10px;border-bottom:.5px solid var(--bd)}}tr:hover{{background:var(--card-hover)}}
.disc{{font-size:11px;color:var(--ht);margin-top:2rem;padding:12px 16px;background:var(--sf);border-radius:8px;border:.5px solid var(--bd)}}

/* Market summary strip */
.mkt-strip{{display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:8px;padding:12px 20px;background:var(--card-hover);border-top:.5px solid var(--bd)}}
.ms-item{{text-align:center;font-size:11px;color:var(--mt)}}
.ms-val{{font-size:14px;font-weight:500;color:var(--tx)}}

@media(max-width:640px){{
  .gc-head{{grid-template-columns:1fr;gap:8px}}
  .gc-pick{{text-align:left}}
  .mkt-row{{grid-template-columns:80px 1fr 60px 60px;padding:8px 14px;font-size:12px}}
  .mkt-strip{{grid-template-columns:repeat(2,1fr)}}
}}
</style></head><body>
<h1>Multi-league prediction engine</h1>
<p class="sub">Multi-market predictions &mdash; {now}</p>

<div class="metrics">
<div class="m"><div class="m-l">Backtest accuracy</div><div class="m-v">{bt_pure['overall']['accuracy']*100:.1f}%</div><div class="m-s">{bt_pure['overall']['correct']}/{bt_pure['overall']['total']} games</div></div>
<div class="m"><div class="m-l">Market blend</div><div class="m-v">{bt_mkt['overall']['accuracy']*100:.1f}%</div><div class="m-s">{bt_mkt['overall']['correct']}/{bt_mkt['overall']['total']} games</div></div>
<div class="m"><div class="m-l">Monte Carlo</div><div class="m-v">{mc['n_sims']:,}</div><div class="m-s">simulations</div></div>
<div class="m"><div class="m-l">Games</div><div class="m-v">{len(multi_predictions)}</div><div class="m-s">upcoming</div></div>
<div class="m"><div class="m-l">Spreads</div><div class="m-v">{n_spreads}</div><div class="m-s">predictions</div></div>
<div class="m"><div class="m-l">Totals</div><div class="m-v">{n_totals}</div><div class="m-s">over/under</div></div>
<div class="m"><div class="m-l">BTTS</div><div class="m-v">{n_btts}</div><div class="m-s">soccer only</div></div>
</div>

<div class="row">
<div class="box"><h3>Calibration curve (Monte Carlo)</h3><div class="cw"><canvas id="c1"></canvas></div></div>
<div class="box"><h3>Accuracy by league</h3><div class="cw"><canvas id="c2"></canvas></div></div>
</div>
<div class="row">
<div class="box"><h3>Tier distribution</h3><div class="cw"><canvas id="c3"></canvas></div></div>
<div class="box"><h3>Monte Carlo accuracy</h3><div class="cw"><canvas id="c4"></canvas></div></div>
</div>

<h2>Predictions</h2>
<div class="fb" id="fb"></div>
<div class="mtabs" id="mtabs">
  <button class="a" data-m="all">All markets</button>
  <button data-m="moneyline">Moneyline</button>
  <button data-m="spread">Spread</button>
  <button data-m="totals">Over/Under</button>
  <button data-m="btts">BTTS</button>
</div>
<div class="games" id="games"></div>

<h2>Backtest detail</h2>
<table id="bt"><thead><tr><th></th><th>League</th><th>Matchup</th><th>Score</th><th>Pick</th><th>Actual</th><th>Conf</th><th>Tier</th></tr></thead><tbody></tbody></table>

<div class="disc">
Multi-market prediction engine v2. Moneyline: sport-specific Elo + form + market blend with cross-market signal enhancement.
Spread: win probability to margin conversion + scoring differential. Totals: Poisson-style team offensive/defensive rate model.
BTTS: team scoring frequency × opponent defensive leak rate. For entertainment and educational purposes only.
</div>

<script>
const MM={mm_json};
const P={pred_json};
const B={bt_details_json};
const gc=getComputedStyle(document.documentElement).getPropertyValue('--bd').trim()||'#e5e4df';
const tc=getComputedStyle(document.documentElement).getPropertyValue('--mt').trim()||'#6b6a65';
Chart.defaults.color=tc;

new Chart(document.getElementById('c1'),{{type:'line',data:{{labels:{cal_labels},datasets:[
{{label:'Perfect',data:{cal_labels}.map(l=>parseFloat(l)),borderColor:'#B4B2A9',borderDash:[5,5],pointRadius:0,borderWidth:1.5}},
{{label:'Predicted',data:{cal_predicted},borderColor:'#378ADD',fill:false,pointRadius:3,borderWidth:2}},
{{label:'Actual',data:{cal_actual},borderColor:'#1D9E75',fill:false,pointRadius:3,borderWidth:2}}
]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:10,padding:12}}}}}},scales:{{y:{{min:20,max:100,grid:{{color:gc}}}},x:{{grid:{{display:false}}}}}}}}}});

new Chart(document.getElementById('c2'),{{type:'bar',data:{{labels:{league_names},datasets:[
{{label:'Pure model',data:{league_pure},backgroundColor:'#378ADD',borderRadius:4}},
{{label:'Market blend',data:{league_mkt},backgroundColor:'#1D9E75',borderRadius:4}}
]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:10,padding:12}}}}}},scales:{{y:{{min:0,max:100,grid:{{color:gc}},ticks:{{callback:v=>v+'%'}}}},x:{{grid:{{display:false}}}}}}}}}});

const tC={{'LOCK':'#1D9E75','STRONG':'#378ADD','LEAN':'#EF9F27','TOSS-UP':'#B4B2A9'}};
new Chart(document.getElementById('c3'),{{type:'doughnut',data:{{labels:{tier_labels},datasets:[{{data:{tier_values},backgroundColor:{tier_labels}.map(t=>tC[t]||'#B4B2A9'),borderWidth:0}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:10,padding:12}}}}}}}}}});

const md={mc_acc};
new Chart(document.getElementById('c4'),{{type:'bar',data:{{labels:Object.keys(md),datasets:[{{data:Object.values(md),backgroundColor:Object.keys(md).map(l=>({{NBA:'#E24B4A',NHL:'#378ADD',EPL:'#1D9E75','La Liga':'#D85A30'}})[l]),borderRadius:4}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{y:{{min:0,max:100,grid:{{color:gc}},ticks:{{callback:v=>v+'%'}}}},x:{{grid:{{display:false}}}}}}}}}});

/* ── Helpers ────────────────────────────────────────── */
const dc=l=>l==='La Liga'?'d-LL':'d-'+l;
const pip=(t)=>`<span class="p p-${{t}}">${{t}}</span>`;
const pct=(v)=>(v*100).toFixed(0)+'%';
const spFmt=(v)=>v>0?'+'+v.toFixed(1):v.toFixed(1);

/* ── State ──────────────────────────────────────────── */
let leagueFilter='ALL';
let marketFilter='all';

/* ── Render game cards ──────────────────────────────── */
function renderGames(){{
  const gc=document.getElementById('games');
  let data=MM;
  if(leagueFilter!=='ALL') data=data.filter(p=>p&&p.moneyline&&p.moneyline.league===leagueFilter);

  gc.innerHTML=data.map((p,i)=>{{
    if(!p||!p.moneyline) return '';
    const ml=p.moneyline;
    const sp=p.spread;
    const to=p.totals;
    const bt=p.btts;
    const lg=ml.league;
    const isSoccer=lg==='EPL'||lg==='La Liga';

    /* Header pick display */
    let headPick=ml.pick;
    let headConf=pct(ml.confidence);
    let headTier=ml.tier;

    if(marketFilter==='spread'&&sp){{
      headPick=sp.spread_home<0?ml.home+' '+spFmt(sp.spread_home):ml.away+' '+spFmt(sp.spread_away);
      headConf=pct(sp.confidence);headTier=sp.tier;
    }} else if(marketFilter==='totals'&&to){{
      const ouPick=to.over_prob>0.5?'OVER':'UNDER';
      headPick=ouPick+' '+(to.mkt_total||to.predicted_total);
      headConf=pct(Math.max(to.over_prob,to.under_prob));headTier=to.tier;
    }} else if(marketFilter==='btts'&&bt){{
      headPick=bt.pick;headConf=pct(bt.confidence);headTier=bt.tier;
    }} else if(marketFilter==='btts'&&!bt){{
      return '';
    }}

    /* Market rows */
    let rows='';

    /* Moneyline row */
    if(marketFilter==='all'||marketFilter==='moneyline'){{
      const dp=ml.probs.draw!=null?pct(ml.probs.draw):'—';
      const ec=ml.edge>0?'ep':(ml.edge<-0.02?'en':'');
      const es=(ml.edge>0?'+':'')+(ml.edge*100).toFixed(1)+'%';
      rows+=`<div class="mkt-row">
        <div class="mkt-label">Win</div>
        <div class="mkt-pick">${{ml.pick}} <span style="color:var(--mt);font-weight:400;margin-left:8px">H:${{pct(ml.probs.home)}} A:${{pct(ml.probs.away)}} D:${{dp}}</span></div>
        <div class="${{ec}}" style="text-align:right;font-size:12px">${{es}}</div>
        <div class="mkt-conf">${{pip(ml.tier)}}</div>
      </div>`;
    }}

    /* Spread row */
    if((marketFilter==='all'||marketFilter==='spread')&&sp){{
      const spPick=sp.spread_home<0?ml.home+' '+spFmt(sp.spread_home):ml.away+' '+spFmt(sp.spread_away);
      rows+=`<div class="mkt-row">
        <div class="mkt-label">Spread</div>
        <div class="mkt-pick">${{spPick}} <span style="color:var(--mt);font-weight:400;margin-left:8px">cover: ${{pct(sp.home_cover_prob)}}</span></div>
        <div style="text-align:right;font-size:12px">${{pct(sp.confidence)}}</div>
        <div class="mkt-conf">${{pip(sp.tier)}}</div>
      </div>`;
    }}

    /* Totals row */
    if((marketFilter==='all'||marketFilter==='totals')&&to){{
      const ouPick=to.over_prob>0.5?'OVER':'UNDER';
      const ouConf=Math.max(to.over_prob,to.under_prob);
      const overW=Math.round(to.over_prob*100);
      const underW=100-overW;
      rows+=`<div class="mkt-row">
        <div class="mkt-label">Total</div>
        <div class="mkt-pick">${{ouPick}} ${{to.mkt_total||to.predicted_total}}
          <span style="color:var(--mt);font-weight:400;margin-left:8px">pred: ${{to.predicted_total}} (${{to.exp_home_score}}-${{to.exp_away_score}})</span>
          <div class="ou-bar" style="margin-top:4px"><div class="ou-over" style="width:${{overW}}%"></div><div class="ou-under" style="width:${{underW}}%"></div></div>
        </div>
        <div style="text-align:right;font-size:12px">O:${{pct(to.over_prob)}}</div>
        <div class="mkt-conf">${{pip(to.tier)}}</div>
      </div>`;
    }}

    /* BTTS row */
    if((marketFilter==='all'||marketFilter==='btts')&&bt){{
      const yc=bt.pick==='BTTS Yes'?'btts-yes':'btts-no';
      rows+=`<div class="mkt-row">
        <div class="mkt-label">BTTS</div>
        <div class="mkt-pick"><span class="btts-dot ${{yc}}"></span>${{bt.pick}}
          <span style="color:var(--mt);font-weight:400;margin-left:8px">H scores: ${{pct(bt.home_scores_prob)}} &middot; A scores: ${{pct(bt.away_scores_prob)}}</span>
        </div>
        <div style="text-align:right;font-size:12px">${{pct(bt.confidence)}}</div>
        <div class="mkt-conf">${{pip(bt.tier)}}</div>
      </div>`;
    }}

    return `<div class="game-card open" data-idx="${{i}}">
      <div class="gc-head" onclick="this.parentElement.classList.toggle('open')">
        <div class="gc-league"><span class="dot ${{dc(lg)}}"></span>${{lg}}</div>
        <div class="gc-matchup">${{ml.home}} <span>vs</span> ${{ml.away}}</div>
        <div class="gc-pick">
          <div class="gc-pick-name">${{headPick}}</div>
          <div class="gc-pick-conf">${{headConf}} ${{pip(headTier)}}</div>
        </div>
      </div>
      <div class="gc-markets">${{rows}}</div>
    </div>`;
  }}).join('');
}}

/* ── League filter buttons ──────────────────────────── */
const leagues=['ALL',...new Set(MM.filter(p=>p&&p.moneyline).map(p=>p.moneyline.league))];
const fb=document.getElementById('fb');
leagues.forEach(l=>{{
  const b=document.createElement('button');
  b.className=l==='ALL'?'a':'';b.textContent=l;
  b.onclick=()=>{{leagueFilter=l;fb.querySelectorAll('button').forEach(x=>x.classList.remove('a'));b.classList.add('a');renderGames()}};
  fb.appendChild(b);
}});

/* ── Market tab buttons ─────────────────────────────── */
document.querySelectorAll('#mtabs button').forEach(b=>{{
  b.onclick=()=>{{
    marketFilter=b.dataset.m;
    document.querySelectorAll('#mtabs button').forEach(x=>x.classList.remove('a'));
    b.classList.add('a');
    renderGames();
  }};
}});

/* ── Initial render ─────────────────────────────────── */
renderGames();

/* ── Backtest table ─────────────────────────────────── */
const bb=document.querySelector('#bt tbody');
bb.innerHTML=B.map(d=>{{const m=d.correct?'<span class="ok">&#10003;</span>':'<span class="no">&#10007;</span>';
return`<tr><td>${{m}}</td><td><span class="dot ${{dc(d.league)}}"></span>${{d.league}}</td>
<td>${{d.home}} vs ${{d.away}}</td><td>${{d.score}}</td><td style="font-weight:500">${{d.pick}}</td>
<td>${{d.actual}}</td><td>${{(d.confidence*100).toFixed(0)}}%</td><td><span class="p p-${{d.tier}}">${{d.tier}}</span></td></tr>`}}).join('');
</script></body></html>"""

    return html
