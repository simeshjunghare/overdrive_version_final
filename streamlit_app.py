import streamlit as st
import json
import pandas as pd
import subprocess
from overdrive_scraper import extract_publishers

# 🚨 Page config MUST be the first Streamlit command
st.set_page_config(
    page_title="Overdrive Publisher Finder",
    page_icon="🔍",
    layout="wide"
)

# --- Ensure Chromium is installed for Playwright (runs once per session) ---
@st.cache_resource
def install_playwright():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        st.error(f"Failed to install Playwright Chromium: {e}")

install_playwright()
# --------------------------------------------------------------------------


def main():
    st.title("🔍 Overdrive Publisher Finder")
    st.markdown("Search for publishers on Overdrive and analyze the results.")

    # Sidebar for user input
    with st.sidebar:
        st.header("Search Parameters")
        company_name = st.text_input("Company Name", placeholder="Enter company name")
        min_similarity = st.slider(
            "Minimum Similarity Threshold",
            0.5, 1.0, 0.7, 0.05,
            help="Adjust the similarity threshold for matching publishers"
        )

        if st.button("Search Publishers"):
            if not company_name:
                st.error("Please enter a company name")
            else:
                with st.spinner("Searching for publishers..."):
                    try:
                        results = extract_publishers(company_name, min_similarity)
                        st.session_state['results'] = results
                        st.session_state['company_name'] = company_name
                        st.session_state['min_similarity'] = min_similarity
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")

    # Show results if available
    if 'results' in st.session_state and st.session_state['results']:
        results = st.session_state['results']
        company_name = st.session_state['company_name']
        min_similarity = st.session_state['min_similarity']

        st.subheader(f"Search Results for: {company_name}")

        # Filter matching publishers
        matching_publishers = [
            p for p in results['matching_publishers']
            if p['similarity_score'] >= min_similarity
        ]

        # Matching publishers
        st.subheader("📊 Matching Publishers")
        if not matching_publishers:
            st.info("No publishers matched the similarity threshold.")
        else:
            df_matching = pd.DataFrame(matching_publishers)
            df_matching['Similarity'] = df_matching['similarity_score'].apply(
                lambda x: f"{x*100:.0f}%"
            )

            st.dataframe(
                df_matching[['publisher_name', 'Similarity', 'publisher_url']].rename(
                    columns={
                        'publisher_name': 'Publisher Name',
                        'publisher_url': 'URL'
                    }
                ),
                column_config={
                    "URL": st.column_config.LinkColumn("URL", display_text="Open")
                },
                hide_index=True,
                use_container_width=True
            )

            # Show best match
            top_match = matching_publishers[0] if matching_publishers else None
            if top_match and top_match['similarity_score'] > 0.9:
                st.success(
                    f"✅ Best match: {top_match['publisher_name']} "
                    f"(Similarity: {top_match['similarity_score']*100:.0f}%)"
                )

        # All publishers in expander
        with st.expander("📋 All Publishers"):
            if not results['all_publishers']:
                st.info("No publishers found.")
            else:
                df_all = pd.DataFrame(results['all_publishers'])
                st.dataframe(
                    df_all.rename(columns={
                        'publisher_name': 'Publisher Name',
                        'publisher_url': 'URL'
                    }),
                    column_config={
                        "URL": st.column_config.LinkColumn("URL", display_text="Open")
                    },
                    hide_index=True,
                    use_container_width=True
                )

        # Download JSON button
        json_data = json.dumps(results, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Download Results as JSON",
            data=json_data,
            file_name=f"{company_name.replace(' ', '_').lower()}_publishers.json",
            mime="application/json"
        )

    # Instructions
    with st.expander("ℹ️ How to use"):
        st.markdown("""
        1. Enter a company name in the sidebar  
        2. Adjust the similarity threshold if needed  
        3. Click **Search Publishers**  
        4. View and download the results  

        The tool shows:
        - Matching publishers (based on similarity score)  
        - All publishers found for the search term  

        You can download the results as a JSON file.
        """)


if __name__ == "__main__":
    main()
