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

1. In `filter_creator.py`, enter a window name inside `FilterCreator()` with the window you want to view. Run the python program.
2. Click `Add Filter` in the UI. Currently, there are only a few supported filters, but it's easy to expand.
3. Your new filter will be visible in the UI. Click on it to adjust its parameters.
4. Add more filters and reorder them as you wish.
5. Name your filter and click `Save Filter`.

## Use your filter with `apply_filter.py`

This is an API to easily use the filters you create. It's used as follows:
```py
from apply_filter import ApplyFilter

my_filter = ApplyFilter("<filter_preset_name_that_you_wrote>")
my_filtered_image = my_filter.apply(image)
```

# Contribution

[Here's a GPT](https://chat.openai.com/g/g-84Wr6Wyxe-filter-class-creator) that will will help you create new filters for `filters.py`. Copy and paste the generated class into `filters.py`.