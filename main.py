import sys
import os
import re
import logging
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QListWidget, QFrame, QGroupBox, QMessageBox,
    QCheckBox, QTreeWidget, QTreeWidgetItem, QHeaderView, QInputDialog
)
from PySide6.QtCore import Qt, QThread, Signal, Slot

from pytubefix import YouTube
from pytubefix.helpers import safe_filename, target_directory
from pytubefix.itags import get_format_profile
from pytubefix.monostate import Monostate
from pytubefix.file_system import file_system_verify

LOG_LEVEL = logging.INFO  # Change this to logging.DEBUG when you need detailed logs

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("youtube_downloader.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class FetchThread(QThread):
    finished = Signal(list, list, list, str)
    error = Signal(str)
    client_switched = Signal(str, str)

    def __init__(self, url, use_oauth=False):
        super().__init__()
        self.url = url
        self.use_oauth = use_oauth

    def run(self):
        try:
            logger.debug(f"Initializing YouTube object with URL: {self.url} and use_oauth={self.use_oauth}")
            yt = YouTube(self.url, use_oauth=self.use_oauth)
            original_client = yt.client
            logger.debug(f"Original client: {original_client}")

            streams_info = []
            streams_objects = []

            for stream in yt.streams:
                stream_info = (
                    f"Itag: {stream.itag} | Type: {stream.type.capitalize()} | "
                    f"Resolution: {getattr(stream, 'resolution', 'N/A')} | "
                    f"FPS: {getattr(stream, 'fps', 'N/A')} | "
                    f"Mime Type: {stream.mime_type} | "
                    f"Filesize: {stream.filesize_mb:.2f} MB | "
                    f"Adaptive: {'Yes' if stream.is_adaptive else 'No'} | "
                    f"Progressive: {'Yes' if stream.is_progressive else 'No'} | "
                    f"Audio: {'Yes' if stream.includes_audio_track else 'No'} | "
                    f"Video: {'Yes' if stream.includes_video_track else 'No'}"
                )
                streams_info.append(stream_info)
                streams_objects.append(stream)

                logger.debug(f"Stream Info: {stream_info}")

            captions_info = [f"{caption.name} ({caption.code})" for caption in yt.captions]
            logger.debug(f"Available captions: {captions_info}")

            if yt.client != original_client:
                logger.debug(f"Client switched from {original_client} to {yt.client}")
                self.client_switched.emit(original_client, yt.client)

            self.finished.emit(streams_info, captions_info, streams_objects, "Data fetched successfully.")
        except Exception as e:
            logger.error(f"Error in FetchThread: {e}", exc_info=True)
            self.error.emit(str(e))


class DownloadThread(QThread):
    completed = Signal(str)
    error = Signal(str)

    def __init__(self, stream, output_path=None, filename=None, filename_prefix=None,
                 skip_existing=True, timeout=None, max_retries=0,
                 interrupt_checker=None):
        super().__init__()
        self.stream = stream
        self.output_path = output_path
        self.filename = filename
        self.filename_prefix = filename_prefix
        self.skip_existing = skip_existing
        self.timeout = timeout
        self.max_retries = max_retries
        self.interrupt_checker = interrupt_checker

    def run(self):
        try:
            logger.debug(f"Starting download with filename: {self.filename}")
            downloaded_file = self.stream.download(
                output_path=self.output_path,
                filename=self.filename,
                filename_prefix=self.filename_prefix,
                skip_existing=self.skip_existing,
                timeout=self.timeout,
                max_retries=self.max_retries,
                interrupt_checker=self.interrupt_checker
            )
            if downloaded_file:
                logger.info(f"Download completed: {downloaded_file}")
                self.completed.emit(downloaded_file)
            else:
                logger.warning("Download was skipped or failed.")
                self.error.emit("Download was skipped or failed.")
        except Exception as e:
            logger.error(f"Error in DownloadThread: {e}", exc_info=True)
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Video Info")
        self.setGeometry(100, 100, 1200, 900)

        self.streams_objects = []

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        url_frame = QFrame()
        url_layout = QHBoxLayout(url_frame)
        url_label = QLabel("YouTube URL:")
        self.url_entry = QLineEdit()
        fetch_button = QPushButton("Fetch Info")
        fetch_button.clicked.connect(self.fetch_video_info)
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_entry)
        url_layout.addWidget(fetch_button)
        main_layout.addWidget(url_frame)

        self.use_oauth = QCheckBox("Use OAuth (required for some age-restricted videos)")
        main_layout.addWidget(self.use_oauth)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red;")
        main_layout.addWidget(self.error_label)

        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        main_layout.addWidget(self.title_label)

        streams_group = QGroupBox("Available Streams")
        streams_layout = QVBoxLayout(streams_group)

        self.streams_tree = QTreeWidget()
        self.streams_tree.setHeaderLabels([
            "Stream Type",
            "Resolution",
            "FPS",
            "Format",
            "Filesize",
            "Audio",
            "Video",
            "Adaptive",
            "Progressive",
            "Bitrate",
            "Codecs"
        ])

        header = self.streams_tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        self.streams_tree.setAlternatingRowColors(True)
        self.streams_tree.setSortingEnabled(True)

        streams_layout.addWidget(self.streams_tree)

        self.download_button = QPushButton("Download Selected Stream")
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.download_selected_stream)
        streams_layout.addWidget(self.download_button)

        captions_group = QGroupBox("Available Captions")
        captions_layout = QVBoxLayout(captions_group)
        self.captions_listbox = QListWidget()
        captions_layout.addWidget(self.captions_listbox)

        info_layout = QVBoxLayout()
        info_layout.addWidget(streams_group, stretch=4)
        info_layout.addWidget(captions_group, stretch=1)
        main_layout.addLayout(info_layout)

        self.status_label = QLabel("Enter a YouTube URL and click Fetch Info to see available streams and captions.")
        main_layout.addWidget(self.status_label)

        self.streams_tree.itemSelectionChanged.connect(self.update_download_button_state)

    def fetch_video_info(self):
        url = self.url_entry.text().strip()
        if not url:
            self.error_label.setText("Please enter a YouTube video URL.")
            return

        self.status_label.setText("Fetching data...")
        self.error_label.clear()
        self.title_label.clear()
        self.streams_tree.clear()
        self.captions_listbox.clear()
        self.download_button.setEnabled(False)

        self.fetch_thread = FetchThread(url, use_oauth=self.use_oauth.isChecked())
        self.fetch_thread.finished.connect(self.update_info)
        self.fetch_thread.error.connect(self.show_error)
        self.fetch_thread.client_switched.connect(self.show_client_switch)
        self.fetch_thread.start()

    @Slot(str, str)
    def show_client_switch(self, original_client, new_client):
        self.status_label.setText(
            f"Client switched from {original_client} to {new_client} to fetch video data."
        )
        logger.debug(f"Client switched from {original_client} to {new_client}")

    @Slot(list, list, list, str)
    def update_info(self, streams_info, captions_info, streams_objects, status):
        self.streams_objects = streams_objects
        if streams_objects:
            title = streams_objects[0].title
            self.title_label.setText(title)
            self.setWindowTitle(f"YouTube Video Info - {title}")
            logger.debug(f"Video Title: {title}")

        self.streams_tree.clear()

        video_parent = QTreeWidgetItem(["Video Streams"])
        audio_parent = QTreeWidgetItem(["Audio Streams"])
        self.streams_tree.addTopLevelItem(video_parent)
        self.streams_tree.addTopLevelItem(audio_parent)

        for stream in streams_objects:
            if stream.type == 'video':
                parent = video_parent
            else:
                parent = audio_parent

            item = QTreeWidgetItem(parent)
            item.setText(0, f"Itag: {stream.itag}")
            item.setText(1, str(getattr(stream, 'resolution', 'N/A')))
            item.setText(2, str(getattr(stream, 'fps', 'N/A')))
            item.setText(3, stream.mime_type)
            item.setText(4, f"{stream.filesize_mb:.2f} MB")
            item.setText(5, "Yes" if stream.includes_audio_track else "No")
            item.setText(6, "Yes" if stream.includes_video_track else "No")
            item.setText(7, "Yes" if stream.is_adaptive else "No")
            item.setText(8, "Yes" if stream.is_progressive else "No")

            bitrate = stream.abr if stream.includes_audio_track else "N/A"
            item.setText(9, bitrate)

            audio_codec, video_codec = stream.parse_codecs()
            codecs = f"Audio: {audio_codec or 'N/A'}, Video: {video_codec or 'N/A'}"
            item.setText(10, codecs)

            tooltip = (
                f"Itag: {stream.itag}\n"
                f"Type: {stream.type}\n"
                f"Resolution: {getattr(stream, 'resolution', 'N/A')}\n"
                f"FPS: {getattr(stream, 'fps', 'N/A')}\n"
                f"Mime Type: {stream.mime_type}\n"
                f"Filesize: {stream.filesize_mb:.2f} MB\n"
                f"Adaptive: {'Yes' if stream.is_adaptive else 'No'}\n"
                f"Progressive: {'Yes' if stream.is_progressive else 'No'}\n"
                f"Audio: {'Yes' if stream.includes_audio_track else 'No'}\n"
                f"Video: {'Yes' if stream.includes_video_track else 'No'}\n"
                f"Bitrate: {bitrate}\n"
                f"Codecs: {codecs}"
            )
            item.setToolTip(0, tooltip)

            logger.debug(f"Stream Selected: Type={stream.type}, Resolution={stream.resolution}, "
                         f"FPS={getattr(stream, 'fps', 'N/A')}, Mime Type={stream.mime_type}, "
                         f"Filesize={stream.filesize_mb:.2f} MB, Adaptive={stream.is_adaptive}, "
                         f"Progressive={stream.is_progressive}, Audio={stream.includes_audio_track}, "
                         f"Video={stream.includes_video_track}, Bitrate={bitrate}, Codecs={codecs}")

        self.streams_tree.expandAll()

        self.captions_listbox.addItems(captions_info)
        self.status_label.setText(status)
        self.error_label.clear()

    def update_download_button_state(self):
        selected_items = self.streams_tree.selectedItems()
        self.download_button.setEnabled(bool(selected_items))

    def get_selected_stream(self):
        selected_items = self.streams_tree.selectedItems()
        if not selected_items:
            raise ValueError("Please select a stream to download.")

        selected_item = selected_items[0]
        itag_text = selected_item.text(0)
        try:
            itag = int(itag_text.split(": ")[1])
        except (IndexError, ValueError):
            raise ValueError("Invalid stream selection.")

        selected_stream = next(
            (stream for stream in self.streams_objects if stream.itag == itag),
            None
        )
        if not selected_stream:
            raise ValueError("Error: Could not find selected stream.")

        logger.debug(f"Selected stream: Itag={itag}, Type={selected_stream.type}")
        return selected_stream

    def construct_filename(self, stream):
        stream_type = "Audio" if stream.type == "audio" else "Video"
        format_subtype = stream.subtype
        bitrate = stream.abr if stream.includes_audio_track and stream.abr else "N/A"
        resolution = stream.resolution if stream.includes_video_track and stream.resolution else "N/A"

        base_title = re.sub(r'[\\/*?:"<>|]', "", stream.title)
        filename_parts = [base_title, stream_type, format_subtype]

        if bitrate != "N/A":
            bitrate_str = bitrate if bitrate.lower().endswith("kbps") else f"{bitrate}kbps"
            filename_parts.append(bitrate_str)

        if resolution != "N/A":
            filename_parts.append(resolution)

        custom_filename = "_".join(filename_parts)

        if stream.type == "audio" and not stream.includes_video_track:
            file_extension = "m4a"
            logger.debug("Stream is audio-only. Overriding file extension to '.m4a'")
        else:
            valid_subtypes = {"mp4", "webm", "m4a", "mp3", "ogg", "flv", "avi"}
            file_extension = format_subtype if format_subtype in valid_subtypes else "mp4"
            if format_subtype not in valid_subtypes:
                logger.warning(f"Unexpected format subtype '{format_subtype}'. Falling back to 'mp4'.")

        custom_filename_with_ext = f"{custom_filename}.{file_extension}"
        max_length = 200
        if len(custom_filename_with_ext) > max_length:
            extension = f".{file_extension}"
            custom_filename_with_ext = f"{custom_filename_with_ext[:max_length - len(extension)]}{extension}"
            logger.warning(f"Filename truncated to: {custom_filename_with_ext}")

        logger.debug(f"Constructed filename: {custom_filename_with_ext}")
        return custom_filename_with_ext, file_extension

    def get_confirmed_filename(self, proposed_filename, file_extension):
        confirmed_filename, ok = QInputDialog.getText(
            self,
            "Confirm Filename",
            f"Filename will be:\n{proposed_filename}\nDo you want to proceed?",
            text=proposed_filename
        )

        if not ok:
            raise ValueError("Download canceled by the user.")

        if confirmed_filename and not confirmed_filename.lower().endswith(f".{file_extension}"):
            confirmed_filename += f".{file_extension}"
            logger.debug(f"Appended extension to user-modified filename: {confirmed_filename}")

        return confirmed_filename or proposed_filename

    def start_download(self, stream, filename):
        self.status_label.setText(f"Starting download as: {filename}")
        self.error_label.clear()
        self.download_button.setEnabled(False)

        self.download_thread = DownloadThread(
            stream=stream,
            filename=filename
        )
        self.download_thread.completed.connect(self.download_completed)
        self.download_thread.error.connect(self.download_error)
        self.download_thread.start()
        logger.info(f"Download thread started for file: {filename}")

    def handle_download_error(self, error_message):
        self.error_label.setText(f"Error: {error_message}")
        self.status_label.setText("Download failed.")
        self.download_button.setEnabled(True)
        QMessageBox.critical(self, "Download Error", error_message)
        logger.error(f"Download error: {error_message}")

    def download_selected_stream(self):
        try:
            selected_stream = self.get_selected_stream()

            proposed_filename, file_extension = self.construct_filename(selected_stream)

            final_filename = self.get_confirmed_filename(proposed_filename, file_extension)

            self.start_download(selected_stream, final_filename)

        except ValueError as ve:
            self.error_label.setText(f"Error: {str(ve)}")
            self.status_label.setText("Download failed.")
            logger.error(f"Download setup error: {str(ve)}")
        except Exception as e:
            self.handle_download_error(str(e))

    @Slot(str)
    def download_completed(self, file_path):
        self.status_label.setText(f"Download completed: {file_path}")
        self.download_button.setEnabled(True)
        QMessageBox.information(self, "Download Complete", f"File saved to:\n{file_path}")

    @Slot(str)
    def download_error(self, error_message):
        self.error_label.setText(f"Error: {error_message}")
        self.status_label.setText("Download failed.")
        self.download_button.setEnabled(True)
        QMessageBox.critical(self, "Download Error", error_message)
        logger.error(f"Download error: {error_message}")

    def show_error(self, error):
        self.error_label.setText(f"Error: {error}")
        self.status_label.setText("Failed to fetch data.")
        logger.error(f"Fetch error: {error}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
