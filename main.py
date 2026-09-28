import datetime
import re
import requests
import streamlit as st
import pytz

# 페이지 설정
st.set_page_config(page_title="학교 급식 찾아보기", page_icon="🍱", layout="centered")

st.title("🍱 학교 급식 찾아보기")
st.caption("나이스 교육정보 개방 포털 API를 활용한 학교 급식 정보 조회 서비스")

# API URL 정의
SCHOOL_INFO_URL = "https://open.neis.go.kr/hub/schoolInfo"
MEAL_INFO_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"


def search_school(school_name: str):
    """학교 이름을 검색하여 리스트로 반환하는 함수"""
    params = {"Type": "json", "SCHUL_NM": school_name}
    try:
        response = requests.get(SCHOOL_INFO_URL, params=params, timeout=5)
        data = response.json()

        # 데이터가 포함된 경우 (schoolInfo 키 존재)
        if "schoolInfo" in data:
            rows = data["schoolInfo"][1]["row"]
            return rows
        return []
    except Exception as e:
        st.error(f"학교 정보를 불러오는 중 오류가 발생했습니다: {e}")
        return []


def expand_school_name(name: str) -> str:
    """축약된 학교 이름을 정식 명칭 형태 단어로 대체하는 함수"""
    expanded = name
    # 축약어 변환 규칙 (긴 단어부터 적용)
    replacements = [
        ("여고", "여자고등학교"),
        ("남고", "남자고등학교"),
        ("여중", "여자중학교"),
        ("남중", "남자중학교"),
        ("여초", "여자초등학교"),
        ("초교", "초등학교"),
        ("고교", "고등학교"),
        ("고", "고등학교"),
        ("중", "중학교"),
        ("초", "초등학교"),
    ]

    for short_form, full_form in replacements:
        if name.endswith(short_form):
            expanded = name[: -len(short_form)] + full_form
            break

    return expanded


def fetch_meal_info(office_code: str, school_code: str, ymd: str):
    """지정한 학교 및 날짜의 중식 급식 메뉴를 조회하는 함수"""
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
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


def clean_menu_text(dish_nm: str) -> str:
    """<br/> 태그를 줄바꿈으로 변경하여 깔끔하게 정돈하는 함수"""
    # <br/>, <br>, <br /> 등의 태그를 줄바꿈으로 변환
    cleaned = re.sub(r"<br\s*/?>", "\n", dish_nm)
    return cleaned


# ---------------- [ 메인 화면 구성 ] ----------------

# 1. 학교 검색 UI
st.subheader("1. 학교 검색")
search_input = st.text_input("학교 이름을 입력하세요 (예: 수도여고, 서울고, 신길초)", placeholder="학교명 입력")

schools_found = []

if search_input.strip():
    query_name = search_input.strip()
    # 1차 검색
    schools_found = search_school(query_name)

    # 1차 검색 결과가 없고 이름 축약 패턴이 의심되면 2차 검색 진행
    if not schools_found:
        expanded_name = expand_school_name(query_name)
        if expanded_name != query_name:
            st.info(f"'{query_name}' 검색 결과가 없어 '{expanded_name}'(으)로 다시 검색합니다.")
            schools_found = search_school(expanded_name)

    if not schools_found:
        st.warning(f"'{query_name}'에 대한 학교 정보를 찾을 수 없습니다. 정확한 학교명을 입력해 주세요.")

selected_school = None
if schools_found:
    # 검색된 학교 목록 옵션 생성 ("학교명 (지역명)")
    options = {
        f"{school['SCHUL_NM']} ({school.get('LCTN_SC_NM', '지역미상')})": school
        for school in schools_found
    }

    selected_label = st.selectbox("검색된 학교 중 해당 학교를 선택하세요:", list(options.keys()))
    selected_school = options[selected_label]

st.markdown("---")

# 2. 날짜 선택 및 급식 조회 UI
st.subheader("2. 날짜 및 급식 선택")

# 한국 시간(KST) 기준 오늘 날짜 구하기
kst = pytz.timezone("Asia/Seoul")
today_kst = datetime.datetime.now(kst).date()

selected_date = st.date_input("조회할 날짜를 선택하세요:", value=today_kst)

if selected_school:
    date_str = selected_date.strftime("%Y%m%d")

    with st.spinner("급식 정보를 가져오는 중입니다..."):
        meal_data = fetch_meal_info(
            office_code=selected_school["ATPT_OFCDC_SC_CODE"],
            school_code=selected_school["SD_SCHUL_CODE"],
            ymd=date_str,
        )

    st.markdown("---")
    st.subheader(f"🍱 {selected_school['SCHUL_NM']} - {selected_date.strftime('%Y년 %m월 %d일')} 중식 메뉴")

    if meal_data:
        raw_dish = meal_data.get("DDISH_NM", "")
        formatted_menu = clean_menu_text(raw_dish)
        calorie_info = meal_data.get("CAL_INFO", "정보 없음")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("### 🥗 오늘의 메뉴")
            st.text(formatted_menu)

        with col2:
            st.markdown("### 🔥 칼로리")
            st.info(calorie_info)

        st.caption("※ 메뉴 뒤 괄호 속 숫자는 알레르기 유발 물질 번호입니다.")
    else:
        st.info("💡 선택하신 날짜에는 등록된 중식 급식 정보가 없습니다. (주말, 공휴일 또는 방학일 수 있습니다.)")
else:
    st.info("👆 위에서 학교를 먼저 검색하고 선택해 주세요.")
