import streamlit as st

from src.libs import config
from src.libs.buttons import sort

dummy_configs = [
    config.DFEColumnConfig(
        column_name="col1",
        column_config={},
        input_widget=st.text_input,
        sorting="asc",
    ),
    config.DFEColumnConfig(
        column_name="col2",
        column_config={},
        input_widget=st.number_input,
        sorting="desc",
    ),
]

sort_button = sort.SortButton("test_table", dummy_configs)

new_configs = sort_button()

print("Updated Configs:")
for cfg in new_configs or []:
    print(f"Column: {cfg.column_name}, Sorting: {cfg.sorting}")
