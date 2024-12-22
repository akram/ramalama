# The following code is inspired from: https://github.com/ericcurtin/lm-pull/blob/main/lm-pull.py

import os
import shutil
import sys
import time
import urllib.request
import urllib.error
from ramalama.file import File


class HttpClient:
    def __init__(self):
        pass

    def init(self, url, headers, output_file, progress, response_str=None):
        output_file_partial = None
        if output_file:
            output_file_partial = output_file + ".partial"

        self.file_size = self.set_resume_point(output_file_partial)
        self.printed = False
        if self.urlopen(url, headers):
            return 1

        self.total_to_download = int(self.response.getheader('content-length', 0))
        if response_str is not None:
            response_str.append(self.response.read().decode('utf-8'))
        else:
            out = File()
            if not out.open(output_file_partial, "ab"):
                print("Failed to open file")

                return 1

            if out.lock():
                print("Failed to exclusively lock file")

                return 1

            self.now_downloaded = 0
            self.start_time = time.time()
            self.perform_download(out.file, progress)

        if output_file:
            os.rename(output_file_partial, output_file)

        if self.printed:
            print("\n")

        return 0

    def urlopen(self, url, headers):
        headers["Range"] = f"bytes={self.file_size}-"
        request = urllib.request.Request(url, headers=headers)
        try:
            self.response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as e:
            print(f"Request failed: {e.code}", file=sys.stderr)
            return 1
        except urllib.error.URLError as e:
            print(f"Network error: {e.reason}", file=sys.stderr)
            return 1

        if self.response.status not in (200, 206):
            print(f"Request failed: {self.response.status}", file=sys.stderr)

            return 1

        return 0

    def perform_download(self, file, progress):
        self.total_to_download += self.file_size
        self.now_downloaded = 0
        self.start_time = time.time()
        while True:
            data = self.response.read(1024)
            if not data:
                break

            size = file.write(data)
            if progress:
                self.update_progress(size)

    def human_readable_time(self, seconds):
        hrs = int(seconds) // 3600
        mins = (int(seconds) % 3600) // 60
        secs = int(seconds) % 60
        width = 10
        if hrs > 0:
            return f"{hrs}h {mins:02}m {secs:02}s".rjust(width)
        elif mins > 0:
            return f"{mins}m {secs:02}s".rjust(width)
        else:
            return f"{secs}s".rjust(width)

    def human_readable_size(self, size):
        width = 10
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.2f} {unit}".rjust(width)

            size /= 1024

        return f"{size:.2f} PB".rjust(width)

    def get_terminal_width(self):
        return shutil.get_terminal_size().columns

    def generate_progress_prefix(self, percentage):
        return f"{percentage}% |".rjust(6)

    def generate_progress_suffix(self, now_downloaded_plus_file_size, speed, estimated_time):
        return f"{self.human_readable_size(now_downloaded_plus_file_size)}/{self.human_readable_size(self.total_to_download)}{self.human_readable_size(speed)}/s{self.human_readable_time(estimated_time)}"  # noqa: E501

    def calculate_progress_bar_width(self, progress_prefix, progress_suffix):
        progress_bar_width = self.get_terminal_width() - len(progress_prefix) - len(progress_suffix) - 3
        if progress_bar_width < 1:
            progress_bar_width = 1

        return progress_bar_width

    def generate_progress_bar(self, progress_bar_width, percentage):
        pos = (percentage * progress_bar_width) // 100
        progress_bar = ""
        for i in range(progress_bar_width):
            progress_bar += "█" if i < pos else " "

        return progress_bar

    def set_resume_point(self, output_file):
        if output_file and os.path.exists(output_file):
            return os.path.getsize(output_file)

        return 0

    def print_progress(self, progress_prefix, progress_bar, progress_suffix):
        print(f"\r{progress_prefix}{progress_bar}| {progress_suffix}", end="")

    def update_progress(self, chunk_size):
        self.now_downloaded += chunk_size
        now_downloaded_plus_file_size = self.now_downloaded + self.file_size
        percentage = (now_downloaded_plus_file_size * 100) // self.total_to_download if self.total_to_download else 100
        progress_prefix = self.generate_progress_prefix(percentage)
        speed = self.calculate_speed(self.now_downloaded, self.start_time)
        tim = (self.total_to_download - self.now_downloaded) // speed
        progress_suffix = self.generate_progress_suffix(now_downloaded_plus_file_size, speed, tim)
        progress_bar_width = self.calculate_progress_bar_width(progress_prefix, progress_suffix)
        progress_bar = self.generate_progress_bar(progress_bar_width, percentage)
        self.print_progress(progress_prefix, progress_bar, progress_suffix)
        self.printed = True

    def calculate_speed(self, now_downloaded, start_time):
        now = time.time()
        elapsed_seconds = now - start_time
        return now_downloaded / elapsed_seconds