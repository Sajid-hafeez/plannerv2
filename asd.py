import streamlit as st
from datetime import datetime, timedelta
import pickle
import os
import numpy as np
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# Define the path to the directory where user-specific data will be saved
DATA_DIR = "user_data"
os.makedirs(DATA_DIR, exist_ok=True)

# Function to load tasks and notes from the file
def load_data(user_id, date):
    file_path = os.path.join(DATA_DIR, f"{user_id}_{date}.pkl")
    if os.path.exists(file_path):
        with open(file_path, "rb") as file:
            return pickle.load(file)
    else:
        return {
            "tasks": {f"{hour:02d}:00 - {hour+1:02d}:00": "" for hour in range(24)},
            "notes": "",
            "whiteboard": None
        }

# Function to save tasks and notes to the file
def save_data(user_id, date, data):
    file_path = os.path.join(DATA_DIR, f"{user_id}_{date}.pkl")
    with open(file_path, "wb") as file:
        pickle.dump(data, file)
    st.success("Data saved!")

# Function to get the initial state of the planner for a given date
def get_initial_state(user_id, date):
    return load_data(user_id, date)

# Function to save whiteboard as image file
def save_whiteboard(image_data, user_id, date):
    img = Image.fromarray((image_data * 255).astype(np.uint8))
    img.save(os.path.join(DATA_DIR, f"{user_id}_{date}_whiteboard.png"))

# Function to load whiteboard from image file
def load_whiteboard(user_id, date):
    file_path = os.path.join(DATA_DIR, f"{user_id}_{date}_whiteboard.png")
    try:
        img = Image.open(file_path)
        return np.array(img) / 255.0
    except FileNotFoundError:
        return None

# Function to save the current state to the session state and file
def save_current_state():
    user_id = st.session_state.user_id
    data = {
        "tasks": st.session_state.tasks,
        "notes": st.session_state.notes,
    }
    save_data(user_id, st.session_state.date, data)
    if st.session_state.whiteboard is not None:
        save_whiteboard(st.session_state.whiteboard, user_id, st.session_state.date)

# Function to plan for tomorrow
def plan_tomorrow():
    tomorrow_date = datetime.now() + timedelta(days=1)
    st.session_state.date = tomorrow_date.strftime('%Y-%m-%d')
    initial_state = get_initial_state(st.session_state.user_id, st.session_state.date)
    st.session_state.tasks = initial_state["tasks"]
    st.session_state.notes = initial_state["notes"]
    st.session_state.whiteboard = load_whiteboard(st.session_state.user_id, st.session_state.date)

# Initialize session state
if 'user_id' not in st.session_state:
    user_id = st.text_input("Enter your username or email to log in", key="user_id_input")
    if user_id:
        st.session_state.user_id = user_id
        st.experimental_rerun()
    st.stop()

if 'date' not in st.session_state:
    st.session_state.date = datetime.now().strftime('%Y-%m-%d')

if 'tasks' not in st.session_state:
    user_id = st.session_state.user_id
    initial_state = get_initial_state(user_id, st.session_state.date)
    st.session_state.tasks = initial_state["tasks"]
    st.session_state.notes = initial_state["notes"]
    st.session_state.whiteboard = load_whiteboard(user_id, st.session_state.date)

# Sidebar for selecting date
st.sidebar.title("Select Date")
user_id = st.session_state.user_id
data_files = [f for f in os.listdir(DATA_DIR) if f.startswith(user_id)]
all_dates = sorted(list(set(f.split('_')[1] for f in data_files if f.endswith('.pkl'))))
selected_date = st.sidebar.date_input("Go to date", datetime.strptime(st.session_state.date, '%Y-%m-%d'))

if selected_date.strftime('%Y-%m-%d') != st.session_state.date:
    st.session_state.date = selected_date.strftime('%Y-%m-%d')
    initial_state = get_initial_state(user_id, st.session_state.date)
    st.session_state.tasks = initial_state["tasks"]
    st.session_state.notes = initial_state["notes"]
    st.session_state.whiteboard = load_whiteboard(user_id, st.session_state.date)
    st.experimental_rerun()

# App title
st.title(f"Day Planner - {st.session_state.date}")

# Whiteboard section
st.subheader("Whiteboard")

# Handle the whiteboard data
if st.session_state.whiteboard is not None:
    whiteboard_array = (st.session_state.whiteboard * 255).astype(np.uint8)
    initial_drawing = {"objects": [], "background": whiteboard_array.tolist()}
else:
    initial_drawing = {"objects": [], "background": "#FFFFFF"}

canvas_result = st_canvas(
    fill_color="rgba(255, 165, 0, 0.3)",  # Fixed fill color with some opacity
    stroke_width=2,
    stroke_color="#000000",
    background_color="#ffffff",
    height=400,
    width=600,
    drawing_mode="freedraw",
    key="canvas",
    initial_drawing=initial_drawing,
)

# Save canvas data
if canvas_result.image_data is not None:
    st.session_state.whiteboard = np.array(canvas_result.image_data)

# Function to create a download link for the whiteboard image
def get_whiteboard_download_link():
    if st.session_state.whiteboard is not None:
        img = Image.fromarray((st.session_state.whiteboard * 255).astype(np.uint8))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        byte_im = buf.getvalue()
        return byte_im
    return None

# Add download button
whiteboard_image = get_whiteboard_download_link()
if whiteboard_image is not None:
    st.download_button(
        label="Download Whiteboard Image",
        data=whiteboard_image,
        file_name=f"whiteboard_{st.session_state.date}.png",
        mime="image/png"
    )

# Top rows for Sleep, Fun, and Work
st.subheader("Categories")
cols = st.columns(3)
with cols[0]:
    st.write("Sleep Hours")
    sleep_start = st.slider("Start", 0, 23, 22, key="sleep_start")
    sleep_end = st.slider("End", 0, 23, 6, key="sleep_end")
with cols[1]:
    fun_hours = st.multiselect("Fun Hours", options=[f"{hour:02d}:00 - {hour+1:02d}:00" for hour in range(24)])
with cols[2]:
    work_hours = st.multiselect("Work Hours", options=[f"{hour:02d}:00 - {hour+1:02d}:00" for hour in range(24)])

# Function to handle sleep hours
def get_sleep_hours(start, end):
    sleep_hours = []
    if start <= end:
        sleep_hours = [f"{hour:02d}:00 - {hour+1:02d}:00" for hour in range(start, end + 1)]
    else:
        sleep_hours = [f"{hour:02d}:00 - {hour+1:02d}:00" for hour in range(start, 24)]
        sleep_hours += [f"{hour:02d}:00 - {hour+1:02d}:00" for hour in range(0, end + 1)]
    return sleep_hours

# Get sleep hours
sleep_hours = get_sleep_hours(sleep_start, sleep_end)

# Reset tasks for sleep hours before updating
for time_slot in st.session_state.tasks:
    if st.session_state.tasks[time_slot] == "Sleep":
        st.session_state.tasks[time_slot] = ""

# Display planner tasks in three vertical columns
st.subheader("Tasks")
task_cols = st.columns(3)  # Create three columns

# Distribute tasks vertically across three columns
for hour in range(24):
    col = task_cols[hour % 3]  # Alternate between columns
    time_slot = f"{hour:02d}:00 - {hour+1:02d}:00"
    
    # Set default values based on selected categories
    if time_slot in sleep_hours:
        st.session_state.tasks[time_slot] = "Sleep"
    elif time_slot in fun_hours:
        st.session_state.tasks[time_slot] = "Fun"
    elif time_slot in work_hours:
        st.session_state.tasks[time_slot] = "Work"
    
    st.session_state.tasks[time_slot] = col.text_input(time_slot, st.session_state.tasks[time_slot])

# Notes section
st.subheader("Notes")
st.session_state.notes = st.text_area("Notes", st.session_state.notes, height=200)

# Save button
if st.button("Save"):
    save_current_state()

# Plan tomorrow button
if st.button("Plan Tomorrow"):
    plan_tomorrow()
    st.experimental_rerun()
