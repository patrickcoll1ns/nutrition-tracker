def main():
    entries = []
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
        except EOFError:
            break
    print(f"Calories: {total_calories(entries)}")
    print(f"Protein: {total_protein(entries)}")
    print(f"Carbs: {total_carbs(entries)}")
    print(f"Fat: {total_fat(entries)}")


def make_entry(date, food, calories, protein, carbs, fat):
    return {"date": date, "food": food, "calories": calories, "protein": protein,
            "carbs": carbs, "fat": fat}

def total_calories(entries):
    total = 0
    for entry in entries:
        total += entry["calories"]
    return total

def total_protein(entries):
    total = 0
    for entry in entries:
        total += entry["protein"]
    return total

def total_carbs(entries):
    total = 0
    for entry in entries:
        total += entry["carbs"]
    return total

def total_fat(entries):
    total = 0
    for entry in entries:
        total += entry["fat"]
    return total


if __name__ == "__main__":
    main()