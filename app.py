import streamlit as st
import pandas as pd
import io # Needed for ensuring string conversion for CSV

# Define the exact columns expected in the target Rechat output format
RECHAT_COLUMNS = [
    'First Name', 'Last Name', 'Marketing Name', 'Phone', 'Email', 'Address',
    'Birthday', 'Home Anniversary', 'Tag', 'Tag', 'Notes',
    'Spouse/Partner - First Name', 'Spouse/Partner - Last Name',
    'Spouse/Partner - Email', 'Spouse/Partner - Phone', 'Spouse/Partner Birthday'
]

# Define the core source columns required from your specific input data format (using cleaned names)
# NOTE: We will strip whitespace from uploaded headers, so use clean names here.
CORE_SOURCE_COLUMNS = [
    'first_name', 'last_name', 'email_1', 'phone_1', 'address', 'city', 'state', 'zip_code'
]
# Define optional source columns used for richer output (Notes, Tags)
OPTIONAL_SOURCE_COLUMNS = [
    'home_owner_status', 'insight', 'gender', 'age', 'credit_range', 'household_income',
    'marital_status', 'household_net_worth', 'occupation', 'n_household_children',
    'email_2', 'email_3', 'phone_2', 'phone_3', 'phone_1_dnc', 'phone_2_dnc', 'phone_3_dnc',
    # Source Category Tags
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
            # Read the uploaded CSV (your specific format)
            df_source = pd.read_csv(uploaded_file)

            # ---- Data Cleaning (Headers) ----
            # Strip leading/trailing whitespace from column headers
            original_columns = df_source.columns.tolist()
            df_source.columns = df_source.columns.str.strip()
            cleaned_columns = df_source.columns.tolist()

            # Display warning if column names were changed due to stripping spaces
            changed_headers = [f"'{orig}' -> '{clean}'" for orig, clean in zip(original_columns, cleaned_columns) if orig != clean]
            if changed_headers:
                 st.warning(f"Note: Whitespace was stripped from some column headers: {', '.join(changed_headers)}")


            # ---- Data Validation ----
            # Check if required core source columns are present (using cleaned names)
            missing_core_cols = [col for col in CORE_SOURCE_COLUMNS if col not in df_source.columns]
            if missing_core_cols:
                st.error(f"Upload Error: Your file is missing required columns (after cleaning headers): {', '.join(missing_core_cols)}. Please ensure your CSV has these columns.")
                st.stop() # Stop execution if core columns are missing

            # Warn if optional source columns are missing
            missing_optional_cols = [col for col in OPTIONAL_SOURCE_COLUMNS if col not in df_source.columns]
            if missing_optional_cols:
                st.warning(f"Note: Optional columns not found (after cleaning headers). Information for {', '.join(missing_optional_cols)} will not be included in the output.")

            # ---- Data Transformation ----
            # Create an empty DataFrame with the target Rechat structure
            df_target = pd.DataFrame(columns=RECHAT_COLUMNS, index=df_source.index)

            # 1. Direct Mappings & Basic Info (Source -> Rechat)
            df_target['First Name'] = df_source['first_name'].fillna('')
            df_target['Last Name'] = df_source['last_name'].fillna('')
            df_target['Email'] = df_source['email_1'].fillna('')
            # Ensure Phone is treated as string
            df_target['Phone'] = df_source['phone_1'].astype(str).replace(r'\.0$', '', regex=True).fillna('')
            df_target['Marketing Name'] = (df_source['first_name'].fillna('') + ' ' + df_source['last_name'].fillna('')).str.strip()

            # 2. Combine Address Fields (Source address, city, state, zip_code -> Rechat Address)
            # Ensure zip_code is string
            zip_str = df_source['zip_code'].astype(str).replace(r'\.0$', '', regex=True).fillna('')
            address_col = df_source['address'].fillna('') + ', ' + \
                          df_source['city'].fillna('') + ' ' + \
                          df_source['state'].fillna('') + ' ' + \
                          zip_str
            # Clean up combined address
            df_target['Address'] = address_col.str.replace(r'^,\s*', '', regex=True)\
                                             .str.replace(r'\s*,\s*$', '', regex=True)\
                                             .str.strip()\
                                             .str.replace(r'\s{2,}', ' ', regex=True)\
                                             .str.replace(r'\s+,', ',', regex=True)\
                                             .str.replace(r',\s*$', '', regex=True)

            # 3. Populate Tags (Using Rechat's duplicate 'Tag' columns)
            # Find indices of the 'Tag' columns in the target list
            tag_indices = [i for i, col_name in enumerate(RECHAT_COLUMNS) if col_name == 'Tag']

            # First Tag column: Use 'home_owner_status' from source
            if 'home_owner_status' in df_source.columns:
                 # Use iloc for assignment due to duplicate column names
                 # Check specifically for "Home Owner" case-insensitively
                df_target.iloc[:, tag_indices[0]] = df_source['home_owner_status'].apply(lambda x: 'Homeowner' if str(x).strip().lower() == 'home owner' else '').fillna('')
            else:
                df_target.iloc[:, tag_indices[0]] = '' # Fill first tag with empty if 'home_owner_status' column is missing

            # Second Tag column: Populate based on source marker columns (Sellers, Residential, etc.)
            available_source_tag_cols = [col for col in SOURCE_TAG_MARKER_COLS if col in df_source.columns]
            tag2_list = []
            if available_source_tag_cols: # Only proceed if some source tag columns exist
                 for index, row in df_source.iterrows():
                      # Collect names of columns where the value is 'x' (case-insensitive)
                      tags = [col for col in available_source_tag_cols if str(row.get(col, '')).strip().lower() == 'x']
                      tag2_list.append(", ".join(tags)) # Join the tags found
            else:
                 tag2_list = [''] * len(df_source) # Fill with empty strings if no source tag columns found

            if len(tag_indices) > 1:
                df_target.iloc[:, tag_indices[1]] = tag2_list
            # Else: No second tag column index found or expected.


            # 4. Construct Rechat Notes field from various source fields
            notes_list = []
            # Define source columns to potentially add to notes, with prefixes (use cleaned names)
            note_source_cols_map = {
                'insight': '', # Add insight directly without prefix
                'occupation': 'Occupation:',
                'gender': 'Gender:',
                'age': 'Age:',
                'marital_status': 'Marital Status:',
                'n_household_children': '# Children:',
                'credit_range': 'Credit:',
                'household_income': 'Income:',
                'household_net_worth': 'Net Worth:',
                # Add secondary/tertiary contact info
                'email_2': 'Email 2:',
                'email_3': 'Email 3:',
                'phone_2': 'Phone 2:',
                'phone_3': 'Phone 3:',
            }
            # Filter this map to only include columns actually present in the uploaded file
            available_note_cols = {k: v for k, v in note_source_cols_map.items() if k in df_source.columns}

            for index, row in df_source.iterrows():
                note_parts = []
                # Add insight first if present
                if 'insight' in available_note_cols and pd.notna(row['insight']) and str(row['insight']).strip():
                     note_parts.append(str(row['insight']).strip())

                # Add other mapped fields from available_note_cols
                for col, prefix in available_note_cols.items():
                    if col == 'insight': continue # Already handled insight
                    value = row[col]
                    if pd.notna(value) and str(value).strip():
                        note_entry = f"{prefix} {str(value).strip()}"
                        # Append DNC status for phones if DNC column exists and has data
                        if col == 'phone_2' and 'phone_2_dnc' in df_source.columns and pd.notna(row.get('phone_2_dnc')):
                            note_entry += f" (DNC: {row['phone_2_dnc']})"
                        if col == 'phone_3' and 'phone_3_dnc' in df_source.columns and pd.notna(row.get('phone_3_dnc')):
                             note_entry += f" (DNC: {row['phone_3_dnc']})"
                        note_parts.append(note_entry)

                # Add DNC for primary phone (phone_1) separately if DNC column exists
                if 'phone_1_dnc' in df_source.columns and pd.notna(row.get('phone_1_dnc')):
                     note_parts.append(f"Primary Phone DNC: {row['phone_1_dnc']}")

                notes_list.append(" | ".join(note_parts)) # Use a separator for readability

            df_target['Notes'] = notes_list


            # 5. Populate Missing Rechat Fields (Birthday, Anniversary, Spouse)
            # Source data lacks this information, fill with empty strings for Rechat compatibility
            df_target['Birthday'] = ''
            df_target['Home Anniversary'] = ''
            df_target['Spouse/Partner - First Name'] = ''
            df_target['Spouse/Partner - Last Name'] = ''
            df_target['Spouse/Partner - Email'] = ''
            df_target['Spouse/Partner - Phone'] = ''
            df_target['Spouse/Partner Birthday'] = ''

            # 6. Final Cleanup - Ensure all target columns exist and fill any remaining NaNs
            for col in RECHAT_COLUMNS:
                if col not in df_target.columns:
                    df_target[col] = '' # Failsafe in case a column was missed
            df_target = df_target.fillna('')

            # Ensure correct column order exactly as defined in RECHAT_COLUMNS
            df_target = df_target[RECHAT_COLUMNS]

            # ---- Display and Download ----
            st.success("Conversion to Rechat format successful!")
            st.write("Converted Rechat Data Preview (first 5 rows):")
            st.dataframe(df_target.head()) # Show first few rows

            # Prepare CSV for download, ensuring all data is treated as string
            output = io.StringIO()
            df_target.to_csv(output, index=False, encoding='utf-8')
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
