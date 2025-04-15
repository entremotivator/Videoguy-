import streamlit as st
import ffmpeg
import os
from tempfile import NamedTemporaryFile
import cv2
import whisper

# Streamlit app configuration
st.set_page_config(page_title="Advanced FFmpeg Video Editor", layout="wide")
st.title("🎬 Advanced FFmpeg Video Editor")

# File uploader for video input
video_file = st.file_uploader("Upload a video", type=["mp4", "mov", "avi", "mkv"])

if video_file:
    with NamedTemporaryFile(delete=False, suffix=".mp4") as temp_input:
        temp_input.write(video_file.read())
        input_path = temp_input.name

    st.video(input_path)

    st.subheader("🛠️ Edit Options")

    # Frame-by-frame preview
    if st.checkbox("Enable Frame-by-Frame Preview"):
        cap = cv2.VideoCapture(input_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_number = st.slider("Select Frame", 0, total_frames - 1, 0)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        if ret:
            st.image(frame, channels="BGR", caption=f"Frame {frame_number}")
        cap.release()

    # Crop selection
    if st.checkbox("Enable Crop"):
        crop_x = st.number_input("Crop X", min_value=0, value=0)
        crop_y = st.number_input("Crop Y", min_value=0, value=0)
        crop_width = st.number_input("Crop Width", min_value=1, value=640)
        crop_height = st.number_input("Crop Height", min_value=1, value=480)
        crop_filter = f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y}"
    else:
        crop_filter = None

    # Resize video
    if st.checkbox("Resize Video"):
        resize_width = st.number_input("Resize Width", min_value=1, value=1280)
        resize_height = st.number_input("Resize Height", min_value=1, value=720)
        resize_filter = f"scale={resize_width}:{resize_height}"
    else:
        resize_filter = None

    # Adjust playback speed
    if st.checkbox("Change Playback Speed"):
        playback_speed = st.slider("Playback Speed (e.g., 0.5 for slow motion)", min_value=0.1, max_value=4.0, value=1.0)
    else:
        playback_speed = None

    # Audio volume adjustment
    if st.checkbox("Adjust Audio Volume"):
        volume_db = st.slider("Volume Adjustment (dB)", min_value=-30.0, max_value=30.0, value=0.0, step=0.5)
        volume_filter = f"volume={volume_db}dB"
    else:
        volume_filter = None

    # Audio replacement
    if st.checkbox("Replace Audio"):
        audio_file = st.file_uploader("Upload Replacement Audio", type=["mp3", "wav", "aac"])
        if audio_file:
            with NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
                temp_audio.write(audio_file.read())
                audio_path = temp_audio.name
        else:
            st.warning("Please upload an audio file to replace the original audio.")
            audio_path = None
    else:
        audio_path = None

    # Automatic subtitles generation
    if st.checkbox("Generate Subtitles"):
        model = whisper.load_model("base")
        result = model.transcribe(input_path)
        srt_path = input_path + ".srt"
        with open(srt_path, "w", encoding="utf-8") as srt_file:
            for i, segment in enumerate(result["segments"]):
                start_time = segment["start"]
                end_time = segment["end"]
                text_content = segment["text"].strip()
                srt_file.write(f"{i + 1}\n")
                srt_file.write(f"{start_time:.3f} --> {end_time:.3f}\n")
                srt_file.write(f"{text_content}\n\n")

    # Add watermark
    if st.checkbox("Add Watermark"):
        watermark_text = st.text_input("Watermark Text")
        watermark_position_x = st.number_input("Watermark X Position", min_value=0, value=10)
        watermark_position_y = st.number_input("Watermark Y Position", min_value=0, value=10)
        watermark_filter = f"drawtext=text='{watermark_text}':x={watermark_position_x}:y={watermark_position_y}:fontsize=24:fontcolor=white"
    else:
        watermark_filter = None

    # Process video button
    if st.button("Process Video"):
        with NamedTemporaryFile(delete=False, suffix=".mp4") as temp_output:
            output_path = temp_output.name

        input_stream = ffmpeg.input(input_path)

        # Apply filters sequentially
        video_filters = []
        
        if crop_filter:
            video_filters.append(crop_filter)

        if resize_filter:
            video_filters.append(resize_filter)

        if watermark_filter:
            video_filters.append(watermark_filter)

        filter_chain = ",".join(video_filters) if video_filters else None

        if filter_chain:
            input_stream = input_stream.video.filter_multi_output(filter_chain)

        # Apply playback speed adjustment
        if playback_speed and playback_speed != 1.0:
            input_stream = input_stream.setpts(f"{1/playback_speed}*PTS").filter('atempo', playback_speed)

        # Handle audio filters and replacement
        if volume_filter:
            input_stream.audio.filter(volume_filter)

        if audio_path:
            audio_stream = ffmpeg.input(audio_path).audio
            output_streams = [input_stream.video, audio_stream]
            output_params = {"vcodec": "libx264", "acodec": "aac"}
            output_process = ffmpeg.output(*output_streams, output_path, **output_params)
        
            ffmpeg.run(output_process)

