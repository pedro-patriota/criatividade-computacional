import streamlit as st
import json
import os
from pathlib import Path
from musicai_sdk import MusicAiClient
from main import process_audio_with_music_ai
from chrodsSync import sync_lyrics_with_chords, load_json_files, save_synced_output

# Set page config
st.set_page_config(
    page_title="Lyrics & Chords Sync",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("🎵 Lyrics & Chords Synchronizer")

# Configuration
API_KEY = os.getenv("API_KEY", "")
WORKFLOW_NAME = "criatividade-comp"
OUTPUT_DIR = "results"


def display_synced_lyrics(synced_data):
    """Display lyrics with chord buttons on black background."""
    if not synced_data:
        return
    
    # Build HTML for display with black background and white text
    display_html = '<div style="background-color: #000000; padding: 40px; border-radius: 10px; font-size: 20px; line-height: 2; color: #ffffff; font-family: \'Courier New\', monospace; position: relative;">'
    
    for item in synced_data:
        word = item['word']
        has_chord = item['has_chord']
        
        if has_chord:
            # Extract chord from word (format: word{CHORD})
            if '{' in word and '}' in word:
                chord_start_idx = word.rfind('{')
                chord_end_idx = word.rfind('}')
                chord = word[chord_start_idx+1:chord_end_idx]
                word_text = word[:chord_start_idx] + word[chord_end_idx+1:]
                
                display_html += f'<span style="position: relative; display: inline-block; margin-right: 8px;"><span style="display: inline-block; position: relative; padding-top: 35px;"><span style="position: absolute; top: 0; left: 0; background: linear-gradient(135deg, #87CEEB 0%, #4A90E2 100%); color: white; border: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: bold; box-shadow: 0 2px 8px rgba(0,0,0,0.4); white-space: nowrap;">{chord}</span><span style="color: #ffffff;">{word_text}</span></span></span>'
            else:
                display_html += f'<span style="color: #ffffff; margin-right: 8px;">{word}</span>'
        else:
            display_html += f'<span style="color: #ffffff; margin-right: 8px;">{word}</span>'
    
    display_html += '</div>'
    
    st.markdown(display_html, unsafe_allow_html=True)


# Main Single Page Layout
st.header("📤 Upload Audio File")

col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader("Choose an MP3 file", type=["mp3", "wav", "m4a"])
    
    if uploaded_file is not None:
        st.success("✅ File uploaded successfully!")
        st.audio(uploaded_file, format="audio/mp3")
        
        # Save to session state
        if "audio_data" not in st.session_state:
            st.session_state.audio_data = uploaded_file
        
        # Show file info
        st.info(f"File size: {uploaded_file.size / 1024 / 1024:.2f} MB")

st.divider()
st.header("⚙️ Process Audio with Music.AI")

if "audio_data" in st.session_state and st.session_state.audio_data:
    if st.button("🚀 Process with Music.AI", key="process_music_ai"):
        try:
            # Save uploaded file temporarily
            temp_file_path = "temp_upload.mp3"
            with open(temp_file_path, "wb") as f:
                f.write(st.session_state.audio_data.getbuffer())
            
            # Use imported function from main.py
            with st.spinner("Processing audio with Music.AI..."):
                result = process_audio_with_music_ai(
                    api_key=API_KEY,
                    workflow_name=WORKFLOW_NAME,
                    mp3_file_path=temp_file_path,
                    output_dir=OUTPUT_DIR,
                    verbose=False
                )
            
            if result["success"]:
                st.success("✅ Job completed successfully!")
                
                # Load the generated JSON files
                lyrics_file = result.get("lyrics_file")
                chords_file = result.get("chords_file")
                
                if lyrics_file and chords_file:
                    with open(lyrics_file, 'r') as f:
                        lyrics_data = json.load(f)
                    with open(chords_file, 'r') as f:
                        chords_data = json.load(f)
                    
                    # Automatically run chords sync
                    with st.spinner("Synchronizing lyrics with chords..."):
                        synced_result = sync_lyrics_with_chords(lyrics_data, chords_data, verbose=False)
                        if synced_result:
                            st.session_state.synced_data = synced_result
                            st.success("✅ Synchronization completed!")
                
                # Clean up
                os.remove(temp_file_path)
            else:
                st.error(f"Job failed: {result.get('message', 'Unknown error')}")
                st.session_state.show_backup_upload = True
        
        except Exception as e:
            st.error(f"Error processing with Music.AI: {str(e)}")
            st.session_state.show_backup_upload = True
else:
    st.info("👈 Please upload an audio file first")

# Show backup file upload only if processing failed
if st.session_state.get("show_backup_upload", False):
    st.divider()
    st.header("📁 Backup: Upload JSON Files")
    st.warning("If Music.AI processing failed, you can upload pre-existing lyrics and chords JSON files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        lyrics_json = st.file_uploader("Upload Lyrics JSON", type=["json"], key="lyrics")
        if lyrics_json:
            st.session_state.lyrics_data = json.load(lyrics_json)
            st.success("✅ Lyrics file loaded!")
    
    with col2:
        chords_json = st.file_uploader("Upload Chords JSON", type=["json"], key="chords")
        if chords_json:
            st.session_state.chords_data = json.load(chords_json)
            st.success("✅ Chords file loaded!")
    
    # If both backup files are loaded, automatically sync
    if "lyrics_data" in st.session_state and "chords_data" in st.session_state and "synced_data" not in st.session_state:
        with st.spinner("Synchronizing lyrics with chords..."):
            synced_result = sync_lyrics_with_chords(st.session_state.lyrics_data, st.session_state.chords_data, verbose=False)
            if synced_result:
                st.session_state.synced_data = synced_result
                st.success("✅ Synchronization completed!")

# Display synced lyrics if available
if "synced_data" in st.session_state:
    st.divider()
    st.header("🎼 Synchronized Lyrics with Chords")
    
    synced_data = st.session_state.synced_data
    display_synced_lyrics(synced_data)
    
    # Download section
    st.divider()
    st.subheader("📥 Download Results")
    
    # Create text output
    text_output = ' '.join([item['word'] for item in synced_data])
    
    # Create JSON output
    json_output = json.dumps(synced_data, indent=2)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="📄 Download as Text",
            data=text_output,
            file_name="lyrics_with_chords.txt",
            mime="text/plain"
        )
    
    with col2:
        st.download_button(
            label="📊 Download as JSON",
            data=json_output,
            file_name="synced_lyrics.json",
            mime="application/json"
        )
