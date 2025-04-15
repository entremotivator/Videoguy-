import streamlit as st
import ffmpeg
import os
from tempfile import NamedTemporaryFile
import cv2
import whisper

# Streamlit app configuration
st.set_page_config(page_title="Advanced FFmpeg Video Editor", layout="wide")
st.title("🎬 Advanced FFmpeg Video Editor with Layers")

# State management for undo functionality and video layers
if "edit_history" not in st.session_state:
    st.session_state.edit_history = []
if "current_video" not in st.session_state:
    st.session_state.current_video = None
if "layer_files" not in st.session_state:
    st.session_state.layer_files = []

def save_edit(video_path):
    """Save the current edit to the history."""
    if video_path:
        st.session_state.edit_history.append(video_path)
        st.session_state.current_video = video_path

def undo_last_edit():
    """Undo the last edit."""
    if len(st.session_state.edit_history) > 1:
        st.session_state.edit_history.pop()
        st.session_state.current_video = st.session_state.edit_history[-1]
    elif len(st.session_state.edit_history) == 1:
        st.warning("Cannot undo further. This is the original video.")

if video_file := st.file_uploader("Upload a video", type=["mp4", "mov", "avi", "mkv"]):
    with NamedTemporaryFile(delete=False, suffix=".mp4") as temp_input:
        temp_input.write(video_file.read())
        input_path = temp_input.name
        save_edit(input_path)

    # Display the current video
    if st.session_state.current_video:
        st.video(st.session_state.current_video)

    # Undo button
    if st.button("Undo Last Edit"):
        undo_last_edit()

    st.subheader("🛠️ Edit Options")

    # Add PNG overlay (e.g., logo or lower third)
    if st.checkbox("Add PNG Overlay"):
        overlay_file = st.file_uploader("Upload PNG Overlay", type=["png"])
        if overlay_file:
            with NamedTemporaryFile(delete=False, suffix=".png") as temp_overlay:
                temp_overlay.write(overlay_file.read())
                overlay_path = temp_overlay.name
                x_position = st.number_input("Overlay X Position", min_value=0, value=10)
                y_position = st.number_input("Overlay Y Position", min_value=0, value=10)
                enable_time = st.slider("Enable Overlay Between (seconds)", 0, 300, (0, 300))
                duration_filter = f"enable='between(t,{enable_time[0]},{enable_time[1]})'"
                overlay_filter = f"[0:v][1:v] overlay={x_position}:{y_position}:{duration_filter}"
                st.session_state.layer_files.append((overlay_path, overlay_filter))

    # Add lower third text
    if st.checkbox("Add Lower Third Text"):
        lower_third_text = st.text_input("Lower Third Text")
        lower_third_x = st.number_input("Lower Third X Position", min_value=0, value=10)
        lower_third_y = st.number_input("Lower Third Y Position", min_value=0, value=500)
        font_size = st.number_input("Font Size", min_value=10, value=24)
        font_color = st.color_picker("Font Color", "#FFFFFF")
        lower_third_filter = f"drawtext=text='{lower_third_text}':x={lower_third_x}:y={lower_third_y}:fontsize={font_size}:fontcolor={font_color}"
        if lower_third_text:
            st.session_state.layer_files.append((None, lower_third_filter))

    # Process video button
    if st.button("Process Video"):
        with NamedTemporaryFile(delete=False, suffix=".mp4") as temp_output:
            output_path = temp_output.name

            input_streams = [ffmpeg.input(st.session_state.current_video)]
            filter_complex_parts = []

            # Add each layer to the filter complex chain
            for idx, (file_path, filter_command) in enumerate(st.session_state.layer_files):
                if file_path:  # If it's an image/video layer
                    input_streams.append(ffmpeg.input(file_path))
                    filter_complex_parts.append(filter_command.replace("[1:v]", f"[{idx+1}:v]"))
                else:  # If it's a drawtext layer
                    filter_complex_parts.append(filter_command)

            filter_complex_chain = ";".join(filter_complex_parts)

            # Apply filters and generate output
            ffmpeg.output(
                *input_streams,
                output_path,
                vcodec="libx264",
                acodec="aac",
                filter_complex=filter_complex_chain,
            ).run()

            save_edit(output_path)
            st.success(f"Video processed successfully! Saved at {output_path}")
