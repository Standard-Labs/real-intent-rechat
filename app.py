import streamlit as st
import pandas as pd

# Define global variables for column mappings
COLUMN_MAPPINGS = {
    "occupation": "Job Title",
    "first_name": "First Name",
    "last_name": "Last Name",
    "address": "Home Street",
    "city": "Home City",
    "state": "Home State",
    "zip_code": "Home Postal Code",
    "phone_1": "Home Phone",
    "phone_2": "Home Phone 1",
    "phone_3": "Home Phone 2",
    "email_1": "E-mail Address",
    "email_2": "E-mail 1",
    "email_3": "E-mail 2",
    "insight": "Notes",
    "household_income": "Notes 1",
    "household_net_worth": "Notes 2",
}


def main():
    st.title('Real Intent to Rechat Converter')

    st.info("""
    Upload a CSV file. The app will convert your Real Intent CSV into a format that can be imported into Realty Juggler.
    """)

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)

        # Check if required columns are in the dataframe
        missing_columns = [col for col in COLUMN_MAPPINGS.keys() if col not in df.columns]

        if 'first_name' not in df.columns:
            missing_columns.append('first_name')
        if 'last_name' not in df.columns:
            missing_columns.append('last_name')

        if not missing_columns:
            df = df[list(COLUMN_MAPPINGS.keys())].rename(columns=COLUMN_MAPPINGS)
            
            if 'Notes 1' in df.columns:
                df['Notes 1'] = f"Household Income: " + df['Notes 1']
            if 'Notes 2' in df.columns:
                df['Notes 2'] = f"Household Net Worth: " + df['Notes 2']

            df['Referred By'] = 'Real Intent'


            # Display the resulting dataframe
            st.write("Converted DataFrame:")
            st.write(df)

            # Download the converted dataframe as CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download converted CSV",
                data=csv,
                file_name='converted_file.csv',
                mime='text/csv',
            )
        else:
            st.write(f"The uploaded file does not contain the required columns: {', '.join(missing_columns)}.")


if __name__ == "__main__":
    main()
