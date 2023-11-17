import cv2 as cv
import numpy as np
from tkinter import *

class BaseFilter:
    def __init__(self):
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
        self.config = {'HSV_ranges': [{'center':[0,0,0], 'thresholds':[0,0,0]}]}
        self.hue_threshold = 0
        self.saturation_threshold = 0
        self.value_threshold = 0
        self.HSV_range = None
        self.clicked_color = None

    def configure(self, config_frame, update_callback):
        # Clear any existing widgets in the configuration frame
        for widget in config_frame.winfo_children():
            widget.destroy()

        # Creating sliders for each HSV component within the config_frame
        Label(config_frame, text="Hue Threshold:").pack()
        hue_scale = Scale(config_frame, from_=0, to=89, orient=HORIZONTAL,
                          command=lambda val: self.on_threshold_change(val, update_callback, 0))
        hue_scale.set(self.hue_threshold)
        hue_scale.pack()

        Label(config_frame, text="Saturation Threshold:").pack()
        sat_scale = Scale(config_frame, from_=0, to=255, orient=HORIZONTAL,
                          command=lambda val: self.on_threshold_change(val, update_callback, 1))
        sat_scale.set(self.saturation_threshold)
        sat_scale.pack()

        Label(config_frame, text="Value Threshold:").pack()
        val_scale = Scale(config_frame, from_=0, to=255, orient=HORIZONTAL,
                          command=lambda val: self.on_threshold_change(val, update_callback, 2))
        val_scale.set(self.value_threshold)
        val_scale.pack()
        
    def on_mouse_click(self, event, x, y, flags, param, image, source=None):
        selected_range = self.config['HSV_ranges'][0]
        # Handle the mouse click event
        if event == cv.EVENT_LBUTTONDOWN and image is not None:
            bgr_color = image[y, x]
            bgr_color_image = np.uint8([[bgr_color]])
            hsv_color = cv.cvtColor(bgr_color_image, cv.COLOR_BGR2HSV)[0][0]
            selected_range['center'] = hsv_color.tolist()

    def on_threshold_change(self, val, update_callback, h_s_v):
        if not self.config['HSV_ranges']:
            # If no range is defined, return
            return

        # Assuming we are modifying the thresholds of the first HSV range
        selected_range = self.config['HSV_ranges'][0]

        # Update the threshold based on whether h_s_v is 0 (hue), 1 (saturation), or 2 (value)
        selected_range['thresholds'][h_s_v] = int(val)

        update_callback()

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

    def configure(self, config_frame, update_callback):
        # Clear any existing widgets in the configuration frame
        for widget in config_frame.winfo_children():
            widget.destroy()

        # Creating a slider for the contrast level within the config_frame
        Label(config_frame, text="Contrast Level:").pack()
        contrast_scale = Scale(config_frame, from_=0.0, to=3.0, resolution=0.1, orient=HORIZONTAL,
                               command=lambda val: self.on_contrast_change(val, update_callback))
        contrast_scale.set(self.config['Contrast'])
        contrast_scale.pack()

    def on_contrast_change(self, val, update_callback):
        self.config['Contrast'] = float(val)
        update_callback()

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

    def configure(self, config_frame, update_callback):
        # Clear any existing widgets in the configuration frame
        for widget in config_frame.winfo_children():
            widget.destroy()

        # Creating a slider for the saturation level within the config_frame
        Label(config_frame, text="Saturation Level:").pack()
        sat_scale = Scale(config_frame, from_=0.0, to=3.0, resolution=0.1, orient=HORIZONTAL,
                          command=lambda val: self.on_saturation_change(val, update_callback))
        sat_scale.set(self.config['Saturation'])
        sat_scale.pack()

    def on_saturation_change(self, val, update_callback):
        self.config['Saturation'] = float(val)
        update_callback()

    def apply(self, image):
        if self.config['Saturation'] == 1.0:  # No change in saturation
            return image

        # Convert to HSV, adjust saturation, and convert back to BGR
        hsv_image = cv.cvtColor(image, cv.COLOR_BGR2HSV).astype("float32")
        hsv_image[..., 1] *= self.config['Saturation']
        hsv_image[..., 1] = np.clip(hsv_image[..., 1], 0, 255)
        adjusted_image = cv.cvtColor(hsv_image.astype("uint8"), cv.COLOR_HSV2BGR)
        return adjusted_image

