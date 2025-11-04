import streamlit as st
import requests
import time
import sys
import os

# --- API Configuration ---

BASE_URL = "https://3a0ae9535730.ngrok-free.app"


MAX_WAIT_SECONDS = 5400


def submit_job(gender: str, text: str) -> (str, str):
    """
    Submits the TTS job to the API.
    Returns (job_id, status_url) on success.
    Raises Exception on failure.
    """
    submit_url = f"{BASE_URL}/polyglot-tts/submit"
    form_data = {
        "gender": (None, gender),
        "text": (None, text),
    }
    
    try:
        response = requests.post(submit_url, files=form_data, headers={"accept": "audio/wav"})
        response.raise_for_status() 
        
        job_data = response.json()
        job_id = job_data.get("job_id")
        status_url = job_data.get("status_url")

        if not (job_id and status_url):
            raise Exception("API response did not contain 'job_id' or 'status_url'.")
            
        return job_id, status_url

    except requests.exceptions.RequestException as e:
        raise Exception(f"Error submitting job: {e}")

def poll_for_completion(job_id: str, status_url: str, status_placeholder, language: str, text_length: int):
    """
    Polls the status URL until the job is 'complete' or it times out.
    Updates the 'status_placeholder' in the Streamlit UI.
    Uses dynamic polling interval based on language and text length.
    """
    
    dynamic_poll_interval = 15 
    if "English" in language:
        if text_length < 500:
            dynamic_poll_interval = 10
        else:
            dynamic_poll_interval = 30
    else:  # Other Indic Languages
        if text_length < 100:
            dynamic_poll_interval = 20
        elif text_length < 500:
            dynamic_poll_interval = 30
        else:
            dynamic_poll_interval = 45
            
    status_placeholder.info(f"Using a polling interval of {dynamic_poll_interval} seconds.")
    
    start_time = time.time()
    status_check_url = f"{BASE_URL}{status_url}"

    while True:
        elapsed_time = time.time() - start_time
        
        # Check for timeout first
        if elapsed_time > MAX_WAIT_SECONDS:
            raise Exception(f"Job {job_id} timed out after {MAX_WAIT_SECONDS} seconds.")

        try:
            response = requests.get(status_check_url)
            response.raise_for_status()
            
            data = response.json()
            current_status = data.get("status")

            if current_status == "complete":
                status_placeholder.success(f"🎉 Job complete! (Total time: {elapsed_time:.1f}s)")
                break
            elif current_status == "processing":
                status_placeholder.info(f"⏳ Status: 'processing'... Total time: {elapsed_time:.1f}s (checking every {dynamic_poll_interval}s)")
                time.sleep(dynamic_poll_interval)
            else:
                raise Exception(f"Error: Unknown status '{current_status}'. Full response: {data}")

        except requests.exceptions.RequestException as e:
            # Continue polling even if one check fails
            status_placeholder.warning(f"Error checking status: {e}. Retrying in {dynamic_poll_interval}s... (Total time: {elapsed_time:.1f}s)")
            time.sleep(dynamic_poll_interval)

def download_result(job_id: str) -> str:
    """
    Downloads the resulting audio file.
    Returns the path to the downloaded file.
    Raises Exception on failure.
    """
    result_url = f"{BASE_URL}/polyglot-tts/result/{job_id}"
    output_filename = f"{job_id}.wav"
    
    try:
        with requests.get(result_url, stream=True) as r:
            r.raise_for_status()
            
            with open(output_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
                    
        if os.path.getsize(output_filename) == 0:
            raise Exception("Downloaded file is empty. The job may have failed silently on the server.")
        
        return output_filename

    except requests.exceptions.RequestException as e:
        raise Exception(f"Error downloading file: {e}")
    except IOError as e:
        raise Exception(f"Error writing file to disk: {e}")


st.set_page_config(page_title="Polyglot TTS", layout="wide")

st.title("🎙️ Polyglot TTS API Client")
st.markdown(f"A Streamlit interface for the TTS API at `{BASE_URL}`.")

with st.form("tts_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        gender = st.selectbox("Select Voice Gender", ("female", "male"), index=0)
    
    with col2:
        language = st.selectbox("Select Language", 
                                ("English (en)", "Hindi (hi)", "Telugu (te)", "Tamil (ta)", "Other"), 
                                index=0)
        st.caption("The API attempts to auto-detect the language from the text.")

    text_input = st.text_area("Text to Synthesize", "Hello, this is a test of the text to speech API.", height=150)
    submitted = st.form_submit_button("Generate Audio")

if submitted:
    if not text_input:
        st.error("Please enter some text to synthesize.")
    else:
        status_placeholder = st.empty()
        
        try:
            with st.spinner("Submitting job to API..."):
                job_id, status_url = submit_job(gender, text_input)
            st.success(f"✅ Job submitted successfully! Job ID: {job_id}")


            text_length = len(text_input)
            poll_for_completion(job_id, status_url, status_placeholder, language, text_length)

            # 3. Download Result
            with st.spinner("Downloading audio file..."):
                audio_file_path = download_result(job_id)

            st.balloons()
            st.subheader("Listen to your audio:")
            st.audio(audio_file_path, format="audio/wav")
            
            # Add a download button
            with open(audio_file_path, "rb") as f:
                st.download_button(
                    label="Download .wav file",
                    data=f,
                    file_name=os.path.basename(audio_file_path),
                    mime="audio/wav"
                )

        except Exception as e:
            status_placeholder.error(f"An error occurred: {e}")
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center;">
        Developed by <a href="httpsReplit:
//ramc26.github.io/RamTechSuite/" target="_blank">🦉</a><br>
        For details or queries, contact <a href="mailto:ramarao.bikkina@jukshio.com">ramarao.bikkina@jukshio.com</a>
    </div>
    """,
    unsafe_allow_html=True
)

