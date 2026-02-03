from db import fetch_dataframe

QUERY = "SELECT id, email_subject FROM analyses LIMIT 5;"
df = fetch_dataframe(QUERY)
print(df)
