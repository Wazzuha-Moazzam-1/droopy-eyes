import win32gui # type: ignore
import psutil

def get_visible_window_titles():
    titles = []

    def collect_window(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()

            if title:
                titles.append(title)

        return True

    win32gui.EnumWindows(collect_window, None)
    return set(titles)    # removes duplicates fast but unordered, i donr care about the order so yea. the set() converts it into a set, and deletes duplicates, while the list() converts it back, yayy

# i guess this is all this module does? but no, we have to filter the data and check if any blacklisted app has been opened.


def load_blacklist(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return {
            line.strip().casefold()
            for line in file
            if line.strip()
        }

def find_running_blacklisted_apps(blacklist):
    detected = set()

    for process in psutil.process_iter(["name"]):
        try:
            process_name = process.info["name"]

            if not process_name:
                continue

            normalized_name = process_name.casefold()

            if normalized_name in blacklist:
                detected.add(normalized_name)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return detected

