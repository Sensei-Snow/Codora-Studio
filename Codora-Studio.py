import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import subprocess
import platform
import os


class XMLHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super(XMLHighlighter, self).__init__(parent)

        self.highlightingRules = []

        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor("#c65c2c"))  # Orange
        keywordFormat.setFontWeight(QFont.Bold)
        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def", "del", "elif", "else", "except",
            "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal", "not",
            "or", "pass", "print", "raise", "return", "try", "while", "with", "yield"
        ]
        self.highlightingRules += [(QRegExp(f"\\b{keyword}\\b"), keywordFormat) for keyword in keywords]

        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor("#a0a0a4"))  # Grey
        self.highlightingRules.append((QRegExp("#.*"), commentFormat))

        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor("#4ea467"))  # Green
        self.highlightingRules.append((QRegExp("\"[^\"]*\""), stringFormat))
        self.highlightingRules.append((QRegExp("'[^']*'"), stringFormat))

        numberFormat = QTextCharFormat()
        numberFormat.setForeground(QColor("#2fc4d8"))  # Cyan
        self.highlightingRules.append((QRegExp(r"\b\d+(\.\d+)?([eE][+-]?\d+)?\b"), numberFormat))

        operatorFormat = QTextCharFormat()
        operatorFormat.setForeground(QColor("#b200b2"))  # Magenta
        operators = ["=", "==", "\\+", "-", "\\*", "/", "%", "<", ">", "<=", ">="]
        self.highlightingRules += [(QRegExp(f"{operator}"), operatorFormat) for operator in operators]

        othersFormat = QTextCharFormat()
        othersFormat.setForeground(QColor("yellow"))  # Yellow
        others = ["\\(", "\\)", "\\{", "\\}", "\\[", "\\]", "\\\\"]
        self.highlightingRules += [(QRegExp(pattern), othersFormat) for pattern in others]

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
        self.setCurrentBlockState(0)


# ----------------------------------------------------------------------------------------------------------------------------Classe Zone de numéros de ligne
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        # --------------------------------------------------------------Éditeur
        self.editor = editor
        self.setFixedWidth(40)

        editor.setContextMenuPolicy(Qt.CustomContextMenu)
        editor.customContextMenuRequested.connect(lambda pos, e=editor: self.show_custom_context_menu(pos, e))

    # --------------------------------------------------------------Mécanique d'écriture des nombres
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QColor(160, 160, 160))

        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber() + 1

        line_height = self.editor.fontMetrics().height()
        top = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()

        while block.isValid() and top < self.editor.height():
            painter.drawText(0, int(top) + line_height // 2 + 7, str(block_number))

            block = block.next()
            top = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
            block_number += 1

    # --------------------------------------------------------------Mise à jour des numéros de ligne
    def update(self):
        self.repaint()

    # --------------------------------------------------------------Création du menu clic droit custom
    def show_custom_context_menu(self, position, editor):
        context_menu = QMenu(editor)

        undo_action = QAction(QIcon("assets/back_white.png"), "Undo", self)
        undo_action.setEnabled(editor.document().isUndoAvailable())
        undo_action.triggered.connect(editor.undo)
        context_menu.addAction(undo_action)

        redo_action = QAction(QIcon("assets/forward_white.png"), "Redo", self)
        redo_action.setEnabled(editor.document().isRedoAvailable())
        redo_action.triggered.connect(editor.redo)
        context_menu.addAction(redo_action)

        context_menu.addSeparator()

        cut_action = QAction(QIcon("assets/cut.png"), "Cut", self)
        cut_action.setEnabled(editor.textCursor().hasSelection())
        cut_action.triggered.connect(editor.cut)
        context_menu.addAction(cut_action)

        copy_action = QAction(QIcon("assets/copy.png"), "Copy", self)
        copy_action.setEnabled(editor.textCursor().hasSelection())
        copy_action.triggered.connect(editor.copy)
        context_menu.addAction(copy_action)

        paste_action = QAction(QIcon("assets/paste.png"), "Paste", self)
        paste_action.setEnabled(bool(QApplication.clipboard().text()))
        paste_action.triggered.connect(editor.paste)
        context_menu.addAction(paste_action)

        context_menu.addSeparator()

        select_all_action = QAction(QIcon("assets/selectall.png"), "Select All", self)
        select_all_action.triggered.connect(editor.selectAll)
        context_menu.addAction(select_all_action)

        context_menu.setStyleSheet("""
            QMenu {
                background-color: #131e23;
                color: white;
                padding-left: 7px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background-color: #2e436e;
            }
        """)

        context_menu.exec_(editor.mapToGlobal(position))


# ----------------------------------------------------------------------------------------------------------------------------Classe IDE
class IDE(QMainWindow):
    def __init__(self):
        super().__init__()

        # --------------------------------------------------------------Onglets
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.setMovable(False)
        self.tabs.currentChanged.connect(self.update_cursor_position)

        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                background-color: #56585d;
                border: solid 1px #56585d;
            }

            QTabBar {
                background-color: #38393c;
            }

            QTabBar::tab {
                background: #38393c;
                padding: 10px;
                margin: 2px;
                border-top-left-radius: 7px;
                border-top-right-radius: 7px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
                font-weight: bold;
                width: 150px;
                color: #a1a2a4;
            }

            QTabBar::tab:selected {
                background: #56585d;
                color: white;
                margin-bottom: -2px;
                margin-top: 3px;
            }

            QTabBar::tab:hover {
                background: #404145;
                color: white;
            }

            QTabBar::close-button {
                image: url("assets/close_tab.png");
                subcontrol-position: right;
                margin-right: 5px;
            }

            QTabBar::close-button:hover {
                image: url("assets/close_tab_hover.png");
            }
        """)

        # --------------------------------------------------------------Tree
        self.file_system_model = QFileSystemModel()
        self.file_system_model.setRootPath(QDir.rootPath())

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_system_model)
        self.tree_view.setRootIndex(self.file_system_model.index(QDir.rootPath()))
        self.tree_view.setColumnWidth(0, 200)
        self.tree_view.setFixedWidth(300)

        self.tree_view.setStyleSheet("""
            QTreeView {
                background-color: #38393c;
                color: white;
                border: none;
            }

            QHeaderView::section {
                background-color: #38393c;
                color: white;
                border: none;
            }

            QScrollBar:horizontal {
                background: #38393c;
            }

            QScrollBar::handle:horizontal {
                background: #56585d;
                min-height: 10px;
                border-radius: 5px;
            }

            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: #38393c;
            }
        """)

        self.tree_view.doubleClicked.connect(self.open_file_from_tree)

        splitter = QSplitter(Qt.Horizontal)

        file_explorer_widget = QWidget()
        file_explorer_widget.setFixedWidth(318)
        file_explorer_layout = QVBoxLayout(file_explorer_widget)
        file_explorer_layout.addWidget(self.tree_view)

        splitter.addWidget(file_explorer_widget)

        splitter.addWidget(self.tabs)

        splitter.setStyleSheet("""
            QSplitter {
                background-color: #38393c;
            }

             QSplitter::handle {
                background-color: #38393c;
             }
        """)

        self.setCentralWidget(splitter)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #38393c;
            }
        """)

        # --------------------------------------------------------------Status Bar
        self.status_bar = self.statusBar()

        self.status_label = QLabel("Line : - | Column : - | Characters : -")
        self.status_label.setStyleSheet("color: white;")
        self.status_label.setContentsMargins(0, 0, 10, 0)
        self.status_bar.addPermanentWidget(self.status_label)

        self.encoding_label = QLabel("Encoding : UTF-8")
        self.encoding_label.setStyleSheet("color: white;")
        self.encoding_label.setAlignment(Qt.AlignRight)
        self.encoding_label.setContentsMargins(0, 0, 10, 0)
        self.status_bar.addPermanentWidget(self.encoding_label)

        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #131e23;
                color: white;
            }
        """)

        # ------------------------------------------------File
        self.menuBar().setStyleSheet("""
            QMenuBar {
                background-color: #131e23;
                color: white;
            }

            QMenuBar::item {
                background-color: transparent;
                padding: 6px 10px;
                border-radius: 5px;
            }

            QMenuBar::item:selected {
                background-color: #0297cd;
            }

            QMenuBar::item:pressed {
                background-color: #01719a;
            }

            QMenu {
                background-color: #131e23;
                color: white;
                padding-left: 7px;
            }

            QMenu::item {
                padding: 6px 20px;
                border-radius: 5px;
            }

            QMenu::item:selected {
                background-color: #2e436e;
            }
        """)

        file_menu = self.menuBar().addMenu("&File")

        open_menu = QMenu("Open a...", self)
        open_menu.setIcon(QIcon("assets/open.png"))
        txt_open_action = QAction(QIcon("assets/txt.png"), "Text file (*.txt)", self)
        txt_open_action.setStatusTip("Open a Text file")
        txt_open_action.triggered.connect(lambda: self.file_open("Text File (*.txt)", ".txt"))
        py_open_action = QAction(QIcon("assets/py.png"), "Python file(*.py)", self)
        py_open_action.setStatusTip("Open a Python file")
        py_open_action.triggered.connect(lambda: self.file_open("Python File (*.py)", ".py"))
        html_open_action = QAction(QIcon("assets/html.png"), "HTML file (*.html)", self)
        html_open_action.setStatusTip("Open a HTML file")
        html_open_action.triggered.connect(lambda: self.file_open("HTML File (*.html)", ".html"))
        css_open_action = QAction(QIcon("assets/css.png"), "CSS file (*.css)", self)
        css_open_action.setStatusTip("Open a CSS file")
        css_open_action.triggered.connect(lambda: self.file_open("CSS File (*.css)", ".css"))
        json_open_action = QAction(QIcon("assets/json.png"), "JSON file (*.json)", self)
        json_open_action.setStatusTip("Open a JSON file")
        json_open_action.triggered.connect(lambda: self.file_open("JSON File (*.json)", ".json"))
        open_menu.addAction(txt_open_action)
        open_menu.addAction(py_open_action)
        open_menu.addAction(html_open_action)
        open_menu.addAction(css_open_action)
        open_menu.addAction(json_open_action)
        file_menu.addMenu(open_menu)
        open_menu.setStyleSheet("""
            QMenu {
                background-color: #131e23;
                color: white;
                padding-left: 7px;
            }

            QMenu::item {
                padding: 6px 20px;
                border-radius: 5px;
            }

            QMenu::item:selected {
                background-color: #2e436e;
            }  
        """)

        open_directory_action = QAction(QIcon("assets/folder_white.png"), "Open project", self)
        open_directory_action.setStatusTip("Open a project in the file tree view")
        open_directory_action.triggered.connect(self.select_folder)
        file_menu.addAction(open_directory_action)

        save_file_action = QAction(QIcon("assets/save.png"), "Save", self)
        save_file_action.setStatusTip("Save current page")
        save_file_action.triggered.connect(self.file_save)
        file_menu.addAction(save_file_action)

        save_as_menu = QMenu("Save as...", self)
        save_as_menu.setIcon(QIcon("assets/saveas.png"))
        txt_save_action = QAction(QIcon("assets/txt.png"), "Text file (*.txt)", self)
        txt_save_action.setStatusTip("Save as a Text file")
        txt_save_action.triggered.connect(lambda: self.file_saveas("Text File (*.txt)", ".txt"))
        py_save_action = QAction(QIcon("assets/py.png"), "Python file(*.py)", self)
        py_save_action.setStatusTip("Save as a Python file")
        py_save_action.triggered.connect(lambda: self.file_saveas("Python File (*.py)", ".py"))
        html_save_action = QAction(QIcon("assets/html.png"), "HTML file (*.html)", self)
        html_save_action.setStatusTip("Save as a HTML file")
        html_save_action.triggered.connect(lambda: self.file_saveas("HTML File (*.html)", ".html"))
        css_save_action = QAction(QIcon("assets/css.png"), "CSS file (*.css)", self)
        css_save_action.setStatusTip("Save as a CSS file")
        css_save_action.triggered.connect(lambda: self.file_saveas("CSS File (*.css)", ".css"))
        json_save_action = QAction(QIcon("assets/json.png"), "JSON file (*.json)", self)
        json_save_action.setStatusTip("Save as a JSON file")
        json_save_action.triggered.connect(lambda: self.file_saveas("JSON File (*.json)", ".json"))
        save_as_menu.addAction(txt_save_action)
        save_as_menu.addAction(py_save_action)
        save_as_menu.addAction(html_save_action)
        save_as_menu.addAction(css_save_action)
        save_as_menu.addAction(json_save_action)
        file_menu.addMenu(save_as_menu)
        save_as_menu.setStyleSheet("""
            QMenu {
                background-color: #131e23;
                color: white;
                padding-left: 7px;
            }

            QMenu::item {
                padding: 6px 20px;
                border-radius: 5px;
            }

            QMenu::item:selected {
                background-color: #2e436e;
            }  
        """)

        # ------------------------------------------------Edit
        edit_menu = self.menuBar().addMenu("&Edit")

        undo_action = QAction(QIcon("assets/back_white.png"), "Undo", self)
        undo_action.setStatusTip("Undo last change")
        undo_action.triggered.connect(lambda: self.current_editor() and self.current_editor().undo())
        edit_menu.addAction(undo_action)

        redo_action = QAction(QIcon("assets/forward_white.png"), "Redo", self)
        redo_action.setStatusTip("Redo last change")
        redo_action.triggered.connect(lambda: self.current_editor() and self.current_editor().redo())
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction(QIcon("assets/cut.png"), "Cut", self)
        cut_action.setStatusTip("Cut selected text")
        cut_action.triggered.connect(lambda: self.current_editor() and self.current_editor().cut())
        edit_menu.addAction(cut_action)

        copy_action = QAction(QIcon("assets/copy.png"), "Copy", self)
        copy_action.setStatusTip("Copy selected text")
        copy_action.triggered.connect(lambda: self.current_editor() and self.current_editor().copy())
        edit_menu.addAction(copy_action)

        paste_action = QAction(QIcon("assets/paste.png"), "Paste", self)
        paste_action.setStatusTip("Paste from clipboard")
        paste_action.triggered.connect(lambda: self.current_editor() and self.current_editor().paste())
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        select_action = QAction(QIcon("assets/selectall.png"), "Select all", self)
        select_action.setStatusTip("Select all text")
        select_action.triggered.connect(lambda: self.current_editor() and self.current_editor().selectAll())
        edit_menu.addAction(select_action)

        edit_menu.addSeparator()

        wrap_action = QAction("Wrap text to window", self)
        wrap_action.setStatusTip("Check to wrap text to window")
        wrap_action.setCheckable(True)
        wrap_action.setChecked(True)
        wrap_action.triggered.connect(lambda: self.toggle_wrap(wrap_action.isChecked()))
        edit_menu.addAction(wrap_action)

        # ------------------------------------------------Terminal
        terminal_menu = self.menuBar().addMenu("&Terminal")

        terminal_action = QAction(QIcon("assets/terminal.png"), "Open terminal", self)
        terminal_action.setStatusTip("Open a terminal in a different window")
        terminal_action.triggered.connect(lambda: self.open_terminal())
        terminal_menu.addAction(terminal_action)

        terminal_cd_action = QAction(QIcon("assets/terminal_cd.png"), "Open terminal in project's directory", self)
        terminal_cd_action.setStatusTip("Open a terminal in the project's directory in a different window")
        terminal_cd_action.triggered.connect(lambda: self.open_terminal_in_folder())
        terminal_menu.addAction(terminal_cd_action)

        # ------------------------------------------------Editor
        editor_menu = self.menuBar().addMenu("&Editor")

        new_tab_action = QAction(QIcon("assets/tab_white.png"), "Open a new tab", self)
        new_tab_action.setStatusTip("Open a new blank tab in the editor")
        new_tab_action.triggered.connect(lambda: self.add_new_tab())
        editor_menu.addAction(new_tab_action)

        # ------------------------------------------------Run
        editor_menu = self.menuBar().addMenu("&Run")

        run_code_action = QAction(QIcon("assets/play.png"), "Run code", self)
        run_code_action.setStatusTip("Execute the code in a new terminal")
        run_code_action.triggered.connect(self.execute_code)
        editor_menu.addAction(run_code_action)

        # --------------------------------------------------------------Tool Bar
        self.toolbar = QToolBar()
        self.toolbar.setFixedHeight(45)
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setContextMenuPolicy(Qt.PreventContextMenu)

        self.space1 = QWidget()
        self.space1.setFixedWidth(35)
        self.space2 = QWidget()
        self.space2.setFixedWidth(35)
        self.space3 = QWidget()
        self.space3.setFixedWidth(35)

        self.select_folder_button = QPushButton()
        self.select_folder_button.setIcon(QIcon("assets/folder.png"))
        self.select_folder_button.clicked.connect(self.select_folder)

        self.new_tab_button = QPushButton()
        self.new_tab_button.setIcon(QIcon("assets/tab.png"))
        self.new_tab_button.clicked.connect(lambda: self.add_new_tab())

        self.command_bar = QLineEdit()
        self.command_bar.setPlaceholderText("Enter your command...")
        self.command_bar.returnPressed.connect(self.execute_command)
        self.command_bar.setFixedWidth(400)
        self.command_bar.setFixedHeight(30)
        self.command_bar.setStyleSheet("""
            QLineEdit {
                border: 2px solid #56789c;
                border-radius: 10px;
                padding: 5px 10px;
                font-size: 12px;
                background-color: #ecf0f1;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border: 2px solid #0297cd;
                background-color: white;
            }
        """)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search in the text...")
        self.search_bar.returnPressed.connect(self.search_text)
        self.search_bar.setFixedWidth(250)
        self.search_bar.setFixedHeight(30)
        self.search_bar.setStyleSheet("""
            QLineEdit {
                border: 2px solid #56789c;
                border-radius: 10px;
                padding: 5px 10px;
                font-size: 12px;
                background-color: #ecf0f1;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border: 2px solid #0297cd;
                background-color: white;
            }
        """)

        self.clear_highlight_button = QPushButton()
        self.clear_highlight_button.setIcon(QIcon("assets/eraser.png"))
        self.clear_highlight_button.clicked.connect(lambda: self.clear_highlight(self.current_editor()))

        self.execute_code_button = QPushButton()
        self.execute_code_button.setIcon(QIcon("assets/play.png"))
        self.execute_code_button.clicked.connect(lambda: self.execute_code(self.current_editor()))

        self.toolbar.addWidget(self.select_folder_button)
        self.toolbar.addWidget(self.new_tab_button)
        self.toolbar.addWidget(self.space1)
        self.toolbar.addWidget(self.command_bar)
        self.toolbar.addWidget(self.space2)
        self.toolbar.addWidget(self.search_bar)
        self.toolbar.addWidget(self.clear_highlight_button)
        self.toolbar.addWidget(self.space3)
        self.toolbar.addWidget(self.execute_code_button)

        self.toolbar.setStyleSheet("""
            QToolBar {
                background-color: #2f4a56;
                border: none;
                padding: 5px;
            }

            QToolBar QPushButton {
                background-color: #56789c;
                border-radius: 5px;
                padding: 6px;
                margin: 0 4px;
            }

            QToolBar QPushButton:hover {
                background-color: #0297cd;
            }

            QToolBar QPushButton:pressed {
                background-color: #01719a;
            }                  
        """)

        self.addToolBar(self.toolbar)

        # --------------------------------------------------------------Propriétés de la fenêtre
        self.setWindowTitle("Codora Studio")
        self.resize(1315, 768)
        self.setMinimumSize(1315, 600)
        self.setWindowIcon(QIcon("assets/logo.png"))

        # --------------------------------------------------------------Layout vertical
        layout = QVBoxLayout()

        # --------------------------------------------------------------Editor
        self.editor = QPlainTextEdit()
        fixedfont = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        fixedfont.setPointSize(12)
        self.editor.setFont(fixedfont)
        layout.addWidget(self.editor)

        self.path = None

        # --------------------------------------------------------------Ajouter les onglets de démarrage
        self.add_home_tab()

    # ----------------------------------------------------------------------------------------------------------------------------Fonctions IDE

    # --------------------------------------------------------------Démarrer le script Python
    def execute_code(self, editor):

        container = self.tabs.currentWidget()
        editor = container.findChild(QPlainTextEdit)
        script_path = getattr(editor, "current_file", None)

        if script_path:
            if not script_path.lower().endswith(".py"):
                self.dialog_critical("Erreur : le fichier sélectionné n'est pas un fichier Python (.py)")
                return

        if not script_path:
            temp_path = os.path.join(os.path.dirname(__file__), "temp_exec.py")
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(editor.toPlainText())
            script_path = temp_path

        if not os.path.exists(script_path):
            print(f"[ERROR] -- File {script_path} not found")
            return

        script_name = os.path.basename(script_path)

        system = platform.system()

        interpreter = sys.executable

        try:
            if system == "Windows":
                subprocess.Popen(["cmd.exe", "/c", "start", "cmd.exe", "/k", interpreter, script_path])

            elif system == "Linux":
                terminal_commands = [
                    f'gnome-terminal -- bash -c "{interpreter} \\"{script_path}\\"; exec bash"',
                    f'x-terminal-emulator -e bash -c "{interpreter} \\"{script_path}\\"; exec bash"',
                    f'xterm -hold -e {interpreter} "{script_path}"',
                    f'konsole --noclose -e {interpreter} "{script_path}"'
                ]
                launched = False
                for cmd in terminal_commands:
                    try:
                        subprocess.Popen(cmd, shell=True)
                        launched = True
                        break
                    except FileNotFoundError:
                        continue

                if not launched:
                    print("[ERROR] -- Linux terminal not found")
                    print("Maybe you have a too specific distribution, desktop environnment or terminal...")
                    print("If you want, the code to modify is in \"Aelios.py\" beyond the line 520")

            elif system == "Darwin":
                subprocess.Popen(["osascript", "-e",
                                  f'tell application "Terminal" to do script "{interpreter} \\"{script_path}\\""'])

            else:
                print("[ERROR] -- System not supported")

        except FileNotFoundError:
            print(f"[ERROR] -- {script_name} not found")
        except Exception as e:
            print(f"[ERROR] -- There was an error during starting tor executable : {e}")

    # --------------------------------------------------------------Application de la coloration syntaxique
    def apply_highlighter(self, editor):
        editor = self.current_editor()
        if editor:
            self.highlighter = XMLHighlighter(editor.document())

            editor.setStyleSheet("""
                    QPlainTextEdit {
                        background-color: #1e1f22;
                        color: #d5dce0;
                        font-family: Consolas, "Courier New", monospace;
                        border: none;
                    }
                """)

    # --------------------------------------------------------------Faire une recherche dans le code (Partie 1)
    def search_text(self):
        editor = self.current_editor()

        if editor is None:
            self.dialog_critical("Please open a file.")
            self.search_bar.clear()
            return

        text = editor.toPlainText()
        search = self.search_bar.text()

        if search in text:
            self.highlight_text(editor, search)
        else:
            self.search_bar.clear()
            QMessageBox.information(self, "Warning", "The expression : \"" + search + "\" is not in the text",
                                    QMessageBox.Ok)

    # --------------------------------------------------------------Faire une recherche dans le code (Partie 2)
    def highlight_text(self, editor, search):
        cursor = editor.textCursor()
        format = QTextCharFormat()
        format.setBackground(QColor("yellow"))

        cursor.movePosition(QTextCursor.Start)
        editor.setTextCursor(cursor)

        while True:
            cursor = editor.document().find(search, cursor)

            if cursor.isNull():
                break

            cursor.mergeCharFormat(format)

    # --------------------------------------------------------------Effacer la recherche
    def clear_highlight(self, editor):
        self.search_bar.clear()
        cursor = editor.textCursor()
        cursor.select(QTextCursor.Document)
        format = QTextCharFormat()
        format.setBackground(QColor("transparent"))
        cursor.mergeCharFormat(format)

    # --------------------------------------------------------------Exécuter la commande demandée
    def execute_command(self):

        editor = self.current_editor()

        if editor is None:
            self.dialog_critical("Editor not found, please open a file.")
            self.command_bar.clear()
            return

        command = self.command_bar.text()
        if command == "terminal":
            self.open_terminal()
            self.command_bar.clear()
        elif command == "terminal -cd":
            self.open_terminal_in_folder()
            self.command_bar.clear()
        elif command == "select -project":
            self.select_folder()
            self.command_bar.clear()
        elif command == "home":
            self.add_home_tab()
            self.command_bar.clear()
        elif command == "tab -add":
            self.add_new_tab()
            self.command_bar.clear()
        elif command == "tab -close":
            index = self.tabs.currentIndex()
            self.close_tab(index)
            self.command_bar.clear()
        elif command == "run":
            self.execute_code()
            self.command_bar.clear()
        elif command == "file -save":
            self.file_save()
            self.command_bar.clear()
            self.command_bar.setPlaceholderText("Successfully saved the file...")
            QTimer.singleShot(2000, lambda: self.command_bar.setPlaceholderText("Enter your command..."))
        elif command == "file -saveas -txt":
            self.file_saveas("Text File (*.txt)", ".txt")
            self.command_bar.clear()
        elif command == "file -saveas -py":
            self.file_saveas("Python File (*.py)", ".py")
            self.command_bar.clear()
        elif command == "file -saveas -html":
            self.file_saveas("HTML File (*.html)", ".html")
            self.command_bar.clear()
        elif command == "file -saveas -css":
            self.file_saveas("CSS File (*.css)", ".css")
            self.command_bar.clear()
        elif command == "file -saveas -json":
            self.file_saveas("JSON File (*.json)", ".json")
            self.command_bar.clear()
        elif command == "file -openas -txt":
            self.file_open("Text File (*.txt)", ".txt")
            self.command_bar.clear()
        elif command == "file -openas -py":
            self.file_open("Python File (*.py)", ".py")
            self.command_bar.clear()
        elif command == "file -openas -html":
            self.file_open("HTML File (*.html)", ".html")
            self.command_bar.clear()
        elif command == "file -openas -css":
            self.file_open("CSS File (*.css)", ".css")
            self.command_bar.clear()
        elif command == "file -openas -json":
            self.file_open("JSON File (*.json)", ".json")
            self.command_bar.clear()
        elif command == "undo":
            self.current_editor()
            self.current_editor().undo()
            self.command_bar.clear()
        elif command == "redo":
            self.current_editor()
            self.current_editor().redo()
            self.command_bar.clear()
        elif command == "copy":
            self.current_editor()
            self.current_editor().copy()
            self.command_bar.clear()
        elif command == "paste":
            self.current_editor()
            self.current_editor().paste()
            self.command_bar.clear()
        elif command == "cut":
            self.current_editor()
            self.current_editor().cut()
            self.command_bar.clear()
        elif command == "selectall":
            self.current_editor()
            self.current_editor().selectAll()
            self.command_bar.clear()
        elif command == "wraptext":
            editor = self.current_editor()
            if editor:
                current_mode = editor.lineWrapMode()
                editor.setLineWrapMode(
                    QPlainTextEdit.WidgetWidth if current_mode == QPlainTextEdit.NoWrap else QPlainTextEdit.NoWrap)
            self.command_bar.clear()
        else:
            self.command_bar.clear()
            QMessageBox.warning(self, "Warning", "This command does not exist. Please verify or look at the help.",
                                QMessageBox.Ok)

    # --------------------------------------------------------------Ouvrir le terminal
    def open_terminal(self):
        subprocess.Popen("start cmd", shell=True)

    # --------------------------------------------------------------Ouvrir le terminal dans le dossier spécifié
    def open_terminal_in_folder(self):
        path = getattr(self, "project_path", QDir.homePath())

        subprocess.Popen(f'start cmd /K "cd /d {path}"', shell=True)

    # --------------------------------------------------------------Ouvrir un fichier depuis le file_model (Étape 1)
    def open_file_from_tree(self, index):
        file_path = self.file_system_model.filePath(index)

        if os.path.isfile(file_path):
            self.add_file_from_tree(file_path)

    # --------------------------------------------------------------Ouvrir un fichier depuis le file_model (Étape 2)
    def add_file_from_tree(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            editor = QPlainTextEdit()
            fixedfont = QFontDatabase.systemFont(QFontDatabase.FixedFont)
            fixedfont.setPointSize(12)
            editor.setFont(fixedfont)
            editor.setPlainText(content)

            editor.cursorPositionChanged.connect(self.update_cursor_position)

            line_number_area = LineNumberArea(editor)
            editor.blockCountChanged.connect(line_number_area.update)
            editor.updateRequest.connect(lambda rect, dy: line_number_area.update())
            editor.cursorPositionChanged.connect(line_number_area.update)
            layout = QHBoxLayout()
            layout.addWidget(line_number_area)
            layout.addWidget(editor)

            container = QWidget()
            container.setLayout(layout)

            container.path = file_path
            editor.current_file = file_path

            file_icon = self.get_file_icon(file_path)

            index = self.tabs.addTab(container, file_icon, os.path.basename(file_path))
            self.tabs.setCurrentIndex(index)

            self.apply_highlighter(editor)

        except Exception as e:
            self.dialog_critical(f"Erreur à l'ouverture du fichier : {str(e)}")

    # --------------------------------------------------------------Sélectionner un dossier
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choisir un dossier")
        if folder:
            self.project_path = folder
            self.tree_view.setRootIndex(self.file_system_model.index(folder))

    # --------------------------------------------------------------Ajouter un onglet d'accueil
    def add_home_tab(self):
        welcome_label = QLabel(self)

        pixmap = QPixmap("assets/home_screen_2.png")

        welcome_label.setPixmap(pixmap)

        welcome_label.setAlignment(Qt.AlignCenter)

        def resize_image(event):
            label_size = welcome_label.size()

            scaled_pixmap = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            welcome_label.setPixmap(scaled_pixmap)

        welcome_label.resizeEvent = resize_image

        index = self.tabs.addTab(welcome_label, "Welcome")
        self.tabs.setCurrentIndex(index)

    # --------------------------------------------------------------Ajouter un onglet
    def add_new_tab(self, label="New Tab"):
        editor = QPlainTextEdit()
        fixedfont = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        fixedfont.setPointSize(12)
        editor.setFont(fixedfont)

        def toggle_wrap(checked):
            if checked:
                editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
            else:
                editor.setLineWrapMode(QPlainTextEdit.NoWrap)

        editor.toggle_wrap = toggle_wrap.__get__(editor)

        editor.cursorPositionChanged.connect(self.update_cursor_position)

        line_number_area = LineNumberArea(editor)
        editor.blockCountChanged.connect(line_number_area.update)
        editor.updateRequest.connect(lambda rect, dy: line_number_area.update())
        editor.cursorPositionChanged.connect(line_number_area.update)
        layout = QHBoxLayout()
        layout.addWidget(line_number_area)
        layout.addWidget(editor)

        container = QWidget()
        container.setLayout(layout)

        index = self.tabs.addTab(container, "New File")
        self.tabs.setCurrentIndex(index)

        self.force_redraw_line_numbers()

        self.update_cursor_position()

        self.apply_highlighter(editor)

        if self.tabs.count() > 1:
            self.tabs.setMovable(True)
            self.tabs.setStyleSheet("""
                    QTabWidget::pane {
                    background-color: #56585d;
                    border: solid 1px #56585d;
                }

                QTabBar {
                    background-color: #38393c;
                }

                QTabBar::tab {
                    background: #38393c;
                    padding: 10px;
                    margin: 2px;
                    border-top-left-radius: 7px;
                    border-top-right-radius: 7px;
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 0px;
                    font-weight: bold;
                    width: 150px;
                    color: #a1a2a4;
                }

                QTabBar::tab:hover {
                    background: #404145;
                    color: white;
                }

                QTabBar::tab:selected {
                    background: #56585d;
                    color: white;
                    margin-bottom: -2px;
                    margin-top: 3px;
                }

                QTabBar::close-button {
                    image: url("assets/close_tab.png");
                    subcontrol-position: right;
                    margin-right: 5px;
                }

                QTabBar::close-button:hover {
                    image: url("assets/close_tab_hover.png");
                }
            """)

    # --------------------------------------------------------------fermer un onglet
    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)
            if self.tabs.count() == 1:
                self.tabs.setMovable(False)
        else:
            exit()

    # --------------------------------------------------------------Renvoyer l'onglet actuel
    def current_tab(self):
        return self.tabs.currentWidget()

    # --------------------------------------------------------------Renvoyer l'éditeur actuel
    def current_editor(self):
        current_widget = self.tabs.currentWidget()
        if current_widget:
            editor = current_widget.findChild(QPlainTextEdit)
            return editor
        return None

    # --------------------------------------------------------------Maximiser la fenêtre
    def showMaximizedWindow(self):
        self.showMaximized()

    # --------------------------------------------------------------Ouvrir un fichier
    def file_open(self, file_type, extension):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", f"untitled{extension}", file_type,
                                                   options=options)

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()

                editor = QPlainTextEdit()
                fixedfont = QFontDatabase.systemFont(QFontDatabase.FixedFont)
                fixedfont.setPointSize(12)
                editor.setFont(fixedfont)
                editor.setPlainText(content)

                editor.cursorPositionChanged.connect(self.update_cursor_position)

                line_number_area = LineNumberArea(editor)
                editor.blockCountChanged.connect(line_number_area.update)
                editor.updateRequest.connect(lambda rect, dy: line_number_area.update())
                editor.cursorPositionChanged.connect(line_number_area.update)
                layout = QHBoxLayout()
                layout.addWidget(line_number_area)
                layout.addWidget(editor)

                container = QWidget()
                container.setLayout(layout)

                container.path = file_path
                editor.current_file = file_path

                file_icon = self.get_file_icon(file_path)

                index = self.tabs.addTab(container, file_icon, os.path.basename(file_path))
                self.tabs.setCurrentIndex(index)

                self.apply_highlighter(editor)

            except Exception as e:
                self.dialog_critical(f"Erreur à l'ouverture du fichier : {str(e)}")

    # --------------------------------------------------------------Enregistrer le fichier
    def file_save(self):
        tab = self.current_tab()
        editor = tab.findChild(QPlainTextEdit)

        if editor is None:
            self.dialog_critical("Editor not found, please open a file.")
            return

        path = getattr(tab, "path", None)

        if not path:
            return self.file_saveas("All files (*)", "")

        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(editor.toPlainText())
        except Exception as e:
            self.dialog_critical(f"Error during the save : {str(e)}")

    # --------------------------------------------------------------Enregistrer le fichier sous (Étape 1)
    def file_saveas(self, file_type, extension):
        editor = self.current_tab().findChild(QPlainTextEdit)

        if editor is None:
            self.dialog_critical("Editor not found, please open a file.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save File", f"untitled{extension}", file_type)

        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(editor.toPlainText())

                index = self.tabs.currentIndex()
                self.tabs.setTabText(index, os.path.basename(path))

                file_icon = self.get_file_icon(path)
                self.tabs.setTabIcon(index, file_icon)

                container = self.current_tab()
                container.path = path
                editor.current_file = path
            except Exception as e:
                self.dialog_critical(f"Error during the save : {str(e)}")

    # --------------------------------------------------------------Enregistrer le fichier sous (Étape 2)
    def _save_to_path(self, path):
        editor = self.current_editor()
        if not editor:
            self.dialog_critical("Editor not found, please open a file.")
            return

        text = editor.toPlainText()
        try:
            with open(path, 'w') as f:
                f.write(text)
        except Exception as e:
            self.dialog_critical(str(e))

    # --------------------------------------------------------------Contrôler le wrap
    def toggle_wrap(self, checked):
        editor = self.current_editor()
        if editor:
            if checked:
                editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
            else:
                editor.setLineWrapMode(QPlainTextEdit.NoWrap)

    # --------------------------------------------------------------Mettre à jour les infos sur le curseur
    def update_cursor_position(self):
        editor = self.current_editor()
        if editor:
            cursor = editor.textCursor()
            line_number = cursor.blockNumber() + 1
            column_number = cursor.columnNumber()

            self.status_label.setText(
                f"Line : {line_number} | Column : {column_number} | Characters : {len(editor.toPlainText())}")
        else:
            self.status_label.setText("Line : - | Column : - | Characters : -")

    # --------------------------------------------------------------Forcer la mise à jour des numéros de ligne
    def force_redraw_line_numbers(self):
        current_editor = self.current_tab().findChild(QPlainTextEdit)
        if current_editor:
            current_editor.viewport().update()
            for child in self.current_tab().findChildren(QWidget):
                if isinstance(child, LineNumberArea):
                    child.update()

    # --------------------------------------------------------------Obtenir l'icône correspondant au bon type de fichier
    def get_file_icon(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".py":
            return QIcon("assets/py.png")
        elif ext == ".txt":
            return QIcon("assets/txt.png")
        elif ext == ".html":
            return QIcon("assets/html.png")
        elif ext == ".css":
            return QIcon("assets/css.png")
        elif ext == ".json":
            return QIcon("assets/json.png")
        else:
            return QIcon("assets/txt.png")

    # --------------------------------------------------------------Afficher une erreur critique
    def dialog_critical(self, error):
        dialog_critical = QMessageBox(self)
        dialog_critical.setWindowTitle("Critical")
        dialog_critical.setText(error)
        dialog_critical.setIcon(QMessageBox.Critical)
        dialog_critical.show()


# ----------------------------------------------------------------------------------------------------------------------------Fonctions hors IDE

# --------------------------------------------------------------Afficher le SplashScreen
def show_splash():
    splash_pix = QPixmap("assets/splash.png")
    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    splash.setMask(splash_pix.mask())
    splash.show()

    QTimer.singleShot(2000, splash.close)

    return splash


# --------------------------------------------------------------Lancement
app = QApplication(sys.argv)
splash = show_splash()
window = IDE()
QTimer.singleShot(2000, window.showMaximizedWindow)
sys.exit(app.exec_())