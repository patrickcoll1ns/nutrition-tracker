import json, os
from datetime import date
from dotenv import load_dotenv
from google import genai
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
                                    item["fat"], item["usda_id"], item["usda_description"])
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

def make_entry(date, food, calories, protein, carbs, fat, usda_id, usda_description):
    return {"date": date, "food": food, "calories": calories, "protein": protein,
            "carbs": carbs, "fat": fat, "usda_id": usda_id, "usda_description": usda_description}

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

def call_model(text: str):
    load_dotenv()
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = f"""You extract foods and portion sizes from food descriptions.

Return a JSON array. Each element is one food, with these exact keys:
- "food": the food name (string)
- "grams": estimated portion weight in grams (int)

Rules:
- Return ONLY the JSON array. No explanation, no markdown code fences.
- One object per distinct food. "chicken and rice" becomes two objects.
- If no quantity is given, estimate for one standard serving.
- If the input names no food, return an empty array: []

Example:
Input: "two eggs and a slice of toast"
Output: [{{"food": "eggs", "grams": 100}}, {{"food": "toast", "grams": 30}}]

Input: "{text}"
Output:"""
    
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt
    )
    return response.text

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
        candidates = parse_usda_response(call_usda(item["food"]))
        match = select_best_match(candidates)
        if match is None:
            continue
        macros = scale_macros(match, item["grams"])
        meals.append({
            "food": item["food"],
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
    response = requests.get(
        "https://api.nal.usda.gov/fdc/v1/foods/search",
        params={
            "api_key": api_key,
            "query": food_name,
            "pageSize": 1,
            "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)"],
        },
    )
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

def select_best_match(foods):
    if not foods:
        return None
    return foods[0]

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