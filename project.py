import json
from datetime import date

def main():
    entries = load("entries.json")
    todays_date = date.today().isoformat()
    while True: 
        try: 
            food = input("What food did you eat? ")
            calories = int(input("How many calories did it have? "))
            protein = float(input("How many grams of protein did it have? "))
            carbs = float(input("How many grams of carbs did it have? "))
            fat = float(input("How many grams of fat did it have? "))
            entry = make_entry(todays_date, food, calories, protein, carbs, fat)
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
    except FileNotFoundError:
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


if __name__ == "__main__":
    main()