import win32con
import win32gui


def _matching_windows(title_keyword: str):
    matches = []
    keyword = (title_keyword or "").lower()

    def foreach(hwnd, _):
        title = win32gui.GetWindowText(hwnd)
        if not title or not keyword:
            return
        if keyword in title.lower():
            matches.append(
                {
                    "hwnd": hwnd,
                    "title": title,
                    "visible": bool(win32gui.IsWindowVisible(hwnd)),
                    "minimized": bool(win32gui.IsIconic(hwnd)),
                }
            )

    win32gui.EnumWindows(foreach, None)
    return matches


def list_windows(title_keyword: str):
    return _matching_windows(title_keyword)


def count_windows(title_keyword: str):
    return len(_matching_windows(title_keyword))


def has_window(title_keyword: str):
    return count_windows(title_keyword) > 0


def bring_to_front(title_keyword: str):
    matches = _matching_windows(title_keyword)
    if not matches:
        raise RuntimeError(f"Window not found: {title_keyword}")

    focused_titles = []

    for item in matches:
        hwnd = item["hwnd"]

        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOPMOST,
            0,
            0,
            0,
            0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
        )
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_NOTOPMOST,
            0,
            0,
            0,
            0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
        )
        win32gui.SetForegroundWindow(hwnd)
        focused_titles.append(item["title"])

    return focused_titles


def minimize_window(title_keyword: str):
    matches = _matching_windows(title_keyword)
    if not matches:
        raise RuntimeError(f"Window not found: {title_keyword}")

    for item in matches:
        win32gui.ShowWindow(item["hwnd"], win32con.SW_MINIMIZE)

    return len(matches)
