import datetime
import re
import requests
import streamlit as st
import pytz

# 페이지 설정
st.set_page_config(page_title="우리 학교 달력별 급식", page_icon="📅", layout="centered")

st.title("📅 우리 학교 달력별 급식")
st.caption("송탄고등학교 전용 중식 급식 조회 페이지입니다.")

# 송탄고등학교 고정 정보 및 API URL
MEAL_INFO_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
OFFICE_CODE = "J10"      # 경기도교육청
SCHOOL_CODE = "7530480"  # 송탄고등학교


def fetch_meal_info(ymd: str):
    """지정한 날짜(YYYYMMDD)의 송탄고등학교 중식 급식 메뉴를 조회하는 함수"""
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "MMEAL_SC_CODE": "2",  # 중식
        "MLSV_FROM_YMD": ymd,
        "MLSV_TO_YMD": ymd,
    }
    try:
        response = requests.get(MEAL_INFO_URL, params=params, timeout=5)
        data = response.json()

        if "mealServiceDietInfo" in data:
            rows = data["mealServiceDietInfo"][1]["row"]
            if rows:
                return rows[0]
        return None
    except Exception as e:
        st.error(f"급식 정보를 불러오는 중 오류가 발생했습니다: {e}")
        return None


def parse_menu_items(dish_nm: str, show_allergy: bool) -> list:
    """
    DDISH_NM 텍스트(<br/>로 구분)를 개별 메뉴 항목 리스트로 분리하고,
    show_allergy 옵션에 따라 알레르기 번호(괄호 숫자 및 점)를 제거하거나 유지합니다.
    """
    # <br/>, <br>, <br /> 태그 기준으로 분리
    raw_items = re.split(r"<br\s*/?>", dish_nm)
    cleaned_items = []

    for item in raw_items:
        item = item.strip()
        if not item:
            continue

        if not show_allergy:
            # 괄호 안의 숫자, 점, 공백 제거 (예: "쌀밥 (1.2.3)" -> "쌀밥", "닭갈비(5.6.13.)" -> "닭갈비")
            item = re.sub(r"\s*\([\d\.\s]+\)", "", item)

        cleaned_items.append(item.strip())

    return cleaned_items


# ---------------- [ 메인 화면 구성 ] ----------------

# 한국 시간(KST) 기준 오늘 날짜 구하기
kst = pytz.timezone("Asia/Seoul")
today_kst = datetime.datetime.now(kst).date()

# 1. 날짜 선택 및 알레르기 스위치 (나란히 배치)
col_date, col_toggle = st.columns([2, 1], vertical_alignment="bottom")

with col_date:
    selected_date = st.date_input("조회할 날짜를 선택하세요:", value=today_kst)

with col_toggle:
    show_allergy = st.toggle("알레르기 정보 보기", value=True)

date_str = selected_date.strftime("%Y%m%d")

# 2. 급식 정보 API 호출
with st.spinner("급식 정보를 가져오는 중입니다..."):
    meal_data = fetch_meal_info(date_str)

st.markdown("---")

# 3. 급식 정보 표시
if meal_data:
    raw_dish = meal_data.get("DDISH_NM", "")
    calorie_info = meal_data.get("CAL_INFO", "정보 없음")
    menu_list = parse_menu_items(raw_dish, show_allergy)

    # 지표 카드 (메뉴 가짓수 & 칼로리)
    metric_col1, metric_col2 = st.columns(2)
    with metric_col1:
        st.metric(label="🍴 메뉴 가짓수", value=f"{len(menu_list)}개")
    with metric_col2:
        st.metric(label="🔥 칼로리", value=calorie_info)

    st.markdown("### 🥗 오늘의 급식 메뉴")

    # 메뉴 항목을 그리드 카드 형태로 나란히 표시 (한 줄에 최대 3개씩)
    cols_per_row = 3
    for i in range(0, len(menu_list), cols_per_row):
        row_items = menu_list[i : i + cols_per_row]
        cols = st.columns(len(row_items))
        for col, item in zip(cols, row_items):
            with col:
                st.info(f"**{item}**")

    if show_allergy:
        st.caption("※ 메뉴 뒤 괄호 속 숫자는 알레르기 유발 물질 번호입니다.")

else:
    # 급식이 없는 날 안내 메시지
    st.warning("⚠️ 급식이 없는 날입니다.")
    st.info("주말, 공휴일, 재량휴업일 또는 방학기간에는 급식 정보가 제공되지 않습니다.")
