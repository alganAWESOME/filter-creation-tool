import cv2 as cv
import numpy as np
from tkinter import *

class BaseFilter:
    def __init__(self):
        self.config_frame = None
        self.update_callback = None
        pass

    def configure(self):
        raise NotImplementedError

    def apply(self, image):
        raise NotImplementedError

    def serialize_config(self):
        # Convert NumPy types to native Python types for JSON serialization
        config_serializable = {}
        for key, value in self.config.items():
            if isinstance(value, np.ndarray):
                # Convert numpy arrays to lists
                config_serializable[key] = value.tolist()
            elif isinstance(value, (np.int_, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64,
                                    np.uint8, np.uint16, np.uint32, np.uint64)):
                # Convert numpy integers to Python int
                config_serializable[key] = int(value)
            elif isinstance(value, (np.float_, np.float16, np.float32, np.float64)):
                # Convert numpy floats to Python float
                config_serializable[key] = float(value)
            else:
                # Assume the value is already serializable
                config_serializable[key] = value

        return {
            "type": self.__class__.__name__,
            "config": config_serializable
        }

class HSVFilter(BaseFilter):
    def __init__(self):
        super().__init__()
        self.config = {'HSV_ranges': []}
        self.selected_filter_index = None

    def configure(self):
       # Listbox for displaying current filters
        self.filter_listbox = Listbox(self.config_frame)
        self.filter_listbox.pack()
        self.filter_listbox.bind('<<ListboxSelect>>', lambda e: self.on_filter_select(e)) 

        self._update_filter_listbox()

        # Buttons for adding/deleting/configuring filters
        Button(self.config_frame, text="Add Range", command = self.add_filter).pack()
        Button(self.config_frame, text="Delete Range", command = self.delete_filter).pack()
        Button(self.config_frame, text="Configure", command = self.configure_range).pack()

    def _update_filter_listbox(self):
        # Add existing  filters to the listbox
        self.filter_listbox.delete(0, END)
        for i, _ in enumerate(self.config['HSV_ranges']):
            self.filter_listbox.insert(END, f"Filter {i}")

    def add_filter(self):
        # Add a new filter configuration with default values
        new_filter_config = {'center': [0, 0, 0], 'thresholds': [89, 255, 255]}
        self.config['HSV_ranges'].append(new_filter_config)
        self.filter_listbox.insert(END, f"Filter {len(self.config['HSV_ranges'])-1}")
        self.update_callback()

    def delete_filter(self):
        if self.selected_filter_index is None:
            return

        if 0 <= self.selected_filter_index < len(self.config['HSV_ranges']):
            del self.config['HSV_ranges'][self.selected_filter_index]

        self._update_filter_listbox()
        self.update_callback()

    def on_filter_select(self, event):
        selection = event.widget.curselection()
        if selection:
            self.selected_filter_index = selection[0]

    def configure_range(self):
        if self.selected_filter_index is None:
            return
        
        selected_filter = self.config['HSV_ranges'][self.selected_filter_index]

        # Create a new Toplevel window for the sliders
        slider_window = Toplevel()
        slider_window.title(f"Filter {self.selected_filter_index} Configuration")

        # Creating sliders for each HSV component within the config_frame
        Label(slider_window, text="Hue Threshold:").pack()
        hue_scale = Scale(slider_window, from_=0, to=89, orient=HORIZONTAL,
                          command=lambda val: self.on_threshold_change(val, 0))
        hue_scale.set(selected_filter['thresholds'][0])
        hue_scale.pack()

        Label(slider_window, text="Saturation Threshold:").pack()
        sat_scale = Scale(slider_window, from_=0, to=255, orient=HORIZONTAL,
                          command=lambda val: self.on_threshold_change(val, 1))
        sat_scale.set(selected_filter['thresholds'][1])
        sat_scale.pack()

        Label(slider_window, text="Value Threshold:").pack()
        val_scale = Scale(slider_window, from_=0, to=255, orient=HORIZONTAL,
                          command=lambda val: self.on_threshold_change(val, 2))
        val_scale.set(selected_filter['thresholds'][2])
        val_scale.pack()
        
    def on_mouse_click(self, event, x, y, flags, param, image, source=None):
        if self.selected_filter_index is None:
            return
        
        selected_range = self.config['HSV_ranges'][self.selected_filter_index]
        # Handle the mouse click event
        if event == cv.EVENT_LBUTTONDOWN and image is not None:
            bgr_color = image[y, x]
            bgr_color_image = np.uint8([[bgr_color]])
            hsv_color = cv.cvtColor(bgr_color_image, cv.COLOR_BGR2HSV)[0][0]
            selected_range['center'] = hsv_color.tolist()

    def on_threshold_change(self, val, h_s_v):
        if not self.config['HSV_ranges']:
            # If no range is defined, return
            return

        # Assuming we are modifying the thresholds of the first HSV range
        selected_range = self.config['HSV_ranges'][self.selected_filter_index]

        # Update the threshold based on whether h_s_v is 0 (hue), 1 (saturation), or 2 (value)
        selected_range['thresholds'][h_s_v] = int(val)

        self.update_callback()

    def apply(self, image):
        if not self.config['HSV_ranges']:
            return image

        final_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        hsv_image = cv.cvtColor(image, cv.COLOR_BGR2HSV)

        for hsv_range in self.config['HSV_ranges']:
            center, thresholds = hsv_range['center'], hsv_range['thresholds']
            hsv_ranges = self.calc_hsv_ranges(center, thresholds)
            
            for range in hsv_ranges:
                lower_bound = np.array(range['HSV_min'], dtype=np.uint8)
                upper_bound = np.array(range['HSV_max'], dtype=np.uint8)
                current_mask = cv.inRange(hsv_image, lower_bound, upper_bound)
                final_mask = cv.bitwise_or(final_mask, current_mask)

        return cv.bitwise_and(image, image, mask=final_mask)
    
    def calc_hsv_ranges(self, center, thresholds):
        hue_min = (center[0] - thresholds[0]) % 180
        hue_max = (center[0] + thresholds[0]) % 180
        sat_min = max(center[1] - thresholds[1], 0)
        sat_max = min(center[1] + thresholds[1], 255)
        val_min = max(center[2] - thresholds[2], 0)
        val_max = min(center[2] + thresholds[2], 255)

        if hue_min > hue_max:
            return [
                {"HSV_min": [hue_min, sat_min, val_min], "HSV_max": [179, sat_max, val_max]},
                {"HSV_min": [0, sat_min, val_min], "HSV_max": [hue_max, sat_max, val_max]}
            ]
        else:
            return [{"HSV_min": [hue_min, sat_min, val_min], "HSV_max": [hue_max, sat_max, val_max]}]

    def serialize_config(self):
        # for JSON serialization
        serializable_ranges = []
        for hsv_range in self.config['HSV_ranges']:
            serializable_range = {}
            for key, value in hsv_range.items():
                serializable_range[key] = [int(v) for v in value]
            serializable_ranges.append(serializable_range)

        return {
            "type": self.__class__.__name__,
            "config": {"HSV_ranges": serializable_ranges}
        }

class ContrastFilter(BaseFilter):
    name = "Contrast Filter"

    def __init__(self):
        super().__init__()
        self.config = {'Contrast':1.0}

    def configure(self):
        # Creating a slider for the contrast level within the self.config_frame
        Label(self.config_frame, text="Contrast Level:").pack()
        contrast_scale = Scale(self.config_frame, from_=0.0, to=3.0, resolution=0.1, orient=HORIZONTAL,
                               command = self.on_contrast_change)
        contrast_scale.set(self.config['Contrast'])
        contrast_scale.pack()

    def on_contrast_change(self, val):
        self.config['Contrast'] = float(val)
        self.update_callback()

    def apply(self, image):
        # Convert to float for more precision for transformations
        image_float = image.astype(np.float32)

        # Apply the contrast formula
        image_adjusted = image_float * self.config['Contrast']

        # Clip values to the valid range (0 to 255) and convert back to uint8
        image_adjusted = np.clip(image_adjusted, 0, 255).astype(np.uint8)

        return image_adjusted
    
class SaturationFilter(BaseFilter):
    def __init__(self):
        super().__init__()
        self.config = {'Saturation':1.0}

    def configure(self):
        # Creating a slider for the saturation level within the self.config_frame
        Label(self.config_frame, text="Saturation Level:").pack()
        sat_scale = Scale(self.config_frame, from_=0.0, to=3.0, resolution=0.1, orient=HORIZONTAL,
                          command = self.on_saturation_change)
        sat_scale.set(self.config['Saturation'])
        sat_scale.pack()

    def on_saturation_change(self, val):
        self.config['Saturation'] = float(val)
        self.update_callback()

    def apply(self, image):
        if self.config['Saturation'] == 1.0:  # No change in saturation
            return image

        # Convert to HSV, adjust saturation, and convert back to BGR
        hsv_image = cv.cvtColor(image, cv.COLOR_BGR2HSV).astype("float32")
        hsv_image[..., 1] *= self.config['Saturation']
        hsv_image[..., 1] = np.clip(hsv_image[..., 1], 0, 255)
        adjusted_image = cv.cvtColor(hsv_image.astype("uint8"), cv.COLOR_HSV2BGR)
        return adjusted_image

# class DilationFilter(BaseFilter):
#     def __init__(self):
#         super().__init__()
#         self.config = {'kernel_size': 3}  # Default kernel size

#     def configure(self, config_frame, update_callback):
#         # Implementation for configuration UI with a slider for kernel_size
#         # ...

#     def apply(self, image):
#         kernel_size = self.config['kernel_size']
#         kernel = np.ones((kernel_size, kernel_size), np.uint8)
#         return cv.dilate(image, kernel, iterations=1)
    
# class ErosionFilter(BaseFilter):
#     def __init__(self):
#         super().__init__()
#         self.config = {'kernel_size': 3}  # Default kernel size

#     def configure(self, config_frame, update_callback):
#         # Implementation for configuration UI with a slider for kernel_size
#         # ...

#     def apply(self, image):
#         kernel_size = self.config['kernel_size']
#         kernel = np.ones((kernel_size, kernel_size), np.uint8)
#         return cv.erode(image, kernel, iterations=1)
