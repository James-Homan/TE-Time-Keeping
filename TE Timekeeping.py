# pip install tk 
# if SSL Errors type this into command line
# Made By Zachary Mangiafesto 
# pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org pip setuptools
# pip install matplotlib

import time
import csv
import tkinter as tk
from tkinter import messagebox, ttk
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, date2num
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime
import matplotlib.patches as mpatches
import matplotlib
# Define areas with their department codes
areas = {
    1: ("Vigilance Focus Factory", "60011"),
    2: ("Enterprise Focus Factory", "60015"),
    3: ("Liberty Focus Factory", "60012"),
    4: ("Intrepid Focus Factory", "60013"),
    5: ("Freedom Focus Factory", "60017"),
    6: ("Pioneer Focus Factory", "60014"),
    7: ("ESS Chambers", "ESS"),
    8: ("Breaks", "NPRD"),
    9: ("Training", "TRAIN"),
    10: ("E3 Projects", "NPRD")
}
log_file = "area_log.csv"
idle_label = "Untracked (Idle)"
logging_active = False
current_area = idle_label
entry_time = time.time()
# Dictionary to keep track of time spent in each area today
daily_time = defaultdict(float)
def log_entry_exit(area_name, entry_time, exit_time):
    """Logs entry and exit times to CSV"""
    if not logging_active:
        return
        
    duration = exit_time - entry_time
    day = time.strftime('%Y-%m-%d', time.localtime(entry_time))
    daily_time[(area_name, day)] += duration
    department_code = next((code for name, code in areas.values() if name == area_name), "")
    with open(log_file, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            area_name, 
            time.ctime(entry_time), 
            time.ctime(exit_time), 
            round(duration, 2),
            round(daily_time[(area_name, day)] / 3600, 2),  # total hours in the day
            department_code  # department code
        ])
def switch_area(area_name):
    """Switches to a new area and logs time"""
    global current_area, entry_time
    if area_name != current_area:
        exit_time = time.time()
        log_entry_exit(current_area, entry_time, exit_time)
        current_area = area_name
        entry_time = time.time()
        update_display()
def update_display():
    """Updates the GUI with the current area and elapsed time"""
    elapsed = round(time.time() - entry_time, 2)
    label.config(text=f"Current Area: {current_area}\nTime Spent: {elapsed} sec")
    if logging_active:
        root.after(1000, update_display)  # Refresh every second
def start_logging():
    """Starts the logging process"""
    global logging_active, entry_time
    if not logging_active:
        logging_active = True
        entry_time = time.time()
        update_display()
def stop_logging():
    """Stops the logging process"""
    global logging_active
    if logging_active:
        exit_time = time.time()
        log_entry_exit(current_area, entry_time, exit_time)
        logging_active = False
def exit_app():
    """Stops logging and closes the app"""
    stop_logging()
    messagebox.showinfo("Exit", "Logging stopped. Data saved to 'area_log.csv'.")
    root.destroy()
def show_dashboard():
    """Displays the dashboard with daily and weekly logs"""
    # Create a new window for the dashboard
    dashboard = tk.Toplevel(root)
    dashboard.title("Activity Dashboard")
    dashboard.geometry("1000x700")
    # Add radio buttons to toggle between daily and weekly views within the dashboard
    dashboard_view_mode = tk.StringVar(value="daily")
    tk.Label(dashboard, text="Select View Mode:", font=("Arial", 12)).pack(pady=5)
    view_mode_frame = tk.Frame(dashboard)
    view_mode_frame.pack(pady=5)
    tk.Radiobutton(view_mode_frame, text="Daily", variable=dashboard_view_mode, value="daily").pack(side=tk.LEFT, padx=5)
    tk.Radiobutton(view_mode_frame, text="Weekly", variable=dashboard_view_mode, value="weekly").pack(side=tk.LEFT, padx=5)
    # Add date filters within the dashboard
    tk.Label(dashboard, text="From:", font=("Arial", 12)).pack(pady=5)
    dashboard_start_date = tk.StringVar(value=str(datetime.date.today()))
    tk.Entry(dashboard, textvariable=dashboard_start_date, font=("Arial", 12)).pack(pady=5)
    tk.Label(dashboard, text="To:", font=("Arial", 12)).pack(pady=5)
    dashboard_end_date = tk.StringVar(value=str(datetime.date.today()))
    tk.Entry(dashboard, textvariable=dashboard_end_date, font=("Arial", 12)).pack(pady=5)
    # Function to update the dashboard display
    def update_dashboard():
        nonlocal dashboard_view_mode, dashboard_start_date, dashboard_end_date
        # Clear previous plots
        for widget in plot_frame.winfo_children():
            widget.destroy()
        # Read log data
        activities = defaultdict(list)
        with open(log_file, mode='r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip the header
            for row in reader:
                if len(row) == 6:
                    area_name, entry_time, exit_time, duration, total_hours, department_code = row
                    entry_dt = datetime.datetime.strptime(entry_time, "%a %b %d %H:%M:%S %Y")
                    exit_dt = datetime.datetime.strptime(exit_time, "%a %b %d %H:%M:%S %Y")
                    activities[area_name].append((entry_dt, exit_dt, float(duration)))
        # Parse the start and end dates
        start = datetime.datetime.strptime(dashboard_start_date.get(), '%Y-%m-%d').date()
        end = datetime.datetime.strptime(dashboard_end_date.get(), '%Y-%m-%d').date()
        # Create a matplotlib figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot data based on the selected view mode
        colors = plt.get_cmap('tab20').colors
        total_time = 0
        if dashboard_view_mode.get() == "daily":
            # Plot daily multiple bar graph
            unique_dates = set()
            for entries in activities.values():
                for entry_dt, exit_dt, _ in entries:
                    unique_dates.add(entry_dt.date())
            unique_dates = sorted(unique_dates)
            bar_width = 0.2
            bar_positions = {date: i for i, date in enumerate(unique_dates)}
            for i, (area_name, entries) in enumerate(activities.items()):
                daily_durations = defaultdict(float)
                for entry_dt, exit_dt, duration in entries:
                    entry_date = entry_dt.date()
                    if start <= entry_date <= end:
                        daily_durations[entry_date] += duration / 3600  # Convert to hours
                dates = list(daily_durations.keys())
                hours = list(daily_durations.values())
                total_time += sum(hours)
                bar_indexes = [bar_positions[date] + i * bar_width for date in dates]
                ax.bar(bar_indexes, hours, width=bar_width, label=area_name, color=colors[i % len(colors)], alpha=0.75)
            ax.set_xticks([j + bar_width*(len(activities)/2) for j in range(len(unique_dates))])
            ax.set_xticklabels(unique_dates, rotation=45)
        elif dashboard_view_mode.get() == "weekly":
            # Plot weekly calendar-like view
            y_labels = []
            y_ticks = []
            for area_name, entries in activities.items():
                for entry_dt, exit_dt, duration in entries:
                    entry_date = entry_dt.date()
                    if start <= entry_date <= end:
                        y_labels.append(area_name)
                        y_ticks.append(date2num(entry_date))
                        ax.plot([date2num(entry_dt), date2num(exit_dt)], [entry_date, entry_date], linewidth=10, color=colors[len(y_ticks) % len(colors)], label=area_name if area_name not in y_labels else "_nolegend_")
                        
        # Format the x-axis for dates
        ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
        ax.set_xlabel('Date')
        ax.set_ylabel('Hours' if dashboard_view_mode.get() == "daily" else 'Days')
        ax.set_title('Activity Overview')
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        ax.grid(True)
        # Display the plot in the Tkinter window
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        fig.tight_layout(rect=[0, 0, 0.85, 1])
        # Display total time in the dashboard
        total_time_label.config(text=f"Total Time: {total_time:.2f} hours")
    plot_frame = tk.Frame(dashboard)
    plot_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
    total_time_label = tk.Label(dashboard, text="Total Time: 0.00 hours", font=("Arial", 12))
    total_time_label.pack(pady=5)
    # Button to update the dashboard
    tk.Button(dashboard, text="Update Dashboard", font=("Arial", 12), bg="blue", fg="white", command=update_dashboard).pack(pady=10)
    # Initial update of the dashboard
    update_dashboard()
# Ensure CSV file has a header
try:
    with open(log_file, "x", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Area", "Entry Time", "Exit Time", "Duration (seconds)", "Total Hours in the Day", "Department Code"])
except FileExistsError:
    pass
# GUI Setup
root = tk.Tk()
root.title("Area Logger")
root.geometry("600x700")
# Instantiate Tkinter variables after creating the root window
view_mode = tk.StringVar(value="daily")
start_date = tk.StringVar(value=str(datetime.date.today()))
end_date = tk.StringVar(value=str(datetime.date.today()))
# Create a main frame for the listed areas
main_frame = tk.Frame(root)
main_frame.pack(fill="both", expand=True)
# Create and place the area buttons in a grid layout
button_frame = tk.Frame(main_frame)
button_frame.pack(pady=10)
rows, cols = 5, 2  # Number of rows and columns for the grid
for num, (name, code) in areas.items():
    row = (num - 1) // cols  # Row number (based on index)
    col = (num - 1) % cols  # Column number (based on index)
    tk.Button(button_frame, text=f"{name}\n({code})", font=("Arial", 12), command=lambda n=name: switch_area(n)).grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
# Add grid weights for responsiveness
for i in range(rows):
    button_frame.grid_rowconfigure(i, weight=1)
for j in range(cols):
    button_frame.grid_columnconfigure(j, weight=1)
label = tk.Label(main_frame, text="Current Area: Untracked (Idle)\nTime Spent: 0 sec", font=("Arial", 14))
label.pack(pady=10)
# Create a frame for action buttons and arrange them side by side
action_button_frame = tk.Frame(main_frame)
action_button_frame.pack(pady=10)
tk.Button(action_button_frame, text="Start Logging", font=("Arial", 12), bg="green", fg="white", command=start_logging).grid(row=0, column=0, padx=5, pady=5)
tk.Button(action_button_frame, text="Stop Logging", font=("Arial", 12), bg="orange", fg="white", command=stop_logging).grid(row=0, column=1, padx=5, pady=5)
# Below the action buttons
tk.Button(main_frame, text="Set to Idle", font=("Arial", 12), command=lambda: switch_area(idle_label)).pack(pady=10)
tk.Button(main_frame, text="Exit", font=("Arial", 12), bg="red", fg="white", command=exit_app).pack(pady=10)
tk.Button(main_frame, text="Show Dashboard", font=("Arial", 12), bg="blue", fg="white", command=show_dashboard).pack(pady=10)
# Start real-time updates
update_display()
root.mainloop()
