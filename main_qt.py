import sys
import os
import time
import random
import pandas as pd
import threading
from datetime import datetime, timedelta
import csv
import re
from configparser import ConfigParser
import configparser
import shutil
import logging
from logging.handlers import RotatingFileHandler
from decimal import Decimal, ROUND_DOWN

# PyQt6 组件导入
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QComboBox, QLineEdit, QPushButton, QProgressBar,
                           QTextEdit, QFrame, QScrollArea, QGridLayout, QMessageBox,
                           QGroupBox, QTabWidget, QSplitter, QToolBar, QStatusBar,
                           QFileDialog, QSizePolicy, QDialog, QCheckBox, QDialogButtonBox, QTextBrowser)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize, QSettings, QLocale, QObject, QThread, QThreadPool, QUrl # <-- QUrl is needed
from PyQt6.QtGui import QAction, QFont, QIcon, QColor, QPalette, QIntValidator, QDoubleValidator, QCloseEvent, QClipboard, QDesktopServices # <-- Add QDesktopServices

# API相关类导入
from exchange_api_base import BaseExchangeAPI
from binance_exchange import BinanceAPI
from okx_exchange import OKXAPI

# 其他辅助模块导入
from settings_dialog import SettingsDialog
from address_validator import AddressValidator
from history_dialog import HistoryDialog

# 添加打赏对话框类
class DonationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("支持开发者")
        self.setFixedSize(500, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #2D2D2D;
                color: #CCCCCC;
            }
            QLabel {
                color: #CCCCCC;
            }
            QPushButton {
                background-color: #444444;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px 15px;
                color: #CCCCCC;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QLineEdit {
                background-color: #3A3A3A;
                border: 1px solid #555555;
                color: #FFFFFF;
                padding: 5px;
            }
            QGroupBox {
                border: 1px solid #444444;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
                color: #CCCCCC;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
                color: #85C1E9;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 添加说明文本
        description = QLabel("如果您觉得这个工具对您有帮助，欢迎打赏支持开发者继续改进！")
        description.setWordWrap(True)
        description.setStyleSheet("color: #85C1E9; font-size: 12pt; margin-bottom: 20px;")
        layout.addWidget(description)
        
        # EVM地址组
        evm_group = QGroupBox("EVM链地址")
        evm_layout = QVBoxLayout(evm_group)
        evm_layout.setSpacing(10)
        
        # 添加EVM地址
        self.add_donation_address(evm_layout, "ETH:", "0x093e76ab56dbb4d4438305fee72fdbec44b89e17")
        self.add_donation_address(evm_layout, "USDT (TRC20):", "TP3maixTnM7fFYYu4CD2tga4LxVjiW7BMw")
        
        layout.addWidget(evm_group)
        
        # SOL地址组
        sol_group = QGroupBox("Solana链地址")
        sol_layout = QVBoxLayout(sol_group)
        sol_layout.setSpacing(10)
        
        # 添加SOL地址
        self.add_donation_address(sol_layout, "SOL:", "2G4wiH3PSwSPjB6FDFa7FzMAA9ysAYagHSyqUvhhNRMp")
        
        layout.addWidget(sol_group)
        
        # 添加关闭按钮
        close_button = QPushButton("关闭")
        close_button.setFixedWidth(100)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def add_donation_address(self, layout, label_text, address):
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(10)
        
        label = QLabel(label_text)
        label.setStyleSheet("color: #F5B041; min-width: 100px;")
        container_layout.addWidget(label)
        
        address_input = QLineEdit(address)
        address_input.setReadOnly(True)
        address_input.setStyleSheet("""
            QLineEdit {
                background-color: #3A3A3A;
                border: 1px solid #555555;
                color: #FFFFFF;
                padding: 5px;
            }
        """)
        container_layout.addWidget(address_input)
        
        copy_button = QPushButton("复制")
        copy_button.setFixedWidth(60)
        copy_button.clicked.connect(lambda: self.copy_to_clipboard(address))
        container_layout.addWidget(copy_button)
        
        layout.addWidget(container)
    
    def copy_to_clipboard(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "复制成功", "地址已复制到剪贴板！")

# API初始化工作线程类
class ApiInitWorker(QObject):
    finished = pyqtSignal(bool, str, object, str)  # 成功标志, 消息, API实例, 交易所名称
    log_message = pyqtSignal(str, str)     # 消息, 级别
    
    def __init__(self, exchange_name, api_class, config, logger):
        super().__init__()
        self.exchange_name = exchange_name
        self.api_class = api_class
        self.config = config
        self.logger = logger
        self.api_instance = None
        
    def run(self):
        try:
            self.log_message.emit(f"正在为交易所 {self.exchange_name} 初始化API...", "INFO")
            self.api_instance = self.api_class(config=self.config, logger=self.logger)
            self.logger.info(f"已创建 {self.exchange_name} API 实例。正在尝试连接...")
            connected, message = self.api_instance.connect()
            
            # 返回API对象和结果
            self.finished.emit(connected, message, self.api_instance, self.exchange_name)
            
        except Exception as e:
            error_msg = f"初始化或连接 {self.exchange_name} API时发生严重错误: {e}"
            self.log_message.emit(error_msg, "CRITICAL")
            self.finished.emit(False, str(e), None, self.exchange_name)

# 余额查询工作线程类
class BalanceWorker(QObject):
    finished = pyqtSignal(str, str)  # 余额字符串, 币种
    error = pyqtSignal(str, str)     # 错误信息, 币种
    log_message = pyqtSignal(str, str) # 消息, 级别
    
    def __init__(self, api, coin):
        super().__init__()
        self.api = api
        self.coin = coin
        
    def run(self):
        try:
            self.log_message.emit(f"为币种 {self.coin} 请求余额...", "DEBUG")
            balance_val_str = self.api.get_balance(asset=self.coin)
            
            if balance_val_str is not None:
                self.finished.emit(balance_val_str, self.coin)
            else:
                self.error.emit("无法获取余额", self.coin)
        except Exception as e:
            self.error.emit(str(e), self.coin)

# =============================================================================
# 深色主题样式定义
# =============================================================================
DARK_STYLE = """
QWidget {
    background-color: #2D2D2D;
    color: #CCCCCC;
    font-family: 'Microsoft YaHei', Arial;
    font-weight: 500;
}
QMainWindow, QDialog {
    background: #2D2D2D;
}
QTabWidget::pane {
    border: 0px;
    background: #2D2D2D;
    margin: 0px;
}
QTabWidget::tab-bar {
    alignment: left;
}
QTabBar::tab {
    background: #444444;
    border: 1px solid #222222;
    padding: 5px 15px;
    margin-right: 2px;
    color: #CCCCCC;
    font-weight: 500;
}
QTabBar::tab:selected {
    background-color: #666666;
    border-bottom-color: #666666;
    color: white;
    font-weight: 600;
}
QTabBar::tab:hover {
    background: #555555;
}
QPushButton {
    background-color: #444444;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 3px 10px;
    margin: 0px;
    color: #CCCCCC;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #555555;
}
QPushButton:pressed {
    background-color: #666666;
}
QPushButton:disabled {
    background-color: #333333;
    color: #666666;
}
QPushButton#stop_button:!disabled {
    background-color: #FF6B6B;
    border: 1px solid #FF5252;
    color: white;
    font-weight: 600;
}
QPushButton#stop_button:!disabled:hover {
    background-color: #FF5252;
}
QPushButton#stop_button:!disabled:pressed {
    background-color: #FF3838;
}
QLineEdit, QComboBox {
    background-color: #3A3A3A;
    border: 1px solid #555555;
    border-radius: 0px;
    padding: 3px;
    color: #FFFFFF;
    font-weight: 500;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #666666;
    background-color: #666666;
}
QComboBox::down-arrow {
    border-top: 1px solid white;
    border-right: 3px solid transparent;
    border-left: 3px solid transparent;
    width: 0;
    height: 0;
}
QComboBox::down-arrow:disabled {
    border-top: 1px solid white;
    border-right: 1px solid transparent;
    border-left: 1px solid transparent;
    width: 0;
    height: 0;
}
QComboBox:focus {
    border: 1px solid #666666;
}
QProgressBar {
    border: 1px solid #555555;
    border-radius: 0px;
    text-align: center;
    background-color: #3A3A3A;
    height: 20px;
    font-weight: 500;
}
QProgressBar::chunk {
    background-color: #2ECC71;
}
QTextEdit {
    background-color: #2A2A2A;
    border: 1px solid #555555;
    color: #CCCCCC;
}
QGroupBox {
    border: 1px solid #444444;
    border-radius: 0px;
    margin-top: 6px;
    padding-top: 6px;
    color: #CCCCCC;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 3px;
    color: #CCCCCC;
    font-weight: 600;
}
QLabel {
    color: #CCCCCC;
    font-weight: 500;
}
QStatusBar {
    background-color: #333333;
    color: #CCCCCC;
    font-weight: 500;
}
"""

class WithdrawalHelper(QMainWindow):
    # 定义信号
    update_signal = pyqtSignal(str, str)
    progress_update_signal = pyqtSignal(int, str)
    wait_update_signal = pyqtSignal(int, str)
    confirm_withdrawal_signal = pyqtSignal(str, str, Decimal, str, str, bool) # Amount is Decimal
    withdrawal_confirmation_result = pyqtSignal(bool, bool)
    validation_results_signal = pyqtSignal(str, list, int)
    withdrawal_finished_signal = pyqtSignal() # <-- 新增信号，通知提币流程结束
    
    def __init__(self):
        super().__init__()
        
        # Configuration and App Data Directory must be defined before logger setup
        self.app_data_dir = os.path.join(os.path.expanduser("~"), "Documents", "MultiWithdrawalHelper")
        _app_data_dir_existed = os.path.exists(self.app_data_dir) # Store if it existed before trying to create
        if not _app_data_dir_existed:
            try:
                os.makedirs(self.app_data_dir)
            except OSError as e:
                # Fallback print to stderr if directory creation fails before logger is up
                # sys module is imported at the top of the file.
                print(f"CRITICAL: Failed to create app data directory {self.app_data_dir}: {e}", file=sys.stderr)

        # Logger setup
        self.logger = self._setup_logger() # self.app_data_dir is now available
        
        # Log application start and app_data_dir status
        self.logger.info("应用程序启动") # Original log line
        if not _app_data_dir_existed: 
            if os.path.exists(self.app_data_dir): # Check if creation was successful
                 self.logger.info(f"已创建应用数据目录: {self.app_data_dir}")
            else: # Creation was attempted but failed
                 self.logger.error(f"应用数据目录创建失败，请检查权限或路径: {self.app_data_dir}")
        else: # If it already existed
            self.logger.info(f"应用数据目录: {self.app_data_dir} (已存在)")

        self.setWindowTitle("多交易所提币助手")
        self.resize(850, 500)
        
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Initialize config_path and config parser (depends on app_data_dir, which is now set)
        self.config_path = os.path.join(self.app_data_dir, 'config.ini')
        self.config = ConfigParser()

        # Initialize Exchange related variables
        self.EXCHANGES = {"Binance": BinanceAPI, "OKX": OKXAPI}
        self.current_exchange_name = None
        self.current_exchange_api: BaseExchangeAPI | None = None
        
        # Dedicated Binance API for price fetching
        self.price_provider_api: BinanceAPI | None = None
        self.binance_api_for_prices_connected = False
        
        self.ALLOWED_COINS = ['ETH', 'USDT', 'USDC', 'SOL', 'SUI', 'G'] # 定义允许显示的币种列表

        self.supported_coins_for_current_exchange = []
        self.networks_cache = {} 
        self.price_cache = {}
        self.price_cache_ttl = 300
        
        # 添加余额缓存
        self.balance_cache = {}  # 格式: {exchange_coin: (balance_str, timestamp)}
        self.balance_cache_ttl = 30  # 缓存有效期30秒
        
        self.running = False
        
        # 创建线程引用存储列表，避免线程被垃圾回收导致"QThread: Destroyed while thread is still running"错误
        self.thread_references = []
        
        # 设置Qt线程池的最大线程数，避免创建过多线程
        QThreadPool.globalInstance().setMaxThreadCount(10)

        self.address_validator = AddressValidator(self.logger)
        self.settings_dialog = SettingsDialog(self.logger, self.config_path, self)

        # Used addresses, current addresses for processing, last file path
        self.used_addresses = set()
        self.current_addresses = []
        self.last_address_file_path = ""
        self.show_full_addresses = False
        
        # Thread synchronization for withdrawal confirmation
        self.withdrawal_confirm_event = threading.Event()
        self.user_agreed_to_this_withdrawal = False
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # UI Setup - Toolbar should be setup early as it might contain exchange selector
        self._setup_toolbar_and_exchange_selector(main_layout)
        self._setup_main_interface_layout(main_layout)
        
        # Connect signals
        self.update_signal.connect(self._update_log_display)
        self.progress_update_signal.connect(self.update_progress)
        self.wait_update_signal.connect(self.update_wait)
        self.validation_results_signal.connect(self.show_validation_results)
        self.confirm_withdrawal_signal.connect(self._show_withdrawal_confirm_dialog)
        self.withdrawal_confirmation_result.connect(self._handle_withdrawal_confirmation)
        self.withdrawal_finished_signal.connect(self._on_withdrawal_finished) # <-- 连接新信号到槽
        
        self.large_withdrawal_apply_to_all = False
        self.large_withdrawal_decision = None
        
        # Status bar time update timer
        self.status_bar_timer = QTimer(self)
        self.status_bar_timer.timeout.connect(self._update_status_bar_time)
        self.status_bar_timer.start(1000)
        self._update_status_bar_time()

        # Load configuration, initialize API, and update UI accordingly
        QTimer.singleShot(50, self._load_config_and_initialize_api)
        QTimer.singleShot(200, self._post_initial_ui_setup)

    def _setup_logger(self):
        """Configures and returns a logger instance."""
        logger = logging.getLogger("WithdrawalHelper")
        logger.setLevel(logging.DEBUG)

        if logger.hasHandlers():
            logger.handlers.clear()

        log_file_path = os.path.join(self.app_data_dir, 'app.log')
        
        fh = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        
        logger.addHandler(fh)
        return logger

    def _setup_toolbar_and_exchange_selector(self, main_layout):
        """创建顶部工具栏，添加各种操作按钮和交易所选择器"""
        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(5, 2, 5, 2)
        toolbar_layout.setSpacing(8)

        exchange_label = QLabel("交易所:")
        toolbar_layout.addWidget(exchange_label)
        self.exchange_combo_toolbar = QComboBox()
        self.exchange_combo_toolbar.addItems(list(self.EXCHANGES.keys()))
        self.exchange_combo_toolbar.setMinimumWidth(120)
        self.exchange_combo_toolbar.currentTextChanged.connect(self._handle_exchange_change_from_toolbar)
        toolbar_layout.addWidget(self.exchange_combo_toolbar)
        toolbar_layout.addSpacing(20)

        buttons = [
            ("历史记录", self.show_history),
            ("开始提币", self.start_withdrawal),
            ("停止", self.stop_withdrawal),
            ("导入地址", self.import_address_list),
            ("验证地址", self.validate_addresses),
            ("设置", self._open_settings_dialog),
        ]
        
        for text, callback in buttons:
            btn = QPushButton(text)
            btn.setFixedHeight(28)
            
            if text == "停止":
                self.stop_button = btn
                btn.setObjectName("stop_button")
                btn.setEnabled(False)
            elif text == "开始提币":
                self.start_button = btn
            
            btn.clicked.connect(callback)
            toolbar_layout.addWidget(btn)
        
        # 添加打赏按钮
        donation_btn = QPushButton("支持开发者")
        donation_btn.setFixedHeight(28)
        donation_btn.setStyleSheet("color: #3498DB;")
        donation_btn.clicked.connect(self.show_donation_dialog)
        toolbar_layout.addWidget(donation_btn)
        
        # 添加Twitter链接
        twitter_label = QLabel()
        twitter_url = "https://x.com/StayrealLoL"
        # 使用Twitter蓝色，移除下划线，移除图标
        twitter_label.setText(f'''<a href="{twitter_url}" style="color: #1DA1F2; text-decoration: none;">
                               关注作者Twitter</a>''') 
        twitter_label.setTextFormat(Qt.TextFormat.RichText)
        twitter_label.setToolTip(f"访问开发者Twitter: {twitter_url}")
        twitter_label.setOpenExternalLinks(True) # 让QLabel自动处理打开链接
        # 将链接放在伸展项之前，使其靠右
        toolbar_layout.addWidget(twitter_label)
        
        toolbar_layout.addStretch(1)
        main_layout.addWidget(toolbar_widget)
    
    def _setup_main_interface_layout(self, main_layout):
        """设置主界面内容，包括左侧设置区域和右侧地址列表和日志区域"""
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(10)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        # ======= 币种网络区域 =======
        coin_network_group = QGroupBox("币种和网络")
        coin_network_layout = QGridLayout(coin_network_group)
        coin_network_layout.setContentsMargins(10, 15, 10, 10)
        
        coin_network_layout.addWidget(QLabel("提币币种:"), 0, 0)
        self.coin_combo = QComboBox()
        self.coin_combo.currentTextChanged.connect(self.update_networks_on_coin_change)
        self.coin_combo.setFixedWidth(150)
        self.coin_combo.setStyleSheet("""
            QComboBox { padding-right: 20px; background-color: #3A3A3A; color: white; border: 1px solid #555555; }
            QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 20px; border-left: 1px solid #777777; background-color: #666666; }
        """)
        coin_network_layout.addWidget(self.coin_combo, 0, 1)
        
        coin_network_layout.addWidget(QLabel("提币网络:"), 1, 0)
        self.network_combo = QComboBox()
        self.network_combo.setFixedWidth(150)
        self.network_combo.setStyleSheet("""
            QComboBox { padding-right: 20px; background-color: #3A3A3A; color: white; border: 1px solid #555555; }
            QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 20px; border-left: 1px solid #777777; background-color: #666666; }
        """)
        self.network_combo.currentTextChanged.connect(self.update_usd_values_on_network_change)

        coin_network_layout.addWidget(self.network_combo, 1, 1)
        
        # 添加余额、价格、手续费标签
        coin_network_layout.addWidget(QLabel("余额:"), 2, 0)
        self.balance_label = QLabel("N/A")
        self.balance_label.setMinimumWidth(150) # 保持宽度一致
        coin_network_layout.addWidget(self.balance_label, 2, 1)
        
        coin_network_layout.addWidget(QLabel("手续费:"), 4, 0)
        self.fee_label = QLabel("N/A")
        self.fee_label.setMinimumWidth(150)
        coin_network_layout.addWidget(self.fee_label, 4, 1)
        
        left_layout.addWidget(coin_network_group)
        
        self.coin_combo.setEnabled(False)
        self.network_combo.setEnabled(False)
        
        # ======= 提币数量区域 =======
        amount_group = QGroupBox("提币数量")
        amount_layout = QGridLayout(amount_group)
        amount_layout.setContentsMargins(10, 15, 10, 10)
        amount_layout.addWidget(QLabel("最小数量:"), 0, 0)
        self.min_amount_entry = QLineEdit("0.1")
        self.min_amount_entry.setFixedWidth(80)
        amount_layout.addWidget(self.min_amount_entry, 0, 1)
        self.min_amount_usd = QLabel("≈$-.--")
        self.min_amount_usd.setStyleSheet("color: #3498DB;")
        amount_layout.addWidget(self.min_amount_usd, 0, 2)
        amount_layout.addWidget(QLabel("最大数量:"), 1, 0)
        self.max_amount_entry = QLineEdit("100")
        self.max_amount_entry.setFixedWidth(80)
        amount_layout.addWidget(self.max_amount_entry, 1, 1)
        self.max_amount_usd = QLabel("≈$-.--")
        self.max_amount_usd.setStyleSheet("color: #3498DB;")
        amount_layout.addWidget(self.max_amount_usd, 1, 2)
        self.min_amount_entry.textChanged.connect(self.update_usd_values)
        self.max_amount_entry.textChanged.connect(self.update_usd_values)
        left_layout.addWidget(amount_group)
        
        # ======= 地址范围区域 =======
        range_group = QGroupBox("地址范围")
        range_layout = QGridLayout(range_group)
        range_layout.setContentsMargins(10, 15, 10, 10)
        range_layout.addWidget(QLabel("起始序号:"), 0, 0)
        self.start_addr_entry = QLineEdit("1")
        range_layout.addWidget(self.start_addr_entry, 0, 1)
        range_layout.addWidget(QLabel("结束序号:"), 1, 0)
        self.end_addr_entry = QLineEdit("10")
        range_layout.addWidget(self.end_addr_entry, 1, 1)
        left_layout.addWidget(range_group)
        
        # ======= 状态区域 =======
        status_group = QGroupBox("状态")
        status_layout = QVBoxLayout(status_group)
        status_layout.setContentsMargins(10, 15, 10, 10)
        progress_layout = QHBoxLayout()
        self.progress_label = QLabel("进度: 0/0")
        self.progress_label.setFixedWidth(60)
        progress_layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)  # 不显示进度条文本
        progress_layout.addWidget(self.progress_bar)
        status_layout.addLayout(progress_layout)
        wait_layout = QHBoxLayout()
        self.wait_label = QLabel("等待: 0秒")
        self.wait_label.setFixedWidth(60)
        wait_layout.addWidget(self.wait_label)
        self.wait_bar = QProgressBar()
        self.wait_bar.setTextVisible(False)
        wait_layout.addWidget(self.wait_bar)
        status_layout.addLayout(wait_layout)
        left_layout.addWidget(status_group)
        left_layout.addStretch(1)
        
        # ======= 右侧 - 地址列表和日志区域 =======
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        address_container = QWidget()
        address_container_layout = QVBoxLayout(address_container)
        address_container_layout.setContentsMargins(0, 0, 0, 0)
        address_group = QGroupBox("提币地址列表")
        address_layout = QVBoxLayout(address_group)
        address_layout.setContentsMargins(10, 15, 10, 10)
        self.toggle_address_btn = QPushButton("显示")
        self.toggle_address_btn.setToolTip("切换地址显示方式")
        self.toggle_address_btn.setFixedSize(45, 20)
        self.toggle_address_btn.setStyleSheet("""
            QPushButton { background-color: #3A3A3A; border-radius: 2px; border: 1px solid #555555; font-size: 8pt; padding: 0px 2px; }
            QPushButton:hover { background-color: #4A4A4A; } QPushButton:pressed { background-color: #555555; }
            QPushButton:checked { background-color: #666666; border: 1px solid #888888; }
        """)
        self.toggle_address_btn.setCheckable(True)
        self.toggle_address_btn.clicked.connect(self.toggle_address_display)
        self.address_text = QTextEdit()
        self.address_text.setReadOnly(True)
        self.address_text.setFont(QFont("Monospace", 9))
        self.address_text.setStyleSheet("background-color: #252525;")
        address_layout.addWidget(self.address_text)
        address_container_layout.addWidget(address_group)
        self.toggle_address_btn.setParent(address_group)
        QTimer.singleShot(0, lambda: self._adjust_button_position(address_group))
        
        log_container = QWidget()
        log_container_layout = QVBoxLayout(log_container)
        log_container_layout.setContentsMargins(0, 0, 0, 0)
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(10, 15, 10, 10)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Monospace", 9))
        self.log_text.setStyleSheet("background-color: #252525;")
        log_layout.addWidget(self.log_text)
        log_container_layout.addWidget(log_group)
        
        right_splitter.addWidget(address_container)
        right_splitter.addWidget(log_container)
        initial_height = self.height() if self.height() > 200 else 400
        right_splitter.setSizes([int(initial_height/2), int(initial_height/2)])
        right_layout.addWidget(right_splitter)
        
        content_layout.addWidget(left_widget, 1)
        content_layout.addWidget(right_widget, 4)
        main_layout.addWidget(content_widget)
        
        self.status_label = QLabel("就绪")
        self.api_status_indicator = QLabel()
        self.api_status_indicator.setFixedSize(16, 16)
        self.update_api_status_indicator(False)
        
        self.statusBar().addWidget(self.status_label)
        self.statusBar().addPermanentWidget(QLabel("API状态:"))
        self.statusBar().addPermanentWidget(self.api_status_indicator)
        
    def _adjust_button_position(self, parent_group):
        try:
            if not hasattr(self, 'toggle_address_btn') or not self.toggle_address_btn: return
            width = parent_group.width()
            title_height = 22 
            button_height = self.toggle_address_btn.height()
            y_pos = max(0, (title_height - button_height) // 2)
            self.toggle_address_btn.move(width - self.toggle_address_btn.width() - 10, y_pos)
            if not hasattr(parent_group, '_original_resizeEvent'):
                parent_group._original_resizeEvent = parent_group.resizeEvent
            parent_group.resizeEvent = lambda event: self._on_parent_resize(event, parent_group)
        except Exception as e:
            self.log_message(f"调整按钮位置出错: {str(e)}", level="ERROR", exc_info=True)
    
    def _on_parent_resize(self, event, parent_group):
        if hasattr(self, 'toggle_address_btn') and self.toggle_address_btn:
            width = parent_group.width()
            title_height = 22
            button_height = self.toggle_address_btn.height()
            y_pos = max(0, (title_height - button_height) // 2)
            self.toggle_address_btn.move(width - self.toggle_address_btn.width() - 10, y_pos)
        if hasattr(parent_group, '_original_resizeEvent') and parent_group._original_resizeEvent:
            parent_group._original_resizeEvent(event)
        else:
            QGroupBox.resizeEvent(parent_group, event)
        
    def _load_addresses_from_file(self, file_path):
        """Helper method to load addresses and optional labels from a CSV or Excel file.
        
        支持两种文件格式:
        1. 单列地址格式: 包含'address'和可选的'label'列
        2. 多列地址格式: 包含多列，每列代表一种类型的地址(EVM、SUI、SOL等)
        """
        self.log_message(f"尝试从文件加载地址和标签: {file_path}", level="DEBUG")
        try:
            if file_path.lower().endswith('.csv'):
                # header=0 表示第一行是表头
                # dtype=str 确保所有列都作为字符串读取，防止数字地址被错误解析
                # keep_default_na=False 防止空字符串被解析为 NaN
                df = pd.read_csv(file_path, dtype=str, header=0, keep_default_na=False)
            elif file_path.lower().endswith('.xlsx'):
                df = pd.read_excel(file_path, dtype=str, header=0, keep_default_na=False)
            else:
                return False, "不支持的文件格式。请选择 .csv 或 .xlsx 文件。"

            # 检查文件是否为空
            if df.empty:
                return False, "文件为空，没有可导入的地址。"

            # 规范化列名: 转小写，去首尾空格
            df.columns = df.columns.str.strip().str.lower()

            # 检测文件格式: 单列地址格式 vs 多列地址格式
            # 如果含有'address'列，则视为单列地址格式；否则视为多列地址格式
            if 'address' in df.columns:
                # 单列地址格式处理
                return self._process_single_column_addresses(df)
            else:
                # 多列地址格式处理
                return self._process_multi_column_addresses(df)

        except FileNotFoundError:
            self.logger.error(f"地址文件未找到: {file_path}")
            return False, "文件未找到。"
        except Exception as e:
            self.logger.error(f"读取地址文件时出错: {file_path} - {e}", exc_info=True)
            return False, f"读取文件时出错: {e}"
    
    def _process_single_column_addresses(self, df):
        """处理单列地址格式的DataFrame."""
        # 检查必需的 'address' 列是否存在
        if 'address' not in df.columns:
            return False, "文件中未找到名为 'address' 的列 (不区分大小写)。"
            
        # 检查可选的 'label' 列是否存在
        has_label_column = 'label' in df.columns
        if not has_label_column:
            self.log_message("文件中未找到 'label' 列，将不使用地址标签。", level="INFO")

        # 提取数据并构建字典列表
        addresses_data = []
        for index, row in df.iterrows():
            addr = row['address'].strip()
            label = row['label'].strip() if has_label_column and row['label'] else None
            
            if addr: # 只添加地址不为空的行
                addresses_data.append({'address': addr, 'label': label})
        
        if not addresses_data:
            return False, "文件中未能提取到有效的地址行。"

        self.current_addresses = addresses_data # 更新为字典列表
        self.used_addresses = set() # 清除已用地址记录
        
        # 设置当前正在使用的地址类型
        self.current_address_type = 'standard'
        
        self.log_message(f"成功从单列格式文件加载 {len(self.current_addresses)} 条地址记录。", level="INFO")
        return True, f"成功加载 {len(self.current_addresses)} 条地址记录。"

    def _process_multi_column_addresses(self, df):
        """处理多列地址格式的DataFrame，每列代表一种类型的地址."""
        # 检查是否至少有一列
        if len(df.columns) == 0:
            return False, "文件中没有列可供导入。"
            
        # 检测可用的地址类型列
        available_types = []
        address_types_map = {
            'evm': ['evm', 'eth', 'ethereum', 'bsc', 'polygon', 'avax', 'avalanche', 'arb', 'arbitrum'],
            'sui': ['sui'],
            'sol': ['sol', 'solana']
        }
        
        # 创建一个字典，用于存储每种类型对应的列名
        self.address_type_columns = {}
        
        # 检查每一列，判断是否为地址类型列
        for col in df.columns:
            col_lower = col.lower()
            # 跳过包含'label'的列
            if 'label' in col_lower:
                continue
                
            for addr_type, keywords in address_types_map.items():
                if col_lower in keywords or any(keyword in col_lower for keyword in keywords):
                    available_types.append(addr_type)
                    self.address_type_columns[addr_type] = col
                    break
            
            # 如果列名不在预定义的类型中，且不包含'label'，视为自定义类型
            if col not in self.address_type_columns.values() and 'label' not in col_lower:
                # 使用列名本身作为类型标识符
                custom_type = col_lower
                available_types.append(custom_type)
                self.address_type_columns[custom_type] = col
        
        if not available_types:
            return False, "文件中未能识别出任何地址类型列。请确保列名包含EVM、SUI、SOL等关键词，或者使用单列'address'格式。"
        
        # 存储所有可用的地址类型
        self.available_address_types = available_types
        
        # 默认选择第一个可用类型
        self.current_address_type = available_types[0]
        
        # 提取当前选定类型的地址
        self._load_addresses_for_current_type(df)
        
        return True, f"成功加载多列地址文件，可用类型: {', '.join(available_types)}。当前使用: {self.current_address_type}。"
    
    def _load_addresses_for_current_type(self, df=None):
        """根据当前选定的地址类型，从DataFrame中加载相应列的地址."""
        if not hasattr(self, 'current_address_type') or not hasattr(self, 'address_type_columns'):
            self.log_message("无法加载地址：未设置当前地址类型或类型映射。", level="ERROR")
            return
        
        # 如果没有提供DataFrame，则使用last_address_file_path再次加载
        if df is None and hasattr(self, 'last_address_file_path') and self.last_address_file_path:
            try:
                if self.last_address_file_path.lower().endswith('.csv'):
                    df = pd.read_csv(self.last_address_file_path, dtype=str, header=0, keep_default_na=False)
                elif self.last_address_file_path.lower().endswith('.xlsx'):
                    df = pd.read_excel(self.last_address_file_path, dtype=str, header=0, keep_default_na=False)
                else:
                    self.log_message("无法重新加载地址：不支持的文件格式。", level="ERROR")
                    return
            except Exception as e:
                self.log_message(f"重新加载地址文件时出错: {e}", level="ERROR")
                return
        
        if df is None:
            self.log_message("无法加载地址：DataFrame为None且无法重新加载文件。", level="ERROR")
            return
        
        # 获取当前类型对应的列名
        column = self.address_type_columns.get(self.current_address_type)
        if not column or column not in df.columns:
            self.log_message(f"无法找到当前类型 {self.current_address_type} 对应的列 {column}。", level="ERROR")
            return
        
        # 提取地址并构建字典列表
        addresses_data = []
        for index, row in df.iterrows():
            addr = str(row[column]).strip()
            if addr:  # 只添加地址不为空的行
                addresses_data.append({'address': addr, 'label': None})  # 多列格式暂不支持label
        
        self.current_addresses = addresses_data
        self.used_addresses = set()  # 清除已用地址记录
        self.log_message(f"已加载 {len(addresses_data)} 条 {self.current_address_type} 类型的地址。", level="INFO")
        self.refresh_address_list()
    
    def _on_address_type_changed(self, address_type):
        """当用户切换地址类型时调用."""
        if address_type == self.current_address_type:
            return
        
        self.current_address_type = address_type
        self.log_message(f"地址类型已切换为: {address_type}", level="INFO")
        
        # 重新加载当前类型的地址
        self._load_addresses_for_current_type()

    def refresh_address_list(self):
        """刷新界面上的地址列表显示 (处理字典列表)."""
        if not hasattr(self, 'address_text'):
            return # UI not ready
            
        if not self.current_addresses:
            self.address_text.setHtml( 
                "<div style='text-align:center; margin-top:50px;'>"
                "<span style='color:#CCCCCC;'>地址列表为空。请点击「导入地址」按钮导入。</span>"
                "</div>"
            )
            return
                
        html_lines = [] 
        line_count = 0
        for i, item in enumerate(self.current_addresses):
            line_count += 1
            index_str = f"{i + 1:>4}: "
            
            addr = item.get('address', '[地址缺失]')
            label = item.get('label')
            
            display_addr = addr
            if not self.show_full_addresses:
                display_addr = self._mask_addresses_in_text(addr) # 地址打码

            # 构造显示行: 如果有标签，显示 "标签 (地址)"，否则只显示地址
            display_line = f"{index_str}"
            if label:
                # 对标签也进行简单的HTML转义
                label_escaped = label.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                display_line += f"{label_escaped} ({display_addr})"
            else:
                display_line += display_addr
            
            html_lines.append(display_line)

            if line_count > 2000: # 限制显示行数
                 html_lines.append("... (列表过长，仅显示前2000条)")
                 self.logger.warning("地址列表过长，仅在UI中显示前2000条。")
                 break
                
        # 使用 <pre> 标签保留格式和对齐
        display_html = "<pre>" + "\n".join(html_lines) + "</pre>" 
        
        self.address_text.setHtml(display_html)
        self.address_text.verticalScrollBar().setValue(0) # 滚动到顶部
        self.log_message(f"地址列表UI已刷新，显示 {line_count} 条记录。", level="DEBUG")
        
    def load_address_from_last_file(self):
        """尝试从配置文件中记录的上次使用的文件路径加载地址。"""
        if not self.last_address_file_path or not os.path.exists(self.last_address_file_path):
            self.logger.info("上次使用的地址文件路径无效或不存在，跳过自动加载。")
            self.refresh_address_list() # Show empty state if no addresses loaded
            return

        self.log_message(f"尝试从上次使用的文件加载地址: {self.last_address_file_path}", level="INFO")
        success, message = self._load_addresses_from_file(self.last_address_file_path)
        if success:
            self.refresh_address_list()
            # 将下面这行日志从 INFO 改为 DEBUG，并微调内容
            self.log_message(f"自动加载上次地址文件处理完毕: {message}", level="DEBUG")
        else:
            self.log_message(f"自动加载上次地址文件失败: {message}", level="WARNING")
            # Clear last path if it failed to load, prompting user to import again
            failed_path = self.last_address_file_path # Store path before clearing
            self.last_address_file_path = "" 
            self.save_app_config() # Save cleared path
            self.refresh_address_list() # Show empty state
            QMessageBox.warning(self, "加载地址失败", f"无法加载上次使用的地址文件 '{os.path.basename(failed_path)}':\\n{message}\\n\\n请重新导入地址文件。")

    def load_addresses_after_ui_ready(self):
        """UI初始化完成后加载地址列表"""
        try:
            # Don't load if addresses are already present (e.g., from a previous failed load attempt?)
            # Maybe clear self.current_addresses before attempting load? Let's assume not needed for now.
            # if self.current_addresses:
            #    self.refresh_address_list()
            #    return

            # Check if last_address_file_path is set AND exists
            if hasattr(self, 'last_address_file_path') and self.last_address_file_path and os.path.exists(self.last_address_file_path):
                # Call the specific method to load from last file
                self.load_address_from_last_file()
            else:
                # If no valid last path, just refresh to show the empty state message
                self.refresh_address_list() 
        except Exception as e:
            self.log_message(f"加载地址列表失败: {str(e)}", level="ERROR", exc_info=True)
            self.refresh_address_list() # Ensure empty state is shown on error
    
    def update_api_status_indicator(self, connected):
        if not hasattr(self, 'api_status_indicator') or self.api_status_indicator is None:
            return
        current_exchange_display_name = self.current_exchange_name if self.current_exchange_name else "API"
        if connected:
            self.api_status_indicator.setStyleSheet("background-color: #2ECC71; border-radius: 8px; border: 1px solid #27AE60;")
            self.api_status_indicator.setToolTip(f"{current_exchange_display_name} API已连接")
        else:
            self.api_status_indicator.setStyleSheet("background-color: #E74C3C; border-radius: 8px; border: 1px solid #C0392B;")
            self.api_status_indicator.setToolTip(f"{current_exchange_display_name} API未连接或连接失败")

    def _update_log_display(self, action, data):
        if action == "log":
            self.log_text.append(data)
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        elif action == "stop_withdrawal":
            self.stop_withdrawal()

    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
        try:
            current = int(value * self.total_rows / 100)
            total = self.total_rows
        except Exception:
            current = 0
            total = 0
        self.progress_label.setText(f"进度: {current}/{total}")

    def update_wait(self, value, text):
        self.wait_bar.setValue(value)
        self.wait_label.setText(text)
        
    def log_message(self, message, level="INFO", exc_info=False):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        log_entry = f"{timestamp} [{level.upper()}]: {message}"
        color_map = {"ERROR": "#E74C3C", "WARNING": "#F39C12", "SUCCESS": "#2ECC71", "CRITICAL": "#FF0000", "DEBUG": "#888888"}
        color = color_map.get(level.upper(), "#AAAAAA")
        if hasattr(self, 'show_full_addresses') and not self.show_full_addresses:
            log_entry = self._mask_addresses_in_text(log_entry)
        colored_entry = f'<span style="color:{color};">{log_entry}</span>'
        if hasattr(self, 'update_signal'):
            # Only update UI if the level is not DEBUG
            if level.strip().upper() != "DEBUG": # Use strip().upper() for robust check
                try:
                    # Corrected: Emit 'log' action and the HTML formatted colored_entry
                    self.update_signal.emit("log", colored_entry)
                except RuntimeError as e:
                    self.logger.error(f"Failed to update UI with log message: {e}", exc_info=True)
        
    def _mask_addresses_in_text(self, text):
        address_patterns = [
            r'(0x[a-fA-F0-9]{40})',
            r'([13][a-zA-Z0-9]{25,34}|bc1[a-zA-Z0-9]{25,90})',
            r'(T[a-zA-Z0-9]{33})',
            r'([1-9A-HJ-NP-Za-km-z]{32,44})'
        ]
        original_text = text
        for pattern in address_patterns:
            matches = list(re.finditer(pattern, original_text))
            temp_text = list(original_text)
            
            current_offset = 0
            for match in matches:
                original_addr = match.group(1)
                if '...' in original_addr:
                    continue
                    
                prefix = original_addr[:8]
                suffix = original_addr[-6:]
                masked_addr = f"{prefix}...{suffix}"
                
                start = match.start(1) + current_offset
                end = match.end(1) + current_offset
                
                temp_text[start:end] = list(masked_addr)
                current_offset += len(masked_addr) - len(original_addr)
            original_text = "".join(temp_text)
        return original_text

    def _load_config_and_initialize_api(self):
        """加载应用配置, 设置上次选择的交易所, 初始化主API连接, 并尝试初始化Binance作为价格数据源."""
        self.logger.info("开始加载配置文件和初始化API...")
        
        # Initialize price provider API to None/False before attempting
        self.price_provider_api = None
        self.binance_api_for_prices_connected = False
        
        try:
            if not os.path.exists(self.config_path):
                self.log_message("未找到配置文件，将创建默认配置。", level="INFO")
                self._create_default_config() 
            self.config.read(self.config_path, encoding='utf-8')
            if not self.config.sections(): 
                self.log_message("配置文件为空或无法解析，将创建并使用默认配置。", level="WARNING")
                self._create_default_config()
                self.config.read(self.config_path, encoding='utf-8') 
            self.log_message("配置文件加载/解析成功。", level="INFO")
            self._load_general_app_settings_from_config()

            # 尝试初始化 Binance API 作为价格数据源
            self.logger.info("尝试初始化Binance API作为价格数据源...")
            try:
                price_api_candidate = BinanceAPI(self.config, self.logger)
                connected, message = price_api_candidate.connect() # connect()应该返回 (bool, str)
                if connected:
                    self.price_provider_api = price_api_candidate
                    self.binance_api_for_prices_connected = True
                    self.logger.info(f"成功连接到Binance作为价格数据源: {message}")
                else:
                    self.logger.warning(f"无法连接到Binance作为价格数据源: {message}. USD估值可能不可用。")
            except Exception as e_price_api: # Catch any exception during Binance price API init
                self.logger.error(f"初始化Binance价格数据源时发生错误: {e_price_api}", exc_info=True)
                # self.binance_api_for_prices_connected remains False

            # 设置和初始化当前选择的交易所 (主操作API)
            default_exchange = list(self.EXCHANGES.keys())[0]
            last_selected_exchange = self.config.get('GENERAL', 'last_selected_exchange', fallback=default_exchange)
            if last_selected_exchange not in self.EXCHANGES:
                self.logger.warning(f"配置文件中的交易所 '{last_selected_exchange}' 无效，将使用默认交易所 '{default_exchange}'.")
                last_selected_exchange = default_exchange
            
            self.current_exchange_name = last_selected_exchange
            if hasattr(self, 'exchange_combo_toolbar'):
                self.exchange_combo_toolbar.blockSignals(True)
                self.exchange_combo_toolbar.setCurrentText(self.current_exchange_name)
                self.exchange_combo_toolbar.blockSignals(False)
            else:
                self.logger.error("工具栏交易所选择框 (exchange_combo_toolbar) 未初始化!")
            
            # 这个方法会设置 self.current_exchange_api
            self._initialize_api_for_exchange(self.current_exchange_name) 
            
            self.load_addresses_after_ui_ready()
            return True # Main API loading was wrapped in this try, so True if it reaches here
            
        except configparser.Error as e_cfg:
            self.log_message(f"读取配置文件时发生严重错误: {e_cfg}", level="CRITICAL", exc_info=True)
            # Fallthrough to generic error handling below is fine, or specific handling here
        except Exception as e_main:
            self.log_message(f"加载应用配置或初始化主API时发生未知严重错误: {e_main}", level="CRITICAL", exc_info=True)
        
        # Common failure path for main API or config loading issues
        self.update_api_status_indicator(False) 
        if hasattr(self, 'coin_combo'): self.coin_combo.setEnabled(False)
        if hasattr(self, 'network_combo'): self.network_combo.setEnabled(False)
        self.load_addresses_after_ui_ready() # Address loading doesn't depend on API state
        return False # Indicate failure of this overall method

    def _create_default_config(self):
        """创建一份默认的配置文件."""
        self.logger.info(f"正在创建默认配置文件于: {self.config_path}")
        default_cfg = ConfigParser()
        # Ensure sections are added before setting options in them
        default_cfg.add_section('GENERAL')
        default_cfg.set('GENERAL', 'last_selected_exchange', 'Binance')
        default_cfg.set('GENERAL', 'okx_simulated', 'False')
        default_cfg.set('GENERAL', 'last_address_file', '')
        # default_cfg.set('GENERAL', 'theme', 'Dark') # Theme handled by QSettings now or manually

        default_cfg.add_section('BINANCE')
        default_cfg.set('BINANCE', 'api_key', '')
        default_cfg.set('BINANCE', 'api_secret', '')

        default_cfg.add_section('OKX')
        default_cfg.set('OKX', 'api_key', '')
        default_cfg.set('OKX', 'api_secret', '')
        default_cfg.set('OKX', 'passphrase', '')
        
        # Kept for compatibility if old settings exist, but new apps might not need this section directly in main config
        default_cfg.add_section('WITHDRAWAL_PARAMS') # Renamed from WITHDRAWAL to avoid conflict if old GENERAL had it
        default_cfg.set('WITHDRAWAL_PARAMS', 'min_interval', '60')
        default_cfg.set('WITHDRAWAL_PARAMS', 'max_interval', '600')
        default_cfg.set('WITHDRAWAL_PARAMS', 'warning_threshold', '1000')
        default_cfg.set('WITHDRAWAL_PARAMS', 'enable_warning', 'True')
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                default_cfg.write(f)
            self.log_message("默认配置文件已创建。请通过「设置」配置API密钥。", level="WARNING")
        except IOError as e:
            self.log_message(f"创建默认配置文件失败: {e}", level="ERROR", exc_info=True)

    def _load_general_app_settings_from_config(self):
        """从配置中加载通用的应用设置 (非API密钥)."""
        if not self.config.sections() or not self.config.has_section('GENERAL'):
            self.logger.warning("配置文件中缺少GENERAL部分，部分常规设置可能不会加载。")
            return
        self.last_address_file_path = self.config.get('GENERAL', 'last_address_file', fallback='')
        wp_section = 'WITHDRAWAL_PARAMS'
        if self.config.has_section(wp_section):
            self.min_interval = self.config.getint(wp_section, 'min_interval', fallback=60)
            self.max_interval = self.config.getint(wp_section, 'max_interval', fallback=600)
            self.warning_threshold = self.config.getfloat(wp_section, 'warning_threshold', fallback=1000.0)
            self.enable_warning = self.config.getboolean(wp_section, 'enable_warning', fallback=True)
        else:
            self.logger.info(f"配置文件中未找到 '{wp_section}' 部分，将使用默认提现参数。")
            self.min_interval = 60
            self.max_interval = 600
            self.warning_threshold = 1000.0
            self.enable_warning = True
        self.logger.debug("常规应用配置已加载。")

    def _handle_exchange_change_from_toolbar(self, exchange_name: str):
        """处理工具栏中交易所选择的变化."""
        if not exchange_name or (exchange_name == self.current_exchange_name and self.current_exchange_api is not None):
            self.logger.debug(f"交易所选择 '{exchange_name}' 无变化或API已连接，不执行操作。")
            return
        self.log_message(f"交易所已选择: {exchange_name}", level="INFO")
        if self.config.has_section('GENERAL'):
            self.config.set('GENERAL', 'last_selected_exchange', exchange_name)
        else:
            # Re-indent these lines
            self.config.add_section('GENERAL')
            self.config.set('GENERAL', 'last_selected_exchange', exchange_name)
        try:
            with open(self.config_path, 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
            self.logger.info(f"已保存最后选择的交易所 '{exchange_name}' 到 config.ini")
        except IOError as e:
            self.log_message(f"无法保存最后选择的交易所到 config.ini: {e}", level="ERROR", exc_info=True)
        self._initialize_api_for_exchange(exchange_name)

    def _initialize_api_for_exchange(self, exchange_name: str):
        """初始化或切换到指定交易所的API实例."""
        self.log_message(f"正在为交易所 {exchange_name} 初始化API...", level="INFO")        
        if hasattr(self, 'status_label'): 
            self.status_label.setText(f"{exchange_name} - 正在连接...")
        self.update_api_status_indicator(False) 
        self._clear_exchange_specific_ui_elements() 
        
        # --- 开始改进的线程清理 ---
        # 在访问前检查线程对象是否存在且有效
        thread_to_clean = getattr(self, 'api_thread', None)
        if thread_to_clean is not None:
            try:
                if thread_to_clean.isRunning():
                    self.log_message("正在停止之前的API初始化线程...", level="DEBUG")
                    thread_to_clean.quit()
                    if not thread_to_clean.wait(5000):  # 增加等待时间到5秒
                        self.log_message("之前的API线程未能正常退出，可能导致问题。", level="WARNING")
                    else:
                        self.log_message("之前的API线程已停止。", level="DEBUG")
                else:
                     self.log_message("之前的API线程已结束或未运行。", level="DEBUG")
                
                # 请求删除旧线程和worker
                worker_to_delete = getattr(self, 'api_worker', None)
                if worker_to_delete:
                     worker_to_delete.deleteLater()
                thread_to_clean.deleteLater()
                 
            except RuntimeError: # 捕获对象已被删除的错误
                self.log_message("尝试清理API线程时出错：对象可能已被删除。", level="DEBUG")
            except Exception as e_clean: # 捕获其他潜在错误
                 self.log_message(f"清理API线程时发生未知错误: {e_clean}", level="ERROR")
                 
        self.api_thread = None # 显式设置None
        self.api_worker = None
        # --- 结束改进的线程清理 ---
            
        if self.current_exchange_api and hasattr(self.current_exchange_api, 'close'):
            try:
                self.current_exchange_api.close()
                self.log_message(f"已关闭之前的API实例 ({self.current_exchange_api.__class__.__name__}).", level="DEBUG")
            except Exception as e:
                self.log_message(f"关闭旧API实例时出错: {e}", level="ERROR", exc_info=True)
                
        self.current_exchange_api = None 
        self.current_exchange_name = exchange_name 
        api_class = self.EXCHANGES.get(exchange_name)
        if not api_class:
            self.log_message(f"错误: 未找到交易所 {exchange_name} 的API类定义。", level="CRITICAL")
            if hasattr(self, 'status_label'): self.status_label.setText(f"{exchange_name} - API类未找到")
            return
            
        # 读取最新配置
        self.config.read(self.config_path, encoding='utf-8')
        
        # 创建新的线程和工作器
        self.api_thread = QThread()
        # 将线程添加到引用存储列表 (可能不再需要，但暂时保留)
        if hasattr(self, 'thread_references'): self.thread_references.append(self.api_thread)
        
        self.api_worker = ApiInitWorker(exchange_name, api_class, self.config, self.logger)
        self.api_worker.moveToThread(self.api_thread)
        
        # 连接信号
        self.api_thread.started.connect(self.api_worker.run)
        self.api_worker.finished.connect(self._handle_api_init_result)
        self.api_worker.log_message.connect(lambda msg, level: self.log_message(msg, level=level))
        
        # --- 改进的清理连接 ---
        # 当worker完成时，请求线程退出
        self.api_worker.finished.connect(self.api_thread.quit)
        # 当线程结束后，请求删除worker和线程自身
        self.api_thread.finished.connect(self.api_worker.deleteLater)
        self.api_thread.finished.connect(self.api_thread.deleteLater)
        # --- 结束改进的清理连接 ---
        
        # 启动线程
        self.api_thread.start()
        
    def _handle_api_init_result(self, connected, message, api_instance, exchange_name):
        """处理API初始化结果"""
        if connected:
            self.current_exchange_api = api_instance
            self.log_message(f"成功连接到 {exchange_name}: {message}", level="SUCCESS")
            self.update_api_status_indicator(True)
            if hasattr(self, 'status_label'): self.status_label.setText(f"{exchange_name} - 已连接")
            self._perform_full_ui_refresh() 
        else:
            self.log_message(f"连接到 {exchange_name} 失败: {message}", level="ERROR")
            self.update_api_status_indicator(False)
            if hasattr(self, 'status_label'): 
                self.status_label.setText(f"{exchange_name} - 连接失败: {message[:100]}")
            self.current_exchange_api = None

    def _clear_exchange_specific_ui_elements(self):
        """清除UI上依赖于特定交易所API数据的内容 (币种, 网络, 余额等)."""
        self.logger.debug("正在清除交易所特定的UI元素...")
        if hasattr(self, 'coin_combo'): 
            self.coin_combo.blockSignals(True)
            self.coin_combo.clear()
            self.coin_combo.setEnabled(False)
            self.coin_combo.blockSignals(False)
        if hasattr(self, 'network_combo'): 
            self.network_combo.blockSignals(True)
            self.network_combo.clear()
            self.network_combo.setEnabled(False)
            self.network_combo.blockSignals(False)
        if hasattr(self, 'balance_label'): self.balance_label.setText("余额: N/A")
        if hasattr(self, 'fee_label'): self.fee_label.setText("手续费: N/A")    
        if hasattr(self, 'price_label'): self.price_label.setText("价格: N/A")     
        if hasattr(self, 'min_amount_usd'): self.min_amount_usd.setText("≈$-.--")
        if hasattr(self, 'max_amount_usd'): self.max_amount_usd.setText("≈$-.--")
        
        # Indent these lines
        self.supported_coins_for_current_exchange = []
        self.networks_cache = {}
        self.price_cache = {}
        # Clear any displayed API error messages related to coin/network data in status bar or log if needed here.
        self.log_message("交易所特定UI元素已清除。", level="DEBUG")

    def _perform_full_ui_refresh(self):
        """在成功连接到API后, 全面刷新和填充UI元素.
           币种 -> (触发) 网络 -> 余额 -> 价格 -> 手续费.
        """
        if not self.current_exchange_api:
            self.log_message("UI刷新失败: 当前交易所API未设置。", level="WARNING")
            self._clear_exchange_specific_ui_elements() # Ensure UI is cleared if API is gone
            return
        
        self.log_message(f"正在为 {self.current_exchange_name} 刷新UI数据...", level="INFO")
        
        # 1. Populate Coins
        # This part will trigger a cascade of updates if successful (on_coin_selected)
        try:
            self.log_message(f"向 {self.current_exchange_name} API 请求可交易币种...", level="DEBUG")
            # Ensure coin_combo exists before trying to use it
            if not hasattr(self, 'coin_combo'):
                self.log_message("UI控件 (coin_combo) 未初始化，无法填充币种。", level="ERROR")
                return
                
            all_tradable_coins = self.current_exchange_api.get_all_tradable_coins()
            # 筛选币种列表
            filtered_coins = [coin for coin in all_tradable_coins if coin in self.ALLOWED_COINS]
            
            self.supported_coins_for_current_exchange = filtered_coins # 更新支持的币种列表为筛选后的
            
            self.coin_combo.blockSignals(True)
            self.coin_combo.clear()
            if self.supported_coins_for_current_exchange:
                self.coin_combo.addItems(self.supported_coins_for_current_exchange)
                self.coin_combo.setEnabled(True)
                self.log_message(f"为 {self.current_exchange_name} 加载并筛选了 {len(self.supported_coins_for_current_exchange)} 个指定币种: {', '.join(self.supported_coins_for_current_exchange)}。", level="INFO")
                if self.coin_combo.count() > 0:
                    # Try to restore last selected coin for this exchange if applicable, or default to first
                    # This is a more advanced feature, for now, just select the first one.
                    self.coin_combo.setCurrentIndex(0) 
            else:
                self.log_message(f"{self.current_exchange_name} 未返回可交易币种。", level="WARNING")
                self.coin_combo.setEnabled(False)
                self._clear_networks_balance_fee_price_ui() # Clear dependent UI if no coins
            self.coin_combo.blockSignals(False)
            
            # Manually trigger the handler for the newly set current coin, 
            # as setCurrentIndex(0) might not fire currentTextChanged if it was already 0 (though unlikely after clear).
            if self.coin_combo.count() > 0:
                 self.update_networks_on_coin_change(self.coin_combo.currentText())
            elif not self.supported_coins_for_current_exchange: # If list is empty
                 self._clear_networks_balance_fee_price_ui()
            
        except Exception as e:
            self.log_message(f"获取 {self.current_exchange_name} 币种列表失败: {e}", level="ERROR", exc_info=True)
            if hasattr(self, 'coin_combo'): self.coin_combo.clear(); self.coin_combo.setEnabled(False)
            self._clear_networks_balance_fee_price_ui()
    
    def _clear_networks_balance_fee_price_ui(self):
        """Helper to clear network, balance, fee, and price UI elements."""
        if hasattr(self, 'network_combo'): self.network_combo.clear(); self.network_combo.setEnabled(False)
        if hasattr(self, 'balance_label'): self.balance_label.setText("余额: N/A")
        if hasattr(self, 'fee_label'): self.fee_label.setText("手续费: N/A")
        if hasattr(self, 'price_label'): self.price_label.setText("价格: N/A")
        if hasattr(self, 'min_amount_usd'): self.min_amount_usd.setText("≈$-.--")
        if hasattr(self, 'max_amount_usd'): self.max_amount_usd.setText("≈$-.--")
        self.logger.debug("网络、余额、手续费和价格相关UI已清除。")

    def config_updated_and_reconnect(self, resetting=False):
        """当设置对话框保存后调用此方法, 重新加载配置并重新初始化/连接API."""
        self.log_message("配置已更新或重置，正在重新应用...", level="INFO")
        
        # --- 开始改进的线程清理 ---
        # 清理API线程
        thread_to_clean_api = getattr(self, 'api_thread', None)
        if thread_to_clean_api is not None:
            try:
                if thread_to_clean_api.isRunning():
                    self.log_message("等待API初始化线程完成(配置更新)...", level="DEBUG")
                    thread_to_clean_api.quit()
                    if not thread_to_clean_api.wait(5000): 
                        self.log_message("API线程(配置更新)未能正常退出。", level="WARNING")
                worker_to_delete_api = getattr(self, 'api_worker', None)
                if worker_to_delete_api: worker_to_delete_api.deleteLater() 
                thread_to_clean_api.deleteLater()
            except RuntimeError:
                self.log_message("清理API线程(配置更新)时出错：对象可能已被删除。", level="DEBUG")
            except Exception as e_clean_api:
                 self.log_message(f"清理API线程(配置更新)时发生未知错误: {e_clean_api}", level="ERROR")
        self.api_thread = None
        self.api_worker = None
            
        # 清理余额线程
        thread_to_clean_bal = getattr(self, 'balance_thread', None)
        if thread_to_clean_bal is not None:
            try:
                if thread_to_clean_bal.isRunning():
                    self.log_message("等待余额查询线程完成(配置更新)...", level="DEBUG")
                    thread_to_clean_bal.quit()
                    if not thread_to_clean_bal.wait(3000): 
                        self.log_message("余额线程(配置更新)未能正常退出。", level="WARNING")
                worker_to_delete_bal = getattr(self, 'balance_worker', None)
                if worker_to_delete_bal: worker_to_delete_bal.deleteLater()
                thread_to_clean_bal.deleteLater()
            except RuntimeError:
                self.log_message("清理余额线程(配置更新)时出错：对象可能已被删除。", level="DEBUG")
            except Exception as e_clean_bal:
                 self.log_message(f"清理余额线程(配置更新)时发生未知错误: {e_clean_bal}", level="ERROR")
        self.balance_thread = None
        self.balance_worker = None
        # --- 结束改进的线程清理 ---
        
        self.config = ConfigParser()
        if os.path.exists(self.config_path):
            self.config.read(self.config_path, encoding='utf-8')
            self._load_general_app_settings_from_config() 
        else:
            self.log_message("配置文件丢失，无法在配置更新后重新加载。尝试创建默认配置。", level="ERROR", exc_info=True)
            self._create_default_config() 
            self.config.read(self.config_path, encoding='utf-8')
            
        current_selected_exchange_in_toolbar = self.current_exchange_name 
        if hasattr(self, 'exchange_combo_toolbar'):
             current_name_from_ui = self.exchange_combo_toolbar.currentText()
             if current_name_from_ui and current_name_from_ui in self.EXCHANGES:
                 current_selected_exchange_in_toolbar = current_name_from_ui
        if not current_selected_exchange_in_toolbar or current_selected_exchange_in_toolbar not in self.EXCHANGES:
            self.logger.warning("配置更新后无法确定当前交易所，将使用默认交易所。")
            current_selected_exchange_in_toolbar = list(self.EXCHANGES.keys())[0]
            if hasattr(self, 'exchange_combo_toolbar'): 
                self.exchange_combo_toolbar.blockSignals(True)
                self.exchange_combo_toolbar.setCurrentText(current_selected_exchange_in_toolbar)
                self.exchange_combo_toolbar.blockSignals(False)
        self.log_message(f"将为交易所 {current_selected_exchange_in_toolbar} 应用新配置并重新连接。", level="INFO")
        self._initialize_api_for_exchange(current_selected_exchange_in_toolbar)
        if resetting: 
            self.log_message("配置已重置。部分功能可能需要重新配置API密钥。", level="INFO")
            if not (self.current_exchange_api and hasattr(self.current_exchange_api, 'client') and self.current_exchange_api.client is not None):
                 self._clear_exchange_specific_ui_elements()
                 self.update_api_status_indicator(False)

    def show_history(self):
        """处理工具栏 "历史记录" 按钮点击事件. \n           获取历史记录并通过富文本格式在可滚动的自定义对话框中显示。
        """        
        if not self.current_exchange_api:
            self.log_message("无法获取提币历史：API未连接。", level="WARNING")
            QMessageBox.warning(self, "API错误", "交易所API未连接。")
            return

        selected_coin = self.coin_combo.currentText() if hasattr(self, 'coin_combo') and self.coin_combo.currentText() else None
        
        # 使用更简单的方式构造 log_prefix，避免复杂的f-string
        log_prefix = self.current_exchange_name
        if selected_coin:
            log_prefix += f" - {selected_coin}"
            
        self.log_message(f"正在为 {log_prefix} 获取提币历史...", level="INFO")

        try:
            history_records = self.current_exchange_api.get_withdrawal_history(coin=selected_coin)

            if not history_records:
                self.log_message(f"未找到 {log_prefix} 的提币历史记录。", level="INFO")
                QMessageBox.information(self, "历史记录", f"未找到 {log_prefix} 的相关提币历史记录。")
                return

            self.log_message(f"成功获取 {len(history_records)} 条 {log_prefix} 提币历史记录。", level="INFO")
            
            # 定义颜色 (保持与之前一致)
            color_time = "#85C1E9"    # 淡蓝色
            color_amount = "#F5B041"  # 橙色
            color_coin = "#58D68D"    # 绿色
            color_address = "#D2B4DE" # 淡紫色
            color_status_ok = "#2ECC71" # 亮绿色 (成功状态)
            color_status_fail = "#E74C3C" # 红色 (失败状态)
            color_status_pending = "#F7DC6F" # 黄色 (处理中状态)
            color_txid = "#AAB7B8"     # 灰色

            html_content_lines = []
            html_content_lines.append(f"<p style='font-weight:bold; font-size:11pt;'>提币历史 ({log_prefix}):</p>")
            # 使用单引号定义外部字符串，以避免与内部双引号冲突
            html_content_lines.append('<div style="font-family:\"Courier New\", Courier, monospace; font-size:9pt;">') # Start main div 
            
            for i, record in enumerate(history_records):
                self.logger.debug(f"历史记录 #{i+1} ({log_prefix}): {record}")
                
                apply_time = record.get('applyTime', 'N/A')
                status_text = record.get('status_text', 'N/A')
                coin_rec = record.get('coin', 'N/A')
                amt_rec = record.get('amount', 'N/A')
                addr_rec = self._mask_addresses_in_text(record.get('address', 'N/A')) 
                txid_rec = record.get('txId', 'N/A')
                txid_display = txid_rec[:20] + "..." if txid_rec and len(txid_rec) > 20 else txid_rec
                if not txid_rec or txid_rec == 'N/A': txid_display = "(无TXID)"
                
                status_color = color_txid # 默认灰色
                if "成功" in status_text or "completed" in status_text.lower():
                    status_color = color_status_ok
                elif "失败" in status_text or "failed" in status_text.lower() or "已取消" in status_text:
                    status_color = color_status_fail
                elif "处理中" in status_text or "pending" in status_text.lower() or "等待" in status_text:
                    status_color = color_status_pending

                line_html = f"""
                <div style='margin-bottom: 8px; padding-bottom: 5px; border-bottom: 1px solid #444;'>
                    {i+1}. 
                    <span style='color:{color_time};'>时间:</span> {apply_time} <br>
                    &nbsp;&nbsp;&nbsp;<span style='color:{color_status_ok};'>状态:</span> <span style='color:{status_color};'>{status_text}</span> <br>
                    &nbsp;&nbsp;&nbsp;<span style='color:{color_coin};'>币种:</span> {coin_rec}, 
                    <span style='color:{color_amount};'>数量:</span> {amt_rec} <br>
                    &nbsp;&nbsp;&nbsp;<span style='color:{color_address};'>地址:</span> {addr_rec} <br>
                    &nbsp;&nbsp;&nbsp;<span style='color:{color_txid};'>TxID:</span> {txid_display}
                </div>
                """
                html_content_lines.append(line_html)
            
            html_content_lines.append("</div>") # Close main div
            final_html = "\n".join(html_content_lines)

            # 使用新的 HistoryDialog
            history_dialog = HistoryDialog(title=f"{log_prefix} 提币历史", parent=self)
            history_dialog.setContent(final_html)
            history_dialog.exec() # 显示对话框

        except Exception as e:
            self.log_message(f"获取或显示 {log_prefix} 提币历史时出错: {e}", level="ERROR", exc_info=True)
            QMessageBox.critical(self, "错误", f"获取提币历史记录失败: {e}")

    def start_withdrawal(self):
        """处理工具栏 "开始提币" 按钮点击事件.\n           获取参数, 验证输入, 并启动后台提币线程。
        """
        if self.running:
            self.log_message("提币流程已经在运行中。", level="INFO")
            QMessageBox.information(self, "提示", "提币流程已经在运行中。")
            return

        self.log_message("开始提币流程验证...", level="INFO")

        # 1. 检查 API 连接
        if not self.current_exchange_api:
            self.log_message("无法开始提币：API未连接。", level="WARNING")
            QMessageBox.warning(self, "API错误", "交易所API未连接，请先选择交易所并确保API已配置连接。")
            return
            
        # 2. 检查地址列表
        if not self.current_addresses:
            self.log_message("无法开始提币：地址列表为空。", level="WARNING")
            QMessageBox.warning(self, "无地址", "请先导入提币地址列表。")
            return

        # 3. 获取并验证界面参数
        try:
            selected_coin = self.coin_combo.currentText()
            selected_network = self.network_combo.currentText()
            min_amount_str = self.min_amount_entry.text().strip()
            max_amount_str = self.max_amount_entry.text().strip()
            start_index_str = self.start_addr_entry.text().strip()
            end_index_str = self.end_addr_entry.text().strip()

            if not selected_coin:
                raise ValueError("未选择提币币种")
            if not selected_network:
                raise ValueError("未选择提币网络")
            
            min_amount = Decimal(min_amount_str) if min_amount_str else Decimal('0')
            max_amount = Decimal(max_amount_str) if max_amount_str else Decimal('0')
            
            if min_amount <= 0 or max_amount <= 0:
                raise ValueError("提币数量必须大于0")
            if min_amount > max_amount:
                raise ValueError("最小数量不能大于最大数量")

            start_index = int(start_index_str) if start_index_str else 1
            end_index = int(end_index_str) if end_index_str else len(self.current_addresses)

            if start_index < 1:
                raise ValueError("起始序号必须大于等于1")
            if end_index > len(self.current_addresses):
                 raise ValueError(f"结束序号不能超过地址总数 ({len(self.current_addresses)})")
            if start_index > end_index:
                raise ValueError("起始序号不能大于结束序号")
                
        except ValueError as ve:
            self.log_message(f"参数验证失败: {ve}", level="ERROR")
            QMessageBox.warning(self, "参数错误", f"输入参数无效: {ve}")
            return
        except Exception as e:
            self.log_message(f"获取或验证参数时发生未知错误: {e}", level="ERROR", exc_info=True)
            QMessageBox.critical(self, "错误", f"处理参数时出错: {e}")
            return

        # 4. 确认参数并准备启动
        self.log_message(f"参数验证通过: 币种={selected_coin}, 网络={selected_network}, "
                         f"数量范围=[{min_amount}, {max_amount}], 地址范围=[{start_index}, {end_index}]", level="INFO")
                         
        # 更新UI状态
        self.running = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.log_message("提币流程已启动。", level="SUCCESS")
        
        # 设置总行数
        self.total_rows = end_index - start_index + 1
        
        # 5. 启动后台线程
        # 将地址序号调整为0-based index给线程使用
        thread_start_index = start_index - 1 
        thread_end_index = end_index - 1 # 包含结束索引
        
        # 创建并启动线程
        # 注意：传递 Decimal 对象到线程是安全的
        self.withdrawal_thread = threading.Thread(
            target=self._process_withdrawals,
            args=(
                selected_coin,
                selected_network,
                min_amount, 
                max_amount,
                thread_start_index, 
                thread_end_index,
                self.min_interval, # 从配置加载
                self.max_interval  # 从配置加载
            ),
            daemon=True # 设置为守护线程，主程序退出时线程也退出
        )
        self.withdrawal_thread.start()

    def stop_withdrawal(self):
        """处理工具栏 "停止" 按钮点击事件."""
        if self.running:
            self.running = False
            # 通常在这里还会设置一个线程停止的事件或标志，
            # 以便实际的提币循环能够优雅地退出。
            self.log_message("用户请求停止提币流程。", level="INFO")
            if hasattr(self, 'start_button'): self.start_button.setEnabled(True)
            if hasattr(self, 'stop_button'): self.stop_button.setEnabled(False)
            # 重置进度条和等待条 (虽然线程finally里也做了，这里再做一次确保UI更新)
            self.update_progress(0)  # Reset progress
            self.update_wait(0, "等待: 0秒") # Reset wait
            QMessageBox.information(self, "操作停止", "提币流程已请求停止。")
        else:
            self.log_message("没有正在运行的提币流程可以停止。", level="DEBUG")

    def import_address_list(self):
        """处理工具栏 "导入地址" 按钮点击事件.
           允许用户选择一个文件 (如 CSV 或 Excel) 来导入提币地址列表。
        """
        self.log_message("导入地址按钮被点击...", level="INFO")
        
        # 使用 QFileDialog 让用户选择文件
        # 我们在 __init__ 中保存了 last_address_file_path，可以用它作为默认目录
        default_dir = os.path.dirname(self.last_address_file_path) if self.last_address_file_path else os.path.expanduser("~")
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择地址文件",
            default_dir, # 用户上次打开的目录或用户主目录
            "表格文件 (*.csv *.xlsx);;所有文件 (*)"
        )
        
        if file_path:
            self.log_message(f"用户选择的文件路径: {file_path}", level="INFO")
            # 调用新的辅助方法来加载
            success, message = self._load_addresses_from_file(file_path)
            
            if success:
                self.last_address_file_path = file_path # 更新最后路径
                self.refresh_address_list() # 刷新UI显示
                self.save_app_config() # 保存最后路径到配置文件
                QMessageBox.information(self, "导入成功", message)
            else:
                # 加载失败，显示错误信息
                QMessageBox.warning(self, "导入失败", message)
                # 失败时不更新 last_address_file_path, 也不保存配置
        else: # Corrected indent for else corresponding to 'if file_path:'
            self.log_message("用户取消了文件选择。", level="DEBUG")

    def validate_addresses(self):
        """处理工具栏 "验证地址" 按钮点击事件.
           对当前导入的地址列表进行格式验证 (处理字典列表)。
        """
        self.log_message("验证地址按钮被点击...", level="INFO")

        if not hasattr(self, 'current_addresses') or not self.current_addresses:
            self.log_message("没有可供验证的地址，请先导入地址列表。", level="WARNING")
            QMessageBox.warning(self, "无地址", "请先导入提币地址列表。")
            return
                
        if not hasattr(self, 'address_validator') or self.address_validator is None:
            self.log_message("地址验证器未初始化，无法验证地址。", level="ERROR")
            QMessageBox.critical(self, "内部错误", "地址验证器未成功初始化，请重启应用或检查日志。")
            return
                
        selected_coin = self.coin_combo.currentText() if hasattr(self, 'coin_combo') else None
        if not selected_coin:
            self.log_message("未选择币种，无法确定地址验证规则。", level="WARNING")
            QMessageBox.warning(self, "未选币种", "请先在左侧选择一个提币币种，以便进行针对性的地址验证。")
            return
            
        # 提取地址列表用于验证
        addresses_to_validate = [item.get('address', '') for item in self.current_addresses]
        
        self.log_message(f"准备使用币种 {selected_coin} 规则验证 {len(addresses_to_validate)} 个地址...", level="DEBUG")
        
        try:
            all_valid, invalid_addresses_details = AddressValidator.batch_validate_addresses(
                coin_type=selected_coin, 
                addresses=addresses_to_validate # 传递纯地址列表
            )
            
            total_processed = len(addresses_to_validate)
            summary_message = ""
            if all_valid:
                summary_message = f"所有 {total_processed} 个地址均通过 {selected_coin} 格式验证。"
                self.log_message(summary_message, level="SUCCESS")
            else:
                summary_message = f"在 {total_processed} 个地址中，发现 {len(invalid_addresses_details)} 个无效的 {selected_coin} 地址。"
                self.log_message(summary_message, level="WARNING")
                # 注意：这里的 detail['address'] 仍然是原始地址字符串
                # invalid_addresses_details 列表中的 'index' 对应原始地址列表的 1-based 索引
                for detail in invalid_addresses_details:
                    self.logger.warning(f"  无效地址 #{detail['index']}: '{detail['address']}', 原因: {detail['error']}")
            
            # 通过信号将结果发送给UI处理方法
            # show_validation_results 接收的 invalid_details 结构不变
            self.validation_results_signal.emit(summary_message, invalid_addresses_details, total_processed)
            
        except Exception as e_validate:
            error_msg = f"批量验证地址时发生意外错误: {e_validate}"
            self.log_message(error_msg, level="CRITICAL", exc_info=True)
            QMessageBox.critical(self, "验证出错", f"{error_msg}\n详情请查看日志。")

    def toggle_address_display(self):
        """切换地址列表的显示方式 (完整/打码) 并刷新列表。"""
        self.show_full_addresses = not getattr(self, 'show_full_addresses', False)
        self.logger.debug(f"地址显示模式切换为: {'完整' if self.show_full_addresses else '打码'}")
        
        if hasattr(self, 'toggle_address_btn'):
            self.toggle_address_btn.setText("隐藏" if self.show_full_addresses else "显示")
            self.toggle_address_btn.setChecked(self.show_full_addresses)
            
        self.refresh_address_list() # 重新加载并根据新的显示模式格式化地址

    def show_validation_results(self, summary_message: str, invalid_details: list, total_processed: int):
        """显示地址验证结果。
        由 validation_results_signal 信号触发。
        
        参数:
            summary_message (str): 验证结果的简短摘要。
            invalid_details (list): 包含无效地址及其错误信息的字典列表。
                                     每个字典例如: {'index': 1, 'address': 'xxx', 'error': 'reason'}
            total_processed (int): 本次验证的总地址数量。
        """
        self.log_message(f"接收到地址验证结果: {summary_message}", level="INFO")
        self.logger.debug(f"总共处理地址: {total_processed}, 无效地址详情: {invalid_details}")

        if not invalid_details:
            QMessageBox.information(self, "地址验证完成", 
                                    f"{summary_message}\n所有 {total_processed} 个地址均有效。")
        else:
            detailed_errors = "发现以下无效地址:\n\n"
            for item in invalid_details[:10]: # 最多显示前10个的详情
                detailed_errors += f"行 {item['index']}: 地址 '{item['address'][:10]}...' - 原因: {item['error']}\n"
            if len(invalid_details) > 10:
                detailed_errors += f"\n...还有 {len(invalid_details) - 10} 个其他无效地址 (详情请查看日志)。"
            
            # 弹出一个带有详细信息的更复杂对话框可能更好，但暂时用 QMessageBox
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("地址验证结果")
            msg_box.setText(f"{summary_message}\n在 {total_processed} 个地址中发现 {len(invalid_details)} 个无效地址。")
            msg_box.setDetailedText(detailed_errors)
            msg_box.exec()

        # TODO: 未来可以考虑用一个专门的表格对话框来更清晰地展示大量错误

    def _show_withdrawal_confirm_dialog(self, coin: str, network: str, amount: Decimal, address: str, memo: str | None, is_large_withdrawal: bool):
        """显示提币确认对话框。
        由 confirm_withdrawal_signal 信号触发。
        Amount is Decimal.
        """
        self.logger.info(f"请求用户确认提币: {amount} {coin} 到 {address[:10]}... (网络: {network}){' Memo: ' + str(memo) if memo else ''}")
        
        title = "提币确认"
        
        # Construct the message string safely using a list of parts
        message_parts = []
        message_parts.append(f"请确认以下提币操作:\n\n")
        message_parts.append(f"币种: {coin}\n")
        message_parts.append(f"网络: {network}\n")
        # Format Decimal amount to 8 decimal places for display
        message_parts.append(f"数量: {amount:.8f} {coin}\n") 
        message_parts.append(f"地址: {address}\n")
        
        if memo:
            message_parts.append(f"Memo/Tag: {str(memo)}\n")

        if is_large_withdrawal:
            title = "大额提币确认"
            message_parts.append("\n<span style='color:red;'>警告: 这是一笔大额提币操作！</span>\n")

        message_parts.append("\n您确定要执行此提币操作吗？")
        message = "".join(message_parts)

        # Create a QMessageBox instance
        msg_box = QMessageBox(self) # Parent to self
        msg_box.setWindowTitle(title)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setTextFormat(Qt.TextFormat.RichText)  # Enable Rich Text for HTML
        msg_box.setText(message)

        # Configure buttons: "确认" (Yes) and "取消" (Cancel)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        
        button_yes = msg_box.button(QMessageBox.StandardButton.Yes)
        if button_yes: # Defensive check
            button_yes.setText("确认")

        button_cancel = msg_box.button(QMessageBox.StandardButton.Cancel)
        if button_cancel: # Defensive check
            button_cancel.setText("取消")
            msg_box.setDefaultButton(button_cancel) # Make "取消" default

        # Execute the dialog and get the standard button clicked
        clicked_std_button = msg_box.exec()

        user_confirmed = False
        if clicked_std_button == QMessageBox.StandardButton.Yes:
            user_confirmed = True
            self.log_message("用户已确认提币。", level="INFO")
        else: 
            user_confirmed = False
            if clicked_std_button == QMessageBox.StandardButton.Cancel:
                self.log_message("用户已取消提币 (点击'取消'按钮)。", level="INFO")
            else: # Dialog closed via 'X', Esc, or other non-button action
                self.log_message("用户关闭或以其他方式取消了提币确认对话框。", level="INFO")
        
        # Emit the result of user's decision
        self.withdrawal_confirmation_result.emit(user_confirmed, is_large_withdrawal)

    def _handle_withdrawal_confirmation(self, user_confirmed: bool, is_large_withdrawal: bool):
        """处理用户对单笔提币的确认结果。
        由 withdrawal_confirmation_result 信号触发。
        """
        self.logger.debug(f"收到提币确认结果: 用户确认={user_confirmed}, 是否大额={is_large_withdrawal}")

        # 这个方法的核心是将用户的决定传递回正在等待的提币处理逻辑（通常在另一个线程中）。
        # 这通常通过线程同步原语（如 Event, Condition）或队列来实现。

        # 示例逻辑:
        # if hasattr(self, 'withdrawal_thread_confirm_event') and hasattr(self, 'user_agreed_to_this_withdrawal'):
        #     self.user_agreed_to_this_withdrawal = user_confirmed
        #     self.withdrawal_thread_confirm_event.set() # 通知提币线程可以继续处理
        # else:
        #     self.logger.error("无法将用户确认结果传递给提币线程：同步对象未找到。")

        if is_large_withdrawal and not self.large_withdrawal_apply_to_all:
            # 这是针对单次大额提币的确认，且用户没有选择"应用于所有"
            # 如果是第一次大额提币的确认，且用户选择了"应用于所有"，则设置相关标志
            # 这个更复杂的逻辑（询问是否应用到所有）应该在 _show_withdrawal_confirm_dialog 中首次触发，或在提币主循环中管理
            pass # 暂时不处理"应用于所有"的逻辑，假设它由提币循环管理
        
        if not user_confirmed:
            self.log_message("用户未确认该笔提币，操作将跳过或中止。", level="WARNING")
            # 提币线程在收到事件并检查 self.user_agreed_to_this_withdrawal 后会知道跳过
        else:
            self.log_message("用户已确认，提币将继续（如果线程正在等待）。", level="INFO")

        # TODO: 实现与提币线程的同步机制，将 user_confirmed 的结果传递过去。
        # TODO: 如果是大额提币，并且是第一次，可能需要在这里或提币循环中处理"应用于所有"的逻辑，
        #       并相应设置 self.large_withdrawal_apply_to_all 和 self.large_withdrawal_decision。
        self.user_agreed_to_this_withdrawal = user_confirmed
        self.withdrawal_confirm_event.set()
        self.logger.info(f"_handle_withdrawal_confirmation: user_confirmed={user_confirmed}, event set.")

    def _process_withdrawals(self, coin, network, min_amount, max_amount, 
                             start_idx, end_idx, min_interval, max_interval):
        """后台提币处理线程 (处理带标签地址)."""
        self.log_message(f"提币线程开始: 处理地址索引 {start_idx} 到 {end_idx} ({coin} on {network})", level="INFO")
        total_addresses_in_range = end_idx - start_idx + 1
        processed_count = 0
        
        # --- 获取手续费和精度 --- 
        fee_decimal = Decimal('0')
        actual_precision = 8 # 先设置一个默认精度
        self.log_message(f"获取 {coin}-{network} 的提现手续费和精度...", level="DEBUG")
        try:
            # 获取手续费
            fee_info = self.current_exchange_api.get_withdrawal_fee(coin, network)
            if fee_info is not None:
                if isinstance(fee_info, dict):
                    fee_str = fee_info.get('fee')
                elif isinstance(fee_info, (str, float, int)):
                    fee_str = str(fee_info)
                else:
                    fee_str = None
                
                if fee_str: # Example check if fee_str was derived
                    fee_decimal = Decimal(fee_str)
                    self.log_message(f"获取到提币手续费: {fee_decimal} {coin}", level="INFO")
                else:
                     self.log_message(f"无法解析或获取 {coin}-{network} 的手续费信息，将使用 0。", level="WARNING")

            # 获取实际提现精度
            precision_from_api = self.current_exchange_api.get_withdraw_precision(coin, network)
            if precision_from_api is not None:
                actual_precision = precision_from_api
                self.log_message(f"获取到 {coin}-{network} 的实际提现精度: {actual_precision} 位小数", level="INFO")
            else:
                # 如果API未返回精度, 使用默认值并警告
                actual_precision = 6 # 改为更保守的默认值 6
                self.log_message(f"无法从API获取 {coin}-{network} 的提现精度，将使用默认值: {actual_precision} 位小数", level="WARNING")

        except Exception as e_fee_prec:
            self.log_message(f"获取手续费或精度时出错: {e_fee_prec}，将使用默认手续费0和默认精度{actual_precision}。", level="ERROR")
            fee_decimal = Decimal('0') # Ensure fee is 0 on error
            # actual_precision remains the default set earlier (or 6 if set above)
            
        # --- 预获取USD价格用于大额检查 (如果需要) ---
        usd_price = None
        if self.enable_warning and self.price_provider_api and self.binance_api_for_prices_connected:
            try:
                binance_symbol = f"{coin.upper()}USDT"
                price_str = self.price_provider_api.get_symbol_ticker(symbol=binance_symbol)
                if price_str:
                    usd_price = Decimal(price_str)
                    self.log_message(f"获取到 {coin} 的USD价格: {usd_price} (用于大额检查)", level="DEBUG")
            except Exception as e_price:
                self.log_message(f"无法获取 {coin} 的USD价格进行大额检查: {e_price}", level="WARNING")

        # --- 开始循环处理地址 ---
        try:
            for i in range(start_idx, end_idx + 1):
                if not self.running: 
                    self.log_message("提币线程收到停止信号，正在退出...", level="INFO")
                    break
                
                # 获取当前地址信息 (字典)
                current_address_info = self.current_addresses[i]
                addr = current_address_info.get('address')
                label = current_address_info.get('label') # 可能为 None
                
                if not addr: # 如果地址为空，则跳过
                    self.log_message(f"地址索引 {i+1} 的地址为空，跳过。", level="WARNING")
                    processed_count += 1
                    continue
                
                address_display_index = i + 1
                self.log_message(f"[{address_display_index}/{total_addresses_in_range}] 处理地址: {label + ' (' + self._mask_addresses_in_text(addr) + ')' if label else self._mask_addresses_in_text(addr)}...", level="DEBUG")
                
                # --- 1. 生成随机数量并处理精度 ---
                try:
                    random_amount_raw = Decimal(random.uniform(float(min_amount), float(max_amount)))
                    # 根据 *实际获取或默认的* 精度进行截断 (向下取整)
                    quantizer = Decimal('1e-' + str(actual_precision))
                    random_amount_quantized = random_amount_raw.quantize(quantizer, rounding=ROUND_DOWN)
                    self.log_message(f"  -> 计划提币数量 (原始): {random_amount_raw:.18f} {coin}", level="DEBUG")
                    self.log_message(f"  -> 计划提币数量 (量化到 {actual_precision} 位小数): {random_amount_quantized} {coin}", level="DEBUG")
                    
                    if random_amount_quantized <= 0:
                         self.log_message(f"  -> 生成的提币数量过小 ({random_amount_quantized})，跳过此地址。", level="WARNING")
                         processed_count += 1 # 算作处理过
                         continue
                except Exception as e_amount:
                    self.log_message(f"生成或处理提币数量时出错: {e_amount}，跳过此地址 {address_display_index}", level="ERROR")
                    processed_count += 1
                    continue

                # --- 2. 大额提币检查 (应在余额检查之前) ---
                if self.enable_warning and usd_price is not None:
                    try:
                        usd_value = random_amount_quantized * usd_price
                        if usd_value >= Decimal(str(self.warning_threshold)):
                            self.log_message(f"警告：地址 {address_display_index} 的提币金额 ${usd_value:.2f} 达到或超过阈值 ${self.warning_threshold:.2f}", level="WARNING")
                            
                            # 发出信号请求用户确认
                            self.confirm_withdrawal_signal.emit(coin, network, random_amount_quantized, addr, None, True)
                            
                            # 清除事件标志并等待
                            self.withdrawal_confirm_event.clear()
                            self.log_message(f"  -> 等待用户确认大额提币 (地址: {self._mask_addresses_in_text(addr)}, 金额: {random_amount_quantized} {coin})...", level="INFO")
                            self.withdrawal_confirm_event.wait() # 线程在此阻塞直到事件被设置

                            if not self.user_agreed_to_this_withdrawal:
                                self.log_message(f"  -> 用户未确认或取消了大额提币，跳过地址 {address_display_index} ({self._mask_addresses_in_text(addr)})", level="WARNING")
                                processed_count += 1
                                continue # 跳到下一个地址
                            else:
                                self.log_message(f"  -> 用户已确认大额提币，继续执行对地址 {self._mask_addresses_in_text(addr)} 的提币操作。", level="INFO")
                    except Exception as e_large_check:
                         self.log_message(f"大额提币检查计算时出错: {e_large_check}", level="WARNING")

                # --- 3. 检查余额 (考虑手续费) ---
                try:
                    balance_str = self.current_exchange_api.get_balance(coin)
                    if balance_str is None:
                        self.log_message(f"无法获取 {coin} 余额，跳过地址 {address_display_index}", level="WARNING")
                        processed_count += 1
                        continue
                    
                    balance_decimal = Decimal(balance_str)
                    required_amount = random_amount_quantized + fee_decimal
                    
                    if balance_decimal < required_amount:
                        self.log_message(f"余额不足 (需要: {required_amount}, 可用: {balance_decimal})，跳过地址 {address_display_index}", level="WARNING")
                        processed_count += 1
                        continue # 跳到下一个地址
                    else:
                         self.log_message(f"  -> 余额检查通过 (可用: {balance_decimal}, 需要: {required_amount})", level="DEBUG")
                except Exception as e_balance:
                     self.log_message(f"检查余额时出错: {e_balance}，跳过此地址 {address_display_index}", level="ERROR")
                     processed_count += 1
                     continue

                # --- 4. 构造API地址参数并执行实际提币API调用 ---
                address_for_api = addr
                if self.current_exchange_name == 'OKX':
                    # 检查地址类型
                    is_evm_address = addr.startswith('0x') and len(addr) == 42
                    is_sol_address = not is_evm_address and len(addr) >= 32 and len(addr) <= 44
                    
                    if is_evm_address:
                        # 对于EVM地址，OKX API可能期望纯地址，忽略Excel中的label
                        self.log_message(f"  -> OKX EVM地址: 使用原始地址 {self._mask_addresses_in_text(addr)} (忽略Excel label: {label})", level="DEBUG")
                        address_for_api = addr 
                    elif is_sol_address and label:
                        # 对于SOL地址，如果有label，使用 address:label 格式
                        address_for_api = f"{addr}:{label}"
                        self.log_message(f"  -> OKX SOL地址: 使用地址:label格式: {self._mask_addresses_in_text(address_for_api)}", level="DEBUG")
                    elif label: # 其他非EVM地址，且Excel中提供了label
                        address_for_api = f"{addr}:{label}"
                        self.log_message(f"  -> OKX 非EVM地址: 使用地址:label格式: {self._mask_addresses_in_text(address_for_api)}", level="DEBUG")
                    # else: 非EVM地址且无label，address_for_api 保持原始 addr
                
                success = False
                message = "未知错误"
                try:
                    # 格式化提币数量为字符串
                    amount_str_for_api = f"{random_amount_quantized:.{actual_precision}f}"
                    self.log_message(f"  -> 准备调用API提币: {amount_str_for_api} {coin} 到 {self._mask_addresses_in_text(address_for_api)}...", level="INFO")
                    
                    memo = None # TODO: 如果需要支持memo，从 address_info['label'] 或其他地方获取?
                    
                    success, message = self.current_exchange_api.withdraw(
                        coin=coin, 
                        network=network, 
                        address=address_for_api, 
                        amount=amount_str_for_api, # <--- 传递格式化后的字符串
                        memo=memo
                    )
                except Exception as e_withdraw:
                    success = False
                    message = f"API调用异常: {e_withdraw}"
                    self.log_message(f"提币API调用时发生异常: {e_withdraw}", level="ERROR", exc_info=True)

                # --- 5. 处理提币结果 ---
                if success:
                    self.used_addresses.add(addr) # 记录原始地址为已使用
                    withdraw_id = message # API成功时 message 通常是提币ID
                    self.log_message(f"地址 {address_display_index} 提币成功: {withdraw_id}", level="SUCCESS")
                else:
                    error_msg = message # API失败时 message 通常是错误信息
                    self.log_message(f"地址 {address_display_index} ({address_for_api}) 提币失败: {error_msg}", level="ERROR")
                    # 可选：如果提币失败是否重试？或添加到失败列表？暂时只记录日志。

                processed_count += 1

                # --- 6. 更新进度条 ---
                progress_percentage = int((processed_count / total_addresses_in_range) * 100)
                progress_text = f"进度: {progress_percentage}%"
                self.progress_update_signal.emit(progress_percentage, progress_text)

                # --- 7. 随机等待 (如果不是最后一个地址) ---
                if i < end_idx:
                    wait_time = random.randint(min_interval, max_interval)
                    self.log_message(f"下一次提币前等待 {wait_time} 秒...", level="DEBUG")
                    wait_start = time.time()
                    while time.time() - wait_start < wait_time:
                        if not self.running: 
                            self.log_message("在等待期间收到停止信号，退出...", level="INFO")
                            break 
                        remaining_wait = int(wait_time - (time.time() - wait_start))
                        wait_percentage = int(((time.time() - wait_start) / wait_time) * 100) if wait_time > 0 else 100
                        wait_text = f"等待: {remaining_wait}秒"
                        self.wait_update_signal.emit(wait_percentage, wait_text)
                        time.sleep(0.5) 
                    if not self.running: break 
               
                self.wait_update_signal.emit(0, "等待: 0秒") 

        except Exception as e_thread:
            self.log_message(f"提币线程主循环发生意外错误: {e_thread}", level="CRITICAL", exc_info=True)
        finally:
            # --- 8. 线程结束，发射完成信号 --- 
            self.log_message("提币流程正常结束或已停止。", level="INFO")
            # self.running 在 _on_withdrawal_finished 中设置为 False
            self.withdrawal_finished_signal.emit() # 发射信号，由主线程更新UI
            self.logger.debug("_process_withdrawals finally block executed.")

    def _on_withdrawal_finished(self):
        """处理提币线程完成信号的槽函数."""
        self.logger.info("收到提币完成信号，更新UI状态。")
        self.running = False # 确保运行状态为False
        if hasattr(self, 'start_button'): self.start_button.setEnabled(True)
        if hasattr(self, 'stop_button'): self.stop_button.setEnabled(False)
        # 重置进度条和等待条 (虽然线程finally里也做了，这里再做一次确保UI更新)
        self.update_progress(0)  # Reset progress
        self.wait_update_signal.emit(0, "等待: 0秒")

    def show_donation_dialog(self):
        """显示捐赠对话框，包含支持作者的信息和捐赠地址。"""
        donation_dialog = DonationDialog(parent=self)
        donation_dialog.exec()
        
    def closeEvent(self, event: QCloseEvent): # Added type hint for event
        self.logger.info("应用程序正在关闭...")
        
        # 在应用关闭前停止所有可能运行的提币操作
        if hasattr(self, 'running') and self.running:
            self.running = False
            self.log_message("应用程序关闭：提币流程已停止", level="INFO")
        
        # --- 开始改进的线程清理 ---
        threads_to_clean = []
        # 使用 getattr 获取引用，避免 AttributeError
        api_thread = getattr(self, 'api_thread', None)
        api_worker = getattr(self, 'api_worker', None)
        balance_thread = getattr(self, 'balance_thread', None)
        balance_worker = getattr(self, 'balance_worker', None)
        
        if api_thread is not None: threads_to_clean.append(("API", api_thread, api_worker))
        if balance_thread is not None: threads_to_clean.append(("余额", balance_thread, balance_worker))
        
        for name, thread, worker in threads_to_clean:
            try:
                if thread.isRunning():
                    self.log_message(f"正在停止{name}线程...", level="DEBUG")
                    thread.quit()
                    if not thread.wait(3000):
                        self.log_message(f"{name}线程未能正常退出。", level="WARNING")
                # 请求删除worker和线程
                if worker: 
                     worker.deleteLater()
                thread.deleteLater()
            except RuntimeError:
                 self.log_message(f"清理{name}线程时出错：对象可能已被删除。", level="DEBUG")
            except Exception as e_clean:
                 self.log_message(f"清理{name}线程时发生未知错误: {e_clean}", level="ERROR")

        # 清理Python原生提币线程 (无法强制停止，只能等待)
        withdrawal_thread = getattr(self, 'withdrawal_thread', None)
        if withdrawal_thread and withdrawal_thread.is_alive():
            self.log_message("等待提币线程自然结束... (已设置停止标志)", level="INFO")
            # withdrawal_thread.join(5) # 可以选择等待几秒，但不阻塞关闭太久
        # --- 结束改进的线程清理 ---
        
        # 关闭API连接
        if self.current_exchange_api and hasattr(self.current_exchange_api, 'close'):
            try:
                self.current_exchange_api.close()
                self.log_message(f"已关闭 {self.current_exchange_name} API 连接。", level="INFO")
            except Exception as e:
                self.log_message(f"关闭 {self.current_exchange_name} API 时出错: {e}", level="ERROR", exc_info=True)
        
        # 保存窗口状态
        try:
            gui_settings_file = os.path.join(self.app_data_dir, "GuiState.ini")
            q_settings = QSettings(gui_settings_file, QSettings.Format.IniFormat)
            q_settings.setValue("geometry", self.saveGeometry())
            q_settings.setValue("windowState", self.saveState())
            self.logger.info(f"窗口几何状态已保存到: {gui_settings_file}")
        except Exception as e:
            self.logger.error(f"保存窗口几何状态失败: {e}", exc_info=True)

        # 保存其他配置
        self.save_app_config() # Save other app config like last exchange, last file path etc.
        
        # 停止定时器
        if hasattr(self, 'status_bar_timer') and self.status_bar_timer.isActive():
            self.status_bar_timer.stop()
            self.logger.debug("状态栏定时器已停止。")
        
        # 在调用父类closeEvent之前刷新剩余的日志
        logging.shutdown()
        
        # 确保所有Qt事件处理完毕
        QApplication.processEvents()
        
        # 清空线程引用列表 (如果仍在使用)
        if hasattr(self, 'thread_references'):
            self.thread_references.clear()
        
        # 最后调用父类的closeEvent以关闭窗口
        super().closeEvent(event)

    def _open_settings_dialog(self):
        self.logger.debug("打开设置对话框...")
        if self.settings_dialog.exec(): 
            self.log_message("设置已更新。正在重新连接...", level="INFO")
            self.config_updated_and_reconnect(resetting=False) 
        else:
            self.log_message("设置对话框已取消。", level="DEBUG")
            
    def save_app_config(self):
        """将应用的非敏感配置（如下次使用的交易所、地址文件路径）保存到 config.ini"""
        try:
            if not self.config.has_section('GENERAL'):
                self.config.add_section('GENERAL')
            
            # 保存最后选择的交易所 (Toolbar combo's current text is reliable)
            if hasattr(self, 'exchange_combo_toolbar'):
                 current_exchange = self.exchange_combo_toolbar.currentText()
                 if current_exchange in self.EXCHANGES:
                     self.config.set('GENERAL', 'last_selected_exchange', current_exchange)
            
            # 保存最后使用的地址文件路径
            self.config.set('GENERAL', 'last_address_file', getattr(self, 'last_address_file_path', '')) # Use getattr for safety

            # 保存OKX模拟盘设置 (Ensure this is also saved, might need update from settings dialog state)
            # This assumes self.config object holds the latest state from settings dialog or initialization
            okx_simulated_value = self.config.get('GENERAL', 'okx_simulated', fallback='False') 
            self.config.set('GENERAL', 'okx_simulated', okx_simulated_value) 

            with open(self.config_path, 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
            self.logger.info("应用常规配置已保存到 config.ini")
        except Exception as e:
            self.logger.error(f"保存应用配置到 config.ini 时出错: {e}", exc_info=True)
            # Optionally show a message to the user, but might be too noisy on close

    def update_networks_on_coin_change(self, coin_text: str):
        """当币种下拉框选择变化时调用此方法。
           更新网络、余额、价格。
        """
        self.logger.debug(f"币种选择已更改为: {coin_text}")
        if not self.current_exchange_api or not coin_text:
            self.log_message("API未就绪或未选择币种，无法更新网络/余额/价格。", level="DEBUG")
            self._clear_networks_balance_fee_price_ui() # 清除依赖字段
            return

        # 自动切换地址类型
        if hasattr(self, 'available_address_types'):
            # 根据币种确定对应的地址类型
            address_type_map = {
                'SUI': 'sui',
                'SOL': 'sol',
                'ETH': 'evm',
                'USDT': 'evm',
                'USDC': 'evm',
                'G': 'evm'
            }
            
            target_type = address_type_map.get(coin_text.upper())
            if target_type and target_type in self.available_address_types:
                # 如果目标类型在可用类型列表中，则切换
                self.log_message(f"自动切换地址类型为: {target_type}", level="INFO")
                self.current_address_type = target_type
                # 重新加载当前类型的地址
                self._load_addresses_for_current_type()

        # 1. 更新选定币种的网络
        self._update_networks_display(coin_text)
        # 2. 更新选定币种的余额
        self._update_balance_display(coin_text)
        # 3. 更新选定币种的价格（与USDT或默认报价）
        # 4. 费用更新通常由网络选择触发，
        #    但如果自动选择了网络，其处理程序应该更新费用。
        #    如果填充了网络并且_update_networks_display默认选择了一个网络，
        #    那么应该触发update_usd_values_on_network_change（on_network_selected）。

        # 原始调用update_usd_values - 如果涉及币种价格，这可能是放置它的好地方
        self.update_usd_values(force_update=True) # force_update可能与价格获取有关

    def _update_networks_display(self, coin_text: str):
        """更新网络下拉框显示指定币种的可用网络"""
        if not hasattr(self, 'network_combo') or not self.current_exchange_api:
            return
        self.network_combo.blockSignals(True)
        self.network_combo.clear()
        self.network_combo.setEnabled(False)
        try:
            self.log_message(f"为币种 {coin_text} 请求网络列表...", level="DEBUG")
            networks = self.current_exchange_api.get_networks_for_coin(coin=coin_text)
            if networks:
                self.network_combo.addItems(networks)
                self.network_combo.setEnabled(True)
                self.log_message(f"为币种 {coin_text} 填充了 {len(networks)} 个网络。", level="INFO")
                if self.network_combo.count() > 0:
                    self.network_combo.setCurrentIndex(0) 
                    self.network_combo.blockSignals(False)
                    self.update_usd_values_on_network_change(self.network_combo.currentText())
                return
            else:
                self.log_message(f"{self.current_exchange_name} 未返回币种 {coin_text} 的网络信息。", level="WARNING")
        except Exception as e:
            self.log_message(f"获取 {coin_text} 的网络列表时出错: {e}", level="ERROR", exc_info=True)
        self.network_combo.blockSignals(False)
        if hasattr(self, 'fee_label'): self.fee_label.setText("手续费: N/A")
        
    def update_usd_values_on_network_change(self, network_text: str):
        """当网络下拉框选择变化时调用此方法。
           更新手续费。
        """        
        self.logger.debug(f"网络选择已更改为: {network_text}")
        if not self.current_exchange_api or not hasattr(self, 'coin_combo') or not self.coin_combo.currentText() or not network_text:
            self.log_message("API未就绪、未选择币种或网络，无法更新手续费。", level="DEBUG")
            if hasattr(self, 'fee_label'): self.fee_label.setText("手续费: N/A")
            return
        selected_coin = self.coin_combo.currentText()
        self._update_fee_display(selected_coin, network_text)
        
    def _update_fee_display(self, coin: str, network: str):
        """根据当前选择的币种和网络，获取并更新提现手续费的UI显示。"""
        if not hasattr(self, 'fee_label') or not self.current_exchange_api:
            self.logger.debug("_update_fee_display: fee_label 未找到或API未连接，跳过手续费更新。")
            return
                
        self.fee_label.setText("手续费: 正在加载...")
        try:
            self.logger.debug(f"为币种 {coin} ({network}) 请求手续费...")
            # 注意：get_withdrawal_fee 可能返回字符串 "fee asset" 或字典，或None
            fee_data = self.current_exchange_api.get_withdrawal_fee(coin=coin, network=network)
            
            if fee_data is not None:
                if isinstance(fee_data, str): # 例如直接返回 "0.001 BTC"
                    # 如果API返回的是 "fee asset" 格式，并且我们希望只显示 "fee asset"
                    # 或者，如果API只返回费率数字字符串，我们需要加上币种
                    # 假设BaseExchangeAPI的实现会返回一个可以直接显示的字符串或一个包含fee和asset的字典
                    self.fee_label.setText(f"手续费: {fee_data}") 
                    self.logger.info(f"更新手续费 for {coin} on {network}: {fee_data}")
                elif isinstance(fee_data, dict):
                    fee_amount = fee_data.get('fee')
                    fee_asset = fee_data.get('asset', coin) # 如果字典没提供asset，默认用当前币种
                    if fee_amount is not None:
                        self.fee_label.setText(f"手续费: {fee_amount} {fee_asset}")
                        self.logger.info(f"更新手续费 for {coin} on {network}: {fee_amount} {fee_asset}")
                    else: # else for 'if fee_amount is not None:'
                        self.fee_label.setText("手续费: N/A (数据格式错误)")
                        self.logger.warning(f"获取 {coin} ({network}) 手续费成功，但数据格式不包含 'fee'。 数据: {fee_data}")
                else: # else for 'if isinstance(str) / elif isinstance(dict)'
                    # 如果返回了非预期的类型
                    self.fee_label.setText(f"手续费: {str(fee_data)}") 
                    self.logger.warning(f"获取 {coin} ({network}) 手续费返回了未知类型: {type(fee_data)}, 内容: {fee_data}")
            else: # else for 'if fee_data is not None:'
                self.fee_label.setText("手续费: N/A")
                self.logger.warning(f"无法获取 {coin} ({network}) 的手续费。API返回None。")
        except Exception as e:
            self.logger.error(f"更新 {coin} ({network}) 手续费时出错: {e}", exc_info=True)
            self.fee_label.setText("手续费: 获取失败")
            
    def update_usd_values(self, force_update=False):
        """更新界面上与USD估值相关的标签。价格数据固定从Binance获取。"""
        if not hasattr(self, 'coin_combo') or not self.coin_combo.currentText():
            if hasattr(self, 'min_amount_usd'): self.min_amount_usd.setText("≈$-.--")
            if hasattr(self, 'max_amount_usd'): self.max_amount_usd.setText("≈$-.--")
            return
                
        coin = self.coin_combo.currentText()
        quote_currency = "USDT" 
        price = None

        if coin.upper() == quote_currency.upper():
            price = Decimal(1.0)
            self.logger.debug(f"USD估值: {coin} (稳定币) 价格设为 1.0")
        else:
            # 构造Binance交易对格式, e.g., ETHUSDT
            binance_symbol_to_fetch = f"{coin.upper()}{quote_currency.upper()}"
            self.logger.debug(f"USD估值: 使用Binance API获取 {binance_symbol_to_fetch} 的价格。")
            
            price_str = None
            # 检查缓存
            if not force_update and binance_symbol_to_fetch in self.price_cache:
                price_str = self.price_cache.get(binance_symbol_to_fetch)
                if price_str: # Ensure cached value is not None or empty before logging
                    self.logger.debug(f"USD估值: 使用缓存价格 {price_str} for {binance_symbol_to_fetch}")
            
            # 如果缓存未命中或强制更新, 则从API获取
            if not price_str:
                if self.price_provider_api and self.binance_api_for_prices_connected:
                    try:
                        self.logger.debug(f"USD估值: 正在为 {binance_symbol_to_fetch} 通过Binance API请求价格...")
                        price_str = self.price_provider_api.get_symbol_ticker(symbol=binance_symbol_to_fetch)
                        
                        if price_str: # API返回了价格字符串
                            self.price_cache[binance_symbol_to_fetch] = price_str 
                            self.logger.info(f"USD估值: 通过Binance API获取到价格 {price_str} 并缓存 for {binance_symbol_to_fetch}")
                        else: # API调用成功但未返回价格 (e.g.,交易对不存在)
                            self.logger.warning(f"USD估值: Binance API未能返回 {binance_symbol_to_fetch} 的价格。")
                            # 可选: 清除可能存在的旧缓存，以防显示错误价格
                            if binance_symbol_to_fetch in self.price_cache: 
                                del self.price_cache[binance_symbol_to_fetch]
                    except Exception as e_price_fetch:
                        self.logger.error(f"USD估值: 通过Binance API获取 {binance_symbol_to_fetch} 价格时出错: {e_price_fetch}", exc_info=True)
                        price_str = None # 确保出错时price_str为None
                else:
                    self.logger.warning("USD估值: Binance价格数据源未连接或未初始化。无法获取实时价格。")
                    # price_str 保持 None

            # 转换价格字符串为Decimal
            if price_str:
                try:
                    price = Decimal(price_str)
                except Exception as e_decimal_conversion:
                    self.logger.error(f"USD估值: 无法将价格字符串 '{price_str}' (来自 {binance_symbol_to_fetch}) 转换为Decimal: {e_decimal_conversion}")
                    price = None 
        
        # 更新UI上的USD估值
        min_amount_usd_label = getattr(self, 'min_amount_usd', None)
        max_amount_usd_label = getattr(self, 'max_amount_usd', None)

        if price is not None:
            try:
                if hasattr(self, 'min_amount_entry') and min_amount_usd_label:
                    min_val_str = self.min_amount_entry.text().strip() or "0"
                    min_val = Decimal(min_val_str)
                    min_amount_usd_label.setText(f"≈${float(min_val * price):.2f}")
                
                if hasattr(self, 'max_amount_entry') and max_amount_usd_label:
                    max_val_str = self.max_amount_entry.text().strip() or "0"
                    max_val = Decimal(max_val_str)
                    max_amount_usd_label.setText(f"≈${float(max_val * price):.2f}")
            except Exception as e_ui_update:
                self.logger.error(f"USD估值UI更新错误: {e_ui_update}", exc_info=True)
                if min_amount_usd_label: min_amount_usd_label.setText("≈$?.??")
                if max_amount_usd_label: max_amount_usd_label.setText("≈$?.??")
        else:
            if min_amount_usd_label: min_amount_usd_label.setText("≈$N/A")
            if max_amount_usd_label: max_amount_usd_label.setText("≈$N/A")
            self.logger.debug(f"USD估值：因无法获取 {coin}/{quote_currency} (via Binance) 价格，估值显示为 N/A。")

    def _update_balance_display(self, coin_text: str):
        if not hasattr(self, 'balance_label') or not self.current_exchange_api:
            return
            
        # 检查缓存
        cache_key = f"{self.current_exchange_name}_{coin_text}"
        current_time = time.time()
        if cache_key in self.balance_cache:
            balance_str, timestamp = self.balance_cache[cache_key]
            if current_time - timestamp < self.balance_cache_ttl:
                self.logger.debug(f"使用缓存的余额数据: {coin_text} ({self.current_exchange_name})")
                self._handle_balance_result(balance_str, coin_text)
                return
        
        self.balance_label.setText("余额: 正在加载...")
        
        # --- 开始改进的线程清理 ---
        # 在访问前检查线程对象是否存在且有效
        thread_to_clean = getattr(self, 'balance_thread', None)
        if thread_to_clean is not None:
            try:
                if thread_to_clean.isRunning():
                    self.log_message("正在停止之前的余额查询线程...", level="DEBUG")
                    thread_to_clean.quit()
                    if not thread_to_clean.wait(3000): # 等待3秒
                        self.log_message("之前的余额线程未能正常退出，可能导致问题。", level="WARNING")
                    else:
                        self.log_message("之前的余额线程已停止。", level="DEBUG")
                else:
                    self.log_message("之前的余额线程已结束或未运行。", level="DEBUG")
                    
                # 请求删除旧线程和worker
                worker_to_delete = getattr(self, 'balance_worker', None)
                if worker_to_delete:
                    worker_to_delete.deleteLater()
                thread_to_clean.deleteLater()

            except RuntimeError: # 捕获对象已被删除的错误
                self.log_message("尝试清理余额线程时出错：对象可能已被删除。", level="DEBUG")
            except Exception as e_clean: # 捕获其他潜在错误
                self.log_message(f"清理余额线程时发生未知错误: {e_clean}", level="ERROR")
                
        self.balance_thread = None # 显式设置None
        self.balance_worker = None
        # --- 结束改进的线程清理 ---
        
        # 创建新的线程和工作器
        self.balance_thread = QThread()
        # 将线程添加到引用存储列表 (暂时保留)
        if hasattr(self, 'thread_references'): self.thread_references.append(self.balance_thread)
        
        self.balance_worker = BalanceWorker(self.current_exchange_api, coin_text)
        self.balance_worker.moveToThread(self.balance_thread)
        
        # 连接信号
        self.balance_thread.started.connect(self.balance_worker.run)
        self.balance_worker.finished.connect(self._handle_balance_result)
        self.balance_worker.error.connect(self._handle_balance_error)
        self.balance_worker.log_message.connect(lambda msg, level: self.log_message(msg, level=level))
        
        # --- 改进的清理连接 ---
        # 当worker完成或出错时，请求线程退出
        self.balance_worker.finished.connect(self.balance_thread.quit)
        self.balance_worker.error.connect(self.balance_thread.quit)
        # 当线程结束后，请求删除worker和线程自身
        self.balance_thread.finished.connect(self.balance_worker.deleteLater)
        self.balance_thread.finished.connect(self.balance_thread.deleteLater)
        # --- 结束改进的清理连接 ---
        
        # 启动线程
        self.balance_thread.start()
        
    def _handle_balance_result(self, balance_str, coin):
        """处理余额查询结果"""
        if not hasattr(self, 'balance_label'):
            return
            
        try:
            # 更新缓存
            cache_key = f"{self.current_exchange_name}_{coin}"
            self.balance_cache[cache_key] = (balance_str, time.time())
            
            # 格式化余额显示为小数点后两位
            try:
                balance_decimal = Decimal(balance_str)
                formatted_balance = f"{balance_decimal:.2f}" # 格式化为两位小数
            except Exception:
                formatted_balance = balance_str # 如果转换失败，显示原始字符串

            self.balance_label.setText(f"余额: {formatted_balance}")
            self.log_message(f"已更新 {coin} 余额: {formatted_balance}", level="INFO")
        except Exception as e:
            self.log_message(f"处理余额结果时出错: {e}", level="ERROR")
            self.balance_label.setText("余额: 处理错误")
            
    def _handle_balance_error(self, error_msg, coin):
        """处理余额查询错误"""
        if not hasattr(self, 'balance_label'):
            return
            
        self.log_message(f"查询 {coin} 余额失败: {error_msg}", level="ERROR")
        self.balance_label.setText("余额: 查询失败")
        
    def _update_status_bar_time(self):
        """更新状态栏中的时间显示"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(self, 'statusBar'):
                # 这里不会覆盖其他状态消息，因为我们使用设置一个永久widget而不是showMessage
                # 如果需要显示时间，可以在状态栏中添加一个专用的QLabel
                pass
        except Exception as e:
            self.logger.error(f"更新状态栏时间时出错: {str(e)}", exc_info=True)
            
    def _post_initial_ui_setup(self):
        """在UI初始化和API初始化后调用，用于完成最终的UI设置和优化"""
        try:
            # 恢复保存的窗口状态
            try:
                gui_settings_file = os.path.join(self.app_data_dir, "GuiState.ini")
                if os.path.exists(gui_settings_file):
                    q_settings = QSettings(gui_settings_file, QSettings.Format.IniFormat)
                    if q_settings.contains("geometry"):
                        self.restoreGeometry(q_settings.value("geometry"))
                    if q_settings.contains("windowState"):
                        self.restoreState(q_settings.value("windowState"))
                    self.logger.debug("已恢复之前保存的窗口几何状态。")
            except Exception as e:
                self.logger.warning(f"恢复窗口几何状态失败: {e}")
                
            # 如果需要异步加载其他UI元素或数据，可以在这里添加
        except Exception as e:
            self.log_message(f"最终UI设置时出错: {str(e)}", level="ERROR", exc_info=True)

    def _open_external_link(self, url_string: str):
        """在默认浏览器中打开外部链接。"""
        try:
            url = QUrl(url_string)
            if url.isValid():
                self.log_message(f"正在尝试打开外部链接: {url_string}", level="DEBUG")
                opened = QDesktopServices.openUrl(url)
                if not opened:
                    self.log_message(f"无法打开链接: {url_string}", level="WARNING")
                    QMessageBox.warning(self, "打开链接失败", f"无法自动打开链接：\n{url_string}\n\n您可以手动复制并在浏览器中打开。")
            else:
                self.log_message(f"提供的URL无效: {url_string}", level="ERROR")
                QMessageBox.warning(self, "链接无效", f"提供的链接格式无效：\n{url_string}")
        except Exception as e:
            self.log_message(f"打开外部链接时出错: {e}", level="ERROR", exc_info=True)
            QMessageBox.critical(self, "错误", f"尝试打开链接时发生错误：{e}")

if __name__ == "__main__":
    try:
        # 创建 QApplication 实例
        app = QApplication(sys.argv)
        
        # 应用深色主题样式
        app.setStyleSheet(DARK_STYLE) # DARK_STYLE 变量应在您的代码中定义
        
        # 创建 WithdrawalHelper 主窗口实例
        main_window = WithdrawalHelper()
        
        # 添加应用程序退出前的清理函数
        def cleanup():
            print("正在清理应用程序资源...")
            # 确保所有线程都被正确清理
            if hasattr(main_window, 'thread_references'):
                main_window.thread_references.clear()
            logging.shutdown()
            # 移除强制退出
            # import os
            # os._exit(0) 
            
        app.aboutToQuit.connect(cleanup)
        
        # 显示主窗口
        main_window.show()
        
        # 进入 Qt 事件循环
        sys.exit(app.exec())
    except Exception as e:
        print(f"程序出错: {e}")
    finally:
        # 确保程序退出前清理所有资源
        logging.shutdown()

