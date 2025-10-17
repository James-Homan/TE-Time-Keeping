# pip install tk 
# if SSL Errors type this into command line 
# pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org pip setuptools

import time
import csv
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk  # For Scrollbar and styling
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.dates import DateFormatter
import datetime

#----------------------------------------------------------------------------------------------------------
# Logs entry and exit times to CSV
#----------------------------------------------------------------------------------------------------------
def log_entry_exit(area_name, entry_time, exit_time):
    if (entry_time != exit_time):
        duration = exit_time - entry_time
        with open(log_file, mode="a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([area_name, time.ctime(entry_time), time.ctime(exit_time), round(duration, 2)])
    else:
        return
#----------------------------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------------------------
# Switches to a new area and logs time
#----------------------------------------------------------------------------------------------------------
def switch_area(area_name):
    global current_area, entry_time
    if area_name != current_area:
        exit_time = time.time()
        log_entry_exit(current_area, entry_time, exit_time)
        current_area = area_name
        entry_time = time.time()
        update_display()
#----------------------------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------------------------
# Updates the GUI with the current area and elapsed time
#----------------------------------------------------------------------------------------------------------
def update_display():
    elapsed = round(time.time() - entry_time, 2)
    label.config(text=f"Current Area: {current_area}\nTime Spent: {elapsed} sec")
    root.after(1000, update_display)  # Refresh every second
#----------------------------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------------------------
# Stops logging and closes the app
#----------------------------------------------------------------------------------------------------------
def exit_app():
    try:
        entry_time
        exit_time = time.time()
        log_entry_exit(current_area, entry_time, exit_time)
        messagebox.showinfo("Exit", "Logging stopped. Data saved to 'area_log.csv'.")
        root.destroy()
        return
    except NameError:
        messagebox.showinfo("Exit", "No logging session started.")
        root.destroy()
#----------------------------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------------------------
# Starts logging and closes the app
#----------------------------------------------------------------------------------------------------------
def start_log():
    try:
        global entry_time
        entry_time = time.time()
        update_display()
        with open(log_file, mode="a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Area", "Entry Time", "Exit Time", "Duration (seconds)"])
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start log: {e}")
        root.destroy()
#----------------------------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------------------------
# Displays dashboard to user
#----------------------------------------------------------------------------------------------------------
def show_dashboard():
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

    # Create a new window for the dashboard
    dashboard = tk.Toplevel(root)
    dashboard.title("Activity Dashboard")
    dashboard.geometry("800x600")

    # Create a matplotlib figure
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot daily and weekly activity data
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    start_of_week = today - datetime.timedelta(days=today.weekday())  # Start of the week (Monday)
    colors = plt.cm.get_cmap('tab20').colors
    
    for i, (area_name, entries) in enumerate(activities.items()):
        daily_durations = defaultdict(float)
        weekly_durations = defaultdict(float)
        
        for entry_dt, exit_dt, duration in entries:
            entry_date = entry_dt.date()
            if entry_date == today or entry_date == yesterday:
                daily_durations[entry_date] += duration / 3600  # Convert to hours
            if start_of_week <= entry_date <= today:
                weekly_durations[entry_date] += duration / 3600  # Convert to hours

        if daily_durations:
            dates = list(daily_durations.keys())
            hours = list(daily_durations.values())
            ax.bar(dates, hours, label=f"{area_name} (Daily)", color=colors[i % len(colors)])

        if weekly_durations:
            weekly_dates = list(weekly_durations.keys())
            weekly_hours = list(weekly_durations.values())
            ax.bar(weekly_dates, weekly_hours, label=f"{area_name} (Weekly)", alpha=0.5, color=colors[i % len(colors)])

    # Format the x-axis for dates
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
    ax.set_xlabel('Date')
    ax.set_ylabel('Hours')
    ax.set_title('Daily and Weekly Activity')
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    ax.grid(True)

    # Display the plot in the Tkinter window
    canvas = FigureCanvasTkAgg(fig, master=dashboard)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    fig.tight_layout(rect=[0, 0, 0.85, 1])
#----------------------------------------------------------------------------------------------------------


# Define areas
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
start_label = "Start Time"
current_area = idle_label

# GUI Setup
root = tk.Tk()
root.title("Area Logger")
root.geometry("400x600")

# Create a scrollable frame for the listed areas
main_frame = tk.Frame(root)
main_frame.pack(fill="both", expand=True)

canvas = tk.Canvas(main_frame)
scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
scrollable_frame = tk.Frame(canvas)

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

label = tk.Label(root, text="Current Area: Untracked (Idle)\nTime Spent: 0 sec", font=("Arial", 14))
label.pack(pady=10)

# Buttons for each area inside the scrollable frame, displayed in a grid layout
rows, cols = 5, 2  # Number of rows and columns for the grid
for num, name in areas.items():
    row = (num - 1) // cols  # Row number (based on index)
    col = (num - 1) % cols  # Column number (based on index)
    tk.Button(scrollable_frame, text=name, font=("Arial", 12), command=lambda n=name: switch_area(n)).grid(
        row=row, column=col, padx=5, pady=5, sticky="nsew")
    
# Add grid weights for responsiveness
for i in range(rows):
    scrollable_frame.grid_rowconfigure(i, weight=1)
for j in range(cols):
    scrollable_frame.grid_columnconfigure(j, weight=1)

# Start time button
tk.Button(root, text="Set start", font=("Arial", 12), command=lambda: start_log()).pack(pady=10)

# Idle button
tk.Button(root, text="Set to Idle", font=("Arial", 12), command=lambda: switch_area(idle_label)).pack(
    pady=10)

# Show dashboard button
tk.Button(root, text="Show Dashboard", font=("Arial", 12), bg="blue", fg="white", 
          command=show_dashboard).pack(pady=10)

# Exit button
tk.Button(root, text="Exit", font=("Arial", 12), bg="red", fg="white", command=exit_app).pack(pady=10)

root.mainloop()