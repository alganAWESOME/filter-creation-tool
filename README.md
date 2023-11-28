# Quickly create OpenCV filter presets

This project lets you quickly layer OpenCV filters and save filter presets. You can easily change the order of the filters. It also lets you configure filters by interacting with the screen. For example, you can configure an HSV filter by picking a color from the screen capture.

# Installation

Just clone the repo.

Requirements:
```
pip install opencv-python
pip install pywin32
pip install numpy
```

It's currently Windows-only because of `window_capture.py`.

# Usage

## Create a filter preset with `filter_creator.py`

1. In `filter_creator.py`, replace `FilterCreator("Toontown Offline")` with `FilterCreator("<your_window_name>")`. Run the python program.
2. Add filters (e.g. CropFilter, GuassianBlur, CannyEdgeDetector) and reorder them as you wish. Some filters let you interact with the screen, for example with the CropFilter, you can click on the screen to define the top-left and bottom-right of your crop. With HSVFilter you can pick a color from the screen.
3. Give your preset a name and click Save Filter. This will save your filter into `filters.json`.

## Use your filter with `apply_filter.py`

This is an API to easily use the filters you create. It's used as follows:
```py
from apply_filter import ApplyFilter

my_filter = ApplyFilter("<filter_preset_name_that_you_wrote>")
my_filtered_image = my_filter.apply(image)
```

For now, if you want to use the API in your own repo, you need to copy `filters.py`, `filters.json` (contains your filter presets) and `apply_filter.py` into your own directory.

# Contribution

[Here's a GPT](https://chat.openai.com/g/g-84Wr6Wyxe-filter-class-creator) that will will help you create new filters for `filters.py`. Copy and paste the generated class into `filters.py`.