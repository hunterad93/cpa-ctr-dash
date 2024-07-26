import openai
import streamlit as st

# Set up OpenAI API key
openai.api_key = st.secrets["OPENAI_API_KEY"]

def categorize_advertiser(advertiser_name, categories):
    """
    Use ChatGPT to categorize an advertiser based on their name.
    
    :param advertiser_name: str, name of the advertiser
    :param categories: list of str, available categories
    :return: str, the chosen category
    """
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
        print(category)
        # Ensure the returned category is in the list of categories
        if category not in categories:
            return "Uncategorized"
        
        return category
    
    except Exception as e:
        print(f"Error categorizing {advertiser_name}: {str(e)}")
        return "Uncategorized"

def batch_categorize_advertisers(advertisers, categories):
    """
    Categorize a batch of advertisers.
    
    :param advertisers: list of str, names of advertisers
    :param categories: list of str, available categories
    :return: dict, mapping of advertiser names to categories
    """
    categorized = {}
    for advertiser in advertisers:
        category = categorize_advertiser(advertiser, categories)
        categorized[advertiser] = category
    return categorized