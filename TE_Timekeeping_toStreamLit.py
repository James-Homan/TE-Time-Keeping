import streamlit as st
import time
import csv
import matplotlib.pyplot as plt
import pandas as pd
import TimePeriod
import os

#----------------------------------------------------------------------------------------------------------
# GLOBALS
#----------------------------------------------------------------------------------------------------------
areas = {
    1: ("Vigilance", 60011),
    2: ("Enterprise", 60015),
    3: ("Liberty", 60012),
    4: ("Intrepid", 60013),
    5: ("Freedom", 60017),
    6: ("Pioneer", 60014),
    7: ("Meeting", None),
    8: ("Breaks", None),
    9: ("Training", None),
    10: ("E3 Projects",None),
    11: ("Idle", None)
}

# Define consistent colors for each area
area_colors = {
    "Vigilance Focus Factory": "#FF9999",   # Light Red
    "Enterprise Focus Factory": "#66B2FF",  # Light Blue
    "Liberty Focus Factory": "#99FF99",     # Light Green
    "Intrepid Focus Factory": "#FFCC99",    # Light Orange
    "Freedom Focus Factory": "#C2C2F0",     # Light Purple
    "Pioneer Focus Factory": "#FFFF99",     # Light Yellow
    "Meeting": "#E0E0E0",                   # Light Grey
    "Breaks": "#80CBC4",                    # Teal
    "Training": "#FFD54F",                  # Amber
    "E3 Projects": "#A1887F",               # Brown
    "Untracked (Idle)": "#607D8B"           # Blue Grey
}

log_file = "area_log.csv"
idle_label = "Untracked (Idle)"

# Initialize session state
if "timePeriod1" not in st.session_state:
    st.session_state.timePeriod1 = TimePeriod.TimePeriod()
    st.session_state.timePeriod1.set_start_time(0)
    selected_date = pd.Timestamp.now().date()

if "elapsed_time" not in st.session_state:
    st.session_state.elapsed_time = 0

#----------------------------------------------------------------------------------------------------------
# Logs entry and exit times to CSV
#----------------------------------------------------------------------------------------------------------
def log_entry_exit():
    time_period = st.session_state.timePeriod1
    if (time_period.get_start_time() != time_period.get_stop_time()):
        duration = time_period.get_stop_time() - time_period.get_start_time()
        with open(log_file, mode="a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
                time_period.get_area_name(), 
                time.ctime(time_period.get_start_time()), 
                time.ctime(time_period.get_stop_time()), 
                round(duration, 2)
            ])

#----------------------------------------------------------------------------------------------------------
# Switches to a new area and logs time
#----------------------------------------------------------------------------------------------------------
def switch_area(area_name):
    time_period = st.session_state.timePeriod1
    if (time_period.get_start_time() != 0) or (time_period.get_area_name() == "None"):
        if area_name != time_period.get_area_name():
            time_period.set_stop_time(time.time())
            log_entry_exit()
            time_period.set_area_name(area_name)
            time_period.set_start_time(time.time())

#----------------------------------------------------------------------------------------------------------
# Starts logging
#----------------------------------------------------------------------------------------------------------
def start_log():
    time_period = st.session_state.timePeriod1
    time_period.set_start_time(time.time())
    time_period.set_area_name(idle_label)
    
    # Create CSV header if file doesn't exist
    if not os.path.exists(log_file):
        with open(log_file, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Area", "Entry Time", "Exit Time", "Duration (seconds)"])
    
    st.success("Logging started!")

#----------------------------------------------------------------------------------------------------------
# Stops logging and closes session
#----------------------------------------------------------------------------------------------------------
def stop_logging_session():
    time_period = st.session_state.timePeriod1
    time_period.set_stop_time(time.time())
    log_entry_exit()
    time_period.set_start_time(0)
    time_period.set_area_name("None")
    st.success("Logging stopped. Data saved to 'area_log.csv'.")


#----------------------------------------------------------------------------------------------------------
# STREAMLIT UI
#----------------------------------------------------------------------------------------------------------
st.set_page_config(page_title="Area Logger", layout="wide")
st.title("⏱️ Time Keeper")

# Display current status
col1, col2 = st.columns(2)

with col1:
    time_period = st.session_state.timePeriod1
    current_area = time_period.get_area_name() or idle_label
    st.metric("Current Area", current_area)

with col2:
    @st.fragment(run_every=1)
    def show_timer():
        time_period = st.session_state.timePeriod1
        if time_period.get_start_time():
            elapsed = int(time.time() - time_period.get_start_time())
            # Format as HH:MM:SS for a proper timer look
            formatted_time = time.strftime("%H:%M:%S", time.gmtime(elapsed))
            st.metric("Time Elapsed", formatted_time)
        else:
            st.metric("Time Elapsed", "00:00:00")
    show_timer()

# SIDEBAR CONTROLS
with st.sidebar:
    st.title("Control Panel")
    st.divider()
    
    st.subheader("Session Controls")
    
    # Check if logging is currently active
    is_logging = st.session_state.timePeriod1.get_start_time() != 0

    # Start Button
    if st.button("▶️ Start Logging", width='content', disabled=is_logging):
        start_log()
        st.rerun()

    # Stop Button
    if st.button("⏹️ Stop Logging", width='content', disabled=not is_logging):
        if st.session_state.timePeriod1.get_start_time():
            stop_logging_session()
            st.rerun()
        else:
            st.warning("No session data recorded.")

    st.divider()

    # Area selection buttons
    st.subheader("Select Work Area")
    # Display current status
    cols = st.columns(2)
    for i, (num, name) in enumerate(areas.items()):
        with cols[i%2]:
            # Disable area switching if NOT logging
            if st.button(name[0], key=f"btn_area_{num}", width='content', disabled=not is_logging):
                if(name[0] == "Idle"):
                    switch_area(idle_label)
                else:
                    switch_area(name[0])
                st.rerun()
            
# Display log file data and pie chart
if os.path.exists(log_file):
    df = pd.read_csv(log_file)
    # Convert time strings to datetime
    df['Entry Time'] = pd.to_datetime(df['Entry Time'])
    df['Exit Time'] = pd.to_datetime(df['Exit Time'])

    # Date Selection
    st.divider()
    
    # Create columns to restrict width (1 part for date, 3 parts empty space)
    col_date, _ = st.columns([1, 3])
    with col_date:
        selected_date = st.date_input("Select Date for Dashboard", value=pd.Timestamp.now().date())

    # Filter for selected date
    df_date = df[df['Entry Time'].dt.date == selected_date]
    
    # Group by Area and sum duration
    area_totals = df_date.groupby('Area')['Duration (seconds)'].sum().reset_index()
    
    if not area_totals.empty:
        st.subheader("Time Spent by Area")
        area_totals['Duration (Hrs)'] = (area_totals['Duration (seconds)'] / 3600).round(2)

        # Calculate percentages for legend
        total_seconds = area_totals['Duration (seconds)'].sum()
        legend_labels = [f"{row['Area']} ({row['Duration (Hrs)']} hrs)" 
                         for index, row in area_totals.iterrows()]

        # Map colors to the areas present in the data
        # Use a default gray if area name not found in map
        pie_colors = [area_colors.get(x, "#808080") for x in area_totals['Area']]

        # Create figure with dark background
        fig, ax = plt.subplots(figsize=(10, 6))
        dark_blue = '#1f2630' # Nice dark blue hex code
        fig.patch.set_facecolor(dark_blue)
        ax.set_facecolor(dark_blue)
        
        # Create pie chart
        wedges, texts = ax.pie(
            area_totals['Duration (Hrs)'], 
            labels=None,
            startangle=90,
            colors=pie_colors,
            textprops=dict(color="white")
        )
        
        # Set title to white
        ax.set_title("Time Distribution", color='white')
        
        # Add Legend
        legend = ax.legend(wedges, legend_labels, 
                          title="Work Areas",
                          loc="center left",
                          bbox_to_anchor=(1, 0, 0.5, 1))
        
        # Style the legend for dark mode
        plt.setp(legend.get_title(), color='white')
        for text in legend.get_texts():
            text.set_color("white")
        legend.get_frame().set_facecolor(dark_blue)
        legend.get_frame().set_edgecolor('white')
        
        # Equal aspect ratio ensures that pie is drawn as a circle
        ax.axis('equal')
            
        plt.tight_layout()
        st.pyplot(fig, width='stretch')
    
    # Display Area Reference Table
    st.subheader("View Area Details")
    # Convert areas dict to DataFrame
    area_data = [{"Area Name": v[0], "Charge Code": v[1] if v[1] is not None else "-"} for k, v in areas.items()]
    df_areas = pd.DataFrame(area_data)
    # Display with formatting
    st.dataframe(df_areas, use_container_width=True, hide_index=True)
    
    st.subheader("Log Entries")    
    if not df_date.empty:
        st.dataframe(df_date, width='stretch')
    else:
        st.info("No entries for day selected yet.")
    
else:
    st.info("No log entries yet. Start logging to create entries.")