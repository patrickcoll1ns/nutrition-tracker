import json, os
from datetime import date
from dotenv import load_dotenv
import anthropic
import requests
import db

# Sane upper bounds so a joke/adversarial description ("a hundred thousand
# grapes") can't blow up memory or rack up API calls on a shared demo.
MAX_FOODS_PER_MEAL = 20
MAX_QUANTITY_PER_ITEM = 50
MAX_GRAMS_PER_ITEM = 5000
MEAL_TYPES = ("Breakfast", "Lunch", "Dinner", "Snack")


class MealLookupError(Exception):
    """Raised when Claude or USDA can't be reached. Message is safe to show
    to end users — it never includes raw exception text, which for USDA
    errors would otherwise leak the API key (it rides along in the request
    URL that requests.exceptions.* embeds in its message)."""


def main():
    db.init_db()
    todays_date = date.today().isoformat()
    while True:
        try:
            description = input("What did you eat today? Be as specific as possible. ")
            meal_type = input(
                "Meal type (Breakfast, Lunch, Dinner, or Snack): "
            ).strip().title()
            if meal_type not in MEAL_TYPES:
                print("Choose Breakfast, Lunch, Dinner, or Snack.")
                continue
            parsed, unmatched = parse_meal(description)
            if not parsed and not unmatched:
                print("Could not read that, try describing it differently.")
                continue
            for item in parsed:
                entry = make_entry(todays_date, item["food"], meal_type=meal_type,
                                    calories=item["calories"],
                                    protein=item["protein"], carbs=item["carbs"], fat=item["fat"],
                                    usda_id=item["usda_id"], usda_description=item["usda_description"],
                                    grams=item["grams"])
                db.save_entry(entry)
            if unmatched:
                print(f"Couldn't find a USDA match for: {', '.join(unmatched)} — not logged.")
        except EOFError:
            print("\nFinished logging meals\n")
            break
        except MealLookupError as e:
            print(f"\n{e}\n")
        except Exception:
            print("\nSomething went wrong parsing that meal. Please try again.\n")
    todays_entries = db.entries_for(todays_date)
    print(f"Calories: {total(todays_entries, 'calories')}")
    print(f"Protein: {total(todays_entries, 'protein')}")
    print(f"Carbs: {total(todays_entries, 'carbs')}")
    print(f"Fat: {total(todays_entries, 'fat')}")

def total(entries, macro):
    total_macro = 0
    for entry in entries:
        total_macro += entry[macro]
    return round(total_macro, 2)

def make_entry(date, food, *, calories, protein, carbs, fat, usda_id,
               usda_description, grams, meal_type="Uncategorized"):
    # calories/protein/carbs/fat/usda_id/... are keyword-only on purpose:
    # they're mostly same-typed (floats) and easy to transpose (e.g.
    # carbs/fat) if passed positionally.
    return {"date": date, "meal_type": meal_type, "food": food,
            "calories": calories, "protein": protein,
            "carbs": carbs, "fat": fat, "usda_id": usda_id,
            "usda_description": usda_description, "grams": grams}

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
- "quantity": number of separate items (positive int)
- "grams_per_item": estimated weight of one item in grams (positive number)

Rules:
- Return ONLY the JSON array. No explanation, no markdown code fences.
- One object per distinct food. "chicken and rice" becomes two objects.
- Keep quantity separate from the food name.
- Include preparation details such as raw, cooked, baked, or fried in
  "usda_query".
- If no quantity is given, use 1.
- If no weight is given, estimate one standard item's weight.
- For uncountable portions such as rice, use quantity 1 and put the
  complete portion weight in grams_per_item.
- If the input names no food, return an empty array: []

Example:
Input: "two eggs and a slice of toast"
Output: [{{"food": "egg", "usda_query": "egg, whole, cooked", "quantity": 2, "grams_per_item": 50}}, {{"food": "toast", "usda_query": "bread, toasted", "quantity": 1, "grams_per_item": 30}}]

Input: "{text}"
Output:"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
            timeout=30,
        )
    except anthropic.AnthropicError as e:
        raise MealLookupError("Could not reach the meal-parsing model. Please try again.") from e

    try:
        return next(block.text for block in response.content if block.type == "text")
    except StopIteration as e:
        raise MealLookupError("The model returned an unexpected response. Please try again.") from e

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
    required = ("food", "usda_query", "quantity", "grams_per_item")
    valid = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if not all(key in item for key in required):
            continue
        if not isinstance(item["food"], str) or not item["food"].strip():
            continue
        if not isinstance(item["usda_query"], str) or not item["usda_query"].strip():
            continue
        if isinstance(item["quantity"], bool) or not isinstance(item["quantity"], int):
            continue
        if not (0 < item["quantity"] <= MAX_QUANTITY_PER_ITEM):
            continue
        if isinstance(item["grams_per_item"], bool) or not isinstance(
            item["grams_per_item"], (int, float)
        ):
            continue
        if not (0 < item["grams_per_item"] <= MAX_GRAMS_PER_ITEM):
            continue
        valid.append(item)

    return valid[:MAX_FOODS_PER_MEAL]

def expand_food_item(item):
    portions = []
    for _ in range(item["quantity"]):
        portions.append({
            "food": item["food"],
            "usda_query": item["usda_query"],
            "grams": item["grams_per_item"],
        })
    return portions

def parse_meal(text: str):
    foods = parse_response(call_model(text))
    meals = []
    unmatched = []
    for item in foods:
        portions = expand_food_item(item)
        query = item["usda_query"]
        candidates = parse_usda_response(call_usda(query))
        try:
            match = select_best_match_llm(candidates, query)
        except Exception as e:
            # LLM reranking is a nice-to-have. A network/API failure should
            # not prevent the deterministic heuristic from trying — but log
            # it so a persistently broken reranker doesn't go unnoticed.
            print(f"select_best_match_llm failed for {query!r}: {e!r}")
            match = None
        if match is None:
            match = select_best_match(candidates, query)
        if match is None:
            unmatched.append(item["food"])
            continue
        for portion in portions:
            macros = scale_macros(match, portion["grams"])
            meals.append({
                "food": portion["food"],
                "grams": portion["grams"],
                "calories": macros["calories"],
                "protein": macros["protein"],
                "carbs": macros["carbs"],
                "fat": macros["fat"],
                "usda_id": match["fdc_id"],
                "usda_description": match["description"],
            })
    return meals, unmatched

def call_usda(food_name: str):
    load_dotenv()
    api_key = os.environ["USDA_API_KEY"]
    try:
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
    except requests.exceptions.RequestException as e:
        # Not `raise ... from e` displayed anywhere user-facing: requests
        # embeds the full request URL (including ?api_key=...) in these
        # exceptions' messages, so we deliberately don't pass str(e) along.
        raise MealLookupError("Could not reach the USDA food database. Please try again.") from e
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

        required_nutrients = (calories, protein, carbs, fat)
        if not all(required_nutrients):
            continue
        if not all(isinstance(n.get("value"), (int, float)) for n in required_nutrients):
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
        timeout=30,
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
        "calories": round(macros_per_100g["calories"] * factor, 2),
        "protein": round(macros_per_100g["protein"] * factor, 2),
        "carbs": round(macros_per_100g["carbs"] * factor, 2),
        "fat": round(macros_per_100g["fat"] * factor, 2),
    }

if __name__ == "__main__":
    main()
