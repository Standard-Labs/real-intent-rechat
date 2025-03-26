import streamlit as st
import pandas as pd
import io # Needed for ensuring string conversion for CSV

# Define the exact columns expected in the target output format, including duplicates
TARGET_COLUMNS = [
    'First Name', 'Last Name', 'Marketing Name', 'Phone', 'Email', 'Address',
    'Birthday', 'Home Anniversary', 'Tag', 'Tag', 'Notes',
    'Spouse/Partner - First Name', 'Spouse/Partner - Last Name',
    'Spouse/Partner - Email', 'Spouse/Partner - Phone', 'Spouse/Partner Birthday'
]

# Define the source columns required for the transformation
# Essential for basic info: 'First Name', 'Last Name', 'Email 1', 'Phone 1'
# Essential for Address: 'Address', 'City', 'State', 'Zip'
# Used for Tags/Notes: 'Homeowner', 'Insight'
# Optional for Notes: 'Gender', 'Age', 'Credit Range', 'Income Range', 'Marital Status', 'Net Worth Range'
REQUIRED_SOURCE_COLUMNS = [
    'First Name', 'Last Name', 'Email 1', 'Phone 1', 'Address', 'City', 'State', 'Zip'
]

def main():
    st.title('CSV Data Converter') # Changed title to be more generic

    st.info("""
    Upload your CSV file (using the format described in the prompt).
    The app will convert your data into the target upload format,
    combining address fields, mapping relevant data to notes and tags,
    and structuring the output according to the required schema.
    """)

    uploaded_file = st.file_uploader("Choose your source CSV file", type="csv")

    if uploaded_file is not None:
        try:
            # Read the uploaded CSV
            df_source = pd.read_csv(uploaded_file)

            # ---- Data Validation ----
            # Check if required source columns are present
            missing_columns = [col for col in REQUIRED_SOURCE_COLUMNS if col not in df_source.columns]
            if missing_columns:
                st.error(f"Upload Error: The file is missing essential columns: {', '.join(missing_columns)}. Please ensure your CSV contains these columns.")
                st.stop() # Stop execution if essential columns are missing

            # ---- Data Transformation ----
            # Create an empty DataFrame with the target structure
            df_target = pd.DataFrame(columns=TARGET_COLUMNS, index=df_source.index)

            # 1. Direct Mappings & Basic Info
            df_target['First Name'] = df_source['First Name'].fillna('')
            df_target['Last Name'] = df_source['Last Name'].fillna('')
            df_target['Email'] = df_source['Email 1'].fillna('')
            # Ensure Phone is treated as string to preserve formatting
            df_target['Phone'] = df_source['Phone 1'].astype(str).replace(r'\.0$', '', regex=True).fillna('')
            df_target['Marketing Name'] = (df_source['First Name'].fillna('') + ' ' + df_source['Last Name'].fillna('')).str.strip()

            # 2. Combine Address Fields
            # Ensure Zip is string and remove potential '.0' if read as float
            zip_str = df_source['Zip'].astype(str).replace(r'\.0$', '', regex=True).fillna('')
            address_col = df_source['Address'].fillna('') + ', ' + \
                          df_source['City'].fillna('') + ' ' + \
                          df_source['State'].fillna('') + ' ' + \
                          zip_str
            # Clean up combined address (remove leading/trailing commas/spaces, excess internal spaces)
            df_target['Address'] = address_col.str.replace(r'^,\s*', '', regex=True)\
                                             .str.replace(r'\s*,\s*$', '', regex=True)\
                                             .str.strip()\
                                             .str.replace(r'\s{2,}', ' ', regex=True)\
                                             .str.replace(r'\s+,', ',', regex=True)\
                                             .str.replace(r',\s*$', '', regex=True) # Final check for trailing comma


            # 3. Populate Tags
            # Find indices of the 'Tag' columns
            tag_indices = [i for i, col_name in enumerate(TARGET_COLUMNS) if col_name == 'Tag']

            # First Tag column: Use 'Homeowner' status
            if 'Homeowner' in df_source.columns:
                 # Use iloc for assignment to handle duplicate column names
                df_target.iloc[:, tag_indices[0]] = df_source['Homeowner'].apply(lambda x: 'Homeowner' if str(x).strip().lower() == 'yes' else '').fillna('')
            else:
                df_target.iloc[:, tag_indices[0]] = '' # Fill with empty if 'Homeowner' column is missing

            # Second Tag column: Use 'Real Intent' or leave blank
            if len(tag_indices) > 1:
                df_target.iloc[:, tag_indices[1]] = 'Real Intent' # As per original script's intent
            # If only one 'Tag' column was expected, this assignment would fail gracefully or needs adjustment

            # 4. Construct Notes field
            notes_list = []
            # Columns to potentially add to notes with prefixes
            note_source_cols = {
                'Insight': '', # Add insight directly without prefix
                'Gender': 'Gender:',
                'Age': 'Age:',
                'Credit Range': 'Credit:',
                'Income Range': 'Income:',
                'Marital Status': 'Marital Status:',
                'Net Worth Range': 'Net Worth:'
            }
            available_note_cols = {k: v for k, v in note_source_cols.items() if k in df_source.columns}

            for index, row in df_source.iterrows():
                note_parts = []
                for col, prefix in available_note_cols.items():
                    value = row[col]
                    if pd.notna(value) and str(value).strip():
                        if prefix:
                            note_parts.append(f"{prefix} {str(value).strip()}")
                        else:
                            note_parts.append(str(value).strip()) # Append insight directly
                notes_list.append(" | ".join(note_parts)) # Use a separator for readability

            df_target['Notes'] = notes_list

            # 5. Populate Missing Target Fields (Birthday, Anniversary, Spouse)
            # Source data lacks this information, fill with empty strings
            df_target['Birthday'] = ''
            df_target['Home Anniversary'] = ''
            df_target['Spouse/Partner - First Name'] = ''
            df_target['Spouse/Partner - Last Name'] = ''
            df_target['Spouse/Partner - Email'] = ''
            df_target['Spouse/Partner - Phone'] = ''
            df_target['Spouse/Partner Birthday'] = ''

            # 6. Final Cleanup - Ensure all target columns exist and fill any remaining NaNs
            for col in TARGET_COLUMNS:
                if col not in df_target.columns:
                    # This case shouldn't happen if df_target initialized correctly, but good failsafe
                    df_target[col] = ''
            df_target = df_target.fillna('')

            # Ensure correct column order exactly as defined in TARGET_COLUMNS
            df_target = df_target[TARGET_COLUMNS]

            # ---- Display and Download ----
            st.success("Conversion successful!")
            st.write("Converted DataFrame Preview:")
            st.dataframe(df_target.head()) # Show first few rows

            # Prepare CSV for download - ensure all data is treated as string
            # Using io.StringIO to help pandas treat everything as text
            output = io.StringIO()
            df_target.to_csv(output, index=False, encoding='utf-8')
            csv_data = output.getvalue()
            output.close()


            st.download_button(
                label="Download Converted CSV File",
                data=csv_data,
                file_name='converted_upload_data.csv', # Changed filename
                mime='text/csv',
            )

        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
            st.exception(e) # Provides traceback in console/logs for debugging

if __name__ == "__main__":
    main()
