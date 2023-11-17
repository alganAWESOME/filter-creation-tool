# Quickly create OpenCV filter presets

This project lets you quickly create and save image filter presets with OpenCV. It lets you view the effects of your filter live.

# Installation

Just clone the repo.

# Usage

## Create a filter preset with `filter_creator.py`

1. In `filter_creator.py`, replace <WINDOW_NAME> with the window you want to view.
2. Click `Add Filter` in the UI. Currently, there are only a few supported filters, but it's easy to expand.
3. Your new filter will be visible in the UI. Click on it to adjust its parameters. For the `HSVFilter`, you can **use either window as a color picker**.
4. Add more filters and reorder them as you wish.
5. Name your filter and click `Save Filter`.

## Use your filter with `apply_filter.py`

This is an API to easily use the filters you create. It's used as follows:
```py
from apply_filter import ApplyFilter

my_filter = ApplyFilter("<filter_preset_name>")
my_filtered_image = my_filter.apply(image)
```

# Contribution

Contact me if you want to contribute lol.