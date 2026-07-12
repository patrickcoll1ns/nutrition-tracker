import json

def main():
    entries = load("entries.txt")
    date = input("What is the date today? ")
    while True: 
        try: 
            food = input("What food did you eat? ")
            calories = int(input("How many calories did it have? "))
            protein = float(input("How many grams of protein did it have? "))
            carbs = float(input("How many grams of carbs did it have? "))
            fat = float(input("How many grams of fat did it have? "))
            entry = make_entry(date, food, calories, protein, carbs, fat)
            entries.append(entry)
            save("entries.txt", entries)
        except EOFError:
            break
    print(f"Calories: {total(entries, 'calories')}")
    print(f"Protein: {total(entries, 'protein')}")
    print(f"Carbs: {total(entries, 'carbs')}")
    print(f"Fat: {total(entries, 'fat')}")

def total(entries, macro):
    total_macro = 0
    for entry in entries:
        total_macro += entry[macro]
    return total_macro

def make_entry(date, food, calories, protein, carbs, fat):
    return {"date": date, "food": food, "calories": calories, "protein": protein,
            "carbs": carbs, "fat": fat}

def load(f):
    try:
        with open(f) as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    
def save(path, data):
    with open(path, "w") as file:
        json.dump(data, file)



if __name__ == "__main__":
    main()