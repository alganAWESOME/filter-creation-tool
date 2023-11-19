import cv2 as cv
from tkinter import *
from window_capture import WindowCapture
import filters
import json, os

class FilterCreator:
    def __init__(self, window_name):
        self.window_capture = WindowCapture(window_name)
        self.filters = []  # List of filter objects
        self.init_tkinter()
        self.current_screenshot = None
        self.current_filtered_image = None
        self.filter_index = None

    def init_tkinter(self):
        self.root = Tk()
        self.root.title("Filter Configurator")

        # Button to add a new HSV filter
        Button(self.root, text="Add Filter", command=self.add_filter).pack()

        # Listbox to show active filters
        self.filter_list = Listbox(self.root)
        self.filter_list.pack()

        # Frame for filter configuration
        self.config_frame = Frame(self.root)
        self.config_frame.pack(side=BOTTOM)
        self.filter_list.bind('<<ListboxSelect>>', lambda e: self.update_filter_index())

        # Add "Move Up", "Move Down", "Delete" and "Save Filter" buttons
        Button(self.root, text="Move Up", command=self.move_filter_up).pack()
        Button(self.root, text="Move Down", command=self.move_filter_down).pack()
        Button(self.root, text='Delete', command=self.delete_filter).pack()
        Button(self.root, text="Save Filter", command=self.save_filters).pack()
        Button(self.root, text="Load Filter", command=self.load_preset).pack()

        # Entry to name the filter preset
        self.preset_name_entry = Entry(self.root)
        self.preset_name_entry.pack()
            
    def add_filter(self):
        filter_window = Toplevel(self.root)
        filter_window.title("Select Filter Type")

        # List all classes of the filters module
        filter_options = [attr for attr in dir(filters) 
                        if isinstance(getattr(filters, attr), type) and 
                        getattr(filters, attr).__module__ == filters.__name__ and 
                        attr != 'BaseFilter']

        # Create buttons for each filter type
        for option in filter_options:
            Button(filter_window, text=option, 
                command=lambda name=option: self.create_filter(name, filter_window)).pack()

    def create_filter(self, filter_name, filter_window):
        try:
            # Get the class from the filters module using the filter_name string
            filter_class = getattr(filters, filter_name)
            # Instantiate the filter class
            new_filter = filter_class()
            new_filter.config_frame = self.config_frame
            new_filter.update_callback = self.update_filters
        except AttributeError:
            # Raised if filter_name does not correspond to a class in filters module
            raise ValueError("Unknown filter type") from None
        except Exception as e:
            # Handle other potential errors during instantiation
            raise e
        
        self.filters.append(new_filter)
        self.filter_list.insert(END, filter_name)
        filter_window.destroy()
    
    def update_filter_index(self):
        selected_index = self.filter_list.curselection()
        if selected_index:
            self.filter_index = selected_index[0]
        self.update_config_frame()
    
    def update_config_frame(self):
        # Clear current configuration frame
        for widget in self.config_frame.winfo_children():
            widget.destroy()

        if self.filter_index is not None:
            selected_filter = self.filters[self.filter_index]
            selected_filter.configure()

    def move_filter_up(self):
        selected_index = self.filter_list.curselection()
        if selected_index and selected_index[0] > 0:
            index = selected_index[0]
            # Swap the filters
            self.filters[index], self.filters[index - 1] = self.filters[index - 1], self.filters[index]
            # Update the listbox
            self.filter_list.insert(index - 1, self.filter_list.get(index))
            self.filter_list.delete(index + 1)
            self.filter_list.select_set(index - 1)

    def move_filter_down(self):
        selected_index = self.filter_list.curselection()
        if selected_index and selected_index[0] < len(self.filters) - 1:
            index = selected_index[0]
            # Swap the filters
            self.filters[index], self.filters[index + 1] = self.filters[index + 1], self.filters[index]
            # Update the listbox
            self.filter_list.insert(index + 2, self.filter_list.get(index))
            self.filter_list.delete(index)
            self.filter_list.select_set(index + 1)

    def delete_filter(self):
        selected_index = self.filter_list.curselection()
        if selected_index:
            self.filters.pop(selected_index[0])
            self.filter_list.delete(selected_index[0])

    def update_filters(self):
        # Refreshes the filters; called as a callback from filter configuration
        self.apply_filters()

    def apply_filters(self):
        if self.current_screenshot is not None:
            self.current_filtered_image = self.current_screenshot.copy()
            for filter_obj in self.filters:
                self.current_filtered_image = filter_obj.apply(self.current_filtered_image)
            cv.imshow("Filtered", self.current_filtered_image)

    def start(self):
        self.window_capture.start()
        cv.namedWindow("Original")
        cv.namedWindow("Filtered")
        cv.setMouseCallback("Original", self.on_mouse_click_original)
        cv.setMouseCallback("Filtered", self.on_mouse_click_filtered)

        while True:
            self.current_screenshot = self.window_capture.screenshot
            if self.current_screenshot is None:
                continue

            cv.imshow("Original", self.current_screenshot)
            self.apply_filters()

            key = cv.waitKey(1)
            if key == ord('q'):
                self.window_capture.stop()
                cv.destroyAllWindows()
                break

            self.root.update()

    def on_mouse_click_original(self, event, x, y, flags, param):
        self.on_mouse_click(event, x, y, flags, param, source="original")

    def on_mouse_click_filtered(self, event, x, y, flags, param):
        self.on_mouse_click(event, x, y, flags, param, source="filtered")
    
    def on_mouse_click(self, event, x, y, flags, param, source):
        if event == cv.EVENT_LBUTTONDOWN:
            # Handle the mouse click event based on the source (original or filtered)
            if self.filter_index is not None and (self.current_screenshot is not None or self.current_filtered_image is not None):
                selected_filter = self.filters[self.filter_index]
                if hasattr(selected_filter, 'on_mouse_click'):
                    # Pass the appropriate image based on the source
                    source_image = self.current_filtered_image if source == "filtered" else self.current_screenshot
                    selected_filter.on_mouse_click(event, x, y, flags, param, source_image)
                    self.apply_filters()

    def save_filters(self):
        preset_name = self.preset_name_entry.get()
        if not preset_name:
            print("Please enter a name for the preset.")
            return

        # Construct the preset data
        preset_data = [filter.serialize_config() for filter in self.filters]

        # Path to the filters.json file
        file_path = 'filters.json'

        # Check if the file exists and update or add the preset
        if os.path.exists(file_path):
            with open(file_path, 'r+') as file:
                data = json.load(file)

                # Update if the preset already exists, else add a new preset
                if preset_name in data:
                    data[preset_name] = preset_data
                else:
                    data.update({preset_name: preset_data})

                # Write the updated data back to the file
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
        else:
            # Create a new file with the preset
            with open(file_path, 'w') as file:
                json.dump({preset_name: preset_data}, file, indent=4)

        print(f"Preset '{preset_name}' saved.")

    def load_preset(self):
        if not os.path.exists('filters.json'):
            print("No saved filters found.")
            return

        with open('filters.json', 'r') as file:
            presets = json.load(file)

        preset_window = Toplevel(self.root)
        preset_window.title("Load Filter Preset")

        preset_listbox = Listbox(preset_window)
        preset_listbox.pack()

        for preset_name in presets.keys():
            preset_listbox.insert(END, preset_name)

        Button(preset_window, text="Load Selected Preset",
               command=lambda: self.on_preset_selected(preset_listbox, presets, preset_window)).pack()

    def on_preset_selected(self, preset_listbox, presets, preset_window):
        selected_index = preset_listbox.curselection()
        if not selected_index:
            print("Please select a preset.")
            return

        selected_preset_name = preset_listbox.get(selected_index)
        selected_preset = presets[selected_preset_name]

        self.apply_selected_preset(selected_preset, preset_window)

    def apply_selected_preset(self, selected_preset, preset_window):
        new_filters = []
        self.filter_list.delete(0, END)

        for filter_config in selected_preset:
            filter_type = filter_config["type"]
            filter_class = getattr(filters, filter_type, None)
            self.filter_list.insert(END, filter_type)
            if filter_class is None:
                print(f"Unknown filter type: {filter_type}")
                continue

            filter_instance = filter_class()
            filter_instance.config_frame = self.config_frame
            filter_instance.update_callback = self.update_filters
            filter_instance.config = filter_config["config"]
            new_filters.append(filter_instance)

        self.filters = new_filters

        # Close the preset window after applying the preset
        preset_window.destroy()

def main():
    filter = FilterCreator("Toontown Offline")
    filter.start()

if __name__ == "__main__":
    main()
