import json, os
from datetime import date
from dotenv import load_dotenv
import anthropic
import requests

def main():
    entries = load("entries.json")
    todays_date = date.today().isoformat()
    while True: 
        try: 
            description = input("What did you eat today? Be as specific as possible. ")
            parsed = parse_meal(description)
            if not parsed:
                print("Could not read that, try describing it differently.")
                continue
            for item in parsed:
                entry = make_entry(todays_date, item["food"], item["calories"], item["protein"], item["carbs"],
                                    item["fat"], item["usda_id"], item["usda_description"], item["grams"])
                entries.append(entry)
            save("entries.json", entries)
        except EOFError:
            print("\nFinished logging meals\n")
            break
    print(f"Calories: {total(entries_for(entries, todays_date), 'calories')}")
    print(f"Protein: {total(entries_for(entries, todays_date), 'protein')}")
    print(f"Carbs: {total(entries_for(entries, todays_date), 'carbs')}")
    print(f"Fat: {total(entries_for(entries, todays_date), 'fat')}")

def total(entries, macro):
    total_macro = 0
    for entry in entries:
        total_macro += entry[macro]
    return total_macro

def make_entry(date, food, calories, protein, carbs, fat, usda_id, usda_description, grams):
    return {"date": date, "food": food, "calories": calories, "protein": protein,
            "carbs": carbs, "fat": fat, "usda_id": usda_id,
            "usda_description": usda_description, "grams": grams}

def load(path):
    try:
        with open(path) as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    
def save(path, data):
    with open(path, "w") as file:
        json.dump(data, file)

def entries_for(entries, date):
    date_list = []
    for entry in entries:
        if entry["date"] == date:
            date_list.append(entry)
    return date_list

def get_client():
    # Shared by call_model (extraction) and select_best_match_llm (reranking).
    load_dotenv()
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def call_model(text: str):
    client = get_client()
    # usda_query carries prep/cut qualifiers (e.g. "grilled", "skinless") that
    # "food" alone would drop, so call_usda and select_best_match_llm can
    # still match on them even if they're phrased naturally in the input.
    prompt = f"""You extract foods and portion sizes from food descriptions.

Return a JSON array. Each element is one food, with these exact keys:
- "food": the food name as the user described it (string)
- "usda_query": a short USDA-style search phrase for this food, carrying over
  any preparation, cut, or qualifier mentioned or implied (e.g. "chicken
  breast, grilled, skinless") (string)
- "grams": estimated portion weight in grams (int)

Rules:
- Return ONLY the JSON array. No explanation, no markdown code fences.
- One object per distinct food. "chicken and rice" becomes two objects.
- If no quantity is given, estimate for one standard serving.
- If the input names no food, return an empty array: []

Example:
Input: "two eggs and a slice of toast"
Output: [{{"food": "eggs", "usda_query": "egg, whole, raw", "grams": 100}}, {{"food": "toast", "usda_query": "bread, toasted", "grams": 30}}]

Input: "{text}"
Output:"""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return next(block.text for block in response.content if block.type == "text")

def parse_response(raw: str):
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1] # grab the chunk between the fences
        if cleaned.startswith("json"):
            cleaned = cleaned[len("json"):] # drop the language tag
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return []
    
    if not isinstance(data, list):
        return []
    
    # Keep only entries that are well-formed and drop the rest.
    required = ("food", "grams")
    valid = []
    for item in data:
        if isinstance(item, dict) and all(key in item for key in required):
            valid.append(item)
        
    return valid

def parse_meal(text: str):
    foods = parse_response(call_model(text))
    meals = []
    for item in foods:
        # Fall back to the plain food name if the model ever omits usda_query.
        query = item.get("usda_query") or item["food"]
        candidates = parse_usda_response(call_usda(query))
        try:
            match = select_best_match_llm(candidates, item["food"])
        except Exception:
            # LLM reranking is a nice-to-have; fall back to the word-overlap
            # heuristic rather than dropping the food on a network/API hiccup.
            match = select_best_match(candidates, query)
        if match is None:
            continue
        macros = scale_macros(match, item["grams"])
        meals.append({
            "food": item["food"],
            "grams": item["grams"],
            "calories": macros["calories"],
            "protein": macros["protein"],
            "carbs": macros["carbs"],
            "fat": macros["fat"],
            "usda_id": match["fdc_id"],
            "usda_description": match["description"],
        })
    return meals

def call_usda(food_name: str):
    load_dotenv()
    api_key = os.environ["USDA_API_KEY"]
    response = requests.post(
        "https://api.nal.usda.gov/fdc/v1/foods/search",
        params={"api_key": api_key},
        json={
            "query": food_name,
            "pageSize": 10,
            "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)"],
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()

def parse_usda_response(data: dict):
    foods = data.get("foods", [])
    if not isinstance(foods, list):
        return []

    parsed = []
    for food in foods:
        nutrients = food.get("foodNutrients", [])
        calories = next((n for n in nutrients
                          if n.get("nutrientName") == "Energy" and n.get("unitName") == "KCAL"), None)
        protein = next((n for n in nutrients if n.get("nutrientName") == "Protein"), None)
        carbs = next((n for n in nutrients if n.get("nutrientName") == "Carbohydrate, by difference"), None)
        fat = next((n for n in nutrients if n.get("nutrientName") == "Total lipid (fat)"), None)

        if not all([calories, protein, carbs, fat]):
            continue

        parsed.append({
            "fdc_id": food.get("fdcId"),
            "description": food.get("description"),
            "calories": calories["value"],
            "protein": protein["value"],
            "carbs": carbs["value"],
            "fat": fat["value"],
        })

    return parsed

def select_best_match_llm(foods, query):
    if not foods:
        return None
    if len(foods) == 1:
        return foods[0]  # nothing to rank, skip the model call

    # Candidates are indexed rather than passed by fdc_id so the model can
    # just answer with a small integer instead of copying an id string.
    listing = "\n".join(
        f"{i}: {food['description']}" for i, food in enumerate(foods)
    )
    prompt = f"""You match a food description to the closest USDA database entry.

Food described by the user: "{query}"

Candidate USDA entries:
{listing}

Return ONLY the number of the single best-matching entry, with no other
text. If none of them reasonably match the described food, return -1.
"""

    client = get_client()
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=16,
        messages=[{"role": "user", "content": prompt}],
    )
    text = next(block.text for block in response.content if block.type == "text")
    index = int(text.strip())  # raises ValueError on a garbled reply

    if index < 0 or index >= len(foods):
        return None  # model said -1 (no good match) or gave a bogus index
    return foods[index]

def select_best_match(foods, query):
    if not foods:
        return None

    preparation_words = {
        "raw", "baked", "fried", "cooked", "boiled", "grilled",
        "roasted", "dried", "dehydrated", "powder", "chips",
    }
    query_words = set(query.lower().replace(",", "").split())
    query_has_preparation = bool(query_words & preparation_words)

    def score(food):
        description_words = set(
            food["description"].lower().replace(",", "").split()
        )
        matching_words = len(query_words & description_words)
        raw_bonus = (
            1
            if not query_has_preparation and "raw" in description_words
            else 0
        )
        extra_words = len(description_words - query_words)
        return matching_words, raw_bonus, -extra_words

    return max(foods, key=score)

def scale_macros(macros_per_100g, grams):
    factor = grams / 100
    return {
        "calories": macros_per_100g["calories"] * factor,
        "protein": macros_per_100g["protein"] * factor,
        "carbs": macros_per_100g["carbs"] * factor,
        "fat": macros_per_100g["fat"] * factor,
    }

if __name__ == "__main__":
    main()
