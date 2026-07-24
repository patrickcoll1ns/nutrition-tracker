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
                entry = make_entry(todays_date, item["food"], item["calories"], item["protein"], item["carbs"], item["fat"])
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

def make_entry(date, food, calories, protein, carbs, fat):
    return {"date": date, "food": food, "calories": calories, "protein": protein,
            "carbs": carbs, "fat": fat}

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
    return parse_response(call_model(text))

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

if __name__ == "__main__":
    main()