
import pickle   
import pandas as pd
import re
import datetime
import os.path
import numpy as np
import streamlit as st
import glob


def find_newest_file(directory_path, prefix, extension):
    """
    Finds the newest file in a directory that matches a specific prefix and extension.

    Args:
        directory_path (str): The path to the directory to search.
        prefix (str): The prefix of the filename (e.g., 'log_').
        extension (str): The file extension (e.g., '.txt').

    Returns:
        str or None: The path to the newest file, or None if no file is found.
    """
    # Create the search pattern using wildcards
    pattern = os.path.join(directory_path, f"{prefix}*{extension}")
    
    # Get a list of all files matching the pattern
    # glob.glob returns full paths if the directory_path is included in the pattern
    list_of_files = glob.glob(pattern)
    
    # Filter out directories, ensuring only files are considered
    files_only = [f for f in list_of_files if os.path.isfile(f)]

    if not files_only:
        return None  # Return None if no files are found

    # Find the file with the maximum modification time (os.path.getmtime)
    latest_file = max(files_only, key=os.path.getmtime)
    
    return latest_file

directory = "./pickles" # Replace with your directory path
file_prefix = "dataframe" # Replace with your prefix
file_extension = ".pkl" # Replace with your file extension

file_path = find_newest_file(directory, file_prefix, file_extension)
print(file_path)

today = datetime.datetime.now().replace(microsecond=0)
# file_path = f"dataframe.pkl"

if not os.path.isfile(file_path):
    st.markdown(f"## OMSCS Course Occupancy")
    st.markdown(f"#### ERROR: Data unavailable. Try again later.")
    quit() 

else:
    with open(file_path, 'rb') as f:
        pickle_df = pickle.load(f)

    m_timestamp = os.path.getmtime(file_path)
    dataframe_date = datetime.datetime.fromtimestamp(m_timestamp).replace(microsecond=0)

    data_age = today-dataframe_date

df = pickle_df[['Title', 'Course Number', 'Section', 'CRN', 'Status']]
df = df.loc[df['Section'].str.startswith('O') & df['Section'].str[1].str.isdigit()] #== 'O01']
pd.set_option('display.max_colwidth', None)
def parse_integers(text):
    found = re.findall(r'\d+', str(text))
    ints = [int(x) for x in found]
    p = (ints + [0, 0, 0, 0])[:4]
    p[-1] = p[3] - p[-2]
    padded = [p[1], p[1]-p[0], p[3], p[2], 0, 0]
    padded[-2] = padded[0] - padded[1] - padded[2]
    padded[-1] = int(round(100 * (padded[1]+padded[2]) / padded[0]))
    return padded
df[['Seats Total', 'Seats Taken', 'WL Taken', 'WL Left', 'Seats Left', '% Fill Rate']] = pd.DataFrame(df['Status'].apply(parse_integers).tolist(), index=df.index)
df = df.drop(['Status'], axis=1)
df.sort_values(by='Seats Left', ascending=False, inplace=True)
df.drop_duplicates(ignore_index=True, inplace=True)

conditions = [
    (df['Seats Left'] <= 0),
    (df['% Fill Rate'] >= 75) & (df['Seats Left'] > 0),
    (df['% Fill Rate'] < 75)
]
choices = ["🔴", "🟠", "🟢"]
df['Status'] = np.select(conditions, choices, default='')

col = df.pop('Status')
df.insert(0, 'Status', col)

st.set_page_config(layout="wide")
st.markdown("""
        <style>
               .block-container {
                    padding-top: 3rem;
                }
                .right-align-container {
                text-align: right;
                }
            </style>""", unsafe_allow_html=True)

left, middle, right = st.columns([1, 8, 1])

with middle:
    st.markdown("""<div class="right-align-container"><a href='https://ko-fi.com/Y8Y51S5314' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi5.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a></div>""", unsafe_allow_html=True)
    
    #<div class="top-right-container">
    
    st.markdown(f"## OMSCS Course Occupancy")
    st.text(f"Data Age: {data_age}, Data Timestamp: {dataframe_date} UTC")
    search_term = st.text_input("**Search** (keywords OR exact course number, acronyms not yet supported, | & operators OK)")
    if search_term:
        if search_term.isdigit(): df = df[df['Course Number'] == (search_term)]
        else: df = df[df['Title'].str.contains(search_term, case=False, na=False)]

    st.dataframe(df, height="content", width="stretch", hide_index=True, column_config={
        "% Fill Rate": st.column_config.ProgressColumn(
            "% Fill Rate",
            min_value=0,
            max_value=100,
            color="blue"
        )
    })


    



