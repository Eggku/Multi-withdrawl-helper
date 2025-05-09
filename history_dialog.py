from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTextBrowser, QPushButton, 
                           QSizePolicy, QDialogButtonBox)
from PyQt6.QtCore import Qt, QSize

class HistoryDialog(QDialog):
    """A custom dialog to display rich text history with scrolling."""
    def __init__(self, title="历史记录", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        
        # Use a reasonable initial size, allowing internal scrolling
        # Width 650, Height 300 should be enough for ~5-7 entries initially
        self.setMinimumSize(QSize(650, 300)) 
        # Allow dialog to be resized larger if user wants
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding) 

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.text_browser = QTextBrowser(self)
        self.text_browser.setReadOnly(True)
        self.text_browser.setOpenExternalLinks(True) # Allow opening http/https links if any
        # Set a fixed font for better alignment if needed, or rely on HTML styling
        # self.text_browser.setFont(QFont("Courier New", 9)) 
        layout.addWidget(self.text_browser)

        # Standard OK button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, self)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def setContent(self, html_content: str):
        """Sets the HTML content to be displayed in the text browser."""
        self.text_browser.setHtml(html_content)
        # Scroll to top after setting content
        self.text_browser.verticalScrollBar().setValue(0) 