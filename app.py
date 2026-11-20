"""HanaV Insight: combined ETF Finder and Stock Analyzer Streamlit entrypoint."""
from __future__ import annotations
import hmac
import os
import streamlit as st

st.set_page_config(page_title="HanaV Insight",page_icon="📊",layout="wide",
                   initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/innks/NanumSquareRound@master/nanumsquareround.css');
.stApp,.stApp button,.stApp input,.stApp [data-testid="stMarkdownContainer"]{
 font-family:'NanumSquareRound','Malgun Gothic',sans-serif!important}
.stApp section[data-testid="stSidebar"]{
 background:linear-gradient(165deg,#004f40 0%,#003b33 100%)!important;
 border-right:1px solid #137663!important}
.stApp section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a,
.stApp section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a span,
.stApp section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a p{
 color:#ffffff!important}
.stApp section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"]{
 background:#008b70!important;border-radius:9px}
.stApp section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover{
 background:#106b59!important;border-radius:9px}
.stApp section[data-testid="stSidebar"] h1,
.stApp section[data-testid="stSidebar"] h2,
.stApp section[data-testid="stSidebar"] h3,
.stApp section[data-testid="stSidebar"] p,
.stApp section[data-testid="stSidebar"] label,
.stApp section[data-testid="stSidebar"] [data-testid="stCaptionContainer"]{
 color:#e6f5ef!important}
.stApp section[data-testid="stSidebar"] hr{border-color:#276d5b!important}
.stApp section[data-testid="stSidebar"] [data-testid="stButton"] button{
 background:#f6fbf8!important;color:#075443!important;
 border:1px solid #b6d9c9!important}
/* Streamlit wraps sidebar button captions in a Markdown <p>. Override
   the pale sidebar paragraph text specifically inside enabled buttons. */
.stApp section[data-testid="stSidebar"] [data-testid="stButton"] button:not(:disabled) p,
.stApp section[data-testid="stSidebar"] [data-testid="stButton"] button:not(:disabled) span,
.stApp section[data-testid="stSidebar"] [data-testid="stButton"] button:not(:disabled) [data-testid="stMarkdownContainer"],
.stApp section[data-testid="stSidebar"] [data-testid="stButton"] button:not(:disabled) [data-testid="stMarkdownContainer"] *{
 color:#075443!important;
 opacity:1!important;
 font-weight:800!important
}
.stApp section[data-testid="stSidebar"] [data-testid="stButton"] button:not(:disabled):hover{
 background:#dff4e8!important;border-color:#008b70!important
}
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"],
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p,
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]{
 color:#eafbf2!important;font-weight:700!important;
}
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover{
 background:#0b8067!important;border-radius:10px
}
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"]{
 background:#009574!important;border-radius:10px
}
.insight-nav-brand{font-size:26px;font-weight:900;color:#fff;line-height:1.2;padding:12px 0 2px}
.insight-nav-brand strong{color:#6de2b7}
.insight-nav-subtitle{font-size:11px;color:#d5e6df;line-height:1.5;margin-bottom:8px}
.insight-global-label{font-size:21px;font-weight:850;color:#08634f;padding-top:7px}
</style>""",unsafe_allow_html=True)

def _secret(name):
    try:
        val=st.secrets.get(name,"")
        if isinstance(val,str) and val.strip():
            return val.strip()
    except Exception:
        pass
    return os.environ.get(name,"").strip()

# Preserve the existing ETF Finder's password-only gate by default.
# Opt-in email approval requires ENABLE_EMAIL_AUTH=true and complete Supabase Auth secrets.
if _secret("ENABLE_EMAIL_AUTH").lower() in ("1","true","yes","on"):
    from email_access import require_approved_email
    require_approved_email(st)

password=_secret("APP_PASSWORD")
if not password:
    st.error("APP_PASSWORD가 설정되지 않았습니다. 기존 ETF Finder Streamlit Secrets를 확인하세요.")
    st.stop()
if not st.session_state.get("_etf_authenticated",False):
    st.markdown("""<div style="text-align:center;margin:10vh auto 25px">
    <h1 style="color:#008878">📊 HanaV Insight</h1>
    <p>ETF · 주식 통합 투자분석 플랫폼</p>
    <small>Designed &amp; Built by K.H. Ahn</small></div>""",unsafe_allow_html=True)
    _,center,_=st.columns([1,1.2,1])
    with center:
        with st.form("_insight_login_form"):
            attempt=st.text_input("접속 비밀번호",type="password",placeholder="비밀번호를 입력하세요")
            submitted=st.form_submit_button("🔐 로그인",type="primary",use_container_width=True)
        if submitted:
            if hmac.compare_digest(attempt.encode("utf-8"),password.encode("utf-8")):
                st.session_state["_etf_authenticated"]=True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
    st.stop()

with st.sidebar:
    st.markdown('<div class="insight-nav-brand">📊 HanaV <strong>Insight</strong></div>'
                '<div class="insight-nav-subtitle">ETF · 주식 통합 투자분석 플랫폼</div>',
                unsafe_allow_html=True)
    st.divider()

pages=[
    st.Page("pages/2_시장_대시보드.py",title="시장 대시보드",icon="📊",default=True),
    st.Page("etf_finder.py",title="ETF Finder",icon="📈",url_path="etf"),
    st.Page("stock_analyze.py",title="Analyze",icon="🔎",url_path="analyze"),
    st.Page("pages/0_전종목_수급_레이더.py",title="전종목 수급 레이더",icon="📡",url_path="flow-radar"),
    st.Page("pages/1_수급_전환_검색.py",title="수급전환 검색",icon="🔄",url_path="flow-reversal"),
]
page=st.navigation(pages,position="hidden")
with st.sidebar:
    for path,title,icon in (
        ("pages/2_시장_대시보드.py","시장 대시보드","📊"),
        ("etf_finder.py","ETF Finder","📈"),
        ("stock_analyze.py","Analyze","🔎"),
        ("pages/0_전종목_수급_레이더.py","전종목 수급 레이더","📡"),
        ("pages/1_수급_전환_검색.py","수급전환 검색","🔄"),
    ):
        st.page_link(path,label=title,icon=icon,use_container_width=True)

a,b,c=st.columns([1.5,2.6,.65],vertical_alignment="bottom")
with a:
    st.markdown('<div class="insight-global-label">HanaV Insight</div>',unsafe_allow_html=True)
with b:
    query=st.text_input("통합 종목검색",key="_insight_global_query",
                        placeholder="🔎 종목명 또는 종목코드 (예: 삼성전자, 005930)",
                        label_visibility="collapsed")
with c:
    do_search=st.button("검색",type="primary",use_container_width=True,
                        key="_insight_global_search_button")
if do_search and query.strip():
    st.session_state["query"]=query.strip()
    st.switch_page("stock_analyze.py")

with st.sidebar:
    st.divider()
    if st.button("🔒 로그아웃",key="_insight_logout",use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

page.run()
