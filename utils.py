import pandas as pd

def combine_keywords(df):
    """
    Combine keywords from all columns
    """
    combined = []
    for _, row in df.iterrows():
        combined.append(' '.join(str(value) for value in row if pd.notna(value)))
    return pd.DataFrame({'combined_keyword': combined})

def categorize_keywords(df):
    """
    Categorize keywords by region and administrative level
    """
    # 키워드 카테고리화 로직 구현
    # 예시 코드:
    df['category'] = df['Combined_Keyword'].apply(lambda x: 'Category A' if 'A' in x else 'Category B')
    return df

def process_excel_file(xls, selected_sheet):
    """
    Process selected sheet from an Excel file
    """
    df = pd.read_excel(xls, sheet_name=selected_sheet, header=0)
    return df
