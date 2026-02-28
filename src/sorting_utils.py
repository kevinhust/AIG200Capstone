"""
Sorting utilities for the AIG200Capstone project.
[思维过程]: 
1. 目标：实现一个通用的数据排序函数 `sort_data`。
2. 逻辑：支持列表、元组、字典列表。支持自定义键和降序。
3. 健壮性：处理空数据和无效键。
"""

def sort_data(data, key=None, reverse=False):
    """
    Sorts a list of records (dicts, tuples, or primitives).
    
    Args:
        data (list): The list to sort.
        key (str/callable): The key to sort by (if dicts) or a lambda.
        reverse (bool): Whether to sort in descending order.
        
    Returns:
        list: The sorted list.
    """
    if not data:
        return []
    
    # Handle dictionary sorting if key is provided as a string
    if isinstance(key, str) and all(isinstance(item, dict) for item in data):
        # Handle dictionary sorting with None safety
        return sorted(data, key=lambda x: (x.get(key) is None, x.get(key)), reverse=reverse)
    
    # Standard sorting
    return sorted(data, key=key, reverse=reverse)
