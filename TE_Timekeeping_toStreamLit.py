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
    1: "Vigilance Focus Factory",
    2: "Enterprise Focus Factory",
    3: "Liberty Focus Factory",
    4: "Intrepid Focus Factory",
    5: "Freedom Focus Factory",
    6: "Pioneer Focus Factory",
    7: "ESS Chambers",
    8: "Breaks",
    9: "Training",
    10: "E3 Projects"
}

log_file = "area_log.csv"
idle_label = "Untracked (Idle)"

# Initialize session state
if "timePeriod1" not in st.session_state:
    st.session_state.timePeriod1 = TimePeriod.TimePeriod()
    st.session_state.timePeriod1.set_start_time(0)

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
st.title("⏱️ Area Logger - Time Keeping App")

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

# Control buttons
st.subheader("Controls")
col1, col2, col3 = st.columns(3)

# Check if logging is currently active
is_logging = st.session_state.timePeriod1.get_start_time() != 0

with col1:
    # Disable Start if already logging
    if st.button("▶️ Start Logging", width='stretch', disabled=is_logging):
        start_log()
        st.rerun()

with col2:
    # Disable Stop if NOT logging
    if st.button("⏹️ Stop Logging", width='stretch', disabled=not is_logging):
        if time_period.get_start_time():
            stop_logging_session()
            st.rerun()
        else:
            st.warning("No session data recorded.")

with col3:
    # Disable Idle if NOT logging
    if st.button("😴 Set to Idle", width='stretch', disabled=not is_logging):
        switch_area(idle_label)
        st.rerun()

# Area selection buttons
st.subheader("Select Work Area")
cols = st.columns(2)

for num, name in areas.items():
    col_index = (num - 1) % 2
    with cols[col_index]:
        # Disable area switching if NOT logging
        if st.button(name, width='stretch', disabled=not is_logging):
            switch_area(name)
            st.rerun()
            
# Display log file
st.subheader("Today's Log Entries")
if os.path.exists(log_file):
    df = pd.read_csv(log_file)
    
    # Convert time strings to datetime
    df['Entry Time'] = pd.to_datetime(df['Entry Time'])
    df['Exit Time'] = pd.to_datetime(df['Exit Time'])
    
    # Filter for today's entries only
    today = pd.Timestamp.now().date()
    df_today = df[df['Entry Time'].dt.date == today]
    
    if not df_today.empty:
        st.dataframe(df_today, use_container_width=True)
    else:
        st.info("No entries for today yet.")
    
    # Total Time visualization
    st.subheader("Total Time Spent by Area")
    
    # Group by Area and sum duration
    area_totals = df.groupby('Area')['Duration (seconds)'].sum().reset_index()
    
    
    # ...existing code...
    if not area_totals.empty:
        area_totals['Duration (Hrs)'] = (area_totals['Duration (seconds)'] / 3600).round(2)
        
        # Create figure with dark background
        fig, ax = plt.subplots(figsize=(10, 6))
        dark_blue = '#1f2630' # Nice dark blue hex code
        fig.patch.set_facecolor(dark_blue)
        ax.set_facecolor(dark_blue)
        
        # Create bars
        bars = ax.bar(area_totals['Area'], area_totals['Duration (Hrs)'], 
                     color=[plt.cm.Set3(i) for i in range(len(area_totals))])
        
        # Set labels and title to white
        ax.set_ylabel("Total Time (Hrs)", color='white')
        ax.set_xlabel("Work Area", color='white')
        ax.set_title("Total Time Distribution", color='white')
        
        # Set ticks to white
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        
        # Set chart borders (spines) to white
        for spine in ax.spines.values():
            spine.set_edgecolor('white')

        plt.xticks(rotation=45)
        
        # Add labels on top of bars (in white)
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height} hr',
                    ha='center', va='bottom', color='white')
            
        plt.tight_layout()
        st.pyplot(fig)
    
else:
    st.info("No log entries yet. Start logging to create entries.")

