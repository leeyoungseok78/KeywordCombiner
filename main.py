import streamlit as st
import pandas as pd
from utils import combine_keywords, categorize_keywords
from data_handler import load_predefined_data, save_to_csv, update_database_from_excel, create_korean_regions_table
from io import BytesIO
import itertools
import logging
import tempfile
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Korean Keyword Combination Tool", page_icon="assets/favicon.ico")

st.title("한국어 키워드 조합 도구")
st.subheader("지역별 키워드 생성기")

if create_korean_regions_table():
    st.success("데이터베이스 테이블이 성공적으로 생성되었습니다.")
else:
    st.error("데이터베이스 테이블 생성 중 오류가 발생했습니다. 관리자에게 문의해 주세요.")

@st.cache_data
def load_predefined_data_cached():
    return load_predefined_data()

regions_df = load_predefined_data_cached()

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

st.header("데이터 입력")

st.info("엑셀 파일의 첫 번째 행은 제목으로 사용되며, 2행부터 데이터로 처리됩니다.")

uploaded_file = st.file_uploader("엑셀 파일 업로드", type=["xlsx", "xls"])
if uploaded_file is not None:
    try:
        xls = pd.ExcelFile(uploaded_file)
        selected_sheets = st.multiselect("처리할 시트 선택", xls.sheet_names)

        if selected_sheets:
            selected_data = {}
            for sheet in selected_sheets:
                st.subheader(f"{sheet} 시트")
                df = pd.read_excel(xls, sheet_name=sheet, header=0)
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

            if st.button("데이터베이스 업데이트"):
                if update_database_from_excel(df):
                    st.success("데이터베이스가 성공적으로 업데이트되었습니다.")
                    regions_df = load_predefined_data_cached()
                else:
                    st.error("데이터베이스 업데이트 중 오류가 발생했습니다.")
            
            if st.session_state.page == "select":
                if all(len(st.session_state[f'selected_columns_{sheet}']) >= 1 for sheet in selected_sheets):
                    if st.button("다음 단계로"):
                        st.session_state.page = "combine"
                        st.session_state.selected_data = selected_data
                        st.rerun()
                else:
                    st.warning("모든 선택된 시트에서 최소 1개 이상의 열을 선택해 주세요.")

            elif st.session_state.page == "combine":
                st.subheader("키워드 조합")
                selected_data = st.session_state.selected_data
                for sheet, data in selected_data.items():
                    st.write(f"{sheet} 시트 선택된 데이터:")
                    st.dataframe(data)

                st.subheader("키워드 입력")
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

                if st.button("키워드 생성"):
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
                        
                        space_conditions = [space_before_B] + [st.session_state.get(f"space_after_{chr(65+i)}", True) for i in range(len(keyword_inputs)-1)]
                        combined_df['Combined_Keyword'] = combined_df.apply(lambda row: ''.join([' ' + str(row[f'Keyword_{key}']) if cond else str(row[f'Keyword_{key}']) for (key, _), cond in zip(keyword_inputs, space_conditions)]), axis=1)
                        combined_df['Combined_Keyword'] = combined_df['Region'] + combined_df['Combined_Keyword']

                        categorized_df = categorize_keywords(combined_df, regions_df)
                        
                        categorized_df = categorized_df.reset_index(drop=True)
                        categorized_df.index += 1
                        
                        st.header("생성된 키워드")
                        st.dataframe(categorized_df)
                        st.write(f"총 생성된 키워드 수: {len(categorized_df)}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("CSV로 내보내기"):
                            try:
                                logger.info("CSV export button clicked")
                                output = BytesIO()
                                categorized_df.to_csv(output, index=False, encoding='utf-8-sig')
                                output.seek(0)
                                st.download_button(
                                    label="CSV 다운로드",
                                    data=output,
                                    file_name="combined_keywords.csv",
                                    mime="text/csv; charset=utf-8",
                                )
                                logger.info("CSV download button added successfully")
                            except Exception as e:
                                logger.error(f"Error in CSV export process: {str(e)}", exc_info=True)
                                st.error(f"CSV 파일 생성 중 오류가 발생했습니다: {str(e)}")
                    with col2:
                        if st.button("엑셀로 내보내기"):
                            try:
                                logger.info("Excel export button clicked")
                                output = BytesIO()
                                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                    categorized_df.to_excel(writer, sheet_name="Combined Keywords", index=False)
                                output.seek(0)
                                st.download_button(
                                    label="엑셀 파일 다운로드",
                                    data=output,
                                    file_name="combined_keywords.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                                logger.info("Excel download button added successfully")
                            except Exception as e:
                                logger.error(f"Error in Excel export process: {str(e)}", exc_info=True)
                                st.error(f"엑셀 파일 생성 중 오류가 발생했습니다: {str(e)}")
    except Exception as e:
        st.error(f"엑셀 파일을 처리하는 중 오류가 발생했습니다: {str(e)}")

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
    "- '데이터베이스 업데이트' 버튼을 클릭하여 업로드된 엑셀 파일의 데이터로 데이터베이스를 업데이트할 수 있습니다.\n"
    "- 에러 처리가 개선되어 더 친화적인 메시지를 제공합니다.\n\n"
    "**사용 방법**:\n"
    "1. 엑셀 파일을 업로드하고 처리할 시트를 선택합니다.\n"
    "2. 각 시트에서 처리할 열을 선택하고 '다음 단계로' 버튼을 클릭합니다.\n"
    "3. 키워드 B와 추가 키워드를 입력하고 각 키워드 사이의 공백 추가 여부를 선택합니다.\n"
    "4. '키워드 생성' 버튼을 클릭하여 키워드를 조합합니다.\n"
    "5. 결과를 확인하고 필요한 경우 CSV 또는 엑셀 파일로 내보냅니다."
)

if not regions_df.empty:
    st.success("지역 데이터가 성공적으로 로드되었습니다.")
else:
    st.warning("지역 데이터를 로드하는 데 문제가 발생했습니다. 엑셀 파일을 업로드하고 데이터베이스를 업데이트해 주세요.")