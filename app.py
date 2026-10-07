import streamlit as st
import altair as alt
import os
import hmac
import re
import requests
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from html.parser import HTMLParser

st.set_page_config(page_title='HanaV ETF Finder', page_icon='🧭', layout='wide')

st.markdown('''
<style>
:root {color-scheme:light;--primary-color:#008878;--background-color:#F4F8F7;--secondary-background-color:#EDF5F2;--text-color:#203D35}
.stApp,[data-testid="stAppViewContainer"]{background:#F4F8F7;color:#203D35}
.block-container{max-width:1500px;padding-top:1rem}
header[data-testid="stHeader"]{background:#F4F8F7}
.hero{background:linear-gradient(105deg,#005B51 0%,#008878 65%,#DCEFE6 100%);border:1px solid #B8D6CA;border-left:6px solid #008878;padding:18px 22px;border-radius:10px;margin-bottom:14px;box-shadow:0 2px 8px rgba(20,65,47,.06)}
.hero h1{margin:0;color:white!important;font-size:30px}.hero p{margin:6px 0 0;color:#E5F3EE!important}
.step{background:linear-gradient(90deg,#DCEFE6,#F4F9F6);border:1px solid #C4DCD0;border-radius:9px;padding:10px 12px;margin:5px 0;color:#175447;font-weight:750}
.result{background:white;border:1px solid #CFDFD9;border-left:4px solid #008878;border-radius:9px;padding:12px;margin:8px 0}
.muted,[data-testid="stCaptionContainer"]{color:#60766E;font-size:12px}
h1,h2,h3,h4,[data-testid="stWidgetLabel"],[data-testid="stWidgetLabel"] p,[data-testid="stMarkdownContainer"]{color:#203D35}
section[data-testid="stSidebar"]{background:#EDF5F2;border-right:1px solid #CFDFD9}
[data-baseweb="input"],[data-baseweb="input"]>div,[data-baseweb="select"]>div,[data-baseweb="textarea"],[data-baseweb="popover"],[role="listbox"],[role="option"]{background:white!important;color:#203D35!important}
input,textarea,[data-baseweb="select"] span{color:#203D35!important;caret-color:#008878}
[data-baseweb="select"] svg{fill:#536F64}
.stButton>button[kind="secondary"],button[data-testid="stBaseButton-secondary"]{background:#FFFFFF!important;color:#205D4D!important;border:1px solid #C8DBD3!important;box-shadow:none!important}
.stButton>button[kind="secondary"]:hover,button[data-testid="stBaseButton-secondary"]:hover{background:#E5F2EC!important;color:#006F62!important;border-color:#008878!important}
.stButton>button[kind="primary"],button[data-testid="stBaseButton-primary"]{background:#008878!important;color:white!important;border:1px solid #008878!important;font-weight:750}
.stButton>button[kind="primary"] p{color:white!important}
.stButton>button[kind="primary"]:hover{background:#006F62!important}
[data-testid="stMetric"]{background:white;border:1px solid #D4E3DC;border-top:3px solid #008878;border-radius:9px;padding:12px}
[data-testid="stMetricLabel"],[data-testid="stMetricValue"]{color:#203D35}
[data-testid="stExpander"]{background:white;border:1px solid #CFDFD9;border-radius:9px}
[data-testid="stExpander"] summary{color:#203D35}
[data-baseweb="tab"]{color:#536F64}
[data-baseweb="tab"][aria-selected="true"]{background:#E3F1EB;color:#007B69}
[data-baseweb="tab-highlight"]{background:#008878}
[data-testid="stDataFrame"]{border:1px solid #CFDFD9;border-radius:7px;overflow:hidden}
hr{border-color:#D4E3DC}
</style>''', unsafe_allow_html=True)

# Password gate: configure APP_PASSWORD in this app's Streamlit Secrets.
def _etf_app_password():
    try:
        value = st.secrets.get('APP_PASSWORD', '')
        return value if isinstance(value, str) else ''
    except Exception:
        return ''


def _etf_check_password():
    expected = _etf_app_password()
    entered = str(st.session_state.get('_etf_password', ''))
    accepted = bool(expected) and hmac.compare_digest(
        entered.encode('utf-8'), expected.encode('utf-8')
    )
    st.session_state['_etf_authenticated'] = accepted
    st.session_state['_etf_login_error'] = not accepted
    st.session_state['_etf_password'] = ''


def _etf_logout():
    # Clear per-session selections and results together with authentication.
    for key in list(st.session_state):
        del st.session_state[key]


st.session_state.setdefault('_etf_authenticated', False)
st.session_state.setdefault('_etf_login_error', False)

if not _etf_app_password():
    st.error('APP_PASSWORD가 설정되지 않았습니다. 이 앱의 Streamlit Secrets에 APP_PASSWORD를 추가해 주세요.')
    st.stop()

if not st.session_state['_etf_authenticated']:
    st.markdown('''
    <div style="max-width:430px;margin:11vh auto 22px;text-align:center;">
      <div style="font-size:34px;font-weight:950;color:#008878;">HanaV ETF Finder</div>
      <div style="margin-top:7px;color:#536F64;font-size:13px;font-weight:650;">Private Investment Dashboard</div>
      <div style="margin-top:4px;color:#60766E;font-size:11px;">Designed &amp; Built by K.H. Ahn</div>
    </div>''', unsafe_allow_html=True)
    _login_left, _login_center, _login_right = st.columns([1, 1.15, 1])
    with _login_center:
        with st.form('_etf_login_form'):
            st.text_input('비밀번호', type='password', key='_etf_password',
                          placeholder='비밀번호를 입력하세요')
            st.form_submit_button('🔐 로그인', type='primary',
                                  use_container_width=True, on_click=_etf_check_password)
        if st.session_state.get('_etf_login_error', False):
            st.error('비밀번호가 올바르지 않습니다.')
    st.stop()

_login_spacer, _logout_col = st.columns([5, 1])
with _logout_col:
    st.button('🔒 로그아웃', key='_etf_logout_button',
              use_container_width=True, on_click=_etf_logout)


st.markdown('''<div class="hero"><h1>🧭 HanaV ETF Finder</h1><p>원하는 투자대상을 따라가면 조건에 맞는 ETF를 찾는 탐색 엔진 </p></div>''', unsafe_allow_html=True)

# 분류체계는 UI/데이터와 분리해 향후 DB 기반으로 교체 가능하게 둔다.
TREE = {
    '국내자산': {
        '주식': {
            '반도체':[
                '전체','메모리','HBM','AI 반도체','파운드리','팹리스',
                '반도체 장비','반도체 소재·부품','후공정·패키징','전력반도체'
            ],
            '2차전지':[
                '전체','배터리 셀','양극재','음극재','전해질','분리막',
                '동박','배터리 장비','폐배터리·리사이클링','ESS/BESS'
            ],
            'AI':[
                '전체','생성형 AI','AI 반도체','AI 소프트웨어','AI 플랫폼',
                'AI 인프라','데이터센터','클라우드','AI 전력수요'
            ],
            '로봇':[
                '전체','휴머노이드','협동로봇','산업용 로봇','서비스 로봇',
                '감속기','모터·액추에이터','센서·비전','로봇 자동화'
            ],
            '자동차·모빌리티':[
                '전체','완성차','전기차','자동차 부품','자율주행',
                'ADAS','전장','스마트카','수소차'
            ],
            '전력·전기기기':[
                '전체','변압기','배전기기','전선','전력망·그리드',
                '스마트그리드','전력 인프라','데이터센터 전력'
            ],
            '원전·에너지':[
                '전체','원전','SMR','원전 기자재','태양광','풍력',
                '수소','LNG','정유·석유화학','신재생에너지'
            ],
            '방산·우주항공':[
                '전체','방산','항공우주','미사일','지상무기','레이더·전자전',
                '위성','우주산업','조선·함정'
            ],
            '조선·해운':[
                '전체','조선','조선 기자재','LNG선','친환경 선박',
                '해운','물류','항만'
            ],
            '바이오·헬스케어':[
                '전체','제약','바이오','바이오시밀러','CDMO·CMO',
                '의료기기','진단','디지털헬스','비만·당뇨'
            ],
            '인터넷·플랫폼':[
                '전체','인터넷 플랫폼','검색·포털','핀테크',
                '이커머스','광고·마케팅','클라우드'
            ],
            '게임·콘텐츠':[
                '전체','게임','웹툰·웹소설','엔터테인먼트','K-POP',
                '미디어·방송','영화·드라마','콘텐츠 플랫폼'
            ],
            '금융':[
                '전체','은행','증권','보험','카드·결제','핀테크',
                '고배당 금융'
            ],
            '소비재':[
                '전체','화장품','면세','의류·패션','음식료',
                '유통','여행·레저','호텔','K-뷰티'
            ],
            '건설·인프라':[
                '전체','건설','건설기계','시멘트','철강',
                '인프라','스마트시티','데이터센터 인프라'
            ],
            '산업재·기계':[
                '전체','산업기계','공장자동화','스마트팩토리',
                '중공업','기계부품','플랜트'
            ],
            '화학·소재':[
                '전체','화학','정유','석유화학','철강','비철금속',
                '희토류','첨단소재'
            ],
            '운송·물류':[
                '전체','항공','해운','택배·물류','철도','모빌리티'
            ],
            '배당·가치':[
                '전체','고배당','저변동성','가치주','퀄리티',
                '주주환원','밸류업'
            ],
            '중소형·스타일':[
                '전체','코스피200','코스닥150','중소형주',
                '성장주','가치주','모멘텀','저변동성'
            ],
            '친환경·ESG':[
                '전체','ESG','탄소중립','친환경','수소',
                '재생에너지','전기차','자원순환'
            ],
            '농업·식품':[
                '전체','농업','비료','사료','식품','스마트팜'
            ],
        },
        '채권': {
            '국내채권':['전체','국고채','통안채','회사채','금융채','단기채','중기채','장기채','초장기채'],
            '채권전략':['전체','금리하락 수혜','금리상승 방어','듀레이션','크레딧','우량채','고금리채']
        },
        '원자재': {
            '귀금속':['전체','금','은'],
            '에너지':['전체','원유','천연가스'],
            '산업금속':['전체','구리','알루미늄','니켈','희토류'],
            '농산물':['전체','곡물','농산물']
        },
        '리츠': {
            '리츠':['전체','국내 리츠','오피스','물류센터','데이터센터','호텔·리조트','인프라']
        },
        '혼합자산': {
            '자산배분':['전체','주식+채권','인컴','타깃리스크','멀티에셋']
        }
    },

    '해외자산': {
        '주식': {
            '미국 대표지수':[
                '전체','S&P500','NASDAQ100','다우30','러셀2000',
                '미국 대형주','미국 중소형주'
            ],
            '글로벌·국가':[
                '전체','글로벌','미국','중국','일본','인도','베트남',
                '유럽','대만','신흥국','선진국'
            ],
            '빅테크':[
                '전체','Magnificent 7','플랫폼','클라우드','소프트웨어',
                '인터넷','전자상거래'
            ],
            'AI':[
                '전체','생성형 AI','AI 반도체','AI 소프트웨어','AI 플랫폼',
                'AI 인프라','데이터센터','클라우드','AI 전력수요'
            ],
            '반도체':[
                '전체','AI 반도체','메모리·HBM','파운드리','팹리스',
                '반도체 장비','반도체 소재','전력반도체'
            ],
            '로봇':[
                '전체','휴머노이드','산업용 로봇','서비스 로봇',
                '자동화','로봇 부품'
            ],
            '사이버보안':[
                '전체','사이버보안','클라우드 보안','네트워크 보안'
            ],
            '양자컴퓨팅':[
                '전체','양자컴퓨팅','양자통신','차세대 컴퓨팅'
            ],
            '우주·항공':[
                '전체','우주산업','위성','발사체','항공우주','드론'
            ],
            '방산':[
                '전체','미국 방산','글로벌 방산','항공우주 방산',
                '미사일·전자전'
            ],
            '원전·에너지':[
                '전체','원전','SMR','우라늄','태양광','풍력',
                '수소','석유·가스','LNG','신재생에너지'
            ],
            '전력·그리드':[
                '전체','전력망','변압기','스마트그리드',
                '전력 인프라','데이터센터 전력'
            ],
            '전기차·배터리':[
                '전체','전기차','배터리','리튬','배터리 소재',
                '충전 인프라','자율주행'
            ],
            '바이오·헬스케어':[
                '전체','바이오','제약','의료기기','유전체',
                '비만·당뇨','헬스케어 혁신'
            ],
            '금융·핀테크':[
                '전체','은행','보험','자산운용','핀테크',
                '디지털결제','블록체인'
            ],
            '소비·브랜드':[
                '전체','필수소비재','임의소비재','럭셔리',
                '여행·레저','음식료','글로벌 브랜드'
            ],
            '게임·메타버스':[
                '전체','게임','e스포츠','메타버스','디지털콘텐츠'
            ],
            '산업재·인프라':[
                '전체','산업재','건설','인프라','기계',
                '스마트팩토리','물류'
            ],
            '클린테크':[
                '전체','친환경','탄소중립','재생에너지',
                '수소','에너지저장','전기차'
            ],
            '배당·스타일':[
                '전체','고배당','배당성장','퀄리티','가치주',
                '성장주','모멘텀','저변동성'
            ],
        },
        '채권': {
            '미국 국채':['전체','초단기','단기','중기','장기','초장기','물가연동채'],
            '회사채':['전체','투자등급','하이일드','우량회사채'],
            '글로벌 채권':['전체','선진국 채권','신흥국 채권','글로벌 종합채권']
        },
        '원자재': {
            '귀금속':['전체','금','은'],
            '에너지':['전체','원유','천연가스'],
            '산업금속':['전체','구리','알루미늄','니켈','리튬','우라늄'],
            '농산물':['전체','곡물','농산물']
        },
        '리츠': {
            '글로벌 리츠':['전체','미국 리츠','글로벌 리츠','데이터센터','물류','주거','헬스케어','인프라']
        },
        '혼합자산': {
            '자산배분':['전체','주식+채권','인컴','멀티에셋','리스크패리티']
        }
    }
}


# =========================================================
# US-LISTED ETF CATALOG
# - 국내 KRX ETF DB와 별개로 미국 상장 대표 ETF를 테크트리에 통합 표시
# - 가격/상위 구성종목은 선택 시 yfinance로 조회 (API Key 불필요)
# =========================================================

US_ETF_CATALOG = [
    # 미국 대표지수
    {'ticker':'SPY','name':'SPDR S&P 500 ETF Trust','issuer':'State Street','index':'S&P 500','themes':[('주식','미국 대표지수',['S&P500','미국 대형주']),('주식','글로벌·국가',['미국'])]},
    {'ticker':'VOO','name':'Vanguard S&P 500 ETF','issuer':'Vanguard','index':'S&P 500','themes':[('주식','미국 대표지수',['S&P500','미국 대형주']),('주식','글로벌·국가',['미국'])]},
    {'ticker':'IVV','name':'iShares Core S&P 500 ETF','issuer':'BlackRock','index':'S&P 500','themes':[('주식','미국 대표지수',['S&P500','미국 대형주']),('주식','글로벌·국가',['미국'])]},
    {'ticker':'QQQ','name':'Invesco QQQ Trust','issuer':'Invesco','index':'NASDAQ-100','themes':[('주식','미국 대표지수',['NASDAQ100','미국 대형주']),('주식','빅테크',['전체']),('주식','글로벌·국가',['미국'])]},
    {'ticker':'QQQM','name':'Invesco NASDAQ 100 ETF','issuer':'Invesco','index':'NASDAQ-100','themes':[('주식','미국 대표지수',['NASDAQ100','미국 대형주']),('주식','빅테크',['전체'])]},
    {'ticker':'DIA','name':'SPDR Dow Jones Industrial Average ETF Trust','issuer':'State Street','index':'Dow Jones Industrial Average','themes':[('주식','미국 대표지수',['다우30','미국 대형주'])]},
    {'ticker':'IWM','name':'iShares Russell 2000 ETF','issuer':'BlackRock','index':'Russell 2000','themes':[('주식','미국 대표지수',['러셀2000','미국 중소형주'])]},
    {'ticker':'VTWO','name':'Vanguard Russell 2000 ETF','issuer':'Vanguard','index':'Russell 2000','themes':[('주식','미국 대표지수',['러셀2000','미국 중소형주'])]},
    {'ticker':'VTI','name':'Vanguard Total Stock Market ETF','issuer':'Vanguard','index':'CRSP US Total Market','themes':[('주식','미국 대표지수',['미국 대형주','미국 중소형주']),('주식','글로벌·국가',['미국'])]},

    # 글로벌 / 국가
    {'ticker':'VT','name':'Vanguard Total World Stock ETF','issuer':'Vanguard','index':'FTSE Global All Cap','themes':[('주식','글로벌·국가',['글로벌','선진국','신흥국'])]},
    {'ticker':'ACWI','name':'iShares MSCI ACWI ETF','issuer':'BlackRock','index':'MSCI ACWI','themes':[('주식','글로벌·국가',['글로벌','선진국','신흥국'])]},
    {'ticker':'EFA','name':'iShares MSCI EAFE ETF','issuer':'BlackRock','index':'MSCI EAFE','themes':[('주식','글로벌·국가',['선진국'])]},
    {'ticker':'EEM','name':'iShares MSCI Emerging Markets ETF','issuer':'BlackRock','index':'MSCI Emerging Markets','themes':[('주식','글로벌·국가',['신흥국'])]},
    {'ticker':'MCHI','name':'iShares MSCI China ETF','issuer':'BlackRock','index':'MSCI China','themes':[('주식','글로벌·국가',['중국'])]},
    {'ticker':'FXI','name':'iShares China Large-Cap ETF','issuer':'BlackRock','index':'FTSE China 50','themes':[('주식','글로벌·국가',['중국'])]},
    {'ticker':'EWJ','name':'iShares MSCI Japan ETF','issuer':'BlackRock','index':'MSCI Japan','themes':[('주식','글로벌·국가',['일본'])]},
    {'ticker':'INDA','name':'iShares MSCI India ETF','issuer':'BlackRock','index':'MSCI India','themes':[('주식','글로벌·국가',['인도'])]},
    {'ticker':'VNM','name':'VanEck Vietnam ETF','issuer':'VanEck','index':'MarketVector Vietnam Local','themes':[('주식','글로벌·국가',['베트남'])]},
    {'ticker':'VGK','name':'Vanguard FTSE Europe ETF','issuer':'Vanguard','index':'FTSE Developed Europe','themes':[('주식','글로벌·국가',['유럽','선진국'])]},
    {'ticker':'EWT','name':'iShares MSCI Taiwan ETF','issuer':'BlackRock','index':'MSCI Taiwan 25/50','themes':[('주식','글로벌·국가',['대만'])]},

    # 빅테크 / AI / 반도체
    {'ticker':'MAGS','name':'Roundhill Magnificent Seven ETF','issuer':'Roundhill','index':'Magnificent Seven','themes':[('주식','빅테크',['Magnificent 7','플랫폼']),('주식','AI',['AI 플랫폼'])]},
    {'ticker':'XLK','name':'Technology Select Sector SPDR Fund','issuer':'State Street','index':'S&P Technology Select Sector','themes':[('주식','빅테크',['소프트웨어','플랫폼']),('주식','AI',['AI 소프트웨어'])]},
    {'ticker':'VGT','name':'Vanguard Information Technology ETF','issuer':'Vanguard','index':'MSCI US IMI Information Technology 25/50','themes':[('주식','빅테크',['소프트웨어','플랫폼']),('주식','AI',['AI 소프트웨어'])]},
    {'ticker':'IGV','name':'iShares Expanded Tech-Software Sector ETF','issuer':'BlackRock','index':'S&P North American Expanded Technology Software','themes':[('주식','빅테크',['소프트웨어']),('주식','AI',['AI 소프트웨어'])]},
    {'ticker':'SKYY','name':'First Trust Cloud Computing ETF','issuer':'First Trust','index':'ISE CTA Cloud Computing','themes':[('주식','빅테크',['클라우드']),('주식','AI',['클라우드','AI 인프라'])]},
    {'ticker':'AIQ','name':'Global X Artificial Intelligence & Technology ETF','issuer':'Global X','index':'Indxx Artificial Intelligence & Big Data','themes':[('주식','AI',['생성형 AI','AI 소프트웨어','AI 플랫폼','AI 인프라'])]},
    {'ticker':'IRBO','name':'iShares Robotics and Artificial Intelligence Multisector ETF','issuer':'BlackRock','index':'NYSE FactSet Global Robotics and AI','themes':[('주식','AI',['생성형 AI','AI 소프트웨어']),('주식','로봇',['산업용 로봇','서비스 로봇','자동화'])]},
    {'ticker':'SMH','name':'VanEck Semiconductor ETF','issuer':'VanEck','index':'MVIS US Listed Semiconductor 25','themes':[('주식','반도체',['AI 반도체','파운드리','팹리스','반도체 장비'])]},
    {'ticker':'SOXX','name':'iShares Semiconductor ETF','issuer':'BlackRock','index':'NYSE Semiconductor','themes':[('주식','반도체',['AI 반도체','파운드리','팹리스','반도체 장비'])]},
    {'ticker':'SOXQ','name':'Invesco PHLX Semiconductor ETF','issuer':'Invesco','index':'PHLX Semiconductor Sector','themes':[('주식','반도체',['AI 반도체','파운드리','팹리스','반도체 장비'])]},
    {'ticker':'XSD','name':'SPDR S&P Semiconductor ETF','issuer':'State Street','index':'S&P Semiconductor Select Industry','themes':[('주식','반도체',['AI 반도체','팹리스','반도체 장비'])]},

    # 로봇 / 보안 / 양자 / 우주 / 방산
    {'ticker':'BOTZ','name':'Global X Robotics & Artificial Intelligence ETF','issuer':'Global X','index':'Indxx Global Robotics & AI Thematic','themes':[('주식','로봇',['산업용 로봇','서비스 로봇','자동화','로봇 부품']),('주식','AI',['AI 인프라'])]},
    {'ticker':'ROBO','name':'ROBO Global Robotics and Automation Index ETF','issuer':'ROBO Global','index':'ROBO Global Robotics and Automation','themes':[('주식','로봇',['산업용 로봇','서비스 로봇','자동화','로봇 부품'])]},
    {'ticker':'CIBR','name':'First Trust NASDAQ Cybersecurity ETF','issuer':'First Trust','index':'Nasdaq CTA Cybersecurity','themes':[('주식','사이버보안',['사이버보안','클라우드 보안','네트워크 보안'])]},
    {'ticker':'HACK','name':'Amplify Cybersecurity ETF','issuer':'Amplify','index':'ETFMG Prime Cyber Security','themes':[('주식','사이버보안',['사이버보안','클라우드 보안','네트워크 보안'])]},
    {'ticker':'QTUM','name':'Defiance Quantum ETF','issuer':'Defiance','index':'BlueStar Machine Learning and Quantum Computing','themes':[('주식','양자컴퓨팅',['양자컴퓨팅','차세대 컴퓨팅'])]},
    {'ticker':'ARKX','name':'ARK Space Exploration & Innovation ETF','issuer':'ARK Invest','index':'Active','themes':[('주식','우주·항공',['우주산업','위성','발사체','항공우주','드론'])]},
    {'ticker':'UFO','name':'Procure Space ETF','issuer':'ProcureAM','index':'S-Network Space','themes':[('주식','우주·항공',['우주산업','위성','발사체','항공우주'])]},
    {'ticker':'ITA','name':'iShares U.S. Aerospace & Defense ETF','issuer':'BlackRock','index':'Dow Jones U.S. Select Aerospace & Defense','themes':[('주식','방산',['미국 방산','항공우주 방산','미사일·전자전'])]},
    {'ticker':'XAR','name':'SPDR S&P Aerospace & Defense ETF','issuer':'State Street','index':'S&P Aerospace & Defense Select Industry','themes':[('주식','방산',['미국 방산','항공우주 방산','미사일·전자전'])]},
    {'ticker':'PPA','name':'Invesco Aerospace & Defense ETF','issuer':'Invesco','index':'SPADE Defense','themes':[('주식','방산',['미국 방산','항공우주 방산'])]},

    # 에너지 / 전력 / EV
    {'ticker':'URA','name':'Global X Uranium ETF','issuer':'Global X','index':'Solactive Global Uranium & Nuclear Components','themes':[('주식','원전·에너지',['원전','우라늄']),('원자재','산업금속',['우라늄'])]},
    {'ticker':'URNM','name':'Sprott Uranium Miners ETF','issuer':'Sprott','index':'North Shore Global Uranium Mining','themes':[('주식','원전·에너지',['원전','우라늄']),('원자재','산업금속',['우라늄'])]},
    {'ticker':'NLR','name':'VanEck Uranium and Nuclear ETF','issuer':'VanEck','index':'MVIS Global Uranium & Nuclear Energy','themes':[('주식','원전·에너지',['원전','우라늄'])]},
    {'ticker':'TAN','name':'Invesco Solar ETF','issuer':'Invesco','index':'MAC Global Solar Energy','themes':[('주식','원전·에너지',['태양광','신재생에너지']),('주식','클린테크',['재생에너지','친환경'])]},
    {'ticker':'FAN','name':'First Trust Global Wind Energy ETF','issuer':'First Trust','index':'ISE Clean Edge Global Wind Energy','themes':[('주식','원전·에너지',['풍력','신재생에너지']),('주식','클린테크',['재생에너지','친환경'])]},
    {'ticker':'ICLN','name':'iShares Global Clean Energy ETF','issuer':'BlackRock','index':'S&P Global Clean Energy Transition','themes':[('주식','원전·에너지',['신재생에너지']),('주식','클린테크',['친환경','탄소중립','재생에너지'])]},
    {'ticker':'XLE','name':'Energy Select Sector SPDR Fund','issuer':'State Street','index':'S&P Energy Select Sector','themes':[('주식','원전·에너지',['석유·가스','LNG'])]},
    {'ticker':'GRID','name':'First Trust NASDAQ Clean Edge Smart Grid Infrastructure ETF','issuer':'First Trust','index':'Nasdaq OMX Clean Edge Smart Grid Infrastructure','themes':[('주식','전력·그리드',['전력망','스마트그리드','전력 인프라','데이터센터 전력'])]},
    {'ticker':'PAVE','name':'Global X U.S. Infrastructure Development ETF','issuer':'Global X','index':'Indxx U.S. Infrastructure Development','themes':[('주식','산업재·인프라',['산업재','건설','인프라']),('주식','전력·그리드',['전력 인프라'])]},
    {'ticker':'DRIV','name':'Global X Autonomous & Electric Vehicles ETF','issuer':'Global X','index':'Solactive Autonomous & Electric Vehicles','themes':[('주식','전기차·배터리',['전기차','자율주행','충전 인프라'])]},
    {'ticker':'LIT','name':'Global X Lithium & Battery Tech ETF','issuer':'Global X','index':'Solactive Global Lithium','themes':[('주식','전기차·배터리',['배터리','리튬','배터리 소재']),('원자재','산업금속',['리튬'])]},
    {'ticker':'BATT','name':'Amplify Lithium & Battery Technology ETF','issuer':'Amplify','index':'EQM Lithium & Battery Technology','themes':[('주식','전기차·배터리',['배터리','리튬','배터리 소재'])]},

    # 헬스케어 / 금융 / 소비 / 게임 / 산업재
    {'ticker':'XLV','name':'Health Care Select Sector SPDR Fund','issuer':'State Street','index':'S&P Health Care Select Sector','themes':[('주식','바이오·헬스케어',['헬스케어 혁신','제약','의료기기'])]},
    {'ticker':'IBB','name':'iShares Biotechnology ETF','issuer':'BlackRock','index':'ICE Biotechnology','themes':[('주식','바이오·헬스케어',['바이오','유전체'])]},
    {'ticker':'XBI','name':'SPDR S&P Biotech ETF','issuer':'State Street','index':'S&P Biotechnology Select Industry','themes':[('주식','바이오·헬스케어',['바이오','유전체'])]},
    {'ticker':'IHI','name':'iShares U.S. Medical Devices ETF','issuer':'BlackRock','index':'Dow Jones U.S. Select Medical Equipment','themes':[('주식','바이오·헬스케어',['의료기기'])]},
    {'ticker':'XLF','name':'Financial Select Sector SPDR Fund','issuer':'State Street','index':'S&P Financial Select Sector','themes':[('주식','금융·핀테크',['은행','보험','자산운용'])]},
    {'ticker':'KBE','name':'SPDR S&P Bank ETF','issuer':'State Street','index':'S&P Banks Select Industry','themes':[('주식','금융·핀테크',['은행'])]},
    {'ticker':'KRE','name':'SPDR S&P Regional Banking ETF','issuer':'State Street','index':'S&P Regional Banks Select Industry','themes':[('주식','금융·핀테크',['은행'])]},
    {'ticker':'FINX','name':'Global X FinTech ETF','issuer':'Global X','index':'Indxx Global FinTech Thematic','themes':[('주식','금융·핀테크',['핀테크','디지털결제'])]},
    {'ticker':'BLOK','name':'Amplify Transformational Data Sharing ETF','issuer':'Amplify','index':'Active','themes':[('주식','금융·핀테크',['블록체인'])]},
    {'ticker':'XLP','name':'Consumer Staples Select Sector SPDR Fund','issuer':'State Street','index':'S&P Consumer Staples Select Sector','themes':[('주식','소비·브랜드',['필수소비재','음식료','글로벌 브랜드'])]},
    {'ticker':'XLY','name':'Consumer Discretionary Select Sector SPDR Fund','issuer':'State Street','index':'S&P Consumer Discretionary Select Sector','themes':[('주식','소비·브랜드',['임의소비재','여행·레저','글로벌 브랜드'])]},
    {'ticker':'ESPO','name':'VanEck Video Gaming and eSports ETF','issuer':'VanEck','index':'MVIS Global Video Gaming & eSports','themes':[('주식','게임·메타버스',['게임','e스포츠','디지털콘텐츠'])]},
    {'ticker':'HERO','name':'Global X Video Games & Esports ETF','issuer':'Global X','index':'Solactive Video Games & Esports','themes':[('주식','게임·메타버스',['게임','e스포츠','디지털콘텐츠'])]},
    {'ticker':'METV','name':'Roundhill Ball Metaverse ETF','issuer':'Roundhill','index':'Ball Metaverse','themes':[('주식','게임·메타버스',['메타버스','디지털콘텐츠'])]},
    {'ticker':'XLI','name':'Industrial Select Sector SPDR Fund','issuer':'State Street','index':'S&P Industrial Select Sector','themes':[('주식','산업재·인프라',['산업재','기계','인프라'])]},

    # 배당 / 스타일
    {'ticker':'SCHD','name':'Schwab U.S. Dividend Equity ETF','issuer':'Schwab','index':'Dow Jones U.S. Dividend 100','themes':[('주식','배당·스타일',['고배당','배당성장','퀄리티'])]},
    {'ticker':'VIG','name':'Vanguard Dividend Appreciation ETF','issuer':'Vanguard','index':'S&P U.S. Dividend Growers','themes':[('주식','배당·스타일',['배당성장','퀄리티'])]},
    {'ticker':'DGRO','name':'iShares Core Dividend Growth ETF','issuer':'BlackRock','index':'Morningstar US Dividend Growth','themes':[('주식','배당·스타일',['배당성장','퀄리티'])]},
    {'ticker':'VTV','name':'Vanguard Value ETF','issuer':'Vanguard','index':'CRSP US Large Cap Value','themes':[('주식','배당·스타일',['가치주'])]},
    {'ticker':'VUG','name':'Vanguard Growth ETF','issuer':'Vanguard','index':'CRSP US Large Cap Growth','themes':[('주식','배당·스타일',['성장주'])]},
    {'ticker':'QUAL','name':'iShares MSCI USA Quality Factor ETF','issuer':'BlackRock','index':'MSCI USA Sector Neutral Quality','themes':[('주식','배당·스타일',['퀄리티'])]},
    {'ticker':'MTUM','name':'iShares MSCI USA Momentum Factor ETF','issuer':'BlackRock','index':'MSCI USA Momentum SR Variant','themes':[('주식','배당·스타일',['모멘텀'])]},
    {'ticker':'USMV','name':'iShares MSCI USA Min Vol Factor ETF','issuer':'BlackRock','index':'MSCI USA Minimum Volatility','themes':[('주식','배당·스타일',['저변동성'])]},

    # 미국채 / 회사채 / 글로벌채
    {'ticker':'SGOV','name':'iShares 0-3 Month Treasury Bond ETF','issuer':'BlackRock','index':'ICE 0-3 Month US Treasury Securities','themes':[('채권','미국 국채',['초단기'])]},
    {'ticker':'BIL','name':'SPDR Bloomberg 1-3 Month T-Bill ETF','issuer':'State Street','index':'Bloomberg 1-3 Month U.S. Treasury Bill','themes':[('채권','미국 국채',['초단기'])]},
    {'ticker':'SHY','name':'iShares 1-3 Year Treasury Bond ETF','issuer':'BlackRock','index':'ICE U.S. Treasury 1-3 Year','themes':[('채권','미국 국채',['단기'])]},
    {'ticker':'IEF','name':'iShares 7-10 Year Treasury Bond ETF','issuer':'BlackRock','index':'ICE U.S. Treasury 7-10 Year','themes':[('채권','미국 국채',['중기'])]},
    {'ticker':'TLT','name':'iShares 20+ Year Treasury Bond ETF','issuer':'BlackRock','index':'ICE U.S. Treasury 20+ Year','themes':[('채권','미국 국채',['장기','초장기'])]},
    {'ticker':'EDV','name':'Vanguard Extended Duration Treasury ETF','issuer':'Vanguard','index':'Bloomberg US Treasury STRIPS 20-30 Year Equal Par Bond','themes':[('채권','미국 국채',['초장기'])]},
    {'ticker':'TIP','name':'iShares TIPS Bond ETF','issuer':'BlackRock','index':'ICE U.S. Treasury Inflation Linked','themes':[('채권','미국 국채',['물가연동채'])]},
    {'ticker':'LQD','name':'iShares iBoxx $ Investment Grade Corporate Bond ETF','issuer':'BlackRock','index':'Markit iBoxx USD Liquid Investment Grade','themes':[('채권','회사채',['투자등급','우량회사채'])]},
    {'ticker':'HYG','name':'iShares iBoxx $ High Yield Corporate Bond ETF','issuer':'BlackRock','index':'Markit iBoxx USD Liquid High Yield','themes':[('채권','회사채',['하이일드'])]},
    {'ticker':'EMB','name':'iShares J.P. Morgan USD Emerging Markets Bond ETF','issuer':'BlackRock','index':'J.P. Morgan EMBI Global Core','themes':[('채권','글로벌 채권',['신흥국 채권'])]},
    {'ticker':'BNDW','name':'Vanguard Total World Bond ETF','issuer':'Vanguard','index':'Bloomberg Global Aggregate Float Adjusted Composite','themes':[('채권','글로벌 채권',['글로벌 종합채권','선진국 채권'])]},

    # 원자재 / 리츠 / 자산배분
    {'ticker':'GLD','name':'SPDR Gold Shares','issuer':'State Street','index':'Gold Bullion','themes':[('원자재','귀금속',['금'])]},
    {'ticker':'IAU','name':'iShares Gold Trust','issuer':'BlackRock','index':'Gold Bullion','themes':[('원자재','귀금속',['금'])]},
    {'ticker':'SLV','name':'iShares Silver Trust','issuer':'BlackRock','index':'Silver Bullion','themes':[('원자재','귀금속',['은'])]},
    {'ticker':'USO','name':'United States Oil Fund','issuer':'USCF','index':'WTI Crude Oil Futures','themes':[('원자재','에너지',['원유'])]},
    {'ticker':'UNG','name':'United States Natural Gas Fund','issuer':'USCF','index':'Natural Gas Futures','themes':[('원자재','에너지',['천연가스'])]},
    {'ticker':'CPER','name':'United States Copper Index Fund','issuer':'USCF','index':'SummerHaven Copper Index','themes':[('원자재','산업금속',['구리'])]},
    {'ticker':'DBA','name':'Invesco DB Agriculture Fund','issuer':'Invesco','index':'DBIQ Diversified Agriculture','themes':[('원자재','농산물',['곡물','농산물'])]},
    {'ticker':'VNQ','name':'Vanguard Real Estate ETF','issuer':'Vanguard','index':'MSCI US Investable Market Real Estate 25/50','themes':[('리츠','글로벌 리츠',['미국 리츠'])]},
    {'ticker':'REET','name':'iShares Global REIT ETF','issuer':'BlackRock','index':'FTSE EPRA Nareit Global REITs','themes':[('리츠','글로벌 리츠',['글로벌 리츠','미국 리츠'])]},
    {'ticker':'AOR','name':'iShares Core Growth Allocation ETF','issuer':'BlackRock','index':'S&P Target Risk Growth','themes':[('혼합자산','자산배분',['주식+채권','멀티에셋'])]},
    {'ticker':'AOM','name':'iShares Core Moderate Allocation ETF','issuer':'BlackRock','index':'S&P Target Risk Moderate','themes':[('혼합자산','자산배분',['주식+채권','멀티에셋'])]},
    {'ticker':'RPAR','name':'RPAR Risk Parity ETF','issuer':'RPAR','index':'Risk Parity','themes':[('혼합자산','자산배분',['리스크패리티','멀티에셋'])]},
]


def _normalize_etf_identifier(value):
    s=str(value or '').strip()
    if s.isdigit():
        return s.zfill(6)
    return s.upper()


def _is_krx_etf_identifier(value):
    s=str(value or '').strip()
    return s.isdigit()


def _us_catalog_rows():
    rows=[]
    for rank,item in enumerate(US_ETF_CATALOG,1):
        for asset,sector,subs in item.get('themes',[]):
            rows.append({
                'etf_name':item['name'],
                'etf_code':item['ticker'],
                'issuer':item.get('issuer',''),
                'aum':None,
                'turnover':None,
                'fee':None,
                'index_name':item.get('index',''),
                'as_of':'실시간 조회',
                'theme_score':25.0,
                'match_evidence':'미국상장 ETF 테마 분류',
                'listing_market':'미국',
                '_asset':asset,
                '_sector':sector,
                '_subs':subs,
                '_rank':rank,
            })
    return pd.DataFrame(rows)


def search_us_etf_catalog(region,asset,sector,subsector):
    if region!='해외자산':
        return pd.DataFrame()
    df=_us_catalog_rows()
    if df.empty:
        return pd.DataFrame()
    q=df[(df['_asset']==asset)&(df['_sector']==sector)].copy()
    if subsector!='전체':
        q=q[q['_subs'].apply(lambda xs: subsector in (xs or []))]
    if q.empty:
        return pd.DataFrame()
    q=q.sort_values(['_rank','etf_code']).drop_duplicates('etf_code',keep='first')
    return q[[
        'etf_name','etf_code','issuer','aum','turnover','fee','index_name','as_of',
        'theme_score','match_evidence','listing_market'
    ]].reset_index(drop=True)


def get_us_etf_catalog_item(ticker):
    t=str(ticker or '').strip().upper()
    for item in US_ETF_CATALOG:
        if item.get('ticker','').upper()==t:
            return dict(item)
    return {}


@st.cache_data(ttl=3600,show_spinner=False)
def search_us_etf_yahoo(query_text):
    """Yahoo/yfinance 검색으로 카탈로그 밖 미국상장 ETF도 빠른검색에 보완."""
    key=str(query_text or '').strip()
    if not key:
        return pd.DataFrame()
    try:
        yf=_import_yfinance()
        quotes=yf.Search(
            key,max_results=20,news_count=0,lists_count=0,
            include_cb=False,include_nav_links=False,include_research=False,
            enable_fuzzy_query=True,raise_errors=False
        ).quotes
    except Exception:
        return pd.DataFrame()

    rows=[]
    us_exchange_codes={'NMS','NGM','NCM','NYQ','PCX','ASE','BTS','NAS','NYSE','NASDAQ','ARCA'}
    for q in quotes or []:
        if str(q.get('quoteType','')).upper()!='ETF':
            continue
        symbol=str(q.get('symbol','')).strip().upper()
        exch=str(q.get('exchange','')).strip().upper()
        exch_disp=str(q.get('exchDisp','')).strip()
        if not symbol:
            continue
        is_us=(exch in us_exchange_codes) or any(x in exch_disp.lower() for x in ['nasdaq','nyse','arca','cboe'])
        if not is_us:
            continue
        name=str(q.get('longname') or q.get('shortname') or symbol).strip()
        rows.append({
            'etf_name':name,'etf_code':symbol,'issuer':'','aum':None,'turnover':None,
            'fee':None,'index_name':'','as_of':'Yahoo 검색','listing_market':'미국'
        })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).drop_duplicates('etf_code',keep='first').reset_index(drop=True)


def search_etf_direct(query_text):
    """ETF 자체를 코드/티커/이름으로 빠르게 검색: KRX 로컬 DB + 미국상장 대표 ETF."""
    key=str(query_text or '').strip()
    if not key:
        return pd.DataFrame()
    key_n=key.lower().replace(' ','')
    parts=[]

    # KRX 로컬 ETF
    if db_available():
        try:
            m=load_master_db(db_token()).copy()
            if not m.empty:
                code_s=m['etf_code'].fillna('').astype(str)
                name_s=m['etf_name'].fillna('').astype(str)
                mask=(
                    code_s.str.lower().str.replace(' ','',regex=False).str.contains(key_n,regex=False)
                    | name_s.str.lower().str.replace(' ','',regex=False).str.contains(key_n,regex=False)
                )
                k=m.loc[mask,[c for c in ['etf_name','etf_code','issuer','aum','turnover','fee','index_name','as_of'] if c in m.columns]].copy()
                if not k.empty:
                    k['listing_market']='KRX'
                    parts.append(k.head(50))
        except Exception:
            pass

    # 미국상장 ETF 카탈로그
    us=[]
    for rank,item in enumerate(US_ETF_CATALOG,1):
        hay=f"{item.get('ticker','')} {item.get('name','')} {item.get('issuer','')} {item.get('index','')}".lower().replace(' ','')
        if key_n in hay:
            us.append({
                'etf_name':item['name'],'etf_code':item['ticker'],'issuer':item.get('issuer',''),
                'aum':None,'turnover':None,'fee':None,'index_name':item.get('index',''),
                'as_of':'실시간 조회','listing_market':'미국','_rank':rank
            })
    if us:
        u=pd.DataFrame(us).sort_values('_rank').drop(columns=['_rank'])
        parts.append(u)

    # 카탈로그에 없는 미국 ETF도 yfinance Search로 보완
    try:
        live_us=search_us_etf_yahoo(key)
        if isinstance(live_us,pd.DataFrame) and not live_us.empty:
            parts.append(live_us)
    except Exception:
        pass

    if not parts:
        return pd.DataFrame()
    out=pd.concat(parts,ignore_index=True,sort=False)
    out=out.drop_duplicates(subset=['listing_market','etf_code'],keep='first')
    # 티커/코드 정확일치를 맨 위로
    code_norm=out['etf_code'].fillna('').astype(str).str.lower()
    out['_exact']=(code_norm==key.lower()).astype(int)
    out=out.sort_values(['_exact','listing_market','etf_name'],ascending=[False,True,True]).drop(columns=['_exact'])
    return out.reset_index(drop=True)


def _import_yfinance():
    try:
        import yfinance as yf
        return yf
    except ModuleNotFoundError as e:
        raise RuntimeError(
            '미국상장 ETF 조회에는 yfinance가 필요합니다. '
            'requirements.txt에 yfinance>=0.2.50 을 추가한 뒤 Streamlit Cloud를 재부팅해 주세요.'
        ) from e


@st.cache_data(ttl=1800,show_spinner=False)
def get_us_etf_price_history(ticker,period_label):
    yf=_import_yfinance()
    period_map={'1개월':'1mo','3개월':'3mo','6개월':'6mo','1년':'1y'}
    t=yf.Ticker(str(ticker).upper())
    df=t.history(period=period_map.get(period_label,'6mo'),auto_adjust=False)
    if df is None or df.empty or 'Close' not in df.columns:
        return pd.DataFrame()
    out=df.reset_index().copy()
    date_col='Date' if 'Date' in out.columns else out.columns[0]
    out[date_col]=pd.to_datetime(out[date_col],errors='coerce')
    out['Close']=pd.to_numeric(out['Close'],errors='coerce')
    out=out.dropna(subset=[date_col,'Close'])
    return out.rename(columns={date_col:'날짜','Close':'종가'})[['날짜','종가']]


@st.cache_data(ttl=21600,show_spinner=False)
def get_us_etf_holdings(ticker):
    yf=_import_yfinance()
    t=yf.Ticker(str(ticker).upper())
    try:
        funds=t.funds_data
        top=funds.top_holdings if funds is not None else None
    except Exception as e:
        return {'rows':[],'error':str(e)}

    if top is None or getattr(top,'empty',True):
        return {'rows':[],'error':'상위 구성종목 데이터가 비어 있습니다.'}

    df=top.copy().reset_index()
    # yfinance 표준 형태: index=Symbol, columns=['Name','Holding Percent']
    symbol_col=None
    for c in ['Symbol','symbol','index']:
        if c in df.columns:
            symbol_col=c; break
    if symbol_col is None:
        symbol_col=df.columns[0]
    name_col='Name' if 'Name' in df.columns else None
    weight_col='Holding Percent' if 'Holding Percent' in df.columns else None
    if weight_col is None:
        for c in df.columns:
            if 'holding' in str(c).lower() and 'percent' in str(c).lower():
                weight_col=c; break
    if name_col is None:
        name_col=symbol_col
    if weight_col is None:
        return {'rows':[],'error':f'구성비중 컬럼을 찾지 못했습니다: {list(df.columns)}'}

    out=pd.DataFrame({
        '종목코드':df[symbol_col].astype(str),
        '구성종목':df[name_col].astype(str),
        '비중(%)':pd.to_numeric(df[weight_col],errors='coerce')
    }).dropna(subset=['비중(%)'])
    if not out.empty and float(out['비중(%)'].max())<=1.0:
        out['비중(%)']=out['비중(%)']*100.0
    out=out.sort_values('비중(%)',ascending=False).reset_index(drop=True)
    return {'rows':out.to_dict('records'),'error':''}


def render_us_etf_detail(ticker,key_prefix='us_detail'):
    code=str(ticker or '').strip().upper()
    meta=get_us_etf_catalog_item(code)
    etf_name=meta.get('name') or st.session_state.get('selected_etf_name') or code

    st.markdown('---')
    st.subheader(f'🇺🇸 {etf_name} · {code}')
    st.caption('미국 상장 ETF · 가격과 상위 구성종목은 Yahoo Finance/yfinance 공개 데이터를 선택 시 조회합니다.')

    info_cols=st.columns(4)
    info_cols[0].metric('티커',code)
    info_cols[1].metric('상장시장','미국')
    info_cols[2].metric('운용사',str(meta.get('issuer') or '-')[:22])
    info_cols[3].metric('추종지수',str(meta.get('index') or '-')[:28])

    chart_col,holding_col=st.columns([1.35,1],gap='large')
    with chart_col:
        st.markdown('#### 가격 차트')
        period=st.radio(
            '조회기간',['1개월','3개월','6개월','1년'],index=2,horizontal=True,
            key=f'{key_prefix}_period_{code}'
        )
        try:
            with st.spinner(f'{code} 가격 데이터를 불러오는 중...'):
                p=get_us_etf_price_history(code,period)
            if p.empty:
                st.info('해당 기간의 가격 데이터를 불러오지 못했습니다.')
            else:
                p=p.dropna().sort_values('날짜')
                last=float(p['종가'].iloc[-1])
                prev=float(p['종가'].iloc[-2]) if len(p)>=2 else last
                change=((last/prev)-1)*100 if prev else 0.0
                m1,m2=st.columns(2)
                m1.metric('최근 종가',f'${last:,.2f}',f'{change:+.2f}%')
                m2.metric('조회 데이터',f'{len(p):,}일')
                st.altair_chart(
                    alt.Chart(p).mark_line(color='#008878').encode(
                        x=alt.X('날짜:T',title='날짜'),
                        y=alt.Y('종가:Q',title='종가 (USD)',scale=alt.Scale(zero=False)),
                        tooltip=[alt.Tooltip('날짜:T'),alt.Tooltip('종가:Q',format=',.2f')]
                    ).properties(height=390,background='white').configure_axis(
                        labelColor='#536F64',titleColor='#203D35',gridColor='#E1EBE6'
                    ).configure_view(stroke='#CFDFD9').interactive(),
                    use_container_width=True,theme=None
                )
                st.caption(f"{p['날짜'].min():%Y-%m-%d} ~ {p['날짜'].max():%Y-%m-%d} · USD")
        except Exception as e:
            st.warning(f'미국 ETF 가격 조회 실패: {e}')

    with holding_col:
        st.markdown('#### 주요 구성종목')
        try:
            with st.spinner(f'{code} 상위 구성종목을 불러오는 중...'):
                h=get_us_etf_holdings(code)
            rows=h.get('rows') or []
            if not rows:
                st.info('상위 구성종목을 불러오지 못했습니다.')
                if h.get('error'):
                    st.caption(f"조회 오류: {h.get('error')}")
            else:
                hd=pd.DataFrame(rows)
                top=hd.head(10).copy()
                st.altair_chart(
                    alt.Chart(top).mark_bar(color='#008878').encode(
                        x=alt.X('구성종목:N',sort='-y',title='구성종목'),
                        y=alt.Y('비중(%):Q',title='편입비중 (%)'),
                        tooltip=['종목코드','구성종목',alt.Tooltip('비중(%):Q',format='.2f')]
                    ).properties(height=300,background='white').configure_axis(
                        labelColor='#536F64',titleColor='#203D35',gridColor='#E1EBE6'
                    ).configure_view(stroke='#CFDFD9'),
                    use_container_width=True,theme=None
                )
                st.dataframe(
                    hd,use_container_width=True,hide_index=True,height=420,
                    column_config={'비중(%)':st.column_config.NumberColumn(format='%.2f%%')}
                )
                st.caption('Yahoo Finance/yfinance 상위 구성종목 · 데이터 제공 범위 내 표시')
        except Exception as e:
            st.warning(f'미국 ETF 구성종목 조회 실패: {e}')


# =========================================================
# AUTO THEME MAPPING
# ETF명 + 추종지수 + 구성종목명/비중을 이용한 로컬 규칙 기반 자동 매핑
# =========================================================

THEME_RULES_VERSION='2026-09-30-v2'

THEME_KEYWORDS={
    '반도체':['반도체','semiconductor','semicon','chip','sox'],
    '메모리':['메모리','memory','dram','nand'],
    'HBM':['hbm','high bandwidth memory'],
    'AI 반도체':['ai반도체','ai semiconductor','gpu','npu','accelerator','엔비디아','nvidia'],
    '파운드리':['파운드리','foundry','tsmc'],
    '팹리스':['팹리스','fabless'],
    '반도체 장비':['반도체장비','semiconductor equipment','asml','한미반도체','hpsp','원익ips','유진테크','주성엔지니어링'],
    '반도체 소재·부품':['반도체소재','반도체부품','소부장','wafer','웨이퍼','솔브레인','isc'],
    '후공정·패키징':['후공정','패키징','packaging','osat','테스트소켓','test socket'],
    '전력반도체':['전력반도체','power semiconductor','sic','gan'],

    '2차전지':['2차전지','이차전지','배터리','battery','리튬','lithium'],
    '배터리 셀':['배터리셀','battery cell','lg에너지솔루션','삼성sdi','sk온'],
    '양극재':['양극재','cathode','에코프로비엠','포스코퓨처엠','엘앤에프'],
    '음극재':['음극재','anode'],
    '전해질':['전해질','electrolyte'],
    '분리막':['분리막','separator'],
    '동박':['동박','copper foil','skc'],
    '배터리 장비':['배터리장비','battery equipment','피엔티','윤성에프앤씨'],
    '폐배터리·리사이클링':['폐배터리','리사이클','recycling','recycle'],
    'ESS/BESS':['ess','bess','에너지저장','energy storage'],

    'AI':['인공지능','artificial intelligence','generative ai','생성형ai','ai반도체','ai소프트웨어','ai플랫폼','ai인프라'],
    '생성형 AI':['생성형ai','generative ai','llm','chatgpt'],
    'AI 소프트웨어':['ai소프트웨어','ai software','software'],
    'AI 플랫폼':['ai플랫폼','ai platform'],
    'AI 인프라':['ai인프라','ai infrastructure','gpu','accelerator'],
    '데이터센터':['데이터센터','data center','datacenter'],
    '클라우드':['클라우드','cloud'],
    'AI 전력수요':['ai전력','전력수요','power demand','data center power'],

    '로봇':['로봇','robot','robotics','휴머노이드','humanoid'],
    '휴머노이드':['휴머노이드','humanoid','레인보우로보틱스'],
    '협동로봇':['협동로봇','cobot','두산로보틱스'],
    '산업용 로봇':['산업용로봇','industrial robot'],
    '서비스 로봇':['서비스로봇','service robot','로보티즈'],
    '감속기':['감속기','reducer','gearbox','에스피지'],
    '모터·액추에이터':['모터','motor','액추에이터','actuator','하이젠알앤엠'],
    '센서·비전':['센서','sensor','비전','vision'],
    '로봇 자동화':['로봇자동화','automation','factory automation'],

    '자동차·모빌리티':['자동차','완성차','모빌리티','mobility','자율주행','전기차'],
    '완성차':['완성차','현대차','기아','automaker'],
    '전기차':['전기차','electric vehicle','tesla','테슬라'],
    '자동차 부품':['자동차부품','auto parts','현대모비스'],
    '자율주행':['자율주행','autonomous driving','self driving'],
    'ADAS':['adas','첨단운전자'],
    '전장':['전장','automotive electronics'],
    '스마트카':['스마트카','smart car','connected car'],
    '수소차':['수소차','fuel cell vehicle'],

    '전력·전기기기':['전력','전기기기','변압기','전선','그리드','grid'],
    '전력·그리드':['전력','그리드','grid','power infrastructure','변압기'],
    '변압기':['변압기','transformer','hd현대일렉트릭','효성중공업','제룡전기'],
    '배전기기':['배전','distribution equipment','ls electric'],
    '전선':['전선','cable','대한전선','일진전기'],
    '전력망·그리드':['전력망','power grid','grid'],
    '스마트그리드':['스마트그리드','smart grid'],
    '전력 인프라':['전력인프라','power infrastructure'],
    '데이터센터 전력':['데이터센터전력','data center power'],

    '원전·에너지':['원전','원자력','nuclear','smr','우라늄','uranium','태양광','solar','풍력','wind','수소','hydrogen','에너지'],
    '원전':['원전','원자력','nuclear'],
    'SMR':['smr','소형모듈원전','small modular reactor'],
    '원전 기자재':['원전기자재','두산에너빌리티','한전기술','한전kps','비에이치아이'],
    '태양광':['태양광','solar'],
    '풍력':['풍력','wind'],
    '수소':['수소','hydrogen'],
    'LNG':['lng','천연가스','natural gas'],
    '우라늄':['우라늄','uranium'],
    '신재생에너지':['신재생','renewable'],

    '방산·우주항공':['방산','국방','defense','defence','항공우주','aerospace','우주','space'],
    '방산':['방산','defense','defence','한화에어로스페이스','lig넥스원','현대로템'],
    '항공우주':['항공우주','aerospace','한국항공우주'],
    '미사일':['미사일','missile','lig넥스원'],
    '지상무기':['지상무기','현대로템'],
    '레이더·전자전':['레이더','radar','전자전','한화시스템'],
    '위성':['위성','satellite'],
    '우주산업':['우주','space'],
    '조선·함정':['함정','naval','한화오션','hd현대중공업'],

    '조선·해운':['조선','해운','shipbuilding','shipping','선박'],
    '조선':['조선','shipbuilding','hd한국조선해양','hd현대중공업','한화오션','삼성중공업'],
    '조선 기자재':['조선기자재','ship equipment'],
    'LNG선':['lng선','lng carrier'],
    '친환경 선박':['친환경선박','green ship'],
    '해운':['해운','shipping','hmm'],
    '물류':['물류','logistics','cj대한통운'],
    '항만':['항만','port'],

    '바이오·헬스케어':['바이오','bio','제약','pharma','헬스케어','healthcare','의료'],
    '제약':['제약','pharma','유한양행'],
    '바이오':['바이오','bio','삼성바이오로직스','셀트리온','알테오젠'],
    '바이오시밀러':['바이오시밀러','biosimilar','셀트리온'],
    'CDMO·CMO':['cdmo','cmo','삼성바이오로직스'],
    '의료기기':['의료기기','medical device'],
    '진단':['진단','diagnostic'],
    '디지털헬스':['디지털헬스','digital health'],
    '비만·당뇨':['비만','obesity','당뇨','diabetes'],

    '인터넷·플랫폼':['인터넷','platform','플랫폼','naver','카카오','이커머스'],
    '인터넷 플랫폼':['인터넷플랫폼','naver','카카오','platform'],
    '검색·포털':['검색','포털','search','naver'],
    '핀테크':['핀테크','fintech','카카오페이'],
    '이커머스':['이커머스','ecommerce','e-commerce','쿠팡','coupang'],
    '광고·마케팅':['광고','advertising','marketing'],

    '게임·콘텐츠':['게임','gaming','콘텐츠','content','엔터','entertainment','k-pop','웹툰'],
    '게임':['게임','gaming','크래프톤','엔씨소프트','넷마블','펄어비스'],
    '웹툰·웹소설':['웹툰','webtoon','웹소설'],
    '엔터테인먼트':['엔터','entertainment','하이브','jyp','sm엔터'],
    'K-POP':['k-pop','kpop','하이브','jyp'],
    '미디어·방송':['미디어','media','방송'],
    '영화·드라마':['영화','드라마','movie','drama'],
    '콘텐츠 플랫폼':['콘텐츠플랫폼','content platform'],

    '금융':['금융','은행','bank','증권','보험','financial'],
    '은행':['은행','bank','kb금융','신한지주','하나금융지주','우리금융지주'],
    '증권':['증권','securities','미래에셋증권','한국금융지주'],
    '보험':['보험','insurance','삼성생명','삼성화재'],
    '카드·결제':['결제','payment','card'],
    '고배당 금융':['고배당금융','금융고배당'],

    '소비재':['소비','consumer','화장품','cosmetic','뷰티','beauty','음식료','food','유통','retail','여행'],
    '화장품':['화장품','cosmetic','아모레퍼시픽','lg생활건강','코스맥스','한국콜마'],
    'K-뷰티':['k-beauty','k뷰티','화장품'],
    '음식료':['음식료','food','삼양식품','농심','오리온','cj제일제당'],
    '여행·레저':['여행','레저','travel','leisure'],
    '호텔':['호텔','hotel'],

    '건설·인프라':['건설','construction','인프라','infrastructure','시멘트','건설기계'],
    '산업재·인프라':['산업재','industrial','인프라','infrastructure','건설','기계'],
    '산업재·기계':['산업재','산업기계','기계','machinery','스마트팩토리','중공업'],
    '화학·소재':['화학','chemical','소재','materials','철강','steel','희토류','rare earth'],
    '운송·물류':['운송','물류','transport','logistics','항공','해운'],
    '친환경·ESG':['esg','친환경','탄소중립','green','clean','재생에너지'],
    '클린테크':['cleantech','clean tech','친환경','탄소중립','renewable'],
    '농업·식품':['농업','agriculture','식품','food','곡물','비료','사료'],

    '미국 대표지수':['s&p500','sp500','nasdaq100','나스닥100','dow','다우','russell','러셀'],
    'S&P500':['s&p500','s&p 500','sp500'],
    'NASDAQ100':['nasdaq100','nasdaq 100','나스닥100'],
    '다우30':['dow30','dow 30','다우30'],
    '러셀2000':['russell2000','russell 2000','러셀2000'],

    '글로벌·국가':['글로벌','global','world','msci','중국','china','일본','japan','인도','india','베트남','vietnam','유럽','europe','대만','taiwan','신흥국'],
    '빅테크':['빅테크','bigtech','big tech','magnificent','매그니피센트','fang'],
    'Magnificent 7':['magnificent 7','magnificent7','매그니피센트7','m7'],
    '플랫폼':['platform','플랫폼'],
    '소프트웨어':['software','소프트웨어'],
    '인터넷':['internet','인터넷'],
    '전자상거래':['ecommerce','e-commerce','전자상거래'],

    '사이버보안':['cybersecurity','cyber security','사이버보안'],
    '클라우드 보안':['cloud security','클라우드보안'],
    '네트워크 보안':['network security','네트워크보안'],
    '양자컴퓨팅':['quantum computing','양자컴퓨팅','quantum'],
    '양자통신':['quantum communication','양자통신'],

    '배당·가치':['고배당','배당','dividend','밸류업','value','가치','저변동','퀄리티'],
    '배당·스타일':['고배당','배당','dividend','배당성장','quality','value','momentum','저변동'],
    '고배당':['고배당','high dividend'],
    '배당성장':['배당성장','dividend growth'],
    '저변동성':['저변동','low volatility'],
    '가치주':['가치','value'],
    '퀄리티':['퀄리티','quality'],
    '밸류업':['밸류업','value up'],
    '성장주':['성장','growth'],
    '모멘텀':['모멘텀','momentum'],
    '코스피200':['코스피200','kospi200'],
    '코스닥150':['코스닥150','kosdaq150'],
}

# 대표 구성종목 → 산업/세부분야 보강 규칙
COMPANY_THEME_HINTS={
    '삼성전자':[('반도체','메모리'),('AI','AI 반도체')],
    'sk하이닉스':[('반도체','메모리'),('반도체','HBM'),('AI','AI 반도체')],
    '한미반도체':[('반도체','반도체 장비'),('반도체','HBM')],
    'hpsp':[('반도체','반도체 장비')],
    '원익ips':[('반도체','반도체 장비')],
    'lg에너지솔루션':[('2차전지','배터리 셀')],
    '삼성sdi':[('2차전지','배터리 셀')],
    '에코프로비엠':[('2차전지','양극재')],
    '포스코퓨처엠':[('2차전지','양극재')],
    '레인보우로보틱스':[('로봇','휴머노이드')],
    '두산로보틱스':[('로봇','협동로봇')],
    '로보티즈':[('로봇','서비스 로봇')],
    '에스피지':[('로봇','감속기')],
    '하이젠알앤엠':[('로봇','모터·액추에이터')],
    'hd현대일렉트릭':[('전력·전기기기','변압기')],
    '효성중공업':[('전력·전기기기','변압기')],
    '제룡전기':[('전력·전기기기','변압기')],
    '두산에너빌리티':[('원전·에너지','원전 기자재')],
    '한전기술':[('원전·에너지','원전 기자재')],
    '한전kps':[('원전·에너지','원전 기자재')],
    '한화에어로스페이스':[('방산·우주항공','방산')],
    'lig넥스원':[('방산·우주항공','미사일')],
    '한국항공우주':[('방산·우주항공','항공우주')],
    '현대로템':[('방산·우주항공','지상무기')],
    '한화시스템':[('방산·우주항공','레이더·전자전')],
    'hd한국조선해양':[('조선·해운','조선')],
    'hd현대중공업':[('조선·해운','조선')],
    '한화오션':[('조선·해운','조선')],
    '삼성중공업':[('조선·해운','조선')],
    '삼성바이오로직스':[('바이오·헬스케어','CDMO·CMO'),('바이오·헬스케어','바이오')],
    '셀트리온':[('바이오·헬스케어','바이오시밀러')],
    '유한양행':[('바이오·헬스케어','제약')],
    'naver':[('인터넷·플랫폼','인터넷 플랫폼'),('AI','AI 플랫폼')],
    '카카오':[('인터넷·플랫폼','인터넷 플랫폼')],
    '크래프톤':[('게임·콘텐츠','게임')],
    '하이브':[('게임·콘텐츠','K-POP')],
    'kb금융':[('금융','은행')],
    '신한지주':[('금융','은행')],
    '하나금융지주':[('금융','은행')],
    '아모레퍼시픽':[('소비재','화장품')],
    '코스맥스':[('소비재','화장품')],
    '한국콜마':[('소비재','화장품')],
    'nvidia':[('AI','AI 반도체'),('반도체','AI 반도체')],
    '엔비디아':[('AI','AI 반도체'),('반도체','AI 반도체')],
    'tsmc':[('반도체','파운드리')],
    'asml':[('반도체','반도체 장비')],
    'amd':[('반도체','AI 반도체')],
    'microsoft':[('AI','AI 소프트웨어'),('빅테크','소프트웨어')],
    'alphabet':[('AI','AI 플랫폼'),('빅테크','플랫폼')],
    'amazon':[('AI','클라우드'),('빅테크','전자상거래')],
    'meta platforms':[('AI','AI 플랫폼'),('빅테크','플랫폼')],
    'tesla':[('전기차·배터리','전기차')],
}


def _norm_theme_text(value):
    s=str(value or '').lower()
    s=s.replace('&',' and ')
    return re.sub(r'[\s_\-·/,+()\[\]{}:;.%]+','',s)


def _theme_keywords(label):
    vals=[label]
    vals.extend(THEME_KEYWORDS.get(label,[]))
    # 복합 라벨은 각 단어도 보조 키워드로 사용
    for v in re.split(r'[·/+]',str(label)):
        if len(v.strip())>=2:
            vals.append(v.strip())
    out=[]
    seen=set()
    for v in vals:
        n=_norm_theme_text(v)
        if n and n not in seen:
            out.append(n)
            seen.add(n)
    return out


def _infer_region_asset(etf_name,index_name):
    n=_norm_theme_text(f'{etf_name} {index_name}')

    overseas=[
        '미국','s&p','sp500','nasdaq','나스닥','dow','다우','russell','러셀',
        'global','글로벌','world','msci','china','중국','japan','일본','india','인도',
        'vietnam','베트남','europe','유럽','taiwan','대만','emerging','신흥국',
        '해외','treasury','미국채'
    ]
    region='해외자산' if any(_norm_theme_text(x) in n for x in overseas) else '국내자산'

    if any(_norm_theme_text(x) in n for x in ['리츠','reit']):
        asset='리츠'
    elif any(_norm_theme_text(x) in n for x in [
        '채권','국고채','국채','회사채','통안채','bond','treasury','하이일드'
    ]):
        asset='채권'
    elif any(_norm_theme_text(x) in n for x in [
        '원자재','commodity','gold','골드','silver','원유','oil','천연가스','구리','copper'
    ]):
        asset='원자재'
    elif any(_norm_theme_text(x) in n for x in ['혼합','자산배분','멀티에셋','multiasset']):
        asset='혼합자산'
    else:
        asset='주식'

    if asset not in TREE.get(region,{}):
        asset='주식'
    return region,asset


# V0.1 샘플 스키마. 실제 ETF 결과는 다음 단계의 수집 DB가 연결되기 전에는 생성하지 않는다.
ETF_COLUMNS=['etf_code','etf_name','issuer','asset_region','asset_class','sector','subsector','aum','turnover','fee','index_name','as_of','source','collected_at']
HOLDING_COLUMNS=['etf_code','holding_code','holding_name','weight','quantity','as_of','source','collected_at']

from datetime import timedelta
from pathlib import Path
import json, time, inspect

DATA_DIR=Path(__file__).resolve().parent/'data'
DATA_DIR.mkdir(exist_ok=True)
MASTER_FILE=DATA_DIR/'etf_master.csv'
HOLDINGS_FILE=DATA_DIR/'etf_holdings.csv'
STATUS_FILE=DATA_DIR/'collection_status.json'
DB_FILE=DATA_DIR/'etf_finder.db'

def _secret_or_env(name):
    try:
        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return os.getenv(name, '').strip()

def _import_pykrx():
    # KRX 로그인 정보는 .streamlit/secrets.toml 또는 Streamlit Cloud Secrets에서 자동 사용.
    krx_id=_secret_or_env('KRX_ID')
    krx_pw=_secret_or_env('KRX_PW')
    if not krx_id or not krx_pw:
        raise RuntimeError(
            'KRX 로그인 정보가 없습니다. '
            '로컬은 .streamlit/secrets.toml, Streamlit Cloud는 App Settings → Secrets에 '
            'KRX_ID와 KRX_PW를 저장해 주세요.'
        )

    os.environ['KRX_ID']=krx_id
    os.environ['KRX_PW']=krx_pw

    try:
        import pykrx
        from pykrx import stock
        ver=getattr(pykrx,'__version__',getattr(pykrx,'version',''))
        return stock, f'pykrx {ver}'.strip()
    except ModuleNotFoundError as e:
        raise RuntimeError(
            'pykrx가 현재 Streamlit Cloud 환경에 설치되지 않았습니다. '
            'GitHub 저장소에서 app.py와 requirements.txt가 같은 폴더에 있는지 확인한 뒤 '
            'Streamlit Cloud를 재부팅(Reboot)해 주세요. '
            'requirements.txt에는 pykrx==1.2.9가 포함되어 있어야 합니다.'
        ) from e
    except Exception as e:
        raise RuntimeError(f'pykrx 로딩 실패: {e}') from e

def _candidate_dates(days=12):
    d=datetime.now()
    for _ in range(days):
        if d.weekday()<5: yield d.strftime('%Y%m%d')
        d-=timedelta(days=1)

def _find_latest_market_date(stock):
    last_error=None
    for ds in _candidate_dates(20):
        try:
            tickers=stock.get_etf_ticker_list(ds)
            if tickers:
                return ds,list(tickers)
        except Exception as e:
            last_error=e
    msg=str(last_error or '데이터 없음')
    raise RuntimeError(f'최근 ETF 기준일을 확인하지 못했습니다: {msg}')

def _pick_col(df,candidates):
    for c in candidates:
        if c in df.columns: return c
    return None

def _num(v):
    try: return float(str(v).replace(',','').replace('%','').strip())
    except Exception: return None


def _get_etf_pdf(stock, ticker, asof):
    """Installed pykrx signature에 맞춰 ETF PDF를 안전하게 호출."""
    fn = stock.get_etf_portfolio_deposit_file
    try:
        params = list(inspect.signature(fn).parameters.keys())
    except Exception:
        params = []

    if params:
        first = params[0].lower()
        if "date" in first or first in ("fromdate", "trddate"):
            return fn(asof, ticker)
        if "ticker" in first or "code" in first:
            return fn(ticker, asof)

    errors = []
    for args in ((asof, ticker), (ticker, asof)):
        try:
            df = fn(*args)
            if df is not None and not df.empty:
                return df
            errors.append(f"{args}: 빈 DataFrame")
        except Exception as e:
            errors.append(f"{args}: {e}")
    raise RuntimeError("ETF PDF 조회 실패 · " + " | ".join(errors))

def collect_krx_etf_snapshot(progress=None,pause=0.05):
    stock,collector_mode=_import_pykrx()
    asof,tickers=_find_latest_market_date(stock)
    collected_at=datetime.now().isoformat(timespec='seconds')
    master_rows=[]; holding_rows=[]; failures=[]
    try:
        ohlcv=stock.get_etf_ohlcv_by_ticker(asof)
    except Exception:
        ohlcv=pd.DataFrame()

    total=len(tickers)
    consecutive_failures=0
    fail_fast_limit=5

    for i,ticker in enumerate(tickers,1):
        ticker=str(ticker).zfill(6)
        try:
            name=stock.get_etf_ticker_name(ticker) or ticker
            turnover=None
            if not ohlcv.empty and ticker in ohlcv.index and '거래대금' in ohlcv.columns:
                turnover=_num(ohlcv.loc[ticker,'거래대금'])

            pdf=_get_etf_pdf(stock,ticker,asof)
            if pdf is None or pdf.empty:
                raise RuntimeError('PDF 구성종목이 비어 있음')

            d=pdf.reset_index().copy()
            code_col=_pick_col(d,['티커','ticker','종목코드','구성종목코드','index']) or d.columns[0]
            name_col=_pick_col(d,['구성종목명','종목명','name'])
            weight_col=_pick_col(d,['비중','비중(%)','weight'])
            qty_col=_pick_col(d,['계약수','수량','quantity'])
            amount_col=_pick_col(d,['금액','평가금액','amount'])

            amounts=pd.to_numeric(d[amount_col],errors='coerce') if amount_col else None
            amount_total=float(amounts.fillna(0).sum()) if amounts is not None else 0.0
            valid=0

            for _,row in d.iterrows():
                hcode=str(row.get(code_col,'')).strip()
                if hcode.endswith('.0'):
                    hcode=hcode[:-2]
                if hcode.isdigit() and len(hcode)<=6:
                    hcode=hcode.zfill(6)

                hname=str(row.get(name_col,'')).strip() if name_col else ''
                if not hname and hcode.isdigit() and len(hcode)==6:
                    try:
                        hname=stock.get_market_ticker_name(hcode) or hcode
                    except Exception:
                        hname=hcode
                if not hname:
                    hname=hcode or '기타자산'

                w=_num(row.get(weight_col)) if weight_col else None
                if w is None and amount_col and amount_total>0:
                    w=(_num(row.get(amount_col)) or 0.0)/amount_total*100.0
                q=_num(row.get(qty_col)) if qty_col else None

                holding_rows.append({
                    'etf_code':ticker,'holding_code':hcode,'holding_name':hname,
                    'weight':round(float(w or 0),6),'quantity':q,'as_of':asof,
                    'source':'KRX PDF (Portfolio Deposit File)',
                    'collected_at':collected_at
                })
                valid+=1

            if not valid:
                raise RuntimeError('유효 구성종목 없음')

            master_rows.append({
                'etf_code':ticker,'etf_name':name,'issuer':'',
                'asset_region':'','asset_class':'','sector':'','subsector':'',
                'aum':None,'turnover':turnover,'fee':None,'index_name':'',
                'as_of':asof,'source':'KRX Data Marketplace',
                'collected_at':collected_at
            })
            consecutive_failures=0

        except Exception as e:
            failures.append({'etf_code':ticker,'error':str(e)[:600]})
            consecutive_failures+=1
            if not master_rows and consecutive_failures>=fail_fast_limit:
                if progress:
                    progress(i,total,ticker,len(failures))
                sample=' / '.join(
                    f"{x['etf_code']}: {x['error']}" for x in failures[-3:]
                )
                raise RuntimeError(
                    f'ETF 목록 {total:,}개는 조회됐지만 구성종목 조회가 '
                    f'연속 {fail_fast_limit}건 실패해 중단했습니다. 최근 오류: {sample}'
                )

        if progress:
            progress(i,total,ticker,len(failures))
        if pause:
            time.sleep(pause)

    master=pd.DataFrame(master_rows,columns=ETF_COLUMNS)
    holdings=pd.DataFrame(holding_rows,columns=HOLDING_COLUMNS)

    if master.empty or holdings.empty:
        raise RuntimeError('수집 결과가 비어 있어 기존 DB를 변경하지 않았습니다.')

    mt=MASTER_FILE.with_suffix('.tmp')
    ht=HOLDINGS_FILE.with_suffix('.tmp')
    master.to_csv(mt,index=False,encoding='utf-8-sig')
    holdings.to_csv(ht,index=False,encoding='utf-8-sig')
    mt.replace(MASTER_FILE)
    ht.replace(HOLDINGS_FILE)

    status={
        'as_of':asof,'collected_at':collected_at,'total_etfs':total,
        'success_etfs':len(master),'failed_etfs':len(failures),
        'holding_rows':len(holdings),'failures':failures,
        'source':f'KRX Data Marketplace / PDF (Portfolio Deposit File) · {collector_mode}'
    }
    STATUS_FILE.write_text(
        json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8'
    )
    return master,holdings,status


def load_snapshot():
    '''기존 CSV 스냅샷 호환용.'''
    master=pd.read_csv(MASTER_FILE,dtype={'etf_code':str}) if MASTER_FILE.exists() else pd.DataFrame(columns=ETF_COLUMNS)
    holdings=pd.read_csv(HOLDINGS_FILE,dtype={'etf_code':str,'holding_code':str}) if HOLDINGS_FILE.exists() else pd.DataFrame(columns=HOLDING_COLUMNS)
    status=json.loads(STATUS_FILE.read_text(encoding='utf-8')) if STATUS_FILE.exists() else {}
    for df in (master,holdings):
        if 'etf_code' in df:
            df['etf_code']=df['etf_code'].astype(str).str.zfill(6)
    if 'holding_code' in holdings:
        holdings['holding_code']=holdings['holding_code'].fillna('').astype(str)
    return master,holdings,status


# =========================================================
# LOCAL SQLITE DB
# =========================================================

def _db_connect():
    conn=sqlite3.connect(str(DB_FILE),timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    return conn


def save_local_db(master,holdings):
    '''수집 결과를 로컬 SQLite DB에 저장하고 검색 인덱스를 생성.'''
    if master is None or master.empty or holdings is None or holdings.empty:
        raise RuntimeError('저장할 ETF 데이터가 없습니다.')

    m=master.copy()
    h=holdings.copy()

    for df in (m,h):
        if 'etf_code' in df.columns:
            df['etf_code']=df['etf_code'].astype(str).str.zfill(6)
    if 'holding_code' in h.columns:
        h['holding_code']=h['holding_code'].fillna('').astype(str)
    if 'holding_name' in h.columns:
        h['holding_name']=h['holding_name'].fillna('').astype(str)
    if 'weight' in h.columns:
        h['weight']=pd.to_numeric(h['weight'],errors='coerce').fillna(0.0)

    with _db_connect() as conn:
        m.to_sql('etf_master',conn,if_exists='replace',index=False)
        h.to_sql('etf_holdings',conn,if_exists='replace',index=False)
        conn.execute('CREATE INDEX IF NOT EXISTS idx_master_etf_code ON etf_master(etf_code)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_master_tree ON etf_master(asset_region,asset_class,sector,subsector)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_hold_etf_code ON etf_holdings(etf_code)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_hold_stock_code ON etf_holdings(holding_code)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_hold_stock_name ON etf_holdings(holding_name)')
        # 원본 ETF DB가 바뀌면 기존 자동 테마 매핑은 무효화
        conn.execute('DROP TABLE IF EXISTS etf_theme_map')
        conn.execute('DROP TABLE IF EXISTS theme_meta')
        conn.commit()


def migrate_existing_csv_to_db():
    '''기존 CSV가 있으면 KRX 재조회 없이 최초 1회 SQLite DB로 변환.'''
    if DB_FILE.exists():
        return False
    if not (MASTER_FILE.exists() and HOLDINGS_FILE.exists()):
        return False

    master,holdings,_=load_snapshot()
    if master.empty or holdings.empty:
        return False

    save_local_db(master,holdings)
    return True


def db_available():
    if not DB_FILE.exists():
        return False
    try:
        with _db_connect() as conn:
            row=conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='etf_master'"
            ).fetchone()
            row2=conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='etf_holdings'"
            ).fetchone()
        return bool(row and row2)
    except Exception:
        return False


def db_token():
    try:
        return DB_FILE.stat().st_mtime_ns
    except Exception:
        return 0


@st.cache_data(show_spinner=False)
def load_master_db(_token):
    if not db_available():
        return pd.DataFrame(columns=ETF_COLUMNS)
    with _db_connect() as conn:
        df=pd.read_sql_query('SELECT * FROM etf_master',conn)
    if 'etf_code' in df.columns:
        df['etf_code']=df['etf_code'].astype(str).str.zfill(6)
    return df


@st.cache_data(show_spinner=False)
def load_holdings_preview_db(_token,limit=500):
    if not db_available():
        return pd.DataFrame(columns=HOLDING_COLUMNS)
    with _db_connect() as conn:
        df=pd.read_sql_query(
            'SELECT * FROM etf_holdings ORDER BY etf_code, weight DESC LIMIT ?',
            conn,params=(int(limit),)
        )
    return df


def local_db_stats():
    if not db_available():
        return {'etfs':0,'holdings':0}
    try:
        with _db_connect() as conn:
            etfs=conn.execute('SELECT COUNT(*) FROM etf_master').fetchone()[0]
            holdings=conn.execute('SELECT COUNT(*) FROM etf_holdings').fetchone()[0]
        return {'etfs':int(etfs or 0),'holdings':int(holdings or 0)}
    except Exception:
        return {'etfs':0,'holdings':0}


def normalize_stock_query(x):
    return str(x or '').strip().replace(' ','').lower()


def reverse_search_etf_db(query_text,min_weight=0.0,require_all=True):
    '''로컬 SQLite에서만 종목 역검색. 이 함수에서는 KRX/인터넷 호출을 하지 않음.'''
    if not db_available():
        return pd.DataFrame()

    targets=[x.strip() for x in str(query_text).split(',') if x.strip()]
    if not targets:
        return pd.DataFrame()

    parts=[]
    with _db_connect() as conn:
        for raw in targets:
            key=normalize_stock_query(raw)

            if key.isdigit():
                code=key.zfill(6)
                z=pd.read_sql_query(
                    '''
                    SELECT etf_code,holding_code,holding_name,weight,as_of,source
                    FROM etf_holdings
                    WHERE holding_code=?
                    ''',
                    conn,params=(code,)
                )
            else:
                z=pd.read_sql_query(
                    '''
                    SELECT etf_code,holding_code,holding_name,weight,as_of,source
                    FROM etf_holdings
                    WHERE LOWER(REPLACE(holding_name,' ',''))=?
                    ''',
                    conn,params=(key,)
                )
                if z.empty and len(key)>=2:
                    z=pd.read_sql_query(
                        '''
                        SELECT etf_code,holding_code,holding_name,weight,as_of,source
                        FROM etf_holdings
                        WHERE LOWER(REPLACE(holding_name,' ','')) LIKE ?
                        ''',
                        conn,params=(f'%{key}%',)
                    )

            if not z.empty:
                z['_target']=raw
                parts.append(z)

    if not parts:
        return pd.DataFrame()

    hits=pd.concat(parts,ignore_index=True)
    hits['weight']=pd.to_numeric(hits['weight'],errors='coerce').fillna(0.0)

    agg=(hits.groupby('etf_code',as_index=False)
             .agg(match_weight=('weight','sum'),
                  match_count=('_target','nunique'),
                  matched_stocks=('holding_name',lambda x:', '.join(dict.fromkeys(map(str,x)))),
                  as_of=('as_of','max'),
                  source=('source',lambda x:' / '.join(dict.fromkeys(str(v) for v in x if pd.notna(v))))))

    if require_all:
        agg=agg[agg['match_count']>=len(targets)]

    agg=agg[agg['match_weight']>=float(min_weight)]
    if agg.empty:
        return pd.DataFrame()

    codes=agg['etf_code'].astype(str).tolist()
    placeholders=','.join('?' for _ in codes)
    sql=(
        'SELECT etf_code,etf_name,issuer,aum,turnover,fee,index_name '
        f'FROM etf_master WHERE etf_code IN ({placeholders})'
    )
    with _db_connect() as conn:
        master=pd.read_sql_query(sql,conn,params=codes)

    out=agg.merge(master,on='etf_code',how='left')
    order=[
        c for c in [
            'etf_name','etf_code','issuer','match_weight','matched_stocks',
            'match_count','aum','turnover','fee','index_name','as_of','source'
        ] if c in out.columns
    ]
    return (
        out.sort_values(['match_weight','match_count'],ascending=[False,False])
           [order]
           .reset_index(drop=True)
    )



def _theme_source_signature():
    if not db_available():
        return ''
    with _db_connect() as conn:
        m=conn.execute(
            "SELECT COUNT(*),COALESCE(MAX(collected_at),''),COALESCE(MAX(as_of),'') FROM etf_master"
        ).fetchone()
        h=conn.execute(
            "SELECT COUNT(*),COALESCE(MAX(collected_at),''),COALESCE(MAX(as_of),'') FROM etf_holdings"
        ).fetchone()
    return f'{m[0]}|{m[1]}|{m[2]}|{h[0]}|{h[1]}|{h[2]}|{THEME_RULES_VERSION}'


def _saved_theme_signature():
    try:
        with _db_connect() as conn:
            ok=conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='theme_meta'"
            ).fetchone()
            if not ok:
                return ''
            row=conn.execute(
                "SELECT value FROM theme_meta WHERE key='source_signature'"
            ).fetchone()
        return row[0] if row else ''
    except Exception:
        return ''


def _score_keywords(name_n,index_n,holdings,keywords):
    score=0.0
    evidence=[]

    for kw in keywords:
        if kw in name_n:
            score+=8.0
            evidence.append(f'ETF명:{kw}')
        if kw in index_n:
            score+=5.0
            evidence.append(f'지수:{kw}')

    for hname_n,hname_raw,weight in holdings:
        if any(kw in hname_n for kw in keywords):
            w=max(float(weight or 0),0.0)
            score+=min(3.2,0.7+w/10.0)
            evidence.append(f'구성:{hname_raw}({w:.1f}%)')

    return score,evidence


def _company_hint_scores(holdings):
    sector_score={}
    sub_score={}
    ev={}
    for hname_n,hname_raw,weight in holdings:
        w=max(float(weight or 0),0.0)
        for company,hints in COMPANY_THEME_HINTS.items():
            if _norm_theme_text(company) in hname_n:
                bonus=min(5.0,1.4+w/7.0)
                for sector,sub in hints:
                    sector_score[sector]=sector_score.get(sector,0.0)+bonus
                    ev.setdefault(('s',sector),[]).append(f'구성:{hname_raw}({w:.1f}%)')
                    if sub:
                        sub_score[(sector,sub)]=sub_score.get((sector,sub),0.0)+bonus+0.8
                        ev.setdefault(('d',sector,sub),[]).append(f'구성:{hname_raw}({w:.1f}%)')
    return sector_score,sub_score,ev


def build_theme_map():
    """현재 SQLite DB만 사용해 자동 테마 매핑 생성. KRX/인터넷 호출 없음."""
    if not db_available():
        return {'mapped_etfs':0,'rows':0,'generated_at':''}

    with _db_connect() as conn:
        master_df=pd.read_sql_query(
            'SELECT etf_code,etf_name,index_name,issuer,as_of FROM etf_master',
            conn
        )
        holdings_df=pd.read_sql_query(
            'SELECT etf_code,holding_name,weight FROM etf_holdings',
            conn
        )

    if master_df.empty:
        return {'mapped_etfs':0,'rows':0,'generated_at':''}

    master_df['etf_code']=master_df['etf_code'].astype(str).str.zfill(6)
    holdings_df['etf_code']=holdings_df['etf_code'].astype(str).str.zfill(6)
    holdings_df['weight']=pd.to_numeric(holdings_df['weight'],errors='coerce').fillna(0.0)
    holdings_df=holdings_df.sort_values(['etf_code','weight'],ascending=[True,False])

    groups={}
    for code,g in holdings_df.groupby('etf_code',sort=False):
        rows=[]
        for _,r in g.head(40).iterrows():
            raw=str(r.get('holding_name','') or '')
            if raw:
                rows.append((_norm_theme_text(raw),raw,float(r.get('weight',0) or 0)))
        groups[code]=rows

    generated_at=datetime.now().isoformat(timespec='seconds')
    mapped={}

    for _,m in master_df.iterrows():
        code=m['etf_code']
        etf_name=str(m.get('etf_name','') or '')
        index_name=str(m.get('index_name','') or '')
        name_n=_norm_theme_text(etf_name)
        index_n=_norm_theme_text(index_name)
        hrows=groups.get(code,[])

        region,asset=_infer_region_asset(etf_name,index_name)
        sector_tree=TREE.get(region,{}).get(asset,{})
        if not sector_tree:
            continue

        hint_sector,hint_sub,hint_ev=_company_hint_scores(hrows)

        for sector,sub_list in sector_tree.items():
            sec_score,sec_ev=_score_keywords(
                name_n,index_n,hrows,_theme_keywords(sector)
            )
            sec_score+=hint_sector.get(sector,0.0)
            sec_ev+=hint_ev.get(('s',sector),[])

            detail=[]
            best_sub=0.0
            for sub in sub_list:
                if sub=='전체':
                    continue
                sub_score,sub_ev=_score_keywords(
                    name_n,index_n,hrows,_theme_keywords(sub)
                )
                sub_score+=hint_sub.get((sector,sub),0.0)
                sub_ev+=hint_ev.get(('d',sector,sub),[])
                best_sub=max(best_sub,sub_score)

                if sub_score>=3.0:
                    detail.append((sub,sub_score,sub_ev))

            overall=max(sec_score,best_sub*0.72)

            if overall>=2.8:
                ev=list(dict.fromkeys(sec_ev))
                if not ev and detail:
                    ev=list(dict.fromkeys(detail[0][2]))
                mapped[(code,region,asset,sector,'전체')]={
                    'etf_code':code,
                    'region':region,
                    'asset_class':asset,
                    'sector':sector,
                    'subsector':'전체',
                    'score':round(overall,2),
                    'evidence':' · '.join(ev[:6]) or '세부분야 신호',
                    'generated_at':generated_at,
                    'rules_version':THEME_RULES_VERSION
                }

            for sub,sub_score,sub_ev in detail:
                mapped[(code,region,asset,sector,sub)]={
                    'etf_code':code,
                    'region':region,
                    'asset_class':asset,
                    'sector':sector,
                    'subsector':sub,
                    'score':round(sub_score,2),
                    'evidence':' · '.join(list(dict.fromkeys(sub_ev))[:6]) or f'{sub} 키워드',
                    'generated_at':generated_at,
                    'rules_version':THEME_RULES_VERSION
                }

    cols=[
        'etf_code','region','asset_class','sector','subsector',
        'score','evidence','generated_at','rules_version'
    ]
    theme_df=pd.DataFrame(list(mapped.values()),columns=cols)

    with _db_connect() as conn:
        if theme_df.empty:
            conn.execute('DROP TABLE IF EXISTS etf_theme_map')
            conn.execute(
                'CREATE TABLE etf_theme_map('
                'etf_code TEXT,region TEXT,asset_class TEXT,sector TEXT,'
                'subsector TEXT,score REAL,evidence TEXT,generated_at TEXT,rules_version TEXT)'
            )
        else:
            theme_df.to_sql('etf_theme_map',conn,if_exists='replace',index=False)

        conn.execute(
            'CREATE INDEX IF NOT EXISTS idx_theme_tree '
            'ON etf_theme_map(region,asset_class,sector,subsector)'
        )
        conn.execute(
            'CREATE INDEX IF NOT EXISTS idx_theme_code ON etf_theme_map(etf_code)'
        )
        conn.execute(
            'CREATE TABLE IF NOT EXISTS theme_meta(key TEXT PRIMARY KEY,value TEXT)'
        )
        conn.execute(
            "INSERT OR REPLACE INTO theme_meta(key,value) VALUES('source_signature',?)",
            (_theme_source_signature(),)
        )
        conn.execute(
            "INSERT OR REPLACE INTO theme_meta(key,value) VALUES('generated_at',?)",
            (generated_at,)
        )
        conn.commit()

    return {
        'mapped_etfs':int(theme_df['etf_code'].nunique()) if not theme_df.empty else 0,
        'rows':int(len(theme_df)),
        'generated_at':generated_at
    }


def theme_map_stats():
    if not db_available():
        return {'mapped_etfs':0,'rows':0,'generated_at':''}
    try:
        with _db_connect() as conn:
            ok=conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='etf_theme_map'"
            ).fetchone()
            if not ok:
                return {'mapped_etfs':0,'rows':0,'generated_at':''}
            row=conn.execute(
                "SELECT COUNT(DISTINCT etf_code),COUNT(*),"
                "COALESCE(MAX(generated_at),'') FROM etf_theme_map"
            ).fetchone()
        return {
            'mapped_etfs':int(row[0] or 0),
            'rows':int(row[1] or 0),
            'generated_at':str(row[2] or '')
        }
    except Exception:
        return {'mapped_etfs':0,'rows':0,'generated_at':''}


def ensure_theme_map(force=False):
    if not db_available():
        return {'rebuilt':False,'mapped_etfs':0,'rows':0,'generated_at':''}
    current=_theme_source_signature()
    saved=_saved_theme_signature()
    if force or not saved or saved!=current:
        info=build_theme_map()
        info['rebuilt']=True
        return info
    info=theme_map_stats()
    info['rebuilt']=False
    return info


def search_theme_db(region,asset,sector,subsector):
    """선택된 테크트리 조건을 로컬 자동매핑 테이블에서 검색."""
    if not db_available():
        return pd.DataFrame()

    sql=(
        'SELECT m.etf_name,m.etf_code,m.issuer,m.aum,m.turnover,m.fee,'
        'm.index_name,m.as_of,t.score AS theme_score,t.evidence AS match_evidence '
        'FROM etf_theme_map t '
        'JOIN etf_master m ON m.etf_code=t.etf_code '
        'WHERE t.region=? AND t.asset_class=? AND t.sector=? AND t.subsector=? '
        'ORDER BY t.score DESC,COALESCE(m.turnover,0) DESC,m.etf_name'
    )
    try:
        with _db_connect() as conn:
            df=pd.read_sql_query(
                sql,conn,params=(region,asset,sector,subsector)
            )
        if not df.empty:
            df['etf_code']=df['etf_code'].astype(str).str.zfill(6)
        return df
    except Exception:
        return pd.DataFrame()

# =========================================================
# ETF DETAIL VIEW
# 검색 결과 행 클릭 → 가격차트 + 구성종목
# =========================================================

@st.cache_data(show_spinner=False)
def get_etf_holdings_local(etf_code,_db_token):
    if not db_available():
        return pd.DataFrame(columns=HOLDING_COLUMNS)

    code=str(etf_code).zfill(6)
    sql=(
        "SELECT holding_code,holding_name,weight,quantity,as_of,source "
        "FROM etf_holdings WHERE etf_code=? "
        "ORDER BY weight DESC,holding_name"
    )
    with _db_connect() as conn:
        df=pd.read_sql_query(sql,conn,params=(code,))

    if 'weight' in df.columns:
        df['weight']=pd.to_numeric(df['weight'],errors='coerce').fillna(0.0)
    return df


@st.cache_data(show_spinner=False)
def get_etf_master_local(etf_code,_db_token):
    if not db_available():
        return {}

    code=str(etf_code).zfill(6)
    sql="SELECT * FROM etf_master WHERE etf_code=? LIMIT 1"
    with _db_connect() as conn:
        df=pd.read_sql_query(sql,conn,params=(code,))
    return df.iloc[0].to_dict() if not df.empty else {}


@st.cache_data(ttl=1800,show_spinner=False)
def get_etf_price_history(etf_code,period_label):
    days_map={'1개월':45,'3개월':120,'6개월':230,'1년':420}
    days=days_map.get(period_label,230)

    end=datetime.now()
    start=end-timedelta(days=days)

    stock,_collector_mode=_import_pykrx()
    df=stock.get_etf_ohlcv_by_date(
        start.strftime('%Y%m%d'),
        end.strftime('%Y%m%d'),
        str(etf_code).zfill(6)
    )

    if df is None or df.empty:
        return pd.DataFrame()

    out=df.reset_index().copy()

    date_col=None
    for c in ['날짜','Date','date','index']:
        if c in out.columns:
            date_col=c
            break
    if date_col is None:
        date_col=out.columns[0]

    out[date_col]=pd.to_datetime(out[date_col],errors='coerce')
    out=out.dropna(subset=[date_col])

    if '종가' not in out.columns:
        return pd.DataFrame()

    out['종가']=pd.to_numeric(out['종가'],errors='coerce')
    out=out.dropna(subset=['종가'])
    out=out.rename(columns={date_col:'날짜'})
    return out


def _set_selected_etf(etf_code,etf_name='',source=''):
    st.session_state['selected_etf_code']=_normalize_etf_identifier(etf_code)
    st.session_state['selected_etf_name']=str(etf_name or '')
    st.session_state['selected_etf_source']=str(source or '')



class _ETFHTMLTableParser(HTMLParser):
    """외부 ETF 구성종목 페이지의 HTML 표를 표준 라이브러리만으로 읽는 간단 파서."""
    def __init__(self):
        super().__init__()
        self.tables=[]
        self._in_table=False
        self._in_row=False
        self._in_cell=False
        self._table=[]
        self._row=[]
        self._cell=[]

    def handle_starttag(self,tag,attrs):
        tag=tag.lower()
        if tag=='table':
            self._in_table=True
            self._table=[]
        elif self._in_table and tag=='tr':
            self._in_row=True
            self._row=[]
        elif self._in_row and tag in ('td','th'):
            self._in_cell=True
            self._cell=[]
        elif self._in_cell and tag=='br':
            self._cell.append(' ')

    def handle_data(self,data):
        if self._in_cell:
            self._cell.append(data)

    def handle_endtag(self,tag):
        tag=tag.lower()
        if self._in_cell and tag in ('td','th'):
            value=' '.join(''.join(self._cell).split())
            self._row.append(value)
            self._in_cell=False
            self._cell=[]
        elif self._in_row and tag=='tr':
            if any(str(x).strip() for x in self._row):
                self._table.append(self._row)
            self._in_row=False
            self._row=[]
        elif self._in_table and tag=='table':
            if self._table:
                self.tables.append(self._table)
            self._in_table=False
            self._table=[]


def _parse_weight_number(value):
    s=str(value or '').replace(',','').replace('%','').strip()
    if not s or s in ('-','--','nan','None'):
        return None
    m=re.search(r'-?\d+(?:\.\d+)?',s)
    if not m:
        return None
    try:
        return float(m.group())
    except Exception:
        return None


def _clean_external_holding_name(value):
    s=' '.join(str(value or '').split())
    # FunETF 등에서 "한글명/English Name (TICKER)" 형식이면 표시명을 조금 정리
    if '/' in s:
        left,right=s.split('/',1)
        if right.strip():
            s=right.strip()
    s=re.sub(r'\s*\([A-Z0-9.\-]+\)\s*$','',s).strip()
    return s


def _extract_holdings_from_html(html_text,source_label):
    parser=_ETFHTMLTableParser()
    parser.feed(html_text or '')

    candidates=[]

    for table in parser.tables:
        header_idx=None
        name_idx=None
        weight_idx=None

        for i,row in enumerate(table[:8]):
            norm=[re.sub(r'\s+','',str(x)).lower() for x in row]
            for j,cell in enumerate(norm):
                if name_idx is None and ('종목명' in cell or cell in ('name','holding','holdings')):
                    name_idx=j
                if weight_idx is None and ('비중' in cell or 'weight' in cell):
                    weight_idx=j
            if name_idx is not None and weight_idx is not None:
                header_idx=i
                break

        if header_idx is None:
            continue

        rows=[]
        for row in table[header_idx+1:]:
            if max(name_idx,weight_idx)>=len(row):
                continue
            name=_clean_external_holding_name(row[name_idx])
            weight=_parse_weight_number(row[weight_idx])

            if not name or weight is None:
                continue
            if weight<0 or weight>100:
                continue

            # 현금/선물환은 주요 주식 구성종목 표에서 제외
            name_n=_norm_theme_text(name)
            if any(x in name_n for x in [
                '설정현금액','원화현금','현금','cash',
                '외국환포워드','fxfwd','선물환'
            ]):
                continue

            rows.append({
                'holding_name':name,
                'weight':float(weight),
                'source':source_label
            })

        if rows:
            df=pd.DataFrame(rows)
            df=df.drop_duplicates(subset=['holding_name'],keep='first')
            df=df.sort_values('weight',ascending=False).reset_index(drop=True)
            candidates.append(df)

    if not candidates:
        return pd.DataFrame(columns=['holding_name','weight','source'])

    # 행이 가장 많은 유효 표를 우선 사용
    candidates.sort(key=lambda x:(len(x),x['weight'].sum()),reverse=True)
    return candidates[0]


def _extract_basis_date_from_html(html_text):
    plain=re.sub(r'<[^>]+>',' ',html_text or '')
    plain=' '.join(plain.split())

    patterns=[
        r'(\d{4})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})일?\s*기준',
        r'(\d{2})[.\-/]\s*(\d{1,2})[.\-/]\s*(\d{1,2})\s*기준',
    ]
    for p in patterns:
        m=re.search(p,plain)
        if not m:
            continue
        y,mn,d=m.groups()
        if len(y)==2:
            y='20'+y
        try:
            return f'{int(y):04d}{int(mn):02d}{int(d):02d}'
        except Exception:
            pass
    return ''


@st.cache_data(ttl=21600,show_spinner=False)
def get_foreign_etf_weights(etf_code,etf_name):
    """
    KRX PDF가 해외 구성종목 비중을 0으로 제공하는 ETF에 한해
    선택한 ETF의 실제 공개 비중 데이터를 보완 조회한다.
    앱 전체 DB를 다시 수집하지 않는다.
    """
    code=str(etf_code).zfill(6)
    name=str(etf_name or '')
    isin=''

    try:
        stock,_mode=_import_pykrx()
        isin=str(stock.get_etf_isin(code) or '').strip()
    except Exception:
        isin=''

    headers={
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                     'AppleWebKit/537.36 Chrome/130 Safari/537.36',
        'Accept-Language':'ko-KR,ko;q=0.9,en;q=0.7'
    }

    sources=[]

    # TIGER는 운용사 공개 페이지를 우선 시도
    if isin and name.upper().startswith('TIGER'):
        sources.append((
            f'https://www.tigeretf.com/ko/product/search/detail/index.do?ksdFund={isin}&otherPage=asset',
            'TIGER 운용사 공개 구성종목'
        ))

    # 국내 상장 ETF 전반에 대해 ISIN 기반 공개 구성종목 페이지 보완
    if isin:
        sources.append((
            f'https://www.funetf.co.kr/product/etf/view/{isin}',
            'FunETF 공개 구성종목'
        ))

    # 종목코드 기반 보조 페이지
    sources.append((
        f'https://etf.zeroin.co.kr/etf/{code}',
        'KG제로인 공개 구성종목'
    ))

    errors=[]
    best=pd.DataFrame(columns=['holding_name','weight','source'])
    best_date=''

    for url,label in sources:
        try:
            r=requests.get(url,headers=headers,timeout=12)
            r.raise_for_status()

            df=_extract_holdings_from_html(r.text,label)
            if not df.empty:
                basis=_extract_basis_date_from_html(r.text)

                # 더 많은 유효 구성종목을 주는 출처를 채택.
                if len(df)>len(best):
                    best=df.copy()
                    best_date=basis

                # 20개 이상 확보되면 상세 표시 용도로 충분하므로 종료
                if len(best)>=20:
                    break
        except Exception as e:
            errors.append(f'{label}: {e}')

    return {
        'holdings':best.to_dict('records') if not best.empty else [],
        'basis_date':best_date,
        'error':' | '.join(errors[-3:])
    }


def _weights_are_missing(holdings):
    if holdings is None or holdings.empty or 'weight' not in holdings.columns:
        return True
    w=pd.to_numeric(holdings['weight'],errors='coerce').fillna(0.0)
    return bool(len(w)>0 and float(w.max())<=0.0)


def _prepare_holdings_for_detail(code,etf_name,local_holdings):
    """
    국내 ETF: 로컬 KRX 비중 그대로 사용
    해외 ETF 등 KRX 비중이 모두 0: 공개 구성종목 데이터로 표시용 비중 보완
    """
    if local_holdings is None:
        local_holdings=pd.DataFrame(columns=HOLDING_COLUMNS)

    if not _weights_are_missing(local_holdings):
        return local_holdings.copy(),'KRX 로컬 DB','',False

    fallback=get_foreign_etf_weights(code,etf_name)
    rows=fallback.get('holdings') or []

    if rows:
        ext=pd.DataFrame(rows)
        ext['holding_code']=''
        ext['quantity']=None
        ext['as_of']=fallback.get('basis_date') or ''
        ext['source']=ext.get('source','해외 ETF 비중 보완')
        cols=[
            'holding_code','holding_name','weight',
            'quantity','as_of','source'
        ]
        for c in cols:
            if c not in ext.columns:
                ext[c]=None
        ext['weight']=pd.to_numeric(ext['weight'],errors='coerce')
        ext=ext.dropna(subset=['weight'])
        ext=ext[ext['weight']>0]
        ext=ext.sort_values('weight',ascending=False).reset_index(drop=True)

        source=str(ext['source'].iloc[0]) if not ext.empty else '해외 ETF 공개 구성종목'
        return ext[cols],source,fallback.get('basis_date') or '',True

    return local_holdings.copy(),'KRX PDF · 해외종목 비중 미제공','',True

def render_etf_detail(etf_code,key_prefix='detail'):
    if not _is_krx_etf_identifier(etf_code):
        return render_us_etf_detail(etf_code,key_prefix=key_prefix)

    code=str(etf_code).zfill(6)
    master_row=get_etf_master_local(code,db_token())
    local_holdings=get_etf_holdings_local(code,db_token())

    etf_name=str(
        master_row.get('etf_name')
        or st.session_state.get('selected_etf_name')
        or code
    )

    holdings,holding_source,fallback_basis_date,used_fallback=_prepare_holdings_for_detail(
        code,
        etf_name,
        local_holdings
    )

    st.markdown('---')
    st.subheader(f'📈 {etf_name} · {code}')
    st.caption('선택한 ETF의 가격차트와 로컬 DB 구성종목입니다.')

    basis_date='-'
    if fallback_basis_date:
        basis_date=str(fallback_basis_date)
    elif master_row.get('as_of'):
        basis_date=str(master_row.get('as_of'))
    elif not holdings.empty and 'as_of' in holdings.columns:
        basis_date=str(holdings['as_of'].iloc[0])

    local_count=len(local_holdings) if local_holdings is not None else 0
    display_count=len(holdings)
    count_text=f'{local_count:,}개' if local_count else f'{display_count:,}개'

    info_cols=st.columns(4)
    info_cols[0].metric('ETF 코드',code)
    info_cols[1].metric('구성종목',count_text)
    info_cols[2].metric('구성 기준일',basis_date)
    info_cols[3].metric('추종지수',str(master_row.get('index_name') or '-')[:28])

    chart_col,holding_col=st.columns([1.35,1],gap='large')

    with chart_col:
        st.markdown('#### 가격 차트')
        period=st.radio(
            '조회기간',
            ['1개월','3개월','6개월','1년'],
            index=2,
            horizontal=True,
            key=f'{key_prefix}_period_{code}'
        )

        try:
            with st.spinner('선택 ETF 가격차트를 불러오는 중...'):
                price_df=get_etf_price_history(code,period)

            if price_df.empty:
                st.info('해당 기간의 가격 데이터를 불러오지 못했습니다.')
            else:
                p=price_df[['날짜','종가']].dropna().sort_values('날짜').copy()
                last=float(p['종가'].iloc[-1])
                prev=float(p['종가'].iloc[-2]) if len(p)>=2 else last
                change=((last/prev)-1)*100 if prev else 0.0

                m1,m2=st.columns(2)
                m1.metric('최근 종가',f'{last:,.0f}원',f'{change:+.2f}%')
                m2.metric('조회 데이터',f'{len(p):,}일')

                st.altair_chart(
                    alt.Chart(p).mark_line(color='#008878').encode(
                        x=alt.X('날짜:T', title='날짜'),
                        y=alt.Y('종가:Q', title='종가 (원)', scale=alt.Scale(zero=False)),
                        tooltip=[alt.Tooltip('날짜:T'), alt.Tooltip('종가:Q', format=',.0f')]
                    ).properties(height=390, background='white').configure_axis(
                        labelColor='#536F64', titleColor='#203D35', gridColor='#E1EBE6'
                    ).configure_view(stroke='#CFDFD9').interactive(),
                    use_container_width=True, theme=None
                )

                st.caption(
                    f"{p['날짜'].min():%Y-%m-%d} ~ {p['날짜'].max():%Y-%m-%d} · "
                    "차트만 선택 시 KRX에서 조회합니다."
                )

        except Exception as e:
            st.warning(
                '가격차트를 불러오지 못했습니다. 구성종목은 로컬 DB 데이터로 계속 확인할 수 있습니다. '
                f'차트 오류: {e}'
            )

    with holding_col:
        st.markdown('#### 주요 구성종목')

        if used_fallback and not holdings.empty and pd.to_numeric(
            holdings.get('weight',pd.Series(dtype=float)),
            errors='coerce'
        ).fillna(0).max()>0:
            st.caption(f'비중 출처: {holding_source}')
        elif used_fallback:
            st.info(
                '이 해외 ETF는 KRX PDF에서 구성종목명은 제공되지만 비중은 0으로 제공됩니다. '
                '외부 공개 비중 보완 조회도 실패하여 0.00%를 실제 비중으로 표시하지 않습니다.'
            )

        if holdings.empty:
            st.info('현재 로컬 DB에 이 ETF의 구성종목 데이터가 없습니다.')
        else:
            holdings=holdings.copy()
            holdings['weight']=pd.to_numeric(
                holdings.get('weight',0),
                errors='coerce'
            )

            valid_weight=holdings['weight'].fillna(0)>0

            if valid_weight.any():
                # 실제 양수 비중이 확보된 경우에만 비중 차트/숫자를 표시
                holdings=holdings.sort_values(
                    'weight',
                    ascending=False,
                    na_position='last'
                ).reset_index(drop=True)

                top=holdings[holdings['weight']>0].head(10).copy()

                chart_top=top[['holding_name','weight']].copy()
                chart_top=chart_top[
                    chart_top['holding_name'].fillna('').astype(str).str.len()>0
                ]
                chart_top=chart_top.sort_values('weight',ascending=False)

                if not chart_top.empty:
                    st.altair_chart(
                        alt.Chart(chart_top).mark_bar(color='#008878').encode(
                            x=alt.X('holding_name:N', sort='-y', title='구성종목'),
                            y=alt.Y('weight:Q', title='편입비중 (%)'),
                            tooltip=[alt.Tooltip('holding_name:N', title='구성종목'),
                                     alt.Tooltip('weight:Q', title='비중 (%)', format='.2f')]
                        ).properties(height=300, background='white').configure_axis(
                            labelColor='#536F64', titleColor='#203D35', gridColor='#E1EBE6'
                        ).configure_view(stroke='#CFDFD9'),
                        use_container_width=True, theme=None
                    )
                    st.caption('상위 구성종목 편입비중(%) · 비중 높은 순')

                holding_show=holdings.loc[
                    holdings['weight']>0,
                    ['holding_name','weight']
                ].copy().rename(columns={
                    'holding_name':'구성종목',
                    'weight':'비중(%)'
                })

                st.dataframe(
                    holding_show,
                    use_container_width=True,
                    hide_index=True,
                    height=420,
                    column_config={
                        '구성종목':st.column_config.TextColumn(
                            '구성종목',
                            width='medium'
                        ),
                        '비중(%)':st.column_config.NumberColumn(
                            '비중(%)',
                            format='%.2f%%',
                            width='small'
                        )
                    }
                )

            else:
                # KRX 해외 ETF PDF의 0.0은 실제 0%가 아니므로 비중 숫자를 숨긴다.
                name_only=holdings[['holding_name']].copy()
                name_only=name_only[
                    name_only['holding_name'].fillna('').astype(str).str.len()>0
                ]
                name_only=name_only.rename(columns={'holding_name':'구성종목'})

                st.dataframe(
                    name_only,
                    use_container_width=True,
                    hide_index=True,
                    height=420,
                    column_config={
                        '구성종목':st.column_config.TextColumn(
                            '구성종목',
                            width='large'
                        )
                    }
                )
                st.caption('KRX 원자료에서 해외 구성종목 비중이 제공되지 않아 종목명만 표시합니다.')

            # 원래 KRX 로컬 구성종목 전체도 확인 가능
            with st.expander('전체 구성종목 상세정보'):
                source_df=local_holdings.copy() if not local_holdings.empty else holdings.copy()

                detail_cols=[
                    c for c in [
                        'holding_name','holding_code','weight','quantity','as_of'
                    ] if c in source_df.columns
                ]
                detail_show=source_df[detail_cols].copy().rename(columns={
                    'holding_name':'구성종목',
                    'holding_code':'종목코드',
                    'weight':'비중(%)',
                    'quantity':'수량',
                    'as_of':'기준일'
                })

                # 전부 0인 해외 ETF는 오해 방지를 위해 비중 칼럼 제거
                if (
                    '비중(%)' in detail_show.columns
                    and not detail_show.empty
                    and pd.to_numeric(
                        detail_show['비중(%)'],
                        errors='coerce'
                    ).fillna(0).max()<=0
                ):
                    detail_show=detail_show.drop(columns=['비중(%)'])

                st.dataframe(
                    detail_show,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        '비중(%)':st.column_config.NumberColumn(format='%.2f%%')
                    } if '비중(%)' in detail_show.columns else None
                )


# 기존 CSV가 있다면 네트워크 접속 없이 SQLite로 1회 변환
try:
    _migrated=migrate_existing_csv_to_db()
except Exception:
    _migrated=False

_status={}
try:
    if STATUS_FILE.exists():
        _status=json.loads(STATUS_FILE.read_text(encoding='utf-8'))
except Exception:
    _status={}

_theme_info={'rebuilt':False,'mapped_etfs':0,'rows':0,'generated_at':''}
_theme_error=''
if db_available():
    try:
        _theme_info=ensure_theme_map()
    except Exception as _e:
        _theme_error=str(_e)

_token=db_token()
master=load_master_db(_token)
_stats=local_db_stats()
_theme_stats=theme_map_stats()


# =========================================================
# LOCAL DB STATUS / MANUAL UPDATE
# =========================================================


st.subheader('💾 로컬 ETF 데이터베이스')

with st.expander('🧪 배포환경 진단', expanded=False):
    import sys as _sys
    st.write('Python:', _sys.version.split()[0])
    st.write('실행 파일:', _sys.executable)
    try:
        import pykrx as _pk
        st.success(f"pykrx 설치됨 · {getattr(_pk,'__version__',getattr(_pk,'version','버전 미확인'))}")
    except Exception as _e:
        st.error(f"pykrx 미설치/로드 실패 · {_e}")
    try:
        import yfinance as _yf
        st.success(f"yfinance 설치됨 · {getattr(_yf,'__version__','버전 미확인')} · 미국상장 ETF 조회 가능")
    except Exception as _e:
        st.warning(f"yfinance 미설치 · 미국상장 ETF 상세조회 제한 · {_e}")


_s1,_s2,_s3,_s4=st.columns(4)
_s1.metric('저장 ETF',f"{_stats['etfs']:,}")
_s2.metric('구성종목',f"{_stats['holdings']:,}")
_s3.metric('기준일',_status.get('as_of','-'))
_s4.metric('DB 방식','SQLite')

if _migrated:
    st.success('기존 CSV 데이터를 로컬 SQLite DB로 자동 변환했습니다. KRX 재조회는 하지 않았습니다.')

if db_available():
    st.success('검색 모드: KRX 로컬 DB + 미국상장 ETF 카탈로그 · 일반 검색 시 KRX 전체 재수집 없음')

    if _theme_error:
        st.warning(f'자동 테마 매핑 오류: {_theme_error}')
    else:
        st.caption(
            f"🧠 자동 테마 매핑 · ETF {_theme_stats.get('mapped_etfs',0):,}개 · "
            f"매핑 {_theme_stats.get('rows',0):,}건 · "
            f"생성 {_theme_stats.get('generated_at','-') or '-'}"
        )
        if _theme_info.get('rebuilt'):
            st.success('ETF명·추종지수·구성종목을 기준으로 테마 매핑을 자동 생성했습니다.')

        if st.button('🧠 테마 매핑 다시 생성',key='rebuild_theme_map'):
            with st.spinner('로컬 DB에서 테마를 다시 분류하는 중...'):
                _new_theme=ensure_theme_map(force=True)
                st.cache_data.clear()
            st.success(
                f"테마 매핑 완료 · ETF {_new_theme.get('mapped_etfs',0):,}개 · "
                f"매핑 {_new_theme.get('rows',0):,}건"
            )
            st.rerun()
else:
    st.info('아직 로컬 DB가 없습니다. 아래 버튼을 한 번 실행해 최초 DB를 생성하세요.')

_krx_ready=bool(_secret_or_env('KRX_ID') and _secret_or_env('KRX_PW'))
if _krx_ready:
    st.caption('🔐 KRX 로그인 정보: Secrets 자동 사용 · pykrx는 requirements.txt에서 배포 시 설치')
else:
    st.warning('KRX 업데이트용 Secrets가 없습니다. .streamlit/secrets.toml에 KRX_ID와 KRX_PW를 저장해 주세요.')

with st.expander('🔄 KRX에서 로컬 DB 새로고침',expanded=not db_available()):
    st.caption(
        '이 버튼을 누를 때만 KRX 전체 데이터를 조회합니다. '
        '저장 완료 후 종목검색·테크트리·ETF 조회는 모두 로컬 DB에서 실행됩니다.'
    )

    if st.button('KRX 전체 데이터로 로컬 DB 업데이트',type='primary',use_container_width=True):
        if not _krx_ready:
            st.error('secrets.toml의 KRX_ID / KRX_PW를 먼저 확인해 주세요.')
            st.stop()

        bar=st.progress(0,text='KRX ETF 데이터를 로컬 DB용으로 수집하는 중...')

        def _progress(i,total,ticker,failed):
            bar.progress(
                min(i/max(total,1),1.0),
                text=f'{i:,}/{total:,} · {ticker} · 실패 {failed:,}건'
            )

        try:
            _m,_h,_status=collect_krx_etf_snapshot(progress=_progress)
            save_local_db(_m,_h)
            st.cache_data.clear()

            bar.progress(1.0,text='로컬 DB 저장 완료')
            st.success(
                f"기준일 {_status['as_of']} · ETF {_status['success_etfs']:,}개 · "
                f"구성종목 {_status['holding_rows']:,}건을 etf_finder.db에 저장했습니다."
            )
            st.rerun()
        except Exception as e:
            st.error(f'업데이트 실패: {e}')

st.divider()



# =========================================================
# ETF DIRECT SEARCH - KRX + US LISTED
# =========================================================

st.subheader('🔎 ETF명 · 코드/티커 빠른검색')
_d1,_d2=st.columns([4,1])
with _d1:
    direct_query=st.text_input(
        'ETF명 / 코드 / 미국 티커',
        placeholder='예: QQQ, SPY, SOXX, KODEX 200, 069500',
        key='direct_etf_query'
    )
with _d2:
    st.write('')
    st.write('')
    direct_clicked=st.button('빠른검색',type='primary',use_container_width=True,key='direct_etf_search_btn')

if direct_clicked:
    st.session_state['direct_etf_result']=search_etf_direct(direct_query)

_direct_result=st.session_state.get('direct_etf_result')
if isinstance(_direct_result,pd.DataFrame) and direct_query.strip():
    if _direct_result.empty:
        st.info('일치하는 ETF를 찾지 못했습니다.')
    else:
        _direct_show=_direct_result.rename(columns={
            'etf_name':'ETF명','etf_code':'ETF코드/티커','listing_market':'상장시장',
            'issuer':'운용사','aum':'순자산','turnover':'거래대금','fee':'총보수',
            'index_name':'추종지수','as_of':'기준'
        })
        st.caption('국내상장 ETF는 로컬 KRX DB, 미국상장 ETF는 대표 카탈로그 + Yahoo 검색으로 조회합니다.')
        _direct_event=st.dataframe(
            _direct_show,use_container_width=True,hide_index=True,on_select='rerun',
            selection_mode='single-row',key='direct_etf_results_table'
        )
        try:
            _direct_rows=list(_direct_event.selection.rows)
        except Exception:
            _direct_rows=[]
        if _direct_rows:
            _idx=int(_direct_rows[0])
            if 0<=_idx<len(_direct_show):
                _row=_direct_show.iloc[_idx]
                _set_selected_etf(
                    _row.get('ETF코드/티커',''),_row.get('ETF명',''),'direct'
                )
        if (
            st.session_state.get('selected_etf_code')
            and st.session_state.get('selected_etf_source')=='direct'
        ):
            render_etf_detail(st.session_state['selected_etf_code'],key_prefix='direct_detail')

st.divider()

# =========================================================
# TREE SEARCH - KRX LOCAL DB + US LISTED CATALOG
# =========================================================

left,right=st.columns([0.82,1.45],gap='large')

with left:
    st.subheader('🌳 ETF 테크트리')
    region=st.radio(
        'STEP 1 · 투자대상',
        list(TREE.keys()),
        horizontal=True,
        key='tree_region'
    )
    asset=st.selectbox(
        'STEP 2 · 자산군',
        list(TREE[region].keys()),
        key='tree_asset'
    )
    sector=st.selectbox(
        'STEP 3 · 산업/테마',
        list(TREE[region][asset].keys()),
        key='tree_sector'
    )
    subsector=st.selectbox(
        'STEP 4 · 세부분야',
        TREE[region][asset][sector],
        key='tree_subsector'
    )

    st.markdown(
        f'<div class="step">{region} → {asset} → {sector} → {subsector}</div>',
        unsafe_allow_html=True
    )

    tree_search_clicked=st.button(
        '🔎 선택 조건으로 ETF 검색',
        type='primary',
        use_container_width=True,
        key='tree_search_button'
    )

    current_tree=(region,asset,sector,subsector)

    if tree_search_clicked:
        st.session_state['tree_search_params']=current_tree
        st.session_state['tree_search_requested']=True

    saved_tree=st.session_state.get('tree_search_params')
    if saved_tree and saved_tree!=current_tree:
        st.caption('선택 조건이 변경되었습니다. 새 조건으로 보려면 검색 버튼을 다시 눌러주세요.')
    else:
        st.caption('KRX ETF는 저장된 로컬 DB를 사용하고, 해외자산에서는 미국상장 대표 ETF도 함께 검색합니다.')

with right:
    st.subheader('🔎 조건에 맞는 ETF')

    if not st.session_state.get('tree_search_requested'):
        st.info('왼쪽에서 조건을 선택한 뒤 **선택 조건으로 ETF 검색** 버튼을 눌러주세요.')

    else:
        params=st.session_state.get('tree_search_params')
        if not params:
            st.info('검색 조건을 선택해 주세요.')
        else:
            s_region,s_asset,s_sector,s_subsector=params

            st.caption(
                f'검색조건: {s_region} → {s_asset} → {s_sector} → {s_subsector}'
            )

            # 국내상장(KRX) 결과와 미국상장 대표 ETF를 합쳐서 표시한다.
            # KRX DB가 비어 있거나 테마 매핑에 문제가 있어도 해외자산은 미국 ETF 검색 가능.
            with st.spinner('ETF 테마 검색 중...'):
                q_krx=pd.DataFrame()
                if db_available() and not _theme_error:
                    q_krx=search_theme_db(
                        s_region,s_asset,s_sector,s_subsector
                    )
                    if not q_krx.empty:
                        q_krx=q_krx.copy()
                        q_krx['listing_market']='KRX'

                q_us=search_us_etf_catalog(
                    s_region,s_asset,s_sector,s_subsector
                )

                _parts=[x for x in [q_krx,q_us] if isinstance(x,pd.DataFrame) and not x.empty]
                q=pd.concat(_parts,ignore_index=True,sort=False) if _parts else pd.DataFrame()
                if not q.empty:
                    q=q.sort_values(
                        ['theme_score','listing_market','etf_name'],
                        ascending=[False,True,True]
                    ).reset_index(drop=True)

            if q.empty:
                if s_region=='국내자산' and not db_available():
                    st.info('국내상장 ETF 로컬 DB가 비어 있습니다. 최초 1회 KRX DB 업데이트가 필요합니다.')
                elif s_region=='국내자산' and _theme_error:
                    st.warning(f'국내 ETF 테마 매핑을 사용할 수 없습니다: {_theme_error}')
                else:
                    st.info(
                        '현재 분류 기준으로 해당 조건에 맞는 ETF를 찾지 못했습니다. '
                        '미국상장 ETF 카탈로그는 대표 상품 중심이며 계속 확대할 수 있습니다.'
                    )
            else:
                show=q.rename(columns={
                    'etf_name':'ETF명',
                    'etf_code':'ETF코드/티커',
                    'listing_market':'상장시장',
                    'issuer':'운용사',
                    'aum':'순자산',
                    'turnover':'거래대금',
                    'fee':'총보수',
                    'index_name':'추종지수',
                    'as_of':'구성 기준일',
                    'theme_score':'매핑점수',
                    'match_evidence':'매핑 근거'
                })

                st.success(
                    f'{len(show):,}개 ETF를 찾았습니다. '
                    + ('KRX 국내상장 + 미국상장 ETF 통합 결과입니다.' if s_region=='해외자산'
                       else 'ETF명·추종지수·구성종목 기반 자동 테마 매핑 결과입니다.')
                )

                st.caption('👇 ETF 행을 클릭하면 아래에 가격차트와 구성종목이 표시됩니다.')

                theme_event=st.dataframe(
                    show,
                    use_container_width=True,
                    hide_index=True,
                    on_select='rerun',
                    selection_mode='single-row',
                    key='theme_search_results_table',
                    column_config={
                        '매핑점수':st.column_config.NumberColumn(format='%.2f')
                    }
                )

                try:
                    selected_rows=list(theme_event.selection.rows)
                except Exception:
                    selected_rows=[]

                if selected_rows:
                    _idx=int(selected_rows[0])
                    if 0<=_idx<len(show):
                        _row=show.iloc[_idx]
                        _set_selected_etf(
                            _row.get('ETF코드/티커',''),
                            _row.get('ETF명',''),
                            'theme'
                        )

                st.caption(
                    'KRX ETF는 ETF명·추종지수·구성종목을 이용한 규칙 기반 매핑, '
                    '미국상장 ETF는 대표 상품의 검증된 테마 분류를 사용합니다. 투자성과 점수가 아닙니다.'
                )

                if (
                    st.session_state.get('selected_etf_code')
                    and st.session_state.get('selected_etf_source')=='theme'
                ):
                    render_etf_detail(
                        st.session_state['selected_etf_code'],
                        key_prefix='theme_detail'
                    )

st.divider()


# =========================================================
# REVERSE STOCK SEARCH - LOCAL DB ONLY
# =========================================================

a,b=st.columns([1,1.25],gap='large')

with a:
    st.subheader('🔍 종목으로 ETF 찾기')
    st.caption('편입종목 역검색은 현재 국내상장(KRX) ETF 로컬 DB를 대상으로 합니다.')

    names=st.text_input(
        '종목명 / 종목코드',
        placeholder='예: SK하이닉스 또는 000660 · 복수검색: 삼성전자, SK하이닉스'
    )

    c1,c2=st.columns(2)
    with c1:
        min_weight=st.number_input(
            '최소 합산 편입비중 (%)',
            min_value=0.0,max_value=100.0,value=0.0,step=0.5
        )
    with c2:
        match_mode=st.selectbox('복수 종목 조건',['모두 포함','하나 이상 포함'])

    if st.button('ETF 역검색',type='primary',use_container_width=True):
        if not db_available():
            st.warning('로컬 ETF DB가 없습니다. 최초 1회 DB 업데이트가 필요합니다.')
            st.session_state.pop('reverse_search_result',None)
        else:
            with st.spinner('로컬 DB 검색 중...'):
                result=reverse_search_etf_db(
                    names,
                    min_weight=min_weight,
                    require_all=(match_mode=='모두 포함')
                )
            st.session_state['reverse_search_result']=result

    result=st.session_state.get('reverse_search_result')

    if isinstance(result,pd.DataFrame):
        if result.empty:
            st.info('조건에 맞는 ETF를 찾지 못했습니다. 종목명/코드 또는 최소 편입비중을 확인해 주세요.')
        else:
            show=result.rename(columns={
                'etf_name':'ETF명',
                'etf_code':'ETF코드',
                'issuer':'운용사',
                'match_weight':'합산 편입비중(%)',
                'matched_stocks':'일치 종목',
                'match_count':'일치 종목수',
                'aum':'순자산',
                'turnover':'거래대금',
                'fee':'총보수',
                'index_name':'추종지수',
                'as_of':'구성 기준일',
                'source':'출처'
            })

            st.success(f'{len(show):,}개 ETF를 찾았습니다. 로컬 DB 검색 결과입니다.')
            st.caption('👇 ETF 행을 클릭하면 아래에 가격차트와 구성종목이 표시됩니다.')

            reverse_event=st.dataframe(
                show,
                use_container_width=True,
                hide_index=True,
                on_select='rerun',
                selection_mode='single-row',
                key='reverse_search_results_table',
                column_config={
                    '합산 편입비중(%)':st.column_config.NumberColumn(format='%.2f%%')
                }
            )

            try:
                reverse_rows=list(reverse_event.selection.rows)
            except Exception:
                reverse_rows=[]

            if reverse_rows:
                _idx=int(reverse_rows[0])
                if 0<=_idx<len(show):
                    _row=show.iloc[_idx]
                    _set_selected_etf(
                        _row.get('ETF코드',''),
                        _row.get('ETF명',''),
                        'reverse'
                    )

            if (
                st.session_state.get('selected_etf_code')
                and st.session_state.get('selected_etf_source')=='reverse'
            ):
                render_etf_detail(
                    st.session_state['selected_etf_code'],
                    key_prefix='reverse_detail'
                )

with b:
    st.subheader('⚡ 검색 구조')
    st.markdown('''
- **최초 1회 / 수동 업데이트:** KRX → 로컬 DB 저장
- **종목 역검색:** 로컬 SQLite DB만 조회
- **테크트리 필터:** 로컬 ETF Master만 조회
- **Streamlit 재실행:** 저장된 DB를 다시 사용
- **검색할 때마다 1,000개 이상 ETF를 재수집하지 않음**\n- **검색 결과 행 클릭:** 가격차트 + 구성종목 표시
''')
    st.caption(f'로컬 DB: {DB_FILE.name} · 앱 실행 시각: {datetime.now():%Y-%m-%d %H:%M:%S}')

st.divider()


# =========================================================
# LOCAL DB VIEW
# =========================================================

st.subheader('🗄️ 로컬 ETF DB')
t1,t2,t3=st.tabs(['ETF Master','ETF Holdings 미리보기','자동 테마 매핑'])

with t1:
    if master.empty:
        st.info('저장된 ETF Master 데이터가 없습니다.')
    else:
        st.dataframe(master,use_container_width=True,hide_index=True)

with t2:
    if not db_available():
        st.info('저장된 ETF Holdings 데이터가 없습니다.')
    else:
        preview=load_holdings_preview_db(db_token(),500)
        st.caption(f"전체 {_stats['holdings']:,}건 중 최대 500건만 미리 표시합니다. 검색은 전체 DB를 대상으로 합니다.")
        st.dataframe(preview,use_container_width=True,hide_index=True)

with t3:
    if not db_available():
        st.info('로컬 DB가 없습니다.')
    elif _theme_error:
        st.warning(f'자동 테마 매핑 오류: {_theme_error}')
    else:
        try:
            with _db_connect() as conn:
                theme_preview=pd.read_sql_query(
                    'SELECT etf_code,region,asset_class,sector,subsector,score,evidence '
                    'FROM etf_theme_map ORDER BY score DESC LIMIT 500',
                    conn
                )
            st.caption(
                f"전체 자동 매핑 {_theme_stats.get('rows',0):,}건 중 최대 500건을 표시합니다."
            )
            st.dataframe(theme_preview,use_container_width=True,hide_index=True)
        except Exception as _e:
            st.warning(f'테마 매핑 미리보기를 불러오지 못했습니다: {_e}')

