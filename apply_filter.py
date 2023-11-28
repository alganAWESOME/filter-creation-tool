import os
import json
import filters

class ApplyFilter:
    def __init__(self, preset_name):
        self.filters = self.load_preset(preset_name)

    def load_presets(self):
        file_path = 'filters.json'
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                return json.load(file)
        else:
            raise FileNotFoundError("filters.json not found.")

    def load_preset(self, preset_name):
        presets = self.load_presets()
        if preset_name not in presets:
            raise ValueError(f"Preset '{preset_name}' not found.")

        preset_filters = []
        for filter_config in presets[preset_name]:
            filter_type = filter_config["type"]

            filter_obj = getattr(filters, filter_type)()
            filter_obj.config = filter_obj.deserialize_config(filter_config["config"])
            preset_filters.append(filter_obj)

        return preset_filters

    def apply(self, image):
        for filter_obj in self.filters:
            image = filter_obj.apply(image)
        return image
