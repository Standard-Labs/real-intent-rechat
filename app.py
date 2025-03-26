import streamlit as st
import pandas as pd
import io # Needed for ensuring string conversion for CSV

# Define the exact columns expected in the target Rechat output format
RECHAT_COLUMNS_FINAL = [
    'First Name', 'Last Name', 'Marketing Name', 'Phone', 'Email', 'Address',
    'Birthday', 'Home Anniversary', 'Tag', 'Tag', 'Notes',
    'Spouse/Partner - First Name', 'Spouse/Partner - Last Name',
    'Spouse/Partner - Email', 'Spouse/Partner - Phone', 'Spouse/Partner Birthday'
]

# Define column names for INTERNAL processing (unique names for Tags)
RECHAT_COLUMNS_PROCESSING = [
    'First Name', 'Last Name', 'Marketing Name', 'Phone', 'Email', 'Address',
    'Birthday', 'Home Anniversary', 'Tag_1', 'Tag_2', 'Notes', # Use Tag_1, Tag_2 internally
    'Spouse/Partner - First Name', 'Spouse/Partner - Last Name',
    'Spouse/Partner - Email', 'Spouse/Partner - Phone', 'Spouse/Partner Birthday'
]

# Define the core source columns required (using cleaned names)
CORE_SOURCE_COLUMNS = [
    'first_name', 'last_name', 'email_1', 'phone_1', 'address', 'city', 'state', 'zip_code'
]
# Define optional source columns used for richer output (Notes, Tags)
OPTIONAL_SOURCE_COLUMNS = [
    'home_owner_status', 'insight', 'gender', 'age', 'credit_range', 'household_income',
    'marital_status', 'household_net_worth', 'occupation', 'n_household_children',
    'email_2', 'email_3', 'phone_2', 'phone_3', 'phone_1_dnc', 'phone_2_dnc', 'phone_3_dnc',
    'Sellers', 'Brokers And Agents', 'Residential', 'Pre-Movers', 'Mortgages'
]
# List of columns that might indicate source list tags
SOURCE_TAG_MARKER_COLS = ['Sellers', 'Brokers And Agents', 'Residential', 'Pre-Movers', 'Mortgages']

def main():
    st.title('Your Specific Data to Rechat CSV Converter')

    st.info("""
    Upload your specific CSV data file (as provided in the latest sample with columns like 'first_name ', 'email_1 ', 'address ', 'city ', 'state ', 'zip_code ', 'insight', etc.).
    This tool will convert it into the CSV format required for importing into Rechat,
    handling specific column names (including extra spaces), combining address fields,
    generating detailed notes, mapping tags based on 'home_owner_status' and source markers (like 'Sellers', 'Residential'),
    and structuring the output correctly.
    """)

    uploaded_file = st.file_uploader("Upload Your Source CSV File", type="csv")

    if uploaded_file is not None:
        try:
            # Read the uploaded CSV
            df_source = pd.read_csv(uploaded_file)

            # ---- Data Cleaning (Headers) ----
            original_columns = df_source.columns.tolist()
            df_source.columns = df_source.columns.str.strip()
            cleaned_columns = df_source.columns.tolist()
            changed_headers = [f"'{orig}' -> '{clean}'" for orig, clean in zip(original_columns, cleaned_columns) if orig != clean]
            if changed_headers:
                 st.warning(f"Note: Whitespace was stripped from some column headers: {', '.join(changed_headers)}")

            # ---- Data Validation ----
            missing_core_cols = [col for col in CORE_SOURCE_COLUMNS if col not in df_source.columns]
            if missing_core_cols:
                st.error(f"Upload Error: Your file is missing required columns (after cleaning headers): {', '.join(missing_core_cols)}. Please ensure your CSV has these columns.")
                st.stop()
            missing_optional_cols = [col for col in OPTIONAL_SOURCE_COLUMNS if col not in df_source.columns]
            if missing_optional_cols:
                st.warning(f"Note: Optional columns not found (after cleaning headers). Information for {', '.join(missing_optional_cols)} will not be included in the output.")

            # ---- Data Transformation ----
            # Create DataFrame using UNIQUE column names for processing
            df_processing = pd.DataFrame(columns=RECHAT_COLUMNS_PROCESSING, index=df_source.index)

            # 1. Direct Mappings & Basic Info -> df_processing
            df_processing['First Name'] = df_source['first_name'].fillna('')
            df_processing['Last Name'] = df_source['last_name'].fillna('')
            df_processing['Email'] = df_source['email_1'].fillna('')
            df_processing['Phone'] = df_source['phone_1'].astype(str).replace(r'\.0$', '', regex=True).fillna('')
            df_processing['Marketing Name'] = (df_source['first_name'].fillna('') + ' ' + df_source['last_name'].fillna('')).str.strip()

            # 2. Combine Address Fields -> df_processing
            zip_str = df_source['zip_code'].astype(str).replace(r'\.0$', '', regex=True).fillna('')
            address_col = df_source['address'].fillna('') + ', ' + \
                          df_source['city'].fillna('') + ' ' + \
                          df_source['state'].fillna('') + ' ' + \
                          zip_str
            df_processing['Address'] = address_col.str.replace(r'^,\s*', '', regex=True)\
                                             .str.replace(r'\s*,\s*$', '', regex=True)\
                                             .str.strip()\
                                             .str.replace(r'\s{2,}', ' ', regex=True)\
                                             .str.replace(r'\s+,', ',', regex=True)\
                                             .str.replace(r',\s*$', '', regex=True)

            # 3. Populate Tags (Using unique internal names Tag_1, Tag_2)
            if 'home_owner_status' in df_source.columns:
                df_processing['Tag_1'] = df_source['home_owner_status'].apply(lambda x: 'Homeowner' if str(x).strip().lower() == 'home owner' else '').fillna('')
            else:
                df_processing['Tag_1'] = ''

            available_source_tag_cols = [col for col in SOURCE_TAG_MARKER_COLS if col in df_source.columns]
            tag2_list = []
            if available_source_tag_cols:
                 for index, row in df_source.iterrows():
                      tags = [col for col in available_source_tag_cols if str(row.get(col, '')).strip().lower() == 'x']
                      tag2_list.append(", ".join(tags))
            else:
                 tag2_list = [''] * len(df_source)
            df_processing['Tag_2'] = tag2_list

            # 4. Construct Notes field -> df_processing
            notes_list = []
            note_source_cols_map = {
                'insight': '', 'occupation': 'Occupation:', 'gender': 'Gender:', 'age': 'Age:',
                'marital_status': 'Marital Status:', 'n_household_children': '# Children:',
                'credit_range': 'Credit:', 'household_income': 'Income:', 'household_net_worth': 'Net Worth:',
                'email_2': 'Email 2:', 'email_3': 'Email 3:', 'phone_2': 'Phone 2:', 'phone_3': 'Phone 3:',
            }
            available_note_cols = {k: v for k, v in note_source_cols_map.items() if k in df_source.columns}
            for index, row in df_source.iterrows():
                note_parts = []
                if 'insight' in available_note_cols and pd.notna(row['insight']) and str(row['insight']).strip():
                     note_parts.append(str(row['insight']).strip())
                for col, prefix in available_note_cols.items():
                    if col == 'insight': continue
                    value = row.get(col) # Use .get() for safety, though validation should ensure presence
                    if pd.notna(value) and str(value).strip():
                        note_entry = f"{prefix} {str(value).strip()}"
                        if col == 'phone_2' and 'phone_2_dnc' in df_source.columns and pd.notna(row.get('phone_2_dnc')):
                            note_entry += f" (DNC: {row['phone_2_dnc']})"
                        if col == 'phone_3' and 'phone_3_dnc' in df_source.columns and pd.notna(row.get('phone_3_dnc')):
                             note_entry += f" (DNC: {row['phone_3_dnc']})"
                        note_parts.append(note_entry)
                if 'phone_1_dnc' in df_source.columns and pd.notna(row.get('phone_1_dnc')):
                     note_parts.append(f"Primary Phone DNC: {row['phone_1_dnc']}")
                notes_list.append(" | ".join(note_parts))
            df_processing['Notes'] = notes_list

            # 5. Populate Missing Fields -> df_processing
            df_processing['Birthday'] = ''
            df_processing['Home Anniversary'] = ''
            df_processing['Spouse/Partner - First Name'] = ''
            df_processing['Spouse/Partner - Last Name'] = ''
            df_processing['Spouse/Partner - Email'] = ''
            df_processing['Spouse/Partner - Phone'] = ''
            df_processing['Spouse/Partner Birthday'] = ''

            # 6. Final Cleanup (on df_processing)
            for col in RECHAT_COLUMNS_PROCESSING:
                if col not in df_processing.columns:
                    df_processing[col] = ''
            df_processing = df_processing.fillna('')

            # Ensure correct column order for processing/displaying DataFrame
            df_processing = df_processing[RECHAT_COLUMNS_PROCESSING]

            # ---- Display and Download ----
            st.success("Conversion to Rechat format successful!")
            st.write("Converted Data Preview (first 5 rows):")
            # Display the DataFrame with UNIQUE column names (Tag_1, Tag_2)
            st.dataframe(df_processing.head())

            # Prepare FINAL DataFrame for CSV output with DUPLICATE 'Tag' columns
            df_final_output = df_processing.copy()
            # Rename Tag_1 and Tag_2 back to Tag for the CSV output
            df_final_output = df_final_output.rename(columns={'Tag_1': 'Tag', 'Tag_2': 'Tag'})
            # Ensure the column order matches the final Rechat requirement
            # Note: Pandas handles selecting columns even with duplicate names if done by list
            df_final_output = df_final_output[RECHAT_COLUMNS_FINAL]

            # Prepare CSV for download from df_final_output
            output = io.StringIO()
            # Export df_final_output which now has the duplicate 'Tag' columns
            df_final_output.to_csv(output, index=False, encoding='utf-8')
            csv_data = output.getvalue()
            output.close()

            st.download_button(
                label="Download Rechat Import CSV File",
                data=csv_data,
                file_name='rechat_import_data.csv', # Specific filename for Rechat
                mime='text/csv',
            )

        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
            st.exception(e) # Provides traceback in console/logs for debugging

if __name__ == "__main__":
    main()
