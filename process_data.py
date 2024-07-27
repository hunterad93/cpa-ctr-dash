import pandas as pd
import numpy as np
from fuzzywuzzy import process
import os
from ai_categorizer import categorize_advertiser

def load_and_preprocess_multiple_files(folder_path, sheet_name):
    all_data = []
    for file in os.listdir(folder_path):
        if file.endswith('.xlsx'):
            file_path = os.path.join(folder_path, file)
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            print(df.columns)
            all_data.append(df)
    return pd.concat(all_data, ignore_index=True)

def load_and_preprocess_data(file_path, sheet_name):
    return pd.read_excel(file_path, sheet_name=sheet_name)

def get_best_match(name, choices, score_cutoff=90):
    best_match = process.extractOne(name, choices, score_cutoff=score_cutoff)
    return best_match if best_match else None

def hierarchical_match(advertiser, df_lookup, columns_to_check):
    for column in columns_to_check:
        match = get_best_match(advertiser, df_lookup[column].unique())
        if match:
            return match[0], match[1], column
    return None, None, None

def create_vertical_mapping(advertisers, df_lookup):
    columns_to_check = ['Company Name', 'Quickbooks Customer Name', 'Client Group']
    categories = df_lookup['Client Industry Value'].dropna().unique().tolist()
    
    vertical_mapping = []
    for advertiser in advertisers:
        vertical, matched_name, matched_column = categorize_advertiser(advertiser, categories, df_lookup, columns_to_check)
        
        vertical_mapping.append({
            'Advertiser': advertiser,
            'Matched_Company': matched_name if matched_name else 'NO MATCH',
            'Vertical': vertical,
            'Match_Score': None,  # We don't have a score for LLM matching
            'Categorization_Technique': matched_column
        })
    
    return pd.DataFrame(vertical_mapping)

def calculate_vertical_metrics(df):
    grouped = df.groupby(['Vertical', '3rd Party Data Brand', '3rd Party Data ID', 'Advertiser'])
    vertical_metrics = grouped.agg({
        'Clicks': 'sum',
        'Impressions': 'sum',
        'Hypothetical Advertiser Cost (Adv Currency)': 'sum',
        'All Last Click + View Conversions': 'sum'
    }).reset_index()
    
    vertical_metrics['CTR'] = vertical_metrics['Clicks'] / vertical_metrics['Impressions']
    vertical_metrics['CPA'] = vertical_metrics['Hypothetical Advertiser Cost (Adv Currency)'] / vertical_metrics['All Last Click + View Conversions']
    
    vertical_metrics = vertical_metrics[~vertical_metrics['CPA'].isin([np.inf, -np.inf, np.nan, 0])]
    
    return vertical_metrics

if __name__ == "__main__":
    folder_path = '/Users/adamhunter/Downloads/bulk_element_performance'
    lookup_file_path = '/Users/adamhunter/Downloads/Master Lookup - TC.xlsx'
    intermediate_csv_path = 'intermediate_main_data.csv'
    vertical_mapping_path = 'vertical_mapping.csv'

    # Step 1: Load and preprocess main data
    if not os.path.exists(intermediate_csv_path):
        print("Processing raw data files...")
        df_main = load_and_preprocess_multiple_files(folder_path, 'Data Element_data')
        df_main.to_csv(intermediate_csv_path, index=False)
        print(f"Intermediate data saved to '{intermediate_csv_path}'")
    else:
        print(f"Loading intermediate data from '{intermediate_csv_path}'")
        df_main = pd.read_csv(intermediate_csv_path, low_memory=False)

    # Step 2: Extract unique advertisers
    unique_advertisers = df_main['Advertiser'].unique()

    # Step 3 & 4: Create and save vertical mapping
    if not os.path.exists(vertical_mapping_path):
        print("Creating vertical mapping...")
        df_lookup = load_and_preprocess_data(lookup_file_path, 'Master Lookup')
        vertical_mapping = create_vertical_mapping(unique_advertisers, df_lookup)
        vertical_mapping.to_csv(vertical_mapping_path, index=False)
        print(f"Vertical mapping saved to '{vertical_mapping_path}'")
    else:
        print(f"Loading vertical mapping from '{vertical_mapping_path}'")
        vertical_mapping = pd.read_csv(vertical_mapping_path)

    # Step 5: Merge vertical mapping with main data
    df_merged = df_main.merge(vertical_mapping[['Advertiser', 'Vertical']], on='Advertiser', how='left')

    # Step 6: Calculate final metrics
    vertical_metrics_df = calculate_vertical_metrics(df_merged)

    vertical_metrics_df = vertical_metrics_df.drop(columns=['Advertiser'], errors='ignore')

    # Save results
    vertical_metrics_df.to_csv('processed_vertical_metrics.csv', index=False)
    print("Processed data saved to 'processed_vertical_metrics.csv'")