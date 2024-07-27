import openai
import streamlit as st
from fuzzywuzzy import process
from concurrent.futures import ThreadPoolExecutor, as_completed


# Set up OpenAI API key
openai.api_key = st.secrets["OPENAI_API_KEY"]

def get_top_matches(name, choices, n=10):
    return process.extract(name, choices, limit=n)

def llm_choose_match(advertiser_name, top_matches):
    matches_str = "\n".join([f"{match[0]} (Score: {match[1]})" for match in top_matches])
    prompt = f"""
    Given the advertiser name "{advertiser_name}", choose the best matching company from the following list:
    {matches_str}

    Respond with only the exact company name you've chosen, no explanation or anything else.
    If none of the options seem like a good match, respond with "No match".
    """

    def fetch_response():
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that matches advertisers to companies."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                n=1,
                stop=None,
                temperature=0,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error matching {advertiser_name}: {str(e)}")
            return None

    with ThreadPoolExecutor() as executor:
        future = executor.submit(fetch_response)
        chosen_match = future.result()

    return chosen_match if chosen_match != "No match" else None

def categorize_advertiser(advertiser_name, categories, df_lookup, columns_to_check):
    def fetch_top_matches(column):
        return get_top_matches(advertiser_name, df_lookup[column].unique())

    # First, try to find a match using the LLM in parallel
    with ThreadPoolExecutor() as executor:
        future_to_column = {executor.submit(fetch_top_matches, column): column for column in columns_to_check}
        all_top_matches = []
        for future in as_completed(future_to_column):
            all_top_matches.extend(future.result())

    chosen_match = llm_choose_match(advertiser_name, all_top_matches)

    if chosen_match:
        # Find the vertical for the chosen match
        for column in columns_to_check:
            if chosen_match in df_lookup[column].values:
                vertical = df_lookup.loc[df_lookup[column] == chosen_match, 'Client Industry Value'].iloc[0]
                return vertical, chosen_match, 'Matched'

    # If no match is found, use the original categorization method
    prompt = f"""
    Given the advertiser name "{advertiser_name}", choose the most appropriate category from the following list:
    {', '.join(categories)}
    
    Respond with only the category name precisely as written, no explanation or anything else, your response is being used to fill in a spreadsheet.
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that categorizes advertisers."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            n=1,
            stop=None,
            temperature=0,
        )

        category = response.choices[0].message.content.strip()
        if category not in categories:
            return "Uncategorized", None, 'AI Categorized'

        return category, None, 'AI Categorized'

    except Exception as e:
        print(f"Error categorizing {advertiser_name}: {str(e)}")
        return "Uncategorized", None, 'AI Categorized'