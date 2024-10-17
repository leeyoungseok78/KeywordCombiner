import streamlit as st
import pandas as pd
from utils import combine_keywords, categorize_keywords, process_excel_file
from io import BytesIO
import itertools
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="한국어 키워드 조합 도구", page_icon="assets/favicon.ico")

# Add custom CSS for Korean font support
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    st.title("한국어 키워드 조합 도구")
    st.subheader("지역별 키워드 생성기")

    if 'page' not in st.session_state:
        st.session_state.page = "select"
    if 'additional_keywords' not in st.session_state:
        st.session_state.additional_keywords = []
    if 'space_after_A' not in st.session_state:
        st.session_state.space_after_A = True

    st.sidebar.title("작업 관리")
    if st.sidebar.button("초기화"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "select"
        st.session_state.additional_keywords = []
        st.rerun()

    if st.session_state.page == "select":
        select_page()
    elif st.session_state.page == "combine":
        combine_page()

def select_page():
    st.header("데이터 입력")
    st.info("엑셀 파일의 첫 번째 행은 제목으로 사용되며, 2행부터 데이터로 처리됩니다.")

    uploaded_file = st.file_uploader("엑셀 파일 업로드", type=["xlsx", "xls"])
    if uploaded_file is not None:
        process_uploaded_file(uploaded_file)

def combine_page():
    st.subheader("키워드 조합")
    selected_data = st.session_state.selected_data
    for sheet, data in selected_data.items():
        st.write(f"{sheet} 시트 선택된 데이터:")
        st.dataframe(data)

    st.subheader("키워드 입력")
    keyword_inputs = process_keyword_inputs()

    if st.button("키워드 생성"):
        generate_keywords(selected_data, keyword_inputs)

    # 키워드가 생성되었을 때 내보내기 버튼을 표시
    if 'categorized_df' in st.session_state:
        st.header("생성된 키워드")
        st.dataframe(st.session_state.categorized_df)
        st.write(f"총 생성된 키워드 수: {len(st.session_state.categorized_df)}")
        display_export_buttons()

def process_uploaded_file(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        selected_sheets = st.multiselect("처리할 시트 선택", xls.sheet_names)

        if selected_sheets:
            selected_data = {}
            for sheet in selected_sheets:
                process_sheet(xls, sheet, selected_data)
            
            if all(len(st.session_state[f'selected_columns_{sheet}']) >= 1 for sheet in selected_sheets):
                if st.button("다음 단계로"):
                    st.session_state.page = "combine"
                    st.session_state.selected_data = selected_data
                    st.rerun()
            else:
                st.warning("모든 선택된 시트에서 최소 1개 이상의 열을 선택해 주세요.")
    except Exception as e:
        st.error(f"엑셀 파일을 처리하는 중 오류가 발생했습니다: {str(e)}")

def process_sheet(xls, sheet, selected_data):
    st.subheader(f"{sheet} 시트")
    df = process_excel_file(xls, sheet)
    st.write(f"{sheet} 시트 데이터:")
    st.dataframe(df)
    
    st.subheader(f"{sheet} 시트 열 선택")
    st.info("처리할 열을 선택해 주세요. 최소 1개 이상의 열을 선택해야 합니다.")

    if f'selected_columns_{sheet}' not in st.session_state:
        st.session_state[f'selected_columns_{sheet}'] = []

    column_options = df.columns.tolist()
    selected_columns = st.multiselect(f"{sheet} 시트에서 처리할 열 선택", column_options, key=f"multiselect_{sheet}")
    st.session_state[f'selected_columns_{sheet}'] = [df.columns.get_loc(col) for col in selected_columns]

    st.markdown(f"**선택된 열 ({sheet}):** {', '.join(selected_columns)}")

    selected_data[sheet] = df[selected_columns]

def process_keyword_inputs():
    keyword_inputs = []

    if "space_before_B" not in st.session_state:
        st.session_state.space_before_B = True

    space_before_B = st.checkbox("선택된 데이터와 키워드 B 사이에 공백 추가", key="space_before_B")

    keyword_b = st.text_area("키워드 B 입력 (줄바꿈으로 구분)", height=100)
    keyword_inputs.append(("B", keyword_b))

    for i, keyword in enumerate(st.session_state.additional_keywords):
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            new_keyword = st.text_area(f"키워드 {chr(67+i)} 입력 (줄바꿈으로 구분)", value=keyword, height=100, key=f"keyword_{chr(67+i)}")
        with col2:
            if st.button(f"- 삭제", key=f"remove_{i}"):
                st.session_state.additional_keywords.pop(i)
                st.rerun()
        with col3:
            if f"space_after_{chr(66+i)}" not in st.session_state:
                st.session_state[f"space_after_{chr(66+i)}"] = True

            space_after = st.checkbox(f"공백 추가 (키워드 {chr(66+i)} 뒤)", key=f"space_{chr(66+i)}")
        keyword_inputs.append((chr(67+i), new_keyword))

    if st.button("+ 키워드 추가"):
        st.session_state.additional_keywords.append("")
        st.rerun()

    return keyword_inputs

def generate_keywords(selected_data, keyword_inputs):
    with st.spinner("키워드 생성 중..."):
        combined_df = pd.DataFrame(columns=['Region'] + [f'Keyword_{key}' for key, _ in keyword_inputs])
        keywords_lists = [
            [k.strip() for k in keyword.split('\n') if k.strip()]
            for _, keyword in keyword_inputs
        ]
        
        all_combinations = list(itertools.product(*keywords_lists))
        
        all_rows = []
        
        for sheet, data in selected_data.items():
            for _, row in data.iterrows():
                for col in data.columns:
                    region = row[col]
                    if pd.notna(region):
                        for combination in all_combinations:
                            new_row = {'Region': region}
                            for i, keyword in enumerate(combination):
                                new_row[f'Keyword_{keyword_inputs[i][0]}'] = keyword
                            all_rows.append(new_row)
        
        combined_df = pd.DataFrame(all_rows)
        
        space_conditions = [st.session_state.space_before_B] + [st.session_state.get(f"space_after_{chr(65+i)}", True) for i in range(len(keyword_inputs)-1)]
        combined_df['Combined_Keyword'] = combined_df.apply(lambda row: ''.join([' ' + str(row[f'Keyword_{key}']) if cond else str(row[f'Keyword_{key}']) for (key, _), cond in zip(keyword_inputs, space_conditions)]), axis=1)
        combined_df['Combined_Keyword'] = combined_df['Region'] + combined_df['Combined_Keyword']

        categorized_df = categorize_keywords(combined_df)
        
        categorized_df = categorized_df.reset_index(drop=True)
        categorized_df.index += 1
        
        st.session_state.categorized_df = categorized_df  # 생성된 데이터를 세션 상태에 저장

def display_export_buttons():
    col1, col2 = st.columns(2)
    with col1:
        txt_data = st.session_state.categorized_df.to_csv(index=False, sep='\t', encoding='utf-8')
        st.download_button(
            label="TXT로 내보내기",
            data=txt_data,
            file_name="combined_keywords.txt",
            mime="text/plain",
        )
    with col2:
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            st.session_state.categorized_df.to_excel(writer, sheet_name="Combined Keywords", index=False)
        excel_data = excel_buffer.getvalue()
        st.download_button(
            label="엑셀로 내보내기",
            data=excel_data,
            file_name="combined_keywords.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()

st.sidebar.title("도움말")
st.sidebar.info(
    "이 도구는 지역별 한국어 키워드를 생성하는 데 사용됩니다. "
    "엑셀 파일을 업로드하고 원하는 시트와 열을 선택하세요. "
    "그런 다음 키워드 B와 추가 키워드를 입력하여 키워드를 조합할 수 있습니다. "
    "키워드 생성 버튼을 클릭하면 도구가 키워드를 조합하고 지역별로 분류합니다.\n\n"
    "**새로운 기능**:\n"
    "- 엑셀 파일에서 여러 시트를 선택할 수 있습니다.\n"
    "- 각 시트에서 원하는 열을 선택할 수 있습니다.\n"
    "- 선택한 모든 데이터를 표시합니다.\n"
    "- 키워드 B와 추가 키워드를 여러 줄로 입력할 수 있습니다.\n"
    "- 키워드 추가 및 삭제 기능이 있습니다.\n"
    "- 각 키워드 사이의 공백 추가 여부를 개별적으로 선택할 수 있습니다.\n"
    "- 모든 가능한 조합으로 키워드가 생성됩니다.\n"
    "- 결과를 CSV 또는 엑셀 파일로 내보낼 수 있습니다.\n"
    "- 에러 처리가 개선되어 더 친화적인 메시지를 제공합니다.\n\n"
    "**사용 방법**:\n"
    "1. 엑셀 파일을 업로드하고 처리할 시트를 선택합니다.\n"
    "2. 각 시트에서 처리할 열을 선택하고 '다음 단계로' 버튼을 클릭합니다.\n"
    "3. 키워드 B와 추가 키워드를 입력하고 각 키워드 사이의 공백 추가 여부를 선택합니다.\n"
    "4. '키워드 생성' 버튼을 클릭하여 키워드를 조합합니다.\n"
    "5. 결과를 확인하고 필요한 경우 CSV 또는 엑셀 파일로 내보냅니다."
)
