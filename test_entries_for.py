from project import entries_for, total

entries = [{"date": "7/11/2026",
            "food": "chicken",
            "calories": 190,
            "protein": 30.0,
            "carbs": 4.5,
            "fat": 0.3},
           {"date": "7/11/2026",
            "food": "rice",
            "calories": 90,
            "protein": 4.0,
            "carbs": 40.0,
            "fat": 0.4},
           {"date": "7/12/2026",
            "food": "broccoli",
            "calories": 40,
            "protein": 3.0,
            "carbs": 15.0,
            "fat": 0.3}]

def test_matching_date():
    result = entries_for(entries, "7/11/2026")
    assert len(result) == 2
    assert all(entry["date"] == "7/11/2026" for entry in result)

def test_no_match():
    assert entries_for(entries, "1/1/2026") == []

def test_empty_log():
    assert entries_for([], "7/11/2026") == []

def test_does_not_mutate_original():
    entries_for(entries, "7/11/2026")    
    assert len(entries) == 3

def test_per_day_total():
    assert total(entries_for(entries, "7/11/2026"), "calories") == 280
    assert total(entries_for(entries, "7/12/2026", "calories")) == 40