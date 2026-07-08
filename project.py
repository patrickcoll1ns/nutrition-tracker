date = "7/7/2026"
food = "chicken breast"
calories = 165
protein = 30
carbs = 0
fat = 3
entry0 = {"date": date, "food": food, "calories": calories, "protein": protein,
         "carbs": carbs, "fat": fat}
date = "7/7/2026"
food = "rice"
calories = 205
protein = 4.3
carbs = 44.5
fat = 0.4
entry1 = {"date": date, "food": food, "calories": calories, "protein": protein,
         "carbs": carbs, "fat": fat}
date = "7/7/2026"
food = "broccoli"
calories = 90
protein = 2.5
carbs = 6
fat = 0.3
entry2 = {"date": date, "food": food, "calories": calories, "protein": protein,
         "carbs": carbs, "fat": fat}
entries = [entry0, entry1, entry2]
total = 0
for entry in entries:
    total += entry["calories"]
print(total)