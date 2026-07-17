from project import load, save

entry = [{"date": "7/11/2026", 
                "food": "chicken", 
                "calories": 190, 
                "protein": 30.0, 
                "carbs": 4.5, 
                "fat": 0.3}, 
            ]


def test_load_and_save(tmp_path):
    file_path = tmp_path / "entry.json"
    save(file_path, entry)
    loaded = load(file_path)
    
    assert loaded == entry


def test_fileNotFound(tmp_path):
    file_path = tmp_path / "missing.json"
    assert load(file_path) == []
