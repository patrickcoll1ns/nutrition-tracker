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
    print(f"Calories: {total(entries, "calories")}")
    print(f"Protein: {total(entries, "protein")}")
    print(f"Carbs: {total(entries, "carbs")}")
    print(f"Fat: {total(entries, "fat")}")

def total(entries, macro):
    total = 0
    for entry in entries:
        total += entry[macro]
    return total

def make_entry(date, food, calories, protein, carbs, fat):
    return {"date": date, "food": food, "calories": calories, "protein": protein,
            "carbs": carbs, "fat": fat}


if __name__ == "__main__":
    main()