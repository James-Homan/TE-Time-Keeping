# pip install tk 
# if SSL Errors type this into command line 
# pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org pip setuptools

import time
import csv
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk  # For Scrollbar and styling

#----------------------------------------------------------------------------------------------------------
# Logs entry and exit times to CSV
#----------------------------------------------------------------------------------------------------------
def log_entry_exit(area_name, entry_time, exit_time):
    duration = exit_time - entry_time
    with open(log_file, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([area_name, time.ctime(entry_time), time.ctime(exit_time), round(duration, 2)])
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
    exit_time = time.time()
    log_entry_exit(current_area, entry_time, exit_time)
    messagebox.showinfo("Exit", "Logging stopped. Data saved to 'area_log.csv'.")
    root.destroy()
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
entry_time = time.time()

# Ensure CSV file has a header
try:
    with open(log_file, "x", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Area", "Entry Time", "Exit Time", "Duration (seconds)"])
except FileExistsError:
    pass

# GUI Setup
root = tk.Tk()
root.title("Area Logger")
root.geometry("400x500")

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
tk.Button(root, text="Set start", font=("Arial", 12), command=lambda: switch_area(start_label)).pack(
    pady=10)

# Idle button
tk.Button(root, text="Set to Idle", font=("Arial", 12), command=lambda: switch_area(idle_label)).pack(
    pady=10)

# Exit button
tk.Button(root, text="Exit", font=("Arial", 12), bg="red", fg="white", command=exit_app).pack(
    pady=10)

# Start real-time updates
update_display()
root.mainloop()