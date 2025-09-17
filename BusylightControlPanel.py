#Used for debugging, custom light control 

import tkinter as tk
from tkinter import ttk
import hid
import time
import threading
from busylight_commands import COMMANDS, COLOR_RGB
from queue import Queue, Empty

class BusylightGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Busylight Controller")
        
        # Store busylight devices and their states
        self.busylights = []
        self.light_states = {}  # Stores whether each light is cycling
        self.color_cycles = {}  # Stores color cycle threads
        self.command_queues = {}  # Queue for each light
        
        # Find and connect to busylights
        self.find_busylights()
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create canvas for light circles
        self.canvas = tk.Canvas(self.main_frame, width=400, height=200)
        self.canvas.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Create circles for each light
        self.circles = {}
        self.selected_light = None
        self.create_light_circles()
        
        # Create color selection frame
        self.create_color_controls()
        
        # Start update loop
        self.update_gui()

    def find_busylights(self):
        """Find and connect to all Busylight devices"""
        BUSYLIGHT_MODELS = {
            0x3BCF: "Busylight Omega",
            0x3BCE: "Busylight Alpha"
        }
        VID = 0x27BB
        
        for PID in BUSYLIGHT_MODELS.keys():
            found_devices = hid.enumerate(VID, PID)
            for device_info in found_devices:
                device = hid.device()
                device.open_path(device_info['path'])
                
                busylight = {
                    'info': device_info,
                    'model': BUSYLIGHT_MODELS[PID],
                    'device': device,
                    'path': device_info['path']
                }
                
                self.busylights.append(busylight)
                self.light_states[device_info['path']] = False
                self.command_queues[device_info['path']] = Queue()

    def create_light_circles(self):
        """Create clickable circles representing each light"""
        circle_size = 40
        spacing = 60
        start_x = 50
        y = 100
        
        for i, light in enumerate(self.busylights):
            x = start_x + (i * spacing)
            circle = self.canvas.create_oval(
                x - circle_size/2, y - circle_size/2,
                x + circle_size/2, y + circle_size/2,
                fill="white", outline="black", width=2
            )
            
            # Store circle reference
            self.circles[light['path']] = circle
            
            # Bind click event
            self.canvas.tag_bind(circle, '<Button-1>', 
                               lambda e, path=light['path']: self.select_light(path))
            
            # Add label
            self.canvas.create_text(x, y + circle_size/2 + 10,
                                  text=f"Light {i+1}\n{light['model']}", 
                                  anchor="n", justify="center")

    def create_color_controls(self):
        """Create color selection controls"""
        control_frame = ttk.LabelFrame(self.main_frame, text="Color Controls", padding="10")
        control_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")
        
        # Color selection
        ttk.Label(control_frame, text="Select Color:").grid(row=0, column=0, padx=5)
        self.color_var = tk.StringVar(value="white")
        color_combo = ttk.Combobox(control_frame, textvariable=self.color_var)
        color_combo['values'] = list(COMMANDS.keys())
        color_combo.grid(row=0, column=1, padx=5)
        
        # Color cycle toggle
        self.cycle_var = tk.BooleanVar(value=False)
        cycle_check = ttk.Checkbutton(control_frame, text="Color Cycle",
                                    variable=self.cycle_var,
                                    command=self.toggle_color_cycle)
        cycle_check.grid(row=0, column=2, padx=5)
        
        # Apply button
        apply_btn = ttk.Button(control_frame, text="Apply",
                              command=self.apply_color)
        apply_btn.grid(row=0, column=3, padx=5)

    def select_light(self, path):
        """Handle light selection"""
        # Reset previous selection
        if self.selected_light:
            self.canvas.itemconfig(self.circles[self.selected_light],
                                 width=2)
        
        self.selected_light = path
        self.canvas.itemconfig(self.circles[path], width=4)
        
        # Update controls to show current state
        self.cycle_var.set(self.light_states[path])

    def create_command(self, r, g, b):
        """Create a command packet with given RGB values"""
        return [
            0x00, 0x10, 0x01, r, g, b, 0x01, 0x00,
            0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x06, 0x04, 0x55, 0xFF, 0xFF, 0xFF, 0x04,
            0x52
        ]

    def color_cycle_thread(self, path):
        """Thread function for color cycling"""
        target_sum = 0x64
        step = 0x05
        
        while self.light_states[path]:
            for r in range(0, target_sum + 1, step):
                if not self.light_states[path]:
                    break
                    
                for g in range(0, target_sum - r + 1, step):
                    if not self.light_states[path]:
                        break
                        
                    b = target_sum - r - g
                    if b >= 0:
                        command = self.create_command(r, g, b)
                        self.command_queues[path].put(command)
                        time.sleep(0.05)

    def toggle_color_cycle(self):
        """Toggle color cycling for selected light"""
        if not self.selected_light:
            return
            
        self.light_states[self.selected_light] = self.cycle_var.get()
        
        if self.cycle_var.get():
            # Start color cycle thread
            thread = threading.Thread(
                target=self.color_cycle_thread,
                args=(self.selected_light,),
                daemon=True
            )
            self.color_cycles[self.selected_light] = thread
            thread.start()
        else:
            # Stop color cycle and set to white
            self.command_queues[self.selected_light].put(COMMANDS['white'])

    def apply_color(self):
        """Apply selected color to selected light"""
        if not self.selected_light:
            return
            
        # Stop any running color cycle
        self.light_states[self.selected_light] = False
        self.cycle_var.set(False)
        
        # Apply selected color
        color = self.color_var.get()
        if color in COMMANDS:
            self.command_queues[self.selected_light].put(COMMANDS[color])

    def update_gui(self):
        """Update GUI and process command queues"""
        # Process command queues
        for path, queue in self.command_queues.items():
            try:
                while True:
                    command = queue.get_nowait()
                    # Find the corresponding device
                    for light in self.busylights:
                        if light['path'] == path:
                            light['device'].write(command)
                            break
            except Empty:
                pass
        
        # Update circle colors based on last command
        for path, circle in self.circles.items():
            if self.light_states[path]:
                # Show animation effect for cycling lights
                current_color = self.canvas.itemcget(circle, "fill")
                if current_color == "white":
                    self.canvas.itemconfig(circle, fill="lightblue")
                else:
                    self.canvas.itemconfig(circle, fill="white")
            else:
                # Show static color
                self.canvas.itemconfig(circle, fill=self.color_var.get())
        
        # Schedule next update
        self.root.after(100, self.update_gui)

    def cleanup(self):
        """Clean up resources"""
        # Stop all color cycles
        for path in self.light_states:
            self.light_states[path] = False
        
        # Turn off all lights
        off_command = COMMANDS['off']
        for light in self.busylights:
            light['device'].write(off_command)
            light['device'].close()

def main():
    root = tk.Tk()
    app = BusylightGUI(root)
    
    # Set up cleanup on window close
    root.protocol("WM_DELETE_WINDOW", lambda: [app.cleanup(), root.destroy()])
    
    root.mainloop()

if __name__ == "__main__":
    main()
