from src.utils.text_processing import extract_artist_from_title, clean_japanese_artist_name

def test_extract_artist_brackets():
    assert extract_artist_from_title("【Official髭男dism】Pretender") == "Official髭男dism"

def test_extract_artist_hyphen():
    assert extract_artist_from_title("Lady Gaga - Bad Romance") == "Lady Gaga"
    
def test_extract_artist_slash():
    assert extract_artist_from_title("/ Ado : Usseewa") == "Ado"

def test_extract_artist_none():
    assert extract_artist_from_title("Just a random title") is None

def test_clean_japanese_artist():
    assert clean_japanese_artist_name("米津玄師 Kenshi Yonezu") == "米津玄師"
    assert clean_japanese_artist_name("Kenshi Yonezu 米津玄師") == "米津玄師"
    assert clean_japanese_artist_name("Official髭男dism") == "Official髭男dism"
