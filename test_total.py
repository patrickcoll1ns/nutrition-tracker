from project import total
import pytest

entries = [{"date": "7/11/26", 
                "food": "chicken", 
                "calories": 190, 
                "protein": 30.0, 
                "carbs": 4.5, 
                "fat": 0.3}, 
                {"date": "7/11/26", 
                 "food": "rice", 
                 "calories": 90, 
                 "protein": 4.0, 
                 "carbs": 40.0, 
                 "fat": 0.4}, 
                 {"date": "7/12/26", 
                  "food": "broccoli", 
                  "calories": 40, 
                  "protein": 3.0, 
                  "carbs": 15.0, 
                  "fat": 0.3}]


@pytest.mark.parametrize("macro, expected", [
    ("calories", 320), 
    ("protein", pytest.approx(37.0)),
    ("carbs", pytest.approx(59.5)),
    ("fat", pytest.approx(1.0))
])

def test_macros(macro, expected):
    assert total(entries, macro) == expected

def test_emptyList():
    entries = []
    assert total(entries, 'calories') == 0
    assert total(entries, 'protein') == 0
    assert total(entries, 'carbs') == 0
    assert total(entries, 'fat') == 0

def test_nonMacro():
    with pytest.raises(KeyError):
        total(entries, 'sodium')