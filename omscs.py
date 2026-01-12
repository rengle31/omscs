
import pickle   
import pandas as pd
import re
from datetime import date
import os.path
import numpy as np
import streamlit as st

today = date.today()
file_path = f"dataframe_{today}.pkl"
if not os.path.isfile(file_path):
    print(f"The file {file_path} DNE - no pickle - ERROR.")
    quit()
else:
    with open(file_path, 'rb') as f:
        pickle_df = pickle.load(f)
    print(f"loaded {file_path}")

    dataframe_date = file_path.removeprefix("dataframe_").removesuffix(".pkl")
    

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
    (df['% Fill Rate'] >= 100),
    (df['% Fill Rate'] >= 75) & (df['% Fill Rate'] < 100),
    (df['% Fill Rate'] < 75)
]
choices = ["🔴", "🟠", "🟢"]
df['Status'] = np.select(conditions, choices, default='')


# col = df.pop('Status')
# df.insert(0, 'Status', col)

# keywords = ['law', 'marketing', 'os', 'process', 'language', 'deep', 'artificial', 'graphics', 'GPU', 'game', 'video', 'learning']

# pattern = '|'.join(keywords)
# results = df[df['Title'].str.contains(pattern, case=False, na=False)].sort_values(by='Seats Left', ascending=False)
# print(dataframe_date)
# results

# import aka

# courses = ['RL', 'RAIT']

# keywords = [aka.aka[k] for k in courses if k in courses]
# pattern = '|'.join(keywords)
# results = df[df['Title'].str.contains(pattern, case=False, na=False)].sort_values(by='Seats Left', ascending=False)
# print(dataframe_date)
# results



st.set_page_config(layout="wide")

left, middle, right = st.columns([1, 8, 1])

with middle:
    st.markdown(f"### OMSCS Course Occupancy - {dataframe_date}")
    search_term = st.text_input("Enter search term (keyword or exact course number):")
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


    



