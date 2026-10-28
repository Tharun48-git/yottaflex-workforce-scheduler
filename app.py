import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "web_generated"
REPORT_DIR = ROOT / "reports" / "web"

st.set_page_config(
    page_title="YottaFlex | Workforce Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{--bg:#061225;--side:#081a35;--panel:#0c203b;--blue:#1769ff;--cyan:#42b7ff;--green:#00d6a0;--purple:#9747ff;--text:#f4f7ff;--muted:#b0c5e5;--border:#24466f}
html,body,[class*="css"],[data-testid="stAppViewContainer"]{font-family:Inter,sans-serif!important}
.stApp{background:radial-gradient(ellipse at 85% 0%,#12284a 0%,transparent 38%),linear-gradient(140deg,#061225,#08172c);color:var(--text)!important}
[data-testid="stHeader"]{background:rgba(6,18,37,.95)!important}
/* Sidebar visibility and styling */
section[data-testid="stSidebar"]{display:block!important;visibility:visible!important;background:#081a35!important;border-right:1px solid #24466f!important;min-width:290px!important;width:290px!important;flex-shrink:0!important}
section[data-testid="stSidebar"]>div{background:linear-gradient(180deg,#0a1d3c,#06152d)!important;visibility:visible!important}
section[data-testid="stSidebar"] label,section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p{color:#d7e6ff!important;opacity:1!important;font-size:13px!important;font-weight:600!important}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{color:#a9c2e7!important;font-size:13px}
.brand{font-size:30px;font-weight:800;letter-spacing:-1.5px;color:white!important}.brand span{color:#318bff!important}.brand-sub{font-size:10px;letter-spacing:1.5px;font-weight:700;color:#a9c5ee!important;margin-left:42px}
.sidebar-heading{color:white!important;font-size:16px;font-weight:700;margin-top:20px}.sidebar-divider{border-top:1px solid #203f68;margin:18px 0}
div[data-baseweb="select"]>div,div[data-baseweb="input"]>div,[data-testid="stNumberInput"] input{background:#0a1b35!important;color:white!important;border:1px solid #315581!important;border-radius:9px!important}
[data-baseweb="popover"],[data-baseweb="menu"]{background:#102441!important}[data-baseweb="popover"] *,[data-baseweb="menu"] *{color:#f4f7ff!important}
.main .block-container{max-width:1600px;padding-top:2rem;padding-bottom:2rem}
.eyebrow{color:#42b7ff!important;font-size:12px;font-weight:800;letter-spacing:1.6px;margin-bottom:10px}.hero-title{color:#f5f7ff!important;font-size:clamp(34px,3.5vw,48px);font-weight:800;letter-spacing:-2px;line-height:1.15;margin-bottom:12px}.hero-description{color:#b0c5e5!important;font-size:16px;line-height:1.7;margin-bottom:22px}
.notice{background:linear-gradient(100deg,#0b2e67,#0b2044);border:1px solid #1769ff;border-left:5px solid #1769ff;border-radius:11px;padding:17px 20px;color:#72c3ff!important;font-size:14px;margin:20px 0 24px}
.workspace{background:radial-gradient(circle at 100% 100%,#102e69,transparent 40%),linear-gradient(110deg,#0c2344,#0a1930);border:1px solid #1769ff;border-left:4px solid #1769ff;border-radius:15px;padding:26px;margin:22px 0 30px}.workspace-label{color:#258aff!important;font-size:12px;font-weight:800;letter-spacing:1.5px;margin-bottom:10px}.workspace-title{color:#f5f7ff!important;font-size:20px;font-weight:700;margin-bottom:8px}.workspace-copy{color:#b3c9eb!important;font-size:14px;line-height:1.8}
.section-title{color:#f4f7ff!important;font-size:25px;font-weight:800;margin:25px 0 5px}.section-description{color:#a8bfdf!important;font-size:14px;margin-bottom:20px}
.feature-card{min-height:190px;background:linear-gradient(145deg,#0d203b,#09172b);border:1px solid #24436b;border-left:4px solid #1769ff;border-radius:13px;padding:22px 18px}.feature-card.green{border-left-color:#00d6a0}.feature-card.purple{border-left-color:#9747ff}.feature-icon{font-size:27px;margin-bottom:12px}.feature-title{color:#f5f7ff!important;font-size:16px;font-weight:700;margin-bottom:10px}.feature-copy{color:#adc4e8!important;font-size:13px;line-height:1.7}
.metric-card{background:linear-gradient(145deg,#102440,#0a192e);border:1px solid #25466f;border-radius:12px;padding:20px;min-height:120px}.metric-label{color:#a9c2e7!important;font-size:12px;font-weight:700}.metric-value{color:white!important;font-size:29px;font-weight:800;margin-top:10px}.metric-note{color:#55b6ff!important;font-size:11px;margin-top:5px}
.stButton>button,[data-testid="stDownloadButton"]>button{background:linear-gradient(105deg,#5137ff,#2867ff)!important;color:white!important;border:1px solid #557aff!important;border-radius:10px!important;font-weight:700!important;min-height:44px}.stButton>button:hover,[data-testid="stDownloadButton"]>button:hover{filter:brightness(1.15)}
section[data-testid="stSidebar"] .stButton>button{width:100%;min-height:48px;margin-top:10px}
[data-testid="stTabs"] button{color:#b0c5e5!important}[data-testid="stTabs"] button[aria-selected="true"]{color:#55b7ff!important}
[data-testid="stExpander"]{background:#0b1c33!important;border:1px solid #25466f!important}[data-testid="stExpander"] summary,[data-testid="stExpander"] summary p{color:white!important}
[data-testid="stAlert"]{background:#102441!important;color:white!important}.stMarkdown,.stMarkdown p,.stMarkdown li,.stMarkdown h1,.stMarkdown h2,.stMarkdown h3{color:var(--text)}
.status-pill{display:inline-block;background:#073f48;border:1px solid #087f83;color:#4ce5d0!important;padding:4px 10px;border-radius:20px;font-size:10px;font-weight:800}
.footer{border-top:1px solid #203b5e;margin-top:32px;padding-top:18px;color:#7fa5d7!important;font-size:12px;line-height:1.8}#MainMenu,footer{visibility:hidden}
</style>
""", unsafe_allow_html=True)

# Sidebar controls
with st.sidebar:
    st.markdown('''<div class="brand">▥ Yotta<span>Flex</span></div>
    <div class="brand-sub">WORKFORCE INTELLIGENCE</div>
    <div class="sidebar-divider"></div>
    <div class="sidebar-heading">Dataset configuration</div>
    <p>Configure your scheduling run.</p>''', unsafe_allow_html=True)
    seed = st.number_input("Random seed", min_value=1, max_value=999999999, value=20261022, step=1)
    employees = st.selectbox("Number of employees", [100, 500, 1000, 2000], index=0)
    teams = st.selectbox("Number of teams", [10, 25, 50, 100], index=0)
    days = st.selectbox("Schedule duration", [7, 30, 60, 90], index=0, format_func=lambda n: f"{n} days")
    leaves = st.selectbox("Baseline leave requests", [100, 500, 1000, 5000], index=0)
    generate = st.button("▶  Generate & validate", use_container_width=True, type="primary")
    st.markdown('''<p style="font-size:12px;color:#85a8d8!important">ⓘ All generated records are synthetic.</p>
    <div class="sidebar-divider"></div><p style="color:#d7e6ff!important;font-weight:700">Environment</p>
    <span class="status-pill">SYNTHETIC DEMO</span><p style="font-size:12px">No real employee records are used.</p>''', unsafe_allow_html=True)

# Header
st.markdown('''<div class="eyebrow">WORKFORCE OPERATIONS / ANALYTICS</div>
<div class="hero-title">Workforce Intelligence</div>
<div class="hero-description">Your command center for workforce scheduling, shift coverage, operational insights, and scheduling-rule validation.</div>
<div class="notice">ⓘ &nbsp; Synthetic-data demonstration. Results are for exploration and do not constitute production scheduling or compliance approval.</div>''', unsafe_allow_html=True)

# Generate and validate with the project's existing CLI
if generate:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    gen_cmd = [sys.executable, "-m", "workforce_scheduler.cli", "generate", "--out", str(DATA_DIR), "--seed", str(seed), "--employees", str(employees), "--teams", str(teams), "--days", str(days), "--leaves", str(leaves)]
    val_cmd = [sys.executable, "-m", "workforce_scheduler.cli", "validate", "--data", str(DATA_DIR), "--reports", str(REPORT_DIR)]
    try:
        with st.spinner("Generating synthetic workforce data..."):
            result = subprocess.run(gen_cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
        if result.returncode:
            st.error("Dataset generation failed. Details:")
            st.code((result.stderr or result.stdout)[-5000:])
            st.stop()
        with st.spinner("Validating schedules and creating reports..."):
            result = subprocess.run(val_cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
        if result.returncode:
            st.error("Validation failed. Details:")
            st.code((result.stderr or result.stdout)[-5000:])
            st.stop()
        st.session_state["run_result"] = {"data_dir": str(DATA_DIR), "report_dir": str(REPORT_DIR), "seed": int(seed), "employees": employees, "teams": teams, "days": days}
        st.success("Generation and validation completed!")
    except subprocess.TimeoutExpired:
        st.error("The operation took too long. Try a smaller dataset.")
    except Exception as exc:
        st.error(f"Something went wrong: {exc}")

run = st.session_state.get("run_result")
if run is None:
    st.markdown('''<div class="workspace"><div class="workspace-label">YOUR WORKSPACE</div>
    <div class="workspace-title">🚀 &nbsp; Ready for your first run</div><div class="workspace-copy">Choose your settings in the sidebar and click <b>Generate &amp; validate</b>.<br>Start with 100 employees, 10 teams, and 7 days for a quick test.</div></div>
    <div class="section-title">Explore the platform</div><div class="section-description">Tools to help you understand your synthetic workforce data.</div>''', unsafe_allow_html=True)
    a,b,c = st.columns(3)
    with a: st.markdown('<div class="feature-card"><div class="feature-icon">📅</div><div class="feature-title">Shift planning</div><div class="feature-copy">Explore generated shifts, employee records, and schedule data.</div></div>', unsafe_allow_html=True)
    with b: st.markdown('<div class="feature-card green"><div class="feature-icon">📊</div><div class="feature-title">Coverage analytics</div><div class="feature-copy">Review coverage rates and identify uncovered staffing requirements.</div></div>', unsafe_allow_html=True)
    with c: st.markdown('<div class="feature-card purple"><div class="feature-icon">🔎</div><div class="feature-title">Rule validation</div><div class="feature-copy">Inspect scheduling anomalies and download validation reports.</div></div>', unsafe_allow_html=True)
else:
    data_dir, report_dir = Path(run["data_dir"]), Path(run["report_dir"])
    summary_path = report_dir / "validation_summary.json"
    try: summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    except (OSError, json.JSONDecodeError): summary = {}
    def metric(names, fallback=0):
        return next((summary[n] for n in names if n in summary), fallback)
    employee_count = metric(["employees", "employee_count", "total_employees"], run["employees"])
    team_count = metric(["teams", "team_count", "total_teams"], run["teams"])
    coverage = metric(["coverage_met_rate", "coverage_rate"], 0)
    gaps = metric(["coverage_gap_requirements", "coverage_gaps"], 0)
    issues = metric(["issues", "issue_count", "validation_issues"], 0)
    coverage_text = f"{coverage:.1%}" if isinstance(coverage,(int,float)) and coverage <= 1 else (f"{coverage:.1f}%" if isinstance(coverage,(int,float)) else str(coverage))
    st.markdown('<div class="workspace"><div class="workspace-label">YOUR WORKSPACE</div><div class="workspace-title">Workforce run completed</div><div class="workspace-copy">Your dataset has been generated. Explore analytics, inspect CSV files, and download reports below.</div></div><div class="section-title">Analytics overview</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for col,(label,value,note) in zip(cols,[("EMPLOYEES",employee_count,"Synthetic employee records"),("TEAMS",team_count,"Configured workforce teams"),("COVERAGE MET",coverage_text,"Reported coverage rate"),("COVERAGE GAPS",gaps,"Uncovered requirements")]):
        with col: st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>',unsafe_allow_html=True)
    st.write("")
    tab1,tab2,tab3 = st.tabs(["📊 Analytics overview","🗂️ Data explorer","📥 Reports & downloads"])
    with tab1:
        st.markdown("### Run settings")
        st.write(f"**Seed:** {run['seed']}  \n**Employees:** {run['employees']}  \n**Teams:** {run['teams']}  \n**Schedule duration:** {run['days']} days")
        st.markdown("### Validation summary")
        if summary: st.json(summary)
        else: st.info("No validation summary JSON was found.")
        csvs = sorted(data_dir.glob("*.csv"))
        if csvs:
            rows=[]
            for p in csvs:
                try: count=max(0,sum(1 for _ in p.open("r",encoding="utf-8-sig"))-1)
                except OSError: count="Unavailable"
                rows.append({"Dataset":p.name,"Rows":count})
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    with tab2:
        csvs = sorted(data_dir.glob("*.csv"))
        if csvs:
            selected=st.selectbox("Choose a dataset",csvs,format_func=lambda p:p.name)
            try:
                df=pd.read_csv(selected); st.caption(f"{len(df):,} rows · {len(df.columns)} columns")
                query=st.text_input("Search rows",placeholder="Type to filter the dataset...")
                shown=df
                if query:
                    mask=df.astype(str).apply(lambda col:col.str.contains(query,case=False,na=False,regex=False)).any(axis=1); shown=df[mask]
                st.dataframe(shown.head(1000),use_container_width=True,hide_index=True)
                st.download_button("⬇ Download selected CSV",df.to_csv(index=False).encode("utf-8"),file_name=selected.name,mime="text/csv")
            except Exception as exc: st.error(f"Could not read the CSV: {exc}")
        else: st.info("No generated datasets found.")
    with tab3:
        reports=sorted(p for p in report_dir.glob("*") if p.is_file())
        if reports:
            for p in reports:
                st.markdown(f"**{p.name}**")
                mime="text/csv" if p.suffix.lower()==".csv" else "application/json" if p.suffix.lower()==".json" else "application/octet-stream"
                try: st.download_button(f"⬇ Download {p.name}",p.read_bytes(),file_name=p.name,mime=mime,key=f"report_{p.name}")
                except OSError as exc: st.error(f"Unable to read {p.name}: {exc}")
        else: st.info("No reports found.")
    st.markdown(f'<div class="footer"><b style="color:#c6dcff">YottaFlex Workforce Intelligence</b> · Synthetic data demo · Review reports before operational use.<br>Reported validation issue count: {issues}</div>',unsafe_allow_html=True)

if run is None:
    st.markdown('<div class="footer"><b style="color:#c6dcff">YottaFlex Workforce Intelligence</b> · Synthetic data demo · Review reports before operational use.</div>',unsafe_allow_html=True)
