import datetime
import re
import calendar
import requests
import streamlit as st
import streamlit.components.v1 as components
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta

# 페이지 기본 설정
st.set_page_config(page_title="우리 학교 달력별 급식", page_icon="📅", layout="centered")

st.title("📅 우리 학교 달력별 급식")
st.caption("송탄고등학교 전용 중식 급식 조회 및 후식 통계 분석 페이지입니다.")

# ---------------- [ 설정 및 API 키 ] ----------------
# "c7874afab65747d5ae5303ba3de5725d"
NEIS_API_KEY = "YOUR_NEIS_API_KEY"  

MEAL_INFO_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
OFFICE_CODE = "J10"      # 경기도교육청
SCHOOL_CODE = "7530480"  # 송탄고등학교

# 후식 키워드 분류 정의
DESSERT_KEYWORDS = {
    "과일": ["사과", "배", "귤", "바나나", "포도", "수박", "참외", "토마토", "딸기", "파인애플", "키위", "자두", "복숭아", "샤인머스켓", "멜론"],
    "음료수": ["주스", "우유", "요구르트", "에이드", "식혜", "수정과", "차", "라떼", "스무디", "음료", "야쿠르트", "요플레"],
    "디저트": ["케이크", "빵", "파이", "쿠키", "마카롱", "푸딩", "아이스크림", "슈", "도넛", "와플", "떡", "브라우니", "에그타르트", "젤리"]
}


def fetch_single_period(from_ymd: str, to_ymd: str):
    """API 키를 포함하여 특정 기간의 급식 데이터를 수집하는 함수"""
    all_rows = []
    p_index = 1
    p_size = 100

    while True:
        params = {
            "KEY": NEIS_API_KEY,  # 🔑 인증키 전달
            "Type": "json",
            "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
            "SD_SCHUL_CODE": SCHOOL_CODE,
            "MMEAL_SC_CODE": "2",  # 중식
            "MLSV_FROM_YMD": from_ymd,
            "MLSV_TO_YMD": to_ymd,
            "pIndex": p_index,
            "pSize": p_size
        }
        try:
            response = requests.get(MEAL_INFO_URL, params=params, timeout=10)
            data = response.json()
            
            if "mealServiceDietInfo" in data:
                rows = data["mealServiceDietInfo"][1]["row"]
                all_rows.extend(rows)
                if len(rows) < p_size:
                    break
                p_index += 1
            else:
                break
        except Exception:
            break

    return all_rows


@st.cache_data(ttl=3600)
def fetch_6months_data(today_date):
    """인증키를 사용하여 최근 6개월간의 데이터를 월별로 안전하게 모두 수집"""
    total_rows = []
    
    # 최근 6개월 (년, 월)을 계산하여 월별로 호출
    for i in range(5, -1, -1):
        target_dt = today_date - relativedelta(months=i)
        year = target_dt.year
        month = target_dt.month
        
        _, last_day = calendar.monthrange(year, month)
        from_ymd = f"{year}{month:02d}01"
        to_ymd = f"{year}{month:02d}{last_day:02d}"
        
        month_rows = fetch_single_period(from_ymd, to_ymd)
        total_rows.extend(month_rows)
        
    return total_rows


def parse_menu_items(dish_nm: str, show_allergy: bool) -> list:
    """메뉴 텍스트 정제 및 알레르기 수치 필터링"""
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
    """후식 분류 키워드와 대조"""
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


def render_month_calendar_html(year: int, month: int, dessert_dict: dict):
    """HTML 기반 월별 달력 렌더링"""
    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdatescalendar(year, month)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, sans-serif; margin: 0; padding: 5px; }}
            .cal-card {{ border: 1px solid #E0E0E0; padding: 10px; border-radius: 8px; background-color: #FAFAFA; }}
            .cal-title {{ text-align: center; color: #1E3A8A; margin: 0 0 8px 0; font-size: 15px; font-weight: bold; }}
            table {{ width: 100%; border-collapse: collapse; text-align: center; font-size: 11px; table-layout: fixed; }}
            th {{ padding: 5px; background-color: #F1F5F9; border-bottom: 2px solid #CBD5E1; color: #475569; }}
            th.sat {{ color: #2563EB; }}
            th.sun {{ color: #DC2626; }}
            td {{ padding: 3px 2px; height: 44px; vertical-align: top; border: 1px solid #F1F5F9; background-color: #FFFFFF; color: #334155; }}
            td.empty {{ background-color: #F8FAFC; border: none; }}
            td.highlight {{ background-color: #D0E8FF; border: 1px solid #60A5FA; font-weight: bold; color: #1E40AF; }}
            td.sun-text {{ color: #EF4444; }}
            td.sat-text {{ color: #3B82F6; }}
            .dessert-tag {{ font-size: 10px; color: #1E3A8A; margin-top: 2px; word-break: break-all; line-height: 1.1; }}
        </style>
    </head>
    <body>
        <div class="cal-card">
            <div class="cal-title">📅 {year}년 {month}월</div>
            <table>
                <thead>
                    <tr>
                        <th>월</th><th>화</th><th>수</th><th>목</th><th>금</th>
                        <th class="sat">토</th><th class="sun">일</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for week in month_days:
        html += "<tr>"
        for day in week:
            is_current_month = (day.month == month)
            day_str = day.strftime("%Y-%m-%d")
            
            if not is_current_month:
                html += '<td class="empty"></td>'
                continue
                
            desserts = dessert_dict.get(day_str, [])
            has_dessert = len(desserts) > 0
            
            classes = []
            if has_dessert:
                classes.append("highlight")
            else:
                if day.weekday() == 6:
                    classes.append("sun-text")
                elif day.weekday() == 5:
                    classes.append("sat-text")

            class_attr = f'class="{" ".join(classes)}"' if classes else ''

            dessert_label = ""
            if has_dessert:
                dessert_names = ", ".join([d[0] for d in desserts])
                dessert_label = f'<div class="dessert-tag">🍦 {dessert_names}</div>'

            html += f"""
            <td {class_attr}>
                <div>{day.day}</div>
                {dessert_label}
            </td>
            """
        html += "</tr>"
        
    html += """
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return html


# ---------------- [ 화면 레이아웃 및 동작 ] ----------------

kst = pytz.timezone("Asia/Seoul")
today_kst = datetime.datetime.now(kst).date()

# 1. 일자 선택 영역
col_date, col_toggle = st.columns([2, 1], vertical_alignment="bottom")

with col_date:
    selected_date = st.date_input("조회할 날짜를 선택하세요:", value=today_kst)

with col_toggle:
    show_allergy = st.toggle("알레르기 정보 보기", value=True)

date_str = selected_date.strftime("%Y%m%d")
single_meal_list = fetch_single_period(date_str, date_str)
meal_data = single_meal_list[0] if single_meal_list else None

st.markdown("---")

if meal_data:
    raw_dish = meal_data.get("DDISH_NM", "")
    calorie_info = meal_data.get("CAL_INFO", "정보 없음")
    menu_list = parse_menu_items(raw_dish, show_allergy)

    metric_col1, metric_col2 = st.columns(2)
    with metric_col1:
        st.metric(label="🍴 메뉴 가짓수", value=f"{len(menu_list)}개")
    with metric_col2:
        st.metric(label="🔥 칼로리", value=calorie_info)

    st.markdown("### 🥗 선택한 날짜 급식 메뉴")
    cols_per_row = 3
    for i in range(0, len(menu_list), cols_per_row):
        row_items = menu_list[i : i + cols_per_row]
        cols = st.columns(len(row_items))
        for col, item in zip(cols, row_items):
            with col:
                st.info(f"**{item}**")
else:
    st.warning("⚠️ 급식이 없는 날입니다.")

st.markdown("---")

# 2. 인증키 적용 6개월 데이터 통합 수집
st.subheader("📊 최근 6개월 후식 분석 & 달력 현황")

with st.spinner("나이스 API 키를 활용하여 6개월 급식 데이터를 안전하게 가져오는 중..."):
    half_year_data = fetch_6months_data(today_kst)

if half_year_data:
    st.write("**확인하고 싶은 후식 종류를 선택하세요:**")
    chk_cols = st.columns(3)
    with chk_cols[0]:
        chk_fruit = st.checkbox("🍎 과일", value=True)
    with chk_cols[1]:
        chk_drink = st.checkbox("🧃 음료수", value=True)
    with chk_cols[2]:
        chk_dessert = st.checkbox("🍰 디저트", value=True)

    selected_categories = []
    if chk_fruit: selected_categories.append("과일")
    if chk_drink: selected_categories.append("음료수")
    if chk_dessert: selected_categories.append("디저트")

    weekday_names = ["월요일", "화요일", "수요일", "목요일", "금요일"]
    weekday_counts = {day: 0 for day in weekday_names}
    matched_records = []
    dessert_by_date = {}
    
    total_school_days = len(half_year_data)

    for row in half_year_data:
        ymd_str = row.get("MLSV_YMD", "")
        if not ymd_str:
            continue

        dt = datetime.datetime.strptime(ymd_str, "%Y%m%d")
        weekday_idx = dt.weekday()
        if weekday_idx >= 5:
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

        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric(label="🗓️ 최근 6개월 총 급식일", value=f"{total_school_days}일")
        with m_col2:
            st.metric(label="🧁 후식 총 제공 횟수", value=f"{total_dessert_count}회")
        with m_col3:
            st.metric(label="🔄 평균 제공 주기", value=f"약 {avg_days}일마다 1번")

        best_day = max(weekday_counts, key=weekday_counts.get)
        max_count = weekday_counts[best_day]

        st.success(
            f"🎉 인증키를 이용하여 6개월간 총 **{total_school_days}일의 급식 중 {total_dessert_count}회**의 후식을 조회했습니다.\n\n"
            f"📌 가장 후식이 자주 나온 요일은 **{best_day}**입니다. (총 {max_count}회)"
        )

        # 요일별 차트
        df_counts = pd.DataFrame(list(weekday_counts.items()), columns=["요일", "제공 횟수"])
        df_counts["요일"] = pd.Categorical(df_counts["요일"], categories=weekday_names, ordered=True)
        df_counts = df_counts.sort_values("요일")
        st.bar_chart(df_counts, x="요일", y="제공 횟수")

        # 6개 월 달력 표시
        st.markdown("---")
        st.markdown("#### 📅 월별 디저트 달력")

        for i in range(5, -1, -1):
            t_dt = today_kst - relativedelta(months=i)
            y, m = t_dt.year, t_dt.month
            cal_html = render_month_calendar_html(y, m, dessert_by_date)
            components.html(cal_html, height=360, scrolling=False)

        with st.expander(f"🔍 전체 후식 제공 목록 보기 (총 {total_dessert_count}건)"):
            st.dataframe(pd.DataFrame(matched_records), use_container_width=True)
    else:
        st.info("선택한 후식이 제공된 날이 없습니다.")
else:
    st.info("최근 6개월 급식 데이터를 불러올 수 없습니다.")
