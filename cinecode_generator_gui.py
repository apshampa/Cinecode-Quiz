import os
import sys
import json
import re
import subprocess
import threading
import shutil
import queue
from pathlib import Path

# Try importing tkinter components
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter.scrolledtext import ScrolledText
except ImportError:
    print("Error: Tkinter is not installed or available on this system.")
    sys.exit(1)

# Try importing Pillow
PILLOW_AVAILABLE = False
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    pass

CONFIG_FILE = "cinecode_config.json"
DEFAULT_EXCLUSIONS = ["Extras", "Featurettes", "Samples", "Shorts", "Trailers", "Deleted Scenes"]

# Dictionary of common words in movie titles to assist in segmenting concatenated filenames
KNOWN_WORDS = {
    "kill", "bill", "vol", "volume", "matrix", "reloaded", "revolutions", "inception", "mad", "max", "fury", "road",
    "interstellar", "amelie", "la", "land", "blade", "runner", "spider", "man", "into", "verse", "years", "slave",
    "angry", "men", "streetcar", "named", "desire", "marlon", "brando", "trip", "moon", "accordeur", "dangerous",
    "method", "aguirre", "wrath", "god", "alpha", "given", "sunday", "directors", "cut", "apocalypse", "now", "apollo",
    "atonement", "back", "future", "batman", "begins", "ninja", "dark", "knight", "rises", "bicycle", "thieves",
    "black", "swan", "blue", "warmest", "color", "bohemian", "rhapsody", "breaking", "rules", "brokeback", "mountain",
    "career", "opportunities", "casablanca", "children", "childs", "play", "citizen", "kane", "city", "leben",
    "anderen", "death", "proof", "defending", "life", "amerikanische", "freund", "django", "unchained", "dog", "day",
    "afternoon", "donnie", "darko", "eat", "pray", "love", "elysium", "empire", "sun", "eraserhead", "eternal",
    "sunshine", "spotless", "mind", "everything", "everywhere", "all", "once", "ex", "machina", "fahrenheit", "fallen",
    "angels", "fences", "fight", "club", "five", "easy", "pieces", "forrest", "gump", "fruitvale", "station", "goodfellas",
    "good", "will", "hunting", "her", "hiding", "plain", "sight", "hiroshima", "amour", "his", "girl", "friday", "holmes",
    "watson", "glorious", "bastards", "mood", "origins", "isle", "dogs", "wonderful", "jarhead", "johnny", "english",
    "reborn", "strikes", "again", "john", "wick", "chapter", "parabellum", "jojo", "rabbit", "joker", "knives", "knock",
    "dolce", "vita", "lady", "bird", "laila", "majnu", "last", "christmas", "leon", "professional", "pi", "little",
    "women", "living", "yourself", "lola", "rennt", "lolita", "long", "journey", "lost", "translation", "square",
    "foot", "manchester", "sea", "manhattan", "search", "manifesting", "machinist", "matilda", "meet", "joe",
    "melancholia", "memento", "metropolis", "midnight", "paris", "minari", "moonlight", "mother", "nobody", "mulholland",
    "drive", "turkey", "nervous", "forbidden", "country", "old", "no", "name", "bullet", "notting", "hill", "pain",
    "glory", "psycho", "pulp", "fiction", "raging", "bull", "requiem", "dream", "robin", "hood", "rocky", "roger",
    "rosemary", "baby", "saving", "private", "ryan", "scarface", "schindlers", "list", "secret", "lies", "seven",
    "tibet", "shane", "shepherdess", "shutter", "slumdog", "millionaire", "smoke", "signals", "solaris", "sophies",
    "choice", "across", "spin", "round", "stalker", "suicide", "room", "super", "swimming", "pool", "synecdoche",
    "new", "york", "taxi", "driver", "virgin", "tomorrow", "devils", "advocate", "enigma", "kaspar", "hauser",
    "school", "rock", "shallows", "shawshank", "redemption", "act", "killing", "ballad", "buster", "scruggs",
    "birdcage", "deer", "hunter", "exorcist", "fall", "farewell", "fountain", "giant", "mechanical", "graduate",
    "great", "dictator", "handmaiden", "hateful", "eight", "highwaymen", "hundred", "irishman", "iron", "lighthouse",
    "thelma", "louise", "lobster", "loneliness", "runner", "mask", "mirror", "pianist", "prestige", "princess",
    "bride", "silence", "lambs", "sixth", "sense", "sting", "thin", "twilight", "zone", "occurrence", "owl",
    "creek", "bridge", "witch", "wizard", "oz", "tokyo", "story", "toto", "hero", "trainspotting", "triple",
    "frontier", "uncle", "buck", "uncut", "gems", "under", "silver", "lake", "unforgettable", "upgrade", "us",
    "v", "vendetta", "vicky", "cristina", "barcelona", "weekend", "bernies", "willy", "wonka", "chocolate",
    "factory", "zola", "of", "and", "the", "a", "an", "in", "on", "at", "to", "for", "with", "by", "from", "as", 
    "is", "it", "its", "so", "no", "any", "space", "odyssey"
}

def segment_text(text):
    # Dynamic programming word segmenter
    n = len(text)
    dp = [None] * (n + 1)
    dp[0] = []
    
    for i in range(1, n + 1):
        for j in range(i):
            if dp[j] is not None:
                word = text[j:i]
                if word in KNOWN_WORDS or word.isdigit() or word in ("a", "i", "v", "o"):
                    dp[i] = dp[j] + [word]
                    break
    return dp[n] if dp[n] is not None else [text]

# Regular-expression based movie title cleaner helper
def find_movie_year(name):
    # Find all 4-digit numbers in the range 1880 to 2029
    candidates = re.findall(r"(18\d{2}|19\d{2}|20[0-2]\d)", name)
    # Filter out common resolutions that look like years
    valid_years = [y for y in candidates if y not in ("1080", "2160", "4320")]
    return valid_years[-1] if valid_years else None

def clean_movie_title(filename):
    # Strip path and extension
    name = os.path.basename(filename)
    name = os.path.splitext(name)[0]
    name = name.replace("cinecode-", "")
    
    # 1. Look for release year first
    year = find_movie_year(name)
    if year:
        # Split on the last occurrence of the year
        idx = name.rfind(year)
        title_part = name[:idx]
        # Clean delimiters, brackets and parentheses
        title_part = re.sub(r"[\.\-_\(\)\[\]\{\}]+", " ", title_part).strip()
        
        # If title part is completely lowercase and has no spaces, segment it
        if title_part.islower() and " " not in title_part:
            words = segment_text(title_part)
            title_part = " ".join(words)
            
        # If title part is not empty, return formatted title (Year)
        if title_part:
            return f"{title_part.title()} ({year})"
        return year

    # 2. Fallback: Tag-based cleanup if no year is present
    cleaned = re.sub(r"[\.\-_]+", " ", name).strip()
    
    # If cleaned is completely lowercase and has no spaces, segment it
    if cleaned.islower() and " " not in cleaned:
        words = segment_text(cleaned)
        cleaned = " ".join(words)
        
    tags = [
        "1080p", "720p", "480p", "2160p", "4k", "bluray", "brrip", "bdrip", "dvdrip", "webrip", "web-dl", 
        "hdtv", "x264", "h264", "x265", "hevc", "yify", "yts", "aac", "ac3", "dts", "remastered", 
        "vost", "etrg", "evo", "galaxytv", "galaxyrg", "rarbg", "ytsag", "ytsam", "ytslt", "anoxmous", 
        "shaggy", "sujaidr", "mirsad", "deklok", "belos", "etmovies", "sample", "directors cut", "extended", "unrated"
    ]
    
    words = cleaned.split()
    cleaned_words = []
    for word in words:
        lower_word = word.lower()
        has_tag = False
        earliest_idx = len(word)
        for tag in tags:
            idx = lower_word.find(tag)
            if idx != -1 and idx < earliest_idx:
                earliest_idx = idx
                has_tag = True
                
        if has_tag:
            word = word[:earliest_idx]
            if word:
                cleaned_words.append(word)
            break
        cleaned_words.append(word)
        
    cleaned_title = " ".join(cleaned_words).strip().title()
    return cleaned_title if cleaned_title else name.title()


class CineCodeGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CineCode Batch Generator & Manager")
        self.root.geometry("820x820")
        self.root.minsize(750, 720)

        # Threading/Abort/Queue states
        self.is_processing = False
        self.abort_event = threading.Event()
        self.active_process = None
        self.preview_queue = queue.Queue()

        # Database Manager state
        self.db_records = []
        self.filtered_db_records = []

        # Configuration variables
        self.movies_dirs = []
        self.output_dir_var = tk.StringVar()
        self.ffmpeg_path_var = tk.StringVar()
        self.width_var = tk.IntVar(value=1000)
        self.height_var = tk.IntVar(value=400)
        self.smooth_var = tk.BooleanVar(value=False)
        self.mode_var = tk.StringVar(value="High Quality (All Frames)")
        self.clean_titles_var = tk.BooleanVar(value=True)
        self.exclusions = list(DEFAULT_EXCLUSIONS)

        # Load config if exists
        self.load_config()

        # Database Manager folder starts at output directory
        self.db_folder_var = tk.StringVar(value=self.output_dir_var.get())

        # Build UI with Tabs
        self.create_tabs_layout()

        # Check Pillow
        if not PILLOW_AVAILABLE:
            self.log("WARNING: The 'Pillow' library is not installed. Outputting barcodes will fail.\n"
                     "Please open a terminal and run: pip install Pillow\n")
            messagebox.showwarning("Pillow Missing", 
                                   "The Python 'Pillow' library is missing.\n\n"
                                   "Please run 'pip install Pillow' in your command line, "
                                   "otherwise barcode creation will not work.")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    legacy_dir = config.get("movies_dir", "")
                    self.movies_dirs = config.get("movies_dirs", [])
                    if legacy_dir and legacy_dir not in self.movies_dirs:
                        self.movies_dirs.append(legacy_dir)
                        
                    self.output_dir_var.set(config.get("output_dir", ""))
                    self.ffmpeg_path_var.set(config.get("ffmpeg_path", ""))
                    self.width_var.set(config.get("width", 1000))
                    self.height_var.set(config.get("height", 400))
                    self.smooth_var.set(config.get("smooth", False))
                    self.clean_titles_var.set(config.get("clean_titles", True))
                    self.mode_var.set(config.get("mode", "High Quality (All Frames)"))
                    self.exclusions = config.get("exclusions", list(DEFAULT_EXCLUSIONS))
            except Exception as e:
                pass

    def save_config(self):
        config = {
            "movies_dirs": self.movies_dirs,
            "output_dir": self.output_dir_var.get(),
            "ffmpeg_path": self.ffmpeg_path_var.get(),
            "width": self.width_var.get(),
            "height": self.height_var.get(),
            "smooth": self.smooth_var.get(),
            "clean_titles": self.clean_titles_var.get(),
            "mode": self.mode_var.get(),
            "exclusions": self.exclusions
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            pass

    def create_tabs_layout(self):
        # Create Notebook container
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.generator_tab = ttk.Frame(self.notebook)
        self.manager_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.generator_tab, text=" CineCode Batch Generator ")
        self.notebook.add(self.manager_tab, text=" Database Manager ")

        # Build contents for each tab
        self.create_generator_widgets(self.generator_tab)
        self.create_manager_widgets(self.manager_tab)

    def create_generator_widgets(self, container):
        main_frame = ttk.Frame(container, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ------------------- PATHS SECTION -------------------
        paths_label_frame = ttk.LabelFrame(main_frame, text=" Directories & Environment ", padding="10")
        paths_label_frame.pack(fill=tk.X, pady=(0, 10))

        # Movies directories manager
        ttk.Label(paths_label_frame, text="Movies Directories:").grid(row=0, column=0, sticky=tk.NW, pady=5)
        
        self.dirs_frame = ttk.Frame(paths_label_frame)
        self.dirs_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=5, pady=5)
        
        self.dirs_listbox = tk.Listbox(self.dirs_frame, height=4, selectmode=tk.SINGLE, borderwidth=1, relief=tk.SOLID)
        self.dirs_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.update_dirs_listbox()
        
        dirs_scroll = ttk.Scrollbar(self.dirs_frame, orient=tk.VERTICAL, command=self.dirs_listbox.yview)
        dirs_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.dirs_listbox.config(yscrollcommand=dirs_scroll.set)
        
        self.dirs_buttons = ttk.Frame(paths_label_frame)
        self.dirs_buttons.grid(row=0, column=2, sticky=tk.NW, padx=5, pady=5)
        
        ttk.Button(self.dirs_buttons, text="Add Folder...", command=self.add_movies_dir).pack(fill=tk.X, pady=2)
        ttk.Button(self.dirs_buttons, text="Remove Folder", command=self.remove_movies_dir).pack(fill=tk.X, pady=2)

        # Output directory
        ttk.Label(paths_label_frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(paths_label_frame, textvariable=self.output_dir_var, width=50).grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(paths_label_frame, text="Browse...", command=self.browse_output).grid(row=1, column=2, padx=5, pady=5)

        # FFmpeg path
        ttk.Label(paths_label_frame, text="FFmpeg Path (Optional):").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(paths_label_frame, textvariable=self.ffmpeg_path_var, width=50).grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(paths_label_frame, text="Browse...", command=self.browse_ffmpeg).grid(row=2, column=2, padx=5, pady=5)

        paths_label_frame.columnconfigure(1, weight=1)

        # ------------------- MIDDLE SECTION (EXCLUSIONS & SETTINGS) -------------------
        middle_frame = ttk.Frame(main_frame)
        middle_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Exclusions list on the left
        exclusions_frame = ttk.LabelFrame(middle_frame, text=" Exclude Subdirectories ", padding="10")
        exclusions_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.ex_listbox = tk.Listbox(exclusions_frame, height=5, selectmode=tk.SINGLE, borderwidth=1, relief=tk.SOLID)
        self.ex_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=(0, 5))
        self.update_exclusions_listbox()

        scrollbar = ttk.Scrollbar(exclusions_frame, orient=tk.VERTICAL, command=self.ex_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.ex_listbox.config(yscrollcommand=scrollbar.set)

        ex_control_frame = ttk.Frame(exclusions_frame)
        ex_control_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))

        self.ex_entry = ttk.Entry(ex_control_frame, width=15)
        self.ex_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(ex_control_frame, text="Add", command=self.add_exclusion, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(ex_control_frame, text="Remove", command=self.remove_exclusion, width=8).pack(side=tk.LEFT, padx=2)

        # Settings panel on the right
        settings_frame = ttk.LabelFrame(middle_frame, text=" CineCode Settings ", padding="10")
        settings_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))

        ttk.Label(settings_frame, text="Barcode Width (px):").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Spinbox(settings_frame, from_=100, to=10000, increment=100, textvariable=self.width_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(settings_frame, text="Barcode Height (px):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Spinbox(settings_frame, from_=50, to=5000, increment=50, textvariable=self.height_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Checkbutton(settings_frame, text="Smooth Bars (Solid Averaged Bars)", variable=self.smooth_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)

        ttk.Checkbutton(settings_frame, text="Clean Movie Titles (e.g. Movie (Year))", variable=self.clean_titles_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)

        # Processing Mode selector (Turbo, Fast, High Quality)
        ttk.Label(settings_frame, text="Processing Speed:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.mode_combo = ttk.Combobox(settings_frame, textvariable=self.mode_var, values=["High Quality (All Frames)", "Fast (Skip B-Frames)", "Turbo (I-Frames Only)"], state="readonly", width=22)
        self.mode_combo.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)

        # ------------------- PROGRESS & STATUS SECTION -------------------
        status_label_frame = ttk.LabelFrame(main_frame, text=" Processing Progress & Visualizer ", padding="10")
        status_label_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Real-time Barcode Visualizer
        preview_container = ttk.Frame(status_label_frame)
        preview_container.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(preview_container, text="Real-time CineCode Visualizer:").pack(anchor=tk.W, pady=(0, 2))
        
        self.preview_width = 700
        self.preview_height = 100
        self.preview_photo = tk.PhotoImage(width=self.preview_width, height=self.preview_height)
        self.clear_preview_photo()
        
        self.preview_label = tk.Label(preview_container, image=self.preview_photo, bg="#0f172a", bd=1, relief=tk.SOLID)
        self.preview_label.pack(fill=tk.X, expand=True)

        # Progress bar
        self.progress_bar = ttk.Progressbar(status_label_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        # Logs ScrolledText
        self.log_text = ScrolledText(status_label_frame, height=5, font=("Courier New", 9), state=tk.DISABLED, background="#1e1e1e", foreground="#d4d4d4", insertbackground="white")
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # ------------------- CONTROL BUTTONS -------------------
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(5, 0))

        self.start_btn = ttk.Button(buttons_frame, text="Start Batch Processing", command=self.start_processing)
        self.start_btn.pack(side=tk.RIGHT, padx=5)

        self.cancel_btn = ttk.Button(buttons_frame, text="Cancel", command=self.cancel_processing, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.RIGHT, padx=5)

    def create_manager_widgets(self, container):
        # Database Manager Interface Panel
        manager_frame = ttk.Frame(container, padding="15")
        manager_frame.pack(fill=tk.BOTH, expand=True)

        # Folder selection row
        folder_frame = ttk.Frame(manager_frame)
        folder_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(folder_frame, text="Database Folder:").pack(side=tk.LEFT, padx=(0, 5))
        self.db_folder_entry = ttk.Entry(folder_frame, textvariable=self.db_folder_var, width=50)
        self.db_folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(folder_frame, text="Browse...", command=self.browse_db_folder).pack(side=tk.LEFT, padx=2)

        # Top Bar: File Load status and Auto-Clean
        top_bar = ttk.Frame(manager_frame)
        top_bar.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(top_bar, text="Load / Refresh Database", command=self.load_database_json).pack(side=tk.LEFT, padx=(0, 5))
        self.db_status_lbl = ttk.Label(top_bar, text="Database not loaded.", font=("TkDefaultFont", 9, "italic"))
        self.db_status_lbl.pack(side=tk.LEFT, padx=5)

        ttk.Button(top_bar, text="Auto-Clean All Titles", command=self.clean_database_titles_prompt).pack(side=tk.RIGHT, padx=5)

        # Search / Filter Box
        search_frame = ttk.Frame(manager_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(search_frame, text="Search Movie:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.filter_database_list())
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Listbox container
        list_container = ttk.Frame(manager_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        self.db_listbox = tk.Listbox(list_container, font=("TkDefaultFont", 10), borderwidth=1, relief=tk.SOLID, selectmode=tk.EXTENDED)
        self.db_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.db_listbox.bind("<Double-Button-1>", lambda event: self.edit_database_entry())
        self.db_listbox.bind("<<ListboxSelect>>", self.on_database_select)

        db_scroll = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.db_listbox.yview)
        db_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.db_listbox.config(yscrollcommand=db_scroll.set)

        # Actions Frame at bottom
        actions_frame = ttk.Frame(manager_frame)
        actions_frame.pack(fill=tk.X, pady=(10, 0))

        self.selection_lbl = ttk.Label(actions_frame, text="No items selected", font=("TkDefaultFont", 9, "italic"))
        self.selection_lbl.pack(side=tk.LEFT, pady=5)

        self.delete_btn = ttk.Button(actions_frame, text="Delete Selected Movies From Database", state=tk.DISABLED, command=self.delete_database_entry)
        self.delete_btn.pack(side=tk.RIGHT, pady=5)

        self.edit_btn = ttk.Button(actions_frame, text="Edit Selected Title", state=tk.DISABLED, command=self.edit_database_entry)
        self.edit_btn.pack(side=tk.RIGHT, padx=(0, 5), pady=5)

    # ------------------- DATA MANAGEMENT LOGIC -------------------
    def browse_db_folder(self):
        dir_path = filedialog.askdirectory(title="Select Database Directory")
        if dir_path:
            self.db_folder_var.set(os.path.normpath(dir_path))
            self.load_database_json()

    # ------------------- DATA MANAGEMENT LOGIC -------------------
    def load_database_json(self):
        db_dir = self.db_folder_var.get().strip()
        if not db_dir or not os.path.exists(db_dir):
            messagebox.showerror("Error", "Database directory path does not exist.")
            return

        quiz_json_path = os.path.join(db_dir, "quiz_data.json")
        if not os.path.exists(quiz_json_path):
            self.db_records = []
            self.db_status_lbl.configure(text="No quiz_data.json found in folder.")
            self.filter_database_list()
            return

        try:
            with open(quiz_json_path, "r", encoding="utf-8") as f:
                self.db_records = json.load(f)
            # Sort records alphabetically by title
            self.db_records.sort(key=lambda x: x.get("title", "").lower())
            self.db_status_lbl.configure(text=f"Loaded {len(self.db_records)} records successfully.")
            self.filter_database_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read database: {str(e)}")

    def filter_database_list(self):
        query = self.search_var.get().strip().lower()
        self.db_listbox.delete(0, tk.END)
        
        self.filtered_db_records = []
        for record in self.db_records:
            title = record.get("title", "")
            if not query or query in title.lower():
                self.filtered_db_records.append(record)
                self.db_listbox.insert(tk.END, title)

        # Clear active selection display
        self.on_database_select(None)

    def on_database_select(self, event):
        sel = self.db_listbox.curselection()
        count = len(sel)
        total = len(self.filtered_db_records)
        
        if count == 0:
            self.selection_lbl.configure(text="No items selected")
            self.delete_btn.configure(state=tk.DISABLED)
            self.edit_btn.configure(state=tk.DISABLED)
        else:
            self.selection_lbl.configure(text=f"Selected {count} of {total} movies")
            self.delete_btn.configure(state=tk.NORMAL)
            self.edit_btn.configure(state=tk.NORMAL if count == 1 else tk.DISABLED)

    def edit_database_entry(self):
        sel = self.db_listbox.curselection()
        if not sel or len(sel) != 1:
            messagebox.showinfo("Edit Title", "Please select exactly one movie to edit.")
            return

        record = self.filtered_db_records[sel[0]]
        old_title = record.get("title", "")

        # Open edit dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Movie Title")
        dialog.geometry("500x180")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Current Title:", font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W, padx=20, pady=(20, 5))
        ttk.Label(dialog, text=old_title, font=("TkDefaultFont", 10), foreground="gray").pack(anchor=tk.W, padx=20)

        ttk.Label(dialog, text="New Title:", font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W, padx=20, pady=(15, 5))
        new_title_var = tk.StringVar(value=old_title)
        title_entry = ttk.Entry(dialog, textvariable=new_title_var, width=60)
        title_entry.pack(anchor=tk.W, padx=20)
        title_entry.select_range(0, tk.END)
        title_entry.focus_set()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=20, pady=(15, 10))

        def save_edit():
            new_title = new_title_var.get().strip()
            if not new_title:
                messagebox.showerror("Error", "Title cannot be empty.", parent=dialog)
                return
            if new_title == old_title:
                dialog.destroy()
                return

            record["title"] = new_title

            db_dir = self.db_folder_var.get().strip()
            quiz_json_path = os.path.join(db_dir, "quiz_data.json")
            try:
                with open(quiz_json_path, "w", encoding="utf-8") as f:
                    json.dump(self.db_records, f, indent=4)
                dialog.destroy()
                self.load_database_json()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {str(e)}", parent=dialog)

        title_entry.bind("<Return>", lambda e: save_edit())
        ttk.Button(btn_frame, text="Save", command=save_edit).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

        self.root.wait_window(dialog)

    def delete_database_entry(self):
        sel = self.db_listbox.curselection()
        if not sel: return

        count = len(sel)
        confirm_msg = (
            f"Are you sure you want to delete the {count} selected movies from the database?\n\n"
            "This will remove the JSON records and delete the associated barcode image files."
        )
        if not messagebox.askyesno("Confirm Delete", confirm_msg):
            return

        db_dir = self.db_folder_var.get().strip()
        quiz_json_path = os.path.join(db_dir, "quiz_data.json")

        # Get records to delete
        records_to_delete = [self.filtered_db_records[i] for i in sel]
        titles_to_delete = {r.get("title") for r in records_to_delete}
        filenames_to_delete = {r.get("filename") for r in records_to_delete if r.get("filename")}

        # 1. Remove from local array
        self.db_records = [r for r in self.db_records if r.get("title") not in titles_to_delete]

        # 2. Write JSON update
        try:
            with open(quiz_json_path, "w", encoding="utf-8") as f:
                json.dump(self.db_records, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update database JSON: {str(e)}")
            return

        # 3. Delete files
        for filename in filenames_to_delete:
            file_path = os.path.join(db_dir, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    self.log(f"Warning: Could not delete physical file {file_path}: {str(e)}")

        # 4. Refresh Listbox
        self.log(f"Deleted {len(titles_to_delete)} database entries and their images.")
        self.load_database_json()

    def clean_database_titles_prompt(self):
        if not self.db_records:
            messagebox.showerror("No Data", "Please load a database first.")
            return

        changes = []
        for record in self.db_records:
            old_title = record.get("title", "")
            filename = record.get("filename", "")
            if filename:
                new_title = clean_movie_title(filename)
                if old_title != new_title:
                    changes.append({
                        "record": record,
                        "old_title": old_title,
                        "new_title": new_title
                    })

        if not changes:
            messagebox.showinfo("No Changes", "All titles are already formatted correctly!")
            return

        # Open Title Cleanup Preview modal
        dialog = tk.Toplevel(self.root)
        dialog.title("Title Cleanup Preview")
        dialog.geometry("800x500")
        dialog.minsize(700, 400)
        dialog.transient(self.root)
        dialog.grab_set()

        header_lbl = ttk.Label(
            dialog, 
            text=f"The following {len(changes)} movie titles will be cleaned. (Double-click any proposed title to edit it manually):", 
            font=("TkDefaultFont", 10, "bold"),
            wraplength=760
        )
        header_lbl.pack(pady=10, padx=15, anchor=tk.W)

        # Frame for treeview
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        # Create Treeview with Original and Cleaned columns
        tree = ttk.Treeview(frame, columns=("original", "cleaned"), show="headings")
        tree.heading("original", text="Original Title in JSON")
        tree.heading("cleaned", text="Proposed Cleaned Title")
        tree.column("original", width=370, anchor=tk.W)
        tree.column("cleaned", width=370, anchor=tk.W)
        tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scroll.set)

        # Populate treeview and map row IDs to change records
        row_to_change = {}
        for c in changes:
            row_id = tree.insert("", tk.END, values=(c["old_title"], c["new_title"]))
            row_to_change[row_id] = c

        # Bind double-click event for inline editing
        def on_tree_double_click(event):
            region = tree.identify_region(event.x, event.y)
            if region != "cell":
                return
            
            column = tree.identify_column(event.x)
            item = tree.identify_row(event.y)
            
            # Make the "Proposed Cleaned Title" column (column "#2") editable
            if column != "#2" or not item:
                return
                
            x, y, width, height = tree.bbox(item, column)
            
            # Create a temporary entry widget over the cell
            entry = ttk.Entry(tree)
            entry.place(x=x, y=y, width=width, height=height)
            
            # Fill entry with current value and set focus
            current_value = tree.item(item, "values")[1]
            entry.insert(0, current_value)
            entry.select_range(0, tk.END)
            entry.focus_set()
            
            def save_edit(event_inner=None):
                try:
                    if entry.winfo_exists():
                        new_val = entry.get().strip()
                        if new_val:
                            orig_val = tree.item(item, "values")[0]
                            tree.item(item, values=(orig_val, new_val))
                            if item in row_to_change:
                                row_to_change[item]["new_title"] = new_val
                        entry.destroy()
                except Exception:
                    pass
                    
            def cancel_edit(event_inner=None):
                try:
                    if entry.winfo_exists():
                        entry.destroy()
                except Exception:
                    pass
            
            entry.bind("<Return>", save_edit)
            entry.bind("<FocusOut>", save_edit)
            entry.bind("<Escape>", cancel_edit)

        tree.bind("<Double-1>", on_tree_double_click)

        # Action buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=15, pady=10)

        def confirm_action():
            # Apply changes
            for c in changes:
                c["record"]["title"] = c["new_title"]

            # Save database file
            db_dir = self.db_folder_var.get().strip()
            quiz_json_path = os.path.join(db_dir, "quiz_data.json")
            try:
                with open(quiz_json_path, "w", encoding="utf-8") as f:
                    json.dump(self.db_records, f, indent=4)
                messagebox.showinfo("Success", f"Successfully cleaned and updated {len(changes)} movie titles!")
                dialog.destroy()
                self.load_database_json()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save cleaned JSON: {str(e)}")
                dialog.destroy()

        def cancel_action():
            dialog.destroy()

        ttk.Button(btn_frame, text="Confirm & Apply Changes", command=confirm_action).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=cancel_action).pack(side=tk.RIGHT, padx=5)

        self.root.wait_window(dialog)

    # ------------------- GENERATOR WIDGET HELPERS -------------------
    def update_dirs_listbox(self):
        self.dirs_listbox.delete(0, tk.END)
        for d in self.movies_dirs:
            self.dirs_listbox.insert(tk.END, d)

    def add_movies_dir(self):
        dir_path = filedialog.askdirectory(title="Select Movies Folder to Add")
        if dir_path:
            norm_path = os.path.normpath(dir_path)
            if norm_path not in self.movies_dirs:
                self.movies_dirs.append(norm_path)
                self.update_dirs_listbox()
                self.save_config()

    def remove_movies_dir(self):
        sel = self.dirs_listbox.curselection()
        if sel:
            val = self.dirs_listbox.get(sel[0])
            if val in self.movies_dirs:
                self.movies_dirs.remove(val)
                self.update_dirs_listbox()
                self.save_config()

    def browse_output(self):
        dir_path = filedialog.askdirectory(title="Select Output Directory")
        if dir_path:
            self.output_dir_var.set(os.path.normpath(dir_path))
            self.save_config()

    def browse_ffmpeg(self):
        file_path = filedialog.askopenfilename(title="Select FFmpeg Executable (ffmpeg.exe)")
        if file_path:
            self.ffmpeg_path_var.set(os.path.normpath(file_path))
            self.save_config()

    def update_exclusions_listbox(self):
        self.ex_listbox.delete(0, tk.END)
        for item in sorted(self.exclusions):
            self.ex_listbox.insert(tk.END, item)

    def add_exclusion(self):
        val = self.ex_entry.get().strip()
        if val and val not in self.exclusions:
            self.exclusions.append(val)
            self.update_exclusions_listbox()
            self.ex_entry.delete(0, tk.END)
            self.save_config()

    def remove_exclusion(self):
        sel = self.ex_listbox.curselection()
        if sel:
            val = self.ex_listbox.get(sel[0])
            if val in self.exclusions:
                self.exclusions.remove(val)
                self.update_exclusions_listbox()
                self.save_config()

    def log(self, message):
        self.preview_queue.put(("log", message))

    def clear_preview_photo(self):
        self.preview_photo.put("#0f172a", to=(0, 0, self.preview_width, self.preview_height))

    def process_queue(self):
        try:
            while True:
                msg = self.preview_queue.get_nowait()
                msg_type = msg[0]
                if msg_type == "log":
                    text = msg[1]
                    self.log_text.config(state=tk.NORMAL)
                    self.log_text.insert(tk.END, text + "\n")
                    self.log_text.see(tk.END)
                    self.log_text.config(state=tk.DISABLED)
                elif msg_type == "progress":
                    self.progress_bar["value"] = msg[1]
                elif msg_type == "clear_preview":
                    self.clear_preview_photo()
                elif msg_type == "preview":
                    x = msg[1]
                    if isinstance(msg[2], str):
                        color = msg[2]
                        for y in range(self.preview_height):
                            self.preview_photo.put(color, (x, y))
                    else:
                        for y, color_tuple in enumerate(msg[2]):
                            if y < self.preview_height:
                                self.preview_photo.put(color_tuple[0], (x, y))
                elif msg_type == "finish":
                    self.finish_processing(msg[1], msg[2])
                    return
                self.preview_queue.task_done()
        except queue.Empty:
            pass
        
        if self.is_processing:
            self.root.after(30, self.process_queue)

    # Core logic launching
    def start_processing(self):
        if not PILLOW_AVAILABLE:
            messagebox.showerror("Error", "Pillow is not installed. Cannot start. Please run: pip install Pillow")
            return

        if not self.movies_dirs:
            messagebox.showerror("No Directories", "Please add at least one Movies Directory to scan.")
            return

        output_dir = self.output_dir_var.get().strip()
        if not output_dir:
            messagebox.showerror("Invalid Directory", "Please select an Output Directory.")
            return

        os.makedirs(output_dir, exist_ok=True)
        self.save_config()

        self.start_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)

        self.is_processing = True
        self.abort_event.clear()

        # Start queue processing poll
        self.root.after(30, self.process_queue)

        # Start processing thread
        threading.Thread(target=self.process_batch, args=(output_dir,), daemon=True).start()

    def cancel_processing(self):
        if self.is_processing:
            if messagebox.askyesno("Cancel Processing", "Are you sure you want to cancel the batch processing?"):
                self.abort_event.set()
                self.log("Cancelling... terminating active ffmpeg subprocess.")
                if self.active_process:
                    try:
                        self.active_process.terminate()
                    except Exception:
                        pass

    def get_ffmpeg_commands(self):
        ffmpeg_bin = self.ffmpeg_path_var.get().strip()
        if ffmpeg_bin and os.path.exists(ffmpeg_bin):
            ffmpeg_dir = os.path.dirname(ffmpeg_bin)
            ffprobe_bin = os.path.join(ffmpeg_dir, "ffprobe.exe" if os.name == 'nt' else "ffprobe")
            if os.path.exists(ffprobe_bin):
                return ffmpeg_bin, ffprobe_bin
            return ffmpeg_bin, "ffprobe"
        
        # Check in system PATH
        ffmpeg_in_path = shutil.which("ffmpeg")
        ffprobe_in_path = shutil.which("ffprobe")
        
        if not ffmpeg_in_path:
            raise FileNotFoundError("FFmpeg executable was not found. Please install FFmpeg or specify the path to ffmpeg.exe.")
        if not ffprobe_in_path:
            raise FileNotFoundError("FFprobe executable was not found. Please install FFmpeg or specify the path to ffmpeg.exe.")
            
        return ffmpeg_in_path, ffprobe_in_path

    # Extract dominant colors (matching React/TS algorithm)
    def extract_dominant_colors(self, img):
        width, height = img.size
        middle_y = height // 2
        colors = []
        for x in range(width):
            colors.append(img.getpixel((x, middle_y)))

        bucket_size = 24
        color_map = {}
        for r, g, b in colors:
            if r < 20 and g < 20 and b < 20: continue
            if r > 240 and g > 240 and b > 240: continue

            br = min(255, max(0, round(r / bucket_size) * bucket_size))
            bg = min(255, max(0, round(g / bucket_size) * bucket_size))
            bb = min(255, max(0, round(b / bucket_size) * bucket_size))

            key = (br, bg, bb)
            color_map[key] = color_map.get(key, 0) + 1

        sorted_colors = sorted(color_map.items(), key=lambda x: x[1], reverse=True)
        final_colors = []

        def color_distance(c1, c2):
            return ((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2 + (c1[2] - c2[2])**2)**0.5

        for c, count in sorted_colors:
            if len(final_colors) >= 5:
                break
            too_close = False
            for sel in final_colors:
                if color_distance(c, sel) < 60:
                    too_close = True
                    break
            if not too_close:
                final_colors.append(c)

        return [f"#{r:02X}{g:02X}{b:02X}" for r, g, b in final_colors]

    # Background thread execution
    def process_batch(self, output_dir):
        try:
            ffmpeg_path, ffprobe_path = self.get_ffmpeg_commands()
        except FileNotFoundError as e:
            self.log(f"ERROR: {str(e)}")
            self.preview_queue.put(("finish", False, "FFmpeg/FFprobe not found."))
            return

        self.log(f"Using FFmpeg: {ffmpeg_path}")
        self.log("Scanning directories for video files...")

        # Walk through all directories in the movies folder list
        video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v"}
        movie_files = []

        for movies_dir in self.movies_dirs:
            if not os.path.isdir(movies_dir):
                self.log(f"Skipping invalid movie directory: '{movies_dir}'")
                continue
            self.log(f"Scanning directory: '{movies_dir}'")
            for root, dirs, files in os.walk(movies_dir):
                if self.abort_event.is_set():
                    break

                dirs[:] = [d for d in dirs if d not in self.exclusions]

                for file in files:
                    if file.startswith("._") or file.startswith("."):
                        continue
                    ext = os.path.splitext(file)[1].lower()
                    if ext in video_extensions:
                        full_path = os.path.join(root, file)
                        movie_files.append(full_path)

        total_movies = len(movie_files)
        self.log(f"Found {total_movies} movie files to process across directories.\n")

        if total_movies == 0:
            self.preview_queue.put(("finish", True, "No movies found to process."))
            return

        # Load existing database entries
        quiz_data_path = os.path.join(output_dir, "quiz_data.json")
        quiz_records = []
        existing_filenames = set()
        if os.path.exists(quiz_data_path):
            try:
                with open(quiz_data_path, "r", encoding="utf-8") as f:
                    quiz_records = json.load(f)
                    existing_filenames = {record["filename"] for record in quiz_records if "filename" in record}
                self.log(f"Loaded {len(quiz_records)} existing records from quiz_data.json.")
            except Exception as e:
                self.log(f"Failed to load existing quiz_data.json (overwriting): {str(e)}")

        width = self.width_var.get()
        height = self.height_var.get()
        smooth = self.smooth_var.get()

        for idx, movie_path in enumerate(movie_files):
            if self.abort_event.is_set():
                self.log("\n[CANCELLED] Processing aborted by user.")
                break

            progress_pct = int(((idx) / total_movies) * 100)
            self.preview_queue.put(("progress", progress_pct))

            movie_filename = os.path.basename(movie_path)
            
            # Auto-Clean Title on generation!
            if self.clean_titles_var.get():
                movie_title = clean_movie_title(movie_filename)
            else:
                movie_title = os.path.splitext(movie_filename)[0].replace("cinecode-", "")
                movie_title = re.sub(r"[\.\-_]+", " ", movie_title).strip()

            self.log(f"[{idx+1}/{total_movies}] Processing: '{movie_title}'")

            # Safe filenames based on original filename to avoid file conflicts
            raw_title_slug = os.path.splitext(movie_filename)[0].replace("cinecode-", "")
            # Replace dots, dashes, brackets, and parentheses with spaces to keep word boundaries
            normalized_slug = re.sub(r"[\.\-_\(\)\[\]\{\}]+", " ", raw_title_slug)
            safe_title_slug = "_".join(normalized_slug.split()).lower()
            output_png_filename = f"cinecode-{safe_title_slug}.png"
            output_png_path = os.path.join(output_dir, output_png_filename)

            if output_png_filename in existing_filenames and os.path.exists(output_png_path):
                self.log("  -> Cinecode already exists (matched by filename). Skipping.")
                continue

            self.preview_queue.put(("clear_preview",))

            # Probing duration
            try:
                probe_cmd = [
                    ffprobe_path, "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", movie_path
                ]
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                duration_output = subprocess.check_output(probe_cmd, startupinfo=startupinfo).decode().strip()
                duration = float(duration_output)
                if duration <= 0: raise ValueError()
            except Exception:
                self.log("  -> ERROR: Could not probe video duration. Skipping.")
                continue

            # Setup FFmpeg
            skip_args = []
            selected_mode = self.mode_var.get()
            if selected_mode == "Fast (Skip B-Frames)":
                skip_args = ["-skip_frame", "noref"]
            elif selected_mode == "Turbo (I-Frames Only)":
                skip_args = ["-skip_frame", "nokey"]

            if smooth:
                scale_filter = "scale=1:1:flags=area"
                frame_bytes_sz = 3
            else:
                scale_filter = f"scale=1:{height}:flags=area"
                frame_bytes_sz = 1 * height * 3

            fps = width / duration
            ffmpeg_cmd = [ffmpeg_path, "-y"] + skip_args + [
                "-i", movie_path,
                "-vf", f"fps={fps},{scale_filter}",
                "-f", "image2pipe", "-vcodec", "rawvideo", "-pix_fmt", "rgb24", "-"
            ]

            try:
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                self.active_process = subprocess.Popen(
                    ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo
                )

                # Read stderr in a separate thread to prevent deadlock
                stderr_lines = []
                def _read_stderr(pipe, output_list):
                    try:
                        for line in pipe:
                            if isinstance(line, bytes):
                                line = line.decode("utf-8", errors="replace")
                            output_list.append(line.rstrip())
                    except Exception:
                        pass
                stderr_thread = threading.Thread(target=_read_stderr, args=(self.active_process.stderr, stderr_lines), daemon=True)
                stderr_thread.start()

                frames_data = []
                x = 0
                while not self.abort_event.is_set():
                    raw_frame = self.active_process.stdout.read(frame_bytes_sz)
                    if not raw_frame or len(raw_frame) < frame_bytes_sz:
                        break
                    
                    frames_data.append(raw_frame)

                    # Update progressive visualization
                    preview_x = int(x * self.preview_width / width)
                    if 0 <= preview_x < self.preview_width:
                        if smooth:
                            r, g, b = raw_frame[0], raw_frame[1], raw_frame[2]
                            hex_color = f"#{r:02X}{g:02X}{b:02X}"
                            self.preview_queue.put(("preview", preview_x, hex_color))
                        else:
                            preview_colors = []
                            for py in range(self.preview_height):
                                sy = int(py * height / self.preview_height)
                                offset = sy * 3
                                r = raw_frame[offset]
                                g = raw_frame[offset+1]
                                b = raw_frame[offset+2]
                                preview_colors.append((f"#{r:02X}{g:02X}{b:02X}",))
                            self.preview_queue.put(("preview", preview_x, preview_colors))

                    x += 1

                self.active_process.stdout.close()
                self.active_process.wait()
                stderr_thread.join(timeout=5)
                self.active_process = None

                if self.abort_event.is_set():
                    if os.path.exists(output_png_path):
                        os.remove(output_png_path)
                    break

                num_extracted = len(frames_data)
                if num_extracted == 0:
                    # Show the actual FFmpeg error instead of a generic message
                    err_detail = "\n".join(stderr_lines[-10:]) if stderr_lines else "No stderr output captured"
                    self.log(f"  -> ERROR: FFmpeg produced 0 frames. Skipping.\n     FFmpeg stderr:\n     {err_detail}")
                    continue

                # Compile final Pillow Image
                if smooth:
                    img = Image.new("RGB", (num_extracted, 1))
                    for idx_f, rgb in enumerate(frames_data):
                        img.putpixel((idx_f, 0), (rgb[0], rgb[1], rgb[2]))
                    img = img.resize((width, height), Image.Resampling.BILINEAR)
                else:
                    img = Image.new("RGB", (num_extracted, height))
                    for idx_f, slice_data in enumerate(frames_data):
                        for y in range(height):
                            offset = y * 3
                            r = slice_data[offset]
                            g = slice_data[offset+1]
                            b = slice_data[offset+2]
                            img.putpixel((idx_f, y), (r, g, b))
                    if img.width != width:
                        img = img.resize((width, height), Image.Resampling.BILINEAR)

                img.save(output_png_path, "PNG")

                # Extract dominant palette
                palette = self.extract_dominant_colors(img)

                # Append to JSON database
                quiz_records = [r for r in quiz_records if r["title"] != movie_title]
                quiz_records.append({
                    "title": movie_title,
                    "filename": output_png_filename,
                    "colors": palette,
                    "duration_seconds": int(duration)
                })

                with open(quiz_data_path, "w", encoding="utf-8") as f:
                    json.dump(quiz_records, f, indent=4)

                self.log(f"  -> SUCCESS! Dominant Colors: {palette}")

            except Exception as e:
                self.log(f"  -> ERROR (Exception): {str(e)}")
                if os.path.exists(output_png_path):
                    try: os.remove(output_png_path)
                    except Exception: pass
                continue

        # Complete batch
        self.preview_queue.put(("progress", 100))
        if self.abort_event.is_set():
            self.preview_queue.put(("finish", False, "Aborted by user."))
        else:
            self.preview_queue.put(("finish", True, "All movies processed successfully!"))

    def finish_processing(self, success, message):
        self.is_processing = False
        self.active_process = None
        self.start_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        
        if success:
            self.log(f"\n[DONE] {message}")
            messagebox.showinfo("Finished", message)
        else:
            self.log(f"\n[STOPPED] {message}")
            messagebox.showwarning("Stopped", message)


if __name__ == "__main__":
    root = tk.Tk()
    app = CineCodeGeneratorApp(root)
    root.mainloop()
