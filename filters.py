import cv2 as cv
import numpy as np
from tkinter import *
import base64

class BaseFilter:
    def __init__(self):
        self.config = {}
        self.config_frame = None
        self.update_callback = None
        self.visible = True

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

    @staticmethod
    def deserialize_config(config):
        return config

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
        new_filter_config = {'center': [0, 0, 0], 'thresholds': [89//2, 255//2, 255//2]}
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
        if self.config['Saturation'] == 1.0:
            return image

        # Convert to HSV, adjust saturation, and convert back to BGR
        hsv_image = cv.cvtColor(image, cv.COLOR_BGR2HSV).astype("float32")
        hsv_image[..., 1] *= self.config['Saturation']
        hsv_image[..., 1] = np.clip(hsv_image[..., 1], 0, 255)
        adjusted_image = cv.cvtColor(hsv_image.astype("uint8"), cv.COLOR_HSV2BGR)
        return adjusted_image

class DilationFilter(BaseFilter):
    def __init__(self):
        super().__init__()
        self.config = {'dilation_size': 1}

    def configure(self):
        Label(self.config_frame, text="Dilation Size:").pack()
        dilation_size_scale = Scale(self.config_frame, from_=1, to=10, orient=HORIZONTAL,
                                    command=self.on_dilation_size_change)
        dilation_size_scale.set(self.config['dilation_size'])  # Set to current value in config
        dilation_size_scale.pack()

    def on_dilation_size_change(self, val):
        self.config['dilation_size'] = int(val)
        self.update_callback()

    def apply(self, image):
        kernel_size = self.config['dilation_size']
        kernel = cv.getStructuringElement(cv.MORPH_RECT, (kernel_size, kernel_size))
        return cv.dilate(image, kernel)
    
class ErosionFilter(BaseFilter):
    def __init__(self):
        super().__init__()
        self.config = {'erosion_size': 1}

    def configure(self):
        Label(self.config_frame, text="Erosion Size:").pack()
        erosion_size_scale = Scale(self.config_frame, from_=1, to=10, orient=HORIZONTAL,
                                   command=self.on_erosion_size_change)
        erosion_size_scale.set(self.config['erosion_size'])  # Set to current value in config
        erosion_size_scale.pack()

    def on_erosion_size_change(self, val):
        self.config['erosion_size'] = int(val)
        self.update_callback()

    def apply(self, image):
        kernel_size = self.config['erosion_size']
        kernel = cv.getStructuringElement(cv.MORPH_RECT, (kernel_size, kernel_size))
        return cv.erode(image, kernel)

class ThresholdFilter(BaseFilter):
    def __init__(self):
        super().__init__()
        self.config = {'threshold_value': 127, 'max_value': 255}

    def configure(self):
        Label(self.config_frame, text="Threshold Value:").pack()
        threshold_scale = Scale(self.config_frame, from_=0, to=255, orient=HORIZONTAL,
                                command=self.on_threshold_value_change)
        threshold_scale.set(self.config['threshold_value'])
        threshold_scale.pack()

        Label(self.config_frame, text="Max Value:").pack()
        max_value_scale = Scale(self.config_frame, from_=0, to=255, orient=HORIZONTAL,
                                command=self.on_max_value_change)
        max_value_scale.set(self.config['max_value'])
        max_value_scale.pack()

    def on_threshold_value_change(self, val):
        self.config['threshold_value'] = int(val)
        self.update_callback()

    def on_max_value_change(self, val):
        self.config['max_value'] = int(val)
        self.update_callback()

    def apply(self, image):
        # Convert the image to grayscale
        gray_image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        # Apply binary thresholding to the grayscale image
        threshold_value = self.config['threshold_value']
        max_value = self.config['max_value']
        _, binary_image = cv.threshold(gray_image, threshold_value, max_value, cv.THRESH_BINARY)
        return binary_image

class MinimumPixelCountFilter(BaseFilter):
    def __init__(self):
        super().__init__()
        # Initialize configuration with default values
        self.config = {
            'brightness_threshold': 0,
            'pixel_count_threshold': 1000
        }

    def configure(self):
        # Create sliders for brightness and pixel count thresholds
        Label(self.config_frame, text="Brightness Threshold:").pack()
        brightness_scale = Scale(self.config_frame, from_=0, to=255, orient=HORIZONTAL,
                                 command=self.on_brightness_threshold_change)
        brightness_scale.set(self.config['brightness_threshold'])
        brightness_scale.pack()

        Label(self.config_frame, text="Minimum Pixel Count:").pack()
        pixel_count_scale = Scale(self.config_frame, from_=0, to=10000, orient=HORIZONTAL,
                                  command=self.on_pixel_count_threshold_change)
        pixel_count_scale.set(self.config['pixel_count_threshold'])
        pixel_count_scale.pack()

    def on_brightness_threshold_change(self, val):
        self.config['brightness_threshold'] = int(val)
        self.update_callback()

    def on_pixel_count_threshold_change(self, val):
        self.config['pixel_count_threshold'] = int(val)
        self.update_callback()

    def apply(self, image, min_threshold=True):
        if len(image.shape) == 2:
            grayscale = image
        else:
            # Convert the image to grayscale
            grayscale = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        # Count pixels above the brightness threshold
        count = cv.countNonZero(cv.threshold(grayscale, self.config['brightness_threshold'], 255, cv.THRESH_BINARY)[1])

        # Return original image if count exceeds the pixel count threshold, else return black image
        if min_threshold:
            if count >= self.config['pixel_count_threshold']:
                return image
        else:
            if count <= self.config['pixel_count_threshold']:
                return image
        return np.zeros(image.shape, dtype=image.dtype)

class MaxPixelCountFilter(MinimumPixelCountFilter):
    def __init__(self):
        super().__init__()

    def apply(self, image):
        super().apply(image, min_threshold=False)

class GrayscaleFilter(BaseFilter):
    def __init__(self):
        super().__init__()
        self.config = {}

    def configure(self):
        pass

    def apply(self, image):
        return cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    
class CropFilter(BaseFilter):
    def __init__(self):
        super().__init__()
        self.config = {'crops': []}
        self.selected_crop_index = None
        self.temporary_crop_start = None

    def configure(self, mode='Crop'):
        self.crop_listbox = Listbox(self.config_frame)
        self.crop_listbox.pack()
        self.crop_listbox.bind('<<ListboxSelect>>', lambda e: self.on_crop_select(e))
        self._update_crop_listbox()

        Button(self.config_frame, text=f"Add {mode}", command=self.add_crop).pack()
        Button(self.config_frame, text=f"Delete {mode}", command=self.delete_crop).pack()

    def _update_crop_listbox(self):
        self.crop_listbox.delete(0, END)
        for i, _ in enumerate(self.config['crops']):
            self.crop_listbox.insert(END, f"Crop {i}")

    def add_crop(self):
        new_crop_config = {'top_left': [0, 0], 'bottom_right': [100, 100]}
        self.config['crops'].append(new_crop_config)
        self._update_crop_listbox()
        self.update_callback()

    def delete_crop(self):
        if self.selected_crop_index is None:
            return

        if 0 <= self.selected_crop_index < len(self.config['crops']):
            del self.config['crops'][self.selected_crop_index]

        self._update_crop_listbox()
        self.update_callback()

    def on_crop_select(self, event):
        selection = event.widget.curselection()
        if selection:
            self.selected_crop_index = selection[0]

    def on_mouse_click(self, event, x, y, flags, param, image, source=None):
        if event == cv.EVENT_LBUTTONDOWN and image is not None:
            if self.temporary_crop_start:
                selected_crop = self.config['crops'][self.selected_crop_index]
                selected_crop['top_lFeft'] = list(self.temporary_crop_start)
                selected_crop['bottom_right'] = [x, y]
                self.temporary_crop_start = None
            else:
                self.temporary_crop_start = (x, y)

    def apply(self, image):
        if not self.config['crops']:
            return image

        final_mask = np.zeros(image.shape[:2], dtype=np.uint8)

        for crop in self.config['crops']:
            top_left, bottom_right = crop['top_left'], crop['bottom_right']
            crop_mask = np.zeros(image.shape[:2], dtype=np.uint8)
            cv.rectangle(crop_mask, tuple(top_left), tuple(bottom_right), 255, -1)
            final_mask = cv.bitwise_or(final_mask, crop_mask)

        return cv.bitwise_and(image, image, mask=final_mask)

    def serialize_config(self):
        return {
            "type": self.__class__.__name__,
            "config": {"crops": self.config['crops']}
        }

class BlockFilter(CropFilter):
    def __init__(self):
        super().__init__()

    def configure(self, mode='Block'):
        return super().configure(mode)
    
    def apply(self, image):
        if not self.config['crops']:
            return image

        # Start with a mask that covers the whole image
        final_mask = np.ones(image.shape[:2], dtype=np.uint8) * 255

        for crop in self.config['crops']:
            top_left, bottom_right = crop['top_left'], crop['bottom_right']
            # Set the cropped areas to zero (black) in the mask
            cv.rectangle(final_mask, tuple(top_left), tuple(bottom_right), 0, -1)

        # Apply the inverted mask to keep the rest of the image
        return cv.bitwise_and(image, image, mask=final_mask)

class BlackFilter(BaseFilter):
    def __init__(self):
        super().__init__()
    
    def configure(self):
        pass
    
    def apply(self, image):
        # Create a mask where black pixels are marked
        # Assuming the image is in RGB format
        black_pixels_mask = (image[:, :, 0] == 0) & \
                            (image[:, :, 1] == 0) & \
                            (image[:, :, 2] == 0)

        # Create an empty image in grayscale format
        filtered_image = np.zeros(image.shape[:2], dtype=np.uint8)

        # Change black pixels in the original image to white in the filtered image
        filtered_image[black_pixels_mask] = 255

        return filtered_image

class ContourFilter(BaseFilter):
    def __init__(self):
        super().__init__()

    def configure(self):
        pass

    def apply(self, image):
        # Check if the image is binary
        if not self._is_binary(image):
            return image

        # Find contours
        contours, _ = cv.findContours(image, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

        # Draw contours on a blank canvas
        contour_image = np.zeros_like(image)
        cv.drawContours(contour_image, contours, -1, (255, 255, 255), thickness=2)

        return contour_image

    def _is_binary(self, image):
        # Check if the image is binary AND grayscale
        if len(np.unique(image)) == 2 and len(image.shape) <= 2:
            return True
        return False

class ContourAreaFilter(ContourFilter):
    def __init__(self):
        super().__init__()
        self.config = {
            "min_area": 0,
            "max_area": 20000
        }

    def configure(self):
        min_area_slider = Scale(self.config_frame, from_=0, to=20000, orient=HORIZONTAL, label="Min Area", command=self._on_min_change)
        min_area_slider.set(self.config["min_area"])
        min_area_slider.pack()

        max_area_slider = Scale(self.config_frame, from_=0, to=20000, orient=HORIZONTAL, label="Max Area", command=self._on_max_change)
        max_area_slider.set(self.config["max_area"])
        max_area_slider.pack()

    def _on_min_change(self, val):
        self.config['min_area'] = int(val)

    def _on_max_change(self, val):
        self.config['max_area'] = int(val)

    def apply(self, img):
        if not self._is_binary(img):
            return img
        
        contours, _ = cv.findContours(img, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

        mask = np.zeros_like(img)
        for contour in contours:
            area = cv.contourArea(contour)
            if self.config["min_area"] < area < self.config["max_area"]:
                cv.drawContours(mask, [contour], -1, (255, 255, 255), thickness=cv.FILLED)

        result = cv.bitwise_and(img, mask)
        return mask

class ContourCropFilter(CropFilter):
    def __init__(self):
        super().__init__()

    def _is_binary(self, image):
        # Check if the image is binary AND grayscale
        if len(np.unique(image)) == 2 and len(image.shape) <= 2:
            return True
        return False

    def apply(self, image):
        if not self.config['crops'] or not self._is_binary(image):
            return image

        final_image = np.zeros_like(image)
        contours, _ = cv.findContours(image, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

        for crop in self.config['crops']:
            top_left, bottom_right = crop['top_left'], crop['bottom_right']
            crop_rect = cv.rectangle(np.zeros_like(image), tuple(top_left), tuple(bottom_right), 255, -1)

            for contour in contours:
                if self.checkContourInCrop(contour, crop_rect):
                    cv.drawContours(final_image, [contour], -1, 255, thickness=cv.FILLED)

        return final_image

    @staticmethod
    def checkContourInCrop(contour, crop_rect):
        for point in contour:
            if crop_rect[point[0][1], point[0][0]] == 255:
                return True
        return False
    
class CannyEdgeDetector(BaseFilter):
    def __init__(self):
        super().__init__()
        self.config = {
            'Threshold1': 100,
            'Threshold2': 200,
            'ApertureSize': 3,
            'L2Gradient': False
        }

    def configure(self):
        Label(self.config_frame, text="Threshold1:").pack()
        threshold1_scale = Scale(self.config_frame, from_=0, to=255, orient=HORIZONTAL,
                                 command=lambda val: self.on_threshold1_change(val))
        threshold1_scale.set(self.config['Threshold1'])
        threshold1_scale.pack()

        Label(self.config_frame, text="Threshold2:").pack()
        threshold2_scale = Scale(self.config_frame, from_=0, to=255, orient=HORIZONTAL,
                                 command=lambda val: self.on_threshold2_change(val))
        threshold2_scale.set(self.config['Threshold2'])
        threshold2_scale.pack()

        Label(self.config_frame, text="Aperture Size:").pack()
        aperture_size_scale = Scale(self.config_frame, from_=3, to=7, resolution=2, orient=HORIZONTAL,
                                    command=lambda val: self.on_aperture_size_change(val))
        aperture_size_scale.set(self.config['ApertureSize'])
        aperture_size_scale.pack()

        self.l2_gradient_var = IntVar(value=self.config['L2Gradient'])
        l2_gradient_check = Checkbutton(self.config_frame, text="L2 Gradient",
                                        variable=self.l2_gradient_var,
                                        command=self.on_l2_gradient_change)
        l2_gradient_check.pack()

    def on_threshold1_change(self, val):
        self.config['Threshold1'] = int(val)
        self.update_callback()

    def on_threshold2_change(self, val):
        self.config['Threshold2'] = int(val)
        self.update_callback()

    def on_aperture_size_change(self, val):
        self.config['ApertureSize'] = int(val)
        self.update_callback()

    def on_l2_gradient_change(self):
        self.config['L2Gradient'] = bool(self.l2_gradient_var.get())
        self.update_callback()

    def apply(self, image):
        return cv.Canny(image,
                            self.config['Threshold1'],
                            self.config['Threshold2'],
                            apertureSize=self.config['ApertureSize'],
                            L2gradient=self.config['L2Gradient'])
    
class GaussianBlur(BaseFilter):
    def __init__(self):
        super().__init__()
        self.config = {'Kernel Size': 5}

    def configure(self):
        Label(self.config_frame, text="Kernel Size:").pack()
        kernel_size_scale = Scale(self.config_frame, from_=1, to=31, resolution=2, orient=HORIZONTAL,
                                  command=self.on_kernel_size_change)
        kernel_size_scale.set(self.config['Kernel Size'])
        kernel_size_scale.pack()

    def on_kernel_size_change(self, val):
        self.config['Kernel Size'] = int(val)
        self.update_callback()

    def apply(self, image):
        # Ensure the kernel size is odd
        kernel_size = int(self.config['Kernel Size'])
        if kernel_size % 2 == 0:
            kernel_size += 1

        # Apply Gaussian Blur
        blurred_image = cv.GaussianBlur(image, (kernel_size, kernel_size), 0)
        return blurred_image

class GaussianBlur(BaseFilter):
    def __init__(self):
        super().__init__()
        self.config = {'Kernel Size': 5}

    def configure(self):
        Label(self.config_frame, text="Kernel Size:").pack()
        kernel_size_scale = Scale(self.config_frame, from_=1, to=31, resolution=2, orient=HORIZONTAL,
                                  command=self.on_kernel_size_change)
        kernel_size_scale.set(self.config['Kernel Size'])
        kernel_size_scale.pack()

    def on_kernel_size_change(self, val):
        self.config['Kernel Size'] = int(val)
        self.update_callback()

    def apply(self, image):
        # Ensure the kernel size is odd
        kernel_size = int(self.config['Kernel Size'])
        if kernel_size % 2 == 0:
            kernel_size += 1

        # Apply Gaussian Blur
        blurred_image = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
        return blurred_image
