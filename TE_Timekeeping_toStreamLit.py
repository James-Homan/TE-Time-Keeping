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
    1: ("Vigilance Focus Factory", 60012),
    2: ("Enterprise Focus Factory", 60012),
    3: ("Liberty Focus Factory", 60012),
    4: ("Intrepid Focus Factory", 60012),
    5: ("Freedom Focus Factory", 60012),
    6: ("Pioneer Focus Factory", 60012),
    7: ("Meeting", None),
    8: ("Breaks", None),
    9: ("Training", None),
    10: ("E3 Projects",None)
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
        if st.button(name[0], width='stretch', disabled=not is_logging):
            switch_area(name[0])
            st.rerun()
            
# Display log file

if os.path.exists(log_file):
    df = pd.read_csv(log_file)
    
    # Group by Area and sum duration
    area_totals = df.groupby('Area')['Duration (seconds)'].sum().reset_index()
    
    if not area_totals.empty:
        st.subheader("Total Time Spent by Area")
        area_totals['Duration (Hrs)'] = (area_totals['Duration (seconds)'] / 3600).round(2)

        # Calculate percentages for legend
        total_seconds = area_totals['Duration (seconds)'].sum()
        legend_labels = [f"{row['Area']} ({row['Duration (Hrs)']} hrs)" 
                         for index, row in area_totals.iterrows()]

        
        # Create figure with dark background
        fig, ax = plt.subplots(figsize=(10, 6))
        dark_blue = '#1f2630' # Nice dark blue hex code
        fig.patch.set_facecolor(dark_blue)
        ax.set_facecolor(dark_blue)
        
        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            area_totals['Duration (Hrs)'], 
            labels=None,
            autopct='%1.1f%%',
            startangle=90,
            colors=[plt.cm.Set3(i) for i in range(len(area_totals))],
            textprops=dict(color="white")
        )
        
        # Set title to white
        ax.set_title("Total Time Distribution", color='white')
        
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
        st.pyplot(fig, use_container_width=True)
    
    st.subheader("Today's Log Entries")
    # Convert time strings to datetime
    df['Entry Time'] = pd.to_datetime(df['Entry Time'])
    df['Exit Time'] = pd.to_datetime(df['Exit Time'])
    
    # Filter for today's entries only
    today = pd.Timestamp.now().date()
    df_today = df[df['Entry Time'].dt.date == today]
    
    if not df_today.empty:
        st.dataframe(df_today, width='stretch')
    else:
        st.info("No entries for today yet.")
    
else:
    st.info("No log entries yet. Start logging to create entries.")