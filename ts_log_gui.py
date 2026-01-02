import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import datetime

DB = os.path.join(os.path.dirname(__file__), 'area_logger.db')

class TSApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('TS Log GUI')
        self.geometry('800x600')
        self.create_widgets()
        self.conn = sqlite3.connect(DB)
        self.conn.row_factory = sqlite3.Row

    def create_widgets(self):
        frm = ttk.Frame(self)
        frm.pack(fill='both', expand=True, padx=8, pady=8)
        ttk.Label(frm, text='Station:').grid(row=0, column=0, sticky='w')
        self.station = tk.Entry(frm, width=60)
        self.station.grid(row=0, column=1, sticky='w')

        ttk.Label(frm, text='Problem:').grid(row=1, column=0, sticky='nw')
        self.problem = tk.Text(frm, width=60, height=6)
        self.problem.grid(row=1, column=1, sticky='w')

        ttk.Label(frm, text='Solution:').grid(row=2, column=0, sticky='nw')
        self.solution = tk.Text(frm, width=60, height=6)
        self.solution.grid(row=2, column=1, sticky='w')

        ttk.Label(frm, text='Status:').grid(row=3, column=0, sticky='w')
        self.status = ttk.Combobox(frm, values=['Pending','In Progress','Resolved'], state='readonly')
        self.status.current(0)
        self.status.grid(row=3, column=1, sticky='w')

        ttk.Label(frm, text='Priority:').grid(row=4, column=0, sticky='w')
        self.priority = ttk.Combobox(frm, values=['Low','Medium','High'], state='readonly')
        self.priority.current(0)
        self.priority.grid(row=4, column=1, sticky='w')

        btnfrm = ttk.Frame(frm)
        btnfrm.grid(row=5, column=1, sticky='w', pady=8)
        ttk.Button(btnfrm, text='Save', command=self.save).grid(row=0, column=0, padx=4)
        ttk.Button(btnfrm, text='Search', command=self.search).grid(row=0, column=1, padx=4)
        ttk.Button(btnfrm, text='Delete', command=self.delete).grid(row=0, column=2, padx=4)

        self.listbox = tk.Listbox(frm, width=100, height=12)
        self.listbox.grid(row=6, column=0, columnspan=2, pady=8)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)

    def save(self):
        station = self.station.get().strip()
        problem = self.problem.get('1.0', 'end').strip()
        solution = self.solution.get('1.0', 'end').strip()
        status = self.status.get()
        priority = self.priority.get()
        if not station:
            messagebox.showwarning('Missing', 'Station is required')
            return
        cur = self.conn.cursor()
        now = datetime.datetime.now().isoformat()
        cur.execute('INSERT INTO ts_logs (user_id, station, problem, solution, status, priority, created_at) VALUES (?,?,?,?,?,?,?)', (1, station, problem, solution, status, priority, now))
        self.conn.commit()
        messagebox.showinfo('Saved', 'TS entry saved')
        self.search()

    def search(self):
        q = self.listbox
        q.delete(0, 'end')
        cur = self.conn.cursor()
        cur.execute('SELECT id, created_at, station, status, priority FROM ts_logs ORDER BY created_at DESC LIMIT 200')
        for row in cur.fetchall():
            q.insert('end', f"{row['id']} | {row['created_at']} | {row['station']} | {row['status']} | {row['priority']}")

    def on_select(self, event):
        sel = event.widget.curselection()
        if not sel:
            return
        idx = sel[0]
        txt = event.widget.get(idx)
        id = int(txt.split('|',1)[0].strip())
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM ts_logs WHERE id=?', (id,))
        row = cur.fetchone()
        if row:
            self.station.delete(0,'end')
            self.station.insert(0, row['station'])
            self.problem.delete('1.0','end')
            self.problem.insert('1.0', row['problem'] or '')
            self.solution.delete('1.0','end')
            self.solution.insert('1.0', row['solution'] or '')
            try:
                self.status.set(row['status'])
                self.priority.set(row['priority'])
            except Exception:
                pass

    def delete(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning('Select', 'Select an entry to delete')
            return
        txt = self.listbox.get(sel[0])
        id = int(txt.split('|',1)[0].strip())
        if messagebox.askyesno('Confirm', 'Delete selected entry?'):
            cur = self.conn.cursor()
            cur.execute('DELETE FROM ts_logs WHERE id=?', (id,))
            self.conn.commit()
            messagebox.showinfo('Deleted', 'Entry deleted')
            self.search()

if __name__ == '__main__':
    app = TSApp()
    app.search()
    app.mainloop()
