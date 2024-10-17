import pandas as pd

def combine_keywords(df):
    """
    Combine keywords from all columns except 'Region'
    """
    keyword_columns = [col for col in df.columns if col != 'Region']
    df['Combined_Keyword'] = df[keyword_columns].apply(lambda row: ' '.join(filter(None, row)), axis=1)
    return df

def categorize_keywords(df, regions_df):
    """
    Categorize keywords by region and administrative level
    """
    # Merge with regions_df to get administrative levels
    categorized_df = pd.merge(df, regions_df, left_on='Region', right_on='name', how='left')
    
    # Rename columns
    categorized_df = categorized_df.rename(columns={
        'level_1': '광역시도',
        'level_2': '시군구',
        'level_3': '읍면동'
    })
    
    # Select and order columns
    keyword_columns = [col for col in df.columns if col.startswith('Keyword_')]
    columns = ['Region'] + keyword_columns + ['Combined_Keyword', '광역시도', '시군구', '읍면동']
    categorized_df = categorized_df[columns]
    
    return categorized_df

def filter_regions(grouped_data, selected_region):
    """
    Filter regions based on the selected area
    """
    if selected_region in grouped_data.groups:
        return grouped_data.get_group(selected_region)['name'].tolist()
    return []

def process_excel_file(xls, selected_sheet):
    """
    Process selected sheet from an Excel file
    """
    df = pd.read_excel(xls, sheet_name=selected_sheet)
    if 'Region' in df.columns:
        return df
    else:
        raise ValueError(f"Sheet '{selected_sheet}' does not have the required 'Region' column")
