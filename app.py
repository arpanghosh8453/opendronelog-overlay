import streamlit as st
import os
from pathlib import Path
from opendronelog_overlay.ODL_2_AD import convert_odl_to_airdata

st.set_page_config(page_title="ODL to Airdata Converter", page_icon="🚁")

st.title("Drone Log Converter")
st.markdown("Convert your **OpenDroneLog** CSVs to **Airdata** format for easy analysis.")

uploaded_file = st.file_uploader("Upload an OpenDroneLog CSV", type="csv")

if uploaded_file:
    # Save the uploaded file temporarily
    input_path = Path("temp_input.csv")
    output_path = Path("airdata_output.csv")
    
    with open(input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        with st.spinner("Converting..."):
            convert_odl_to_airdata(input_path, output_path)
        
        st.success("Successfully converted!")
        
        # Provide a download button
        with open(output_path, "rb") as f:
            st.download_button(
                label="Download Airdata CSV",
                data=f,
                file_name=f"airdata_{uploaded_file.name}",
                mime="text/csv"
            )
            
    except Exception as e:
        st.error(f"Error during conversion: {e}")
    finally:
        # Cleanup temp files
        if input_path.exists(): os.remove(input_path)
        if output_path.exists(): os.remove(output_path)