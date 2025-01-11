```mermaid
graph TD
    MainWindow[QMainWindow<br>Main Window] --> CentralWidget[QWidget<br>Central Widget]
    CentralWidget --> MainLayout[QVBoxLayout<br>Main Layout]
    
    MainLayout --> URLFrame[QFrame<br>URL Frame]
    URLFrame --> URLLayout[QHBoxLayout<br>URL Layout]
    URLLayout --> URLLabel[QLabel<br>YouTube URL]
    URLLayout --> URLEntry[QLineEdit<br>URL Entry]
    URLLayout --> FetchButton[QPushButton<br>Fetch Info]
    
    MainLayout --> OAuthCheck[QCheckBox<br>Use OAuth]
    MainLayout --> ErrorLabel[QLabel<br>Error Label<br>red styled]
    MainLayout --> TitleLabel[QLabel<br>Title Label<br>bold, centered]
    
    MainLayout --> InfoLayout[QVBoxLayout<br>Info Layout]
    
    InfoLayout --> StreamsGroup[QGroupBox<br>Streams Group<br>Stretch: 4]
    StreamsGroup --> StreamsLayout[QVBoxLayout<br>Streams Layout]
    StreamsLayout --> StreamsTree[QTreeWidget<br>Streams Tree]
    StreamsTree --> TreeHeaders[Tree Headers]
    TreeHeaders --> Type[Stream Type]
    TreeHeaders --> Res[Resolution]
    TreeHeaders --> FPS[FPS]
    TreeHeaders --> Format[Format]
    TreeHeaders --> Size[Filesize]
    TreeHeaders --> Audio[Audio]
    TreeHeaders --> Video[Video]
    TreeHeaders --> Adaptive[Adaptive]
    TreeHeaders --> Progressive[Progressive]
    TreeHeaders --> Bitrate[Bitrate]
    TreeHeaders --> Codecs[Codecs]
    StreamsLayout --> DownloadBtn[QPushButton<br>Download Button]
    
    InfoLayout --> CaptionsGroup[QGroupBox<br>Captions Group<br>Stretch: 1]
    CaptionsGroup --> CaptionsLayout[QVBoxLayout<br>Captions Layout]
    CaptionsLayout --> CaptionsListbox[QListWidget<br>Captions Listbox]
    
    MainLayout --> StatusLabel[QLabel<br>Status Label]
```

```
Main Window (QMainWindow)
└── Central Widget (QWidget)
    └── Main Layout (QVBoxLayout)
        ├── URL Frame (QFrame)
        │   └── URL Layout (QHBoxLayout)
        │       ├── URL Label (QLabel "YouTube URL:")
        │       ├── URL Entry (QLineEdit)
        │       └── Fetch Button (QPushButton "Fetch Info")
        ├── OAuth Checkbox (QCheckBox "Use OAuth...")
        ├── Error Label (QLabel - red styled)
        ├── Title Label (QLabel - bold, centered)
        ├── Info Layout (QVBoxLayout)
        │   ├── Streams Group (QGroupBox) [Stretch: 4]
        │   │   └── Streams Layout (QVBoxLayout)
        │   │       ├── Streams Tree (QTreeWidget)
        │   │       │   └── Headers:
        │   │       │       ├── "Stream Type"
        │   │       │       ├── "Resolution"
        │   │       │       ├── "FPS"
        │   │       │       ├── "Format"
        │   │       │       ├── "Filesize"
        │   │       │       ├── "Audio"
        │   │       │       ├── "Video"
        │   │       │       ├── "Adaptive"
        │   │       │       ├── "Progressive"
        │   │       │       ├── "Bitrate"
        │   │       │       └── "Codecs"
        │   │       └── Download Button (QPushButton)
        │   └── Captions Group (QGroupBox) [Stretch: 1]
        │       └── Captions Layout (QVBoxLayout)
        │           └── Captions Listbox (QListWidget)
        └── Status Label (QLabel)
```
