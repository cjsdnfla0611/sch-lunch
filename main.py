import datetime
import re
import calendar
import requests
import streamlit as st
import pytz
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="우리 학교 달력별 급식", page_icon="📅", layout="centered")

st.title("📅 우리 학교 달력별 급식")
st.caption("송탄고등학교 전용 중식 급식 조회 및 후식 통계 분석 페이지입니다.")

# 송탄고등학교 고정 정보 및 API URL
MEAL_INFO_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
OFFICE_CODE = "J10"      # 경기도교육청
SCHOOL_CODE = "7530480"  # 송탄고등학교

# 후식 키워드 분류 정의
DESSERT_KEYWORDS = {
    "과일": ["사과", "배", "귤", "바나나", "포도", "수박", "참외", "토마토", "딸기", "파인애플", "키위", "자두", "복숭아", "샤인머스켓", "멜론"],
    "음료수": ["주스", "우유", "요구르트", "에이드", "식혜", "수정과", "차", "라떼", "스무디", "음료", "야쿠르트", "요플레"],
    "디저트": ["케이크", "빵", "파이", "쿠키", "마카롱", "푸딩", "아이스크림", "슈", "도넛", "와플", "떡", "브라우니", "에그타르트", "젤리"]
}


def fetch_meal_range(from_ymd: str, to_ymd: str):
    """기간(FROM~TO) 내의 급식 데이터를 조회하는 함수"""
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "MMEAL_SC_CODE": "2",  # 중식
        "MLSV_FROM_YMD": from_ymd,
        "MLSV_TO_YMD": to_ymd,
        "pSize": 300
    }
    try:
        response = requests.get(MEAL_INFO_URL, params=params, timeout=15)
        data = response.json()
        if "mealServiceDietInfo" in data:
            return data["mealServiceDietInfo"][1]["row"]
        return []
    except Exception as e:
        st.error(f"급식 데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return []


def parse_menu_items(dish_nm: str, show_allergy: bool) -> list:
    """메뉴 텍스트를 개별 항목으로 분리하고 알레르기 번호 제거 옵션을 적용하는 함수"""
    raw_items = re.split(r"<br\s*/?>", dish_nm)
    cleaned_items = []
    for item in raw_items:
        item = item.strip()
        if not item:
            continue
        if not show_allergy:
            item = re.sub(r"\s*\([\d\.\s]+\)", "", item)
        cleaned_items.append(item.strip())
    return cleaned_items


def classify_desserts(dish_nm: str, selected_categories: list) -> list:
    """메뉴에서 선택된 카테고리(과일/음료수/디저트)에 해당하는 후식을 추출하는 함수"""
    raw_items = re.split(r"<br\s*/?>", dish_nm)
    found_desserts = []

    for item in raw_items:
        clean_name = re.sub(r"\s*\([\d\.\s]+\)", "", item).strip()
        
        for category in selected_categories:
            keywords = DESSERT_KEYWORDS.get(category, [])
            if any(kw in clean_name for kw in keywords):
                found_desserts.append((clean_name, category))
                break

    return found_desserts


def render_month_calendar(year: int, month: int, dessert_dict: dict):
    """특정 월의 달력을 HTML 테이블로 렌더링 (디저트 나온 날은 파란색 배경)"""
    cal = calendar.Calendar(firstweekday=0)  # 월요일 시작
    month_days = cal.monthdatescalendar(year, month)
    
    html = f"""
    <div style="margin-bottom: 25px; border: 1px solid #E0E0E0; padding: 15px; border-radius: 10px; background-color: #FAFAFA;">
        <h4 style="margin-top:0; text-align: center; color: #1E3A8A;">📅 {year}년 {month}월</h4>
        <table style="width: 100%; border-collapse: collapse; text-align: center; font-size: 13px;">
            <thead>
                <tr style="background-color: #F1F5F9; border-bottom: 2px solid #CBD5E1;">
                    <th style="padding: 6px; color: #475569;">월</th>
                    <th style="padding: 6px; color: #475569;">화</th>
                    <th style="padding: 6px; color: #475569;">수</th>
                    <th style="padding: 6px; color: #475569;">목</th>
                    <th style="padding: 6px; color: #475569;">금</th>
                    <th style="padding: 6px; color: #2563EB;">토</th>
                    <th style="padding: 6px; color: #DC2626;">일</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for week in month_days:
        html += "<tr>"
        for day in week:
            # 해당 월의 날짜인지 확인
            is_current_month = (day.month == month)
            day_str = day.strftime("%Y-%m-%d")
            
            if not is_current_month:
                html += '<td style="padding: 8px; color: #CBD5E1; background-color: #F8FAFC;"></td>'
                continue
                
            desserts = dessert_dict.get(day_str, [])
            has_dessert = len(desserts) > 0
            
            # 스타일 설정
            if has_dessert:
                # 디저트 나온 날은 파란색 강조
                bg_color = "#D0E8FF"
                border = "1px solid #60A5FA"
                font_weight = "bold"
                text_color = "#1E40AF"
            else:
                bg_color = "#FFFFFF"
                border = "1px solid #F1F5F9"
                font_weight = "normal"
                text_color = "#334155"
                
            # 요일별 색상 조정 (일요일/토요일)
            if not has_dessert:
                if day.weekday() == 6:  # 일요일
                    text_color = "#EF4444"
                elif day.weekday() == 5:  # 토요일
                    text_color = "#3B82F6"

            dessert_label = ""
            if has_dessert:
                dessert_names = ", ".join([d[0] for d in desserts])
                dessert_label = f'<div style="font-size: 10px; color: #1E3A8A; margin-top: 2px; word-break: break-all;">🍦 {dessert_names}</div>'

            html += f"""
            <td style="padding: 8px 4px; height: 55px; vertical-align: top; background-color: {bg_color}; border: {border}; font-weight: {font_weight}; color: {text_color};">
                <div>{day.day}</div>
                {dessert_label}
            </td>
            """
        html += "</tr>"
        
    html += """
            </tbody>
        </table>
    </div>
    """
    return html


# ---------------- [ 메인 화면 구성 ] ----------------

kst = pytz.timezone("Asia/Seoul")
today_kst = datetime.datetime.now(kst).date()

# 1. 날짜 선택 및 알레르기 스위치
col_date, col_toggle = st.columns([2, 1], vertical_alignment="bottom")

with col_date:
    selected_date = st.date_input("조회할 날짜를 선택하세요:", value=today_kst)

with col_toggle:
    show_allergy = st.toggle("알레르기 정보 보기", value=True)

date_str = selected_date.strftime("%Y%m%d")

# 단일 날짜 급식 정보 가져오기
single_meal_list = fetch_meal_range(date_str, date_str)
meal_data = single_meal_list[0] if single_meal_list else None

st.markdown("---")

# 2. 날짜별 급식 카드로 표시
if meal_data:
    raw_dish = meal_data.get("DDISH_NM", "")
    calorie_info = meal_data.get("CAL_INFO", "정보 없음")
    menu_list = parse_menu_items(raw_dish, show_allergy)

    metric_col1, metric_col2 = st.columns(2)
    with metric_col1:
        st.metric(label="🍴 메뉴 가짓수", value=f"{len(menu_list)}개")
    with metric_col2:
        st.metric(label="🔥 칼로리", value=calorie_info)

    st.markdown("### 🥗 오늘의 급식 메뉴")

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
    st.warning("⚠️ 급식이 없는 날입니다.")
    st.info("주말, 공휴일, 재량휴업일 또는 방학기간에는 급식 정보가 제공되지 않습니다.")

st.markdown("---")

# 3. 최근 6개월 후식 통계 분석 및 달력 시각화
st.subheader("📊 최근 6개월 후식 분석 & 달력 현황")
st.caption("지난 180일(6개월)간의 급식 데이터를 분석하고, 후식이 제공된 날을 달력에 표시합니다.")

start_date = today_kst - datetime.timedelta(days=180)
start_str = start_date.strftime("%Y%m%d")
end_str = today_kst.strftime("%Y%m%d")

@st.cache_data(ttl=3600)
def load_6months_data(s_date, e_date):
    return fetch_meal_range(s_date, e_date)

with st.spinner("최근 6개월 급식 데이터를 불러오는 중입니다..."):
    half_year_data = load_6months_data(start_str, end_str)

if half_year_data:
    st.write("**확인하고 싶은 후식 종류를 선택하세요:**")
    chk_cols = st.columns(3)
    with chk_cols[0]:
        chk_fruit = st.checkbox("🍎 과일", value=True)
    with chk_cols[1]:
        chk_drink = st.checkbox("🧃 음료수", value=True)
    with chk_cols[2]:
        chk_dessert = st.checkbox("🍰 디저트(빵/케이크/쿠키 등)", value=True)

    selected_categories = []
    if chk_fruit: selected_categories.append("과일")
    if chk_drink: selected_categories.append("음료수")
    if chk_dessert: selected_categories.append("디저트")

    weekday_names = ["월요일", "화요일", "수요일", "목요일", "금요일"]
    weekday_counts = {day: 0 for day in weekday_names}
    matched_records = []
    dessert_by_date = {}  # 날짜별 디저트 저장 딕셔너리 ({'YYYY-MM-DD': [(이름, 카테고리)]})
    
    total_school_days = len(half_year_data)

    for row in half_year_data:
        ymd_str = row.get("MLSV_YMD", "")
        if not ymd_str:
            continue

        dt = datetime.datetime.strptime(ymd_str, "%Y%m%d")
        weekday_idx = dt.weekday()
        if weekday_idx >= 5:  # 주말 제외
            continue

        day_name = weekday_names[weekday_idx]
        dish_nm = row.get("DDISH_NM", "")
        date_formatted = dt.strftime("%Y-%m-%d")

        found_list = classify_desserts(dish_nm, selected_categories)

        if found_list:
            weekday_counts[day_name] += len(found_list)
            dessert_by_date[date_formatted] = found_list
            for item_name, cat in found_list:
                matched_records.append({
                    "날짜": date_formatted,
                    "요일": day_name,
                    "후식 이름": item_name,
                    "분류": cat
                })

    total_dessert_count = len(matched_records)

    st.markdown("#### 🏆 6개월간 통계 요약")

    if total_dessert_count > 0 and total_school_days > 0:
        avg_days = round(total_school_days / total_dessert_count, 1)

        # 1. 요약 카드 표시
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric(label="🗓️ 최근 6개월 총 급식일", value=f"{total_school_days}일")
        with m_col2:
            st.metric(label="🧁 후식 총 제공 횟수", value=f"{total_dessert_count}회")
        with m_col3:
            st.metric(label="🔄 평균 제공 주기", value=f"약 {avg_days}일마다 1번")

        best_day = max(weekday_counts, key=weekday_counts.get)
        max_count = weekday_counts[best_day]

        st.success(f"🎉 최근 6개월간 **총 {total_dessert_count}번**의 후식이 나왔으며, 평균 **{avg_days}일마다 1번씩** 제공되었습니다. (가장 자주 나온 요일: **{best_day}** - {max_count}회)")

        # 2. 요일별 후식 제공 차트
        df_counts = pd.DataFrame(list(weekday_counts.items()), columns=["요일", "제공 횟수"])
        df_counts["요일"] = pd.Categorical(df_counts["요일"], categories=weekday_names, ordered=True)
        df_counts = df_counts.sort_values("요일")

        st.bar_chart(df_counts, x="요일", y="제공 횟수")

        # 3. 1열로 구성된 최근 6개월 달력 시각화
        st.markdown("---")
        st.markdown("#### 📅 월별 디저트 달력 (디저트 나온 날: 🟦 파란색)")
        
        # 최근 6개월의 연/월 목록 추출 (현재 월부터 역순으로 6개 월)
        year_months = []
        curr_year = today_kst.year
        curr_month = today_kst.month

        for i in range(6):
            m = curr_month - i
            y = curr_year
            while m <= 0:
                m += 12
                y -= 1
            year_months.append((y, m))

        # 1열로 달력 출력
        for y, m in year_months:
            cal_html = render_month_calendar(y, m, dessert_by_date)
            st.markdown(cal_html, unsafe_allow_html=True)

        # 4. 상세 목록 (접기)
        with st.expander(f"🔍 선택한 후식이 나온 날짜 전체 목록 보기 (총 {total_dessert_count}건)"):
            df_records = pd.DataFrame(matched_records)
            st.dataframe(df_records, use_container_width=True)
    else:
        st.info("선택하신 후식 종류에 해당하는 급식 내역이 최근 6개월 동안 없습니다.")
else:
    st.info("최근 6개월 급식 데이터를 불러올 수 없습니다.")
