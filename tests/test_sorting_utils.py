import pytest
from src.sorting_utils import sort_data

def test_sort_numbers():
    assert sort_data([3, 1, 4, 1]) == [1, 1, 3, 4]

def test_sort_dicts():
    data = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
        {"name": "Charlie", "age": 35}
    ]
    sorted_data = sort_data(data, key="age")
    assert sorted_data[0]["name"] == "Bob"
    assert sorted_data[2]["name"] == "Charlie"

def test_sort_reverse():
    assert sort_data([1, 2, 5], reverse=True) == [5, 2, 1]

def test_sort_empty():
    assert sort_data([]) == []

def test_sort_missing_key():
    data = [{"a": 1}, {"b": 2}]
    # Should handle missing keys gracefully (None will be at the front)
    sorted_data = sort_data(data, key="a")
    assert len(sorted_data) == 2
