# 导入必要的库
from PyQt6.QtWidgets import (QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                           QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QPushButton,
                           QGroupBox, QMessageBox, QCheckBox, QWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import os
import configparser
# import json # json似乎没有用到，可以移除

class SettingsDialog(QDialog):
    """设置对话框，包含API配置、时间间隔设置和提币阈值设置"""

    def __init__(self, logger, config_path, parent=None):
        super().__init__(parent)
        self.logger = logger  # 保存传入的logger实例
        self.config_path = config_path  # 保存传入的配置文件路径
        self.parent_window = parent  # 保存父窗口引用，用于访问主窗口的方法（如果需要）

        self.logger.debug("SettingsDialog initialized.")

        self.setWindowTitle("设置")
        self.resize(550, 500) # 稍微调整大小以容纳更多设置

        # 加载现有配置
        self.config = configparser.ConfigParser()

        # 如果配置文件存在，则加载
        if os.path.exists(self.config_path): # 使用传入的 config_path
            self.config.read(self.config_path, encoding='utf-8')
        else:
            # 尝试从程序目录加载 (虽然最佳实践是只用用户目录)
            original_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
            if os.path.exists(original_config_path):
                self.config.read(original_config_path, encoding='utf-8')
            # else: # 不再在此处创建默认配置，如果文件不存在，后续逻辑会处理或创建空的section

        # 确保必要的sections存在，如果不存在则添加
        if 'BINANCE' not in self.config:
            self.config['BINANCE'] = {'api_key': '', 'api_secret': ''}
        if 'OKX' not in self.config:
            self.config['OKX'] = {'api_key': '', 'api_secret': '', 'passphrase': ''}
        if 'WITHDRAWAL_PARAMS' not in self.config:
            self.config['WITHDRAWAL_PARAMS'] = {
                'min_interval': '60',
                'max_interval': '600',
                'warning_threshold': '1000',
                'enable_warning': 'True',
                'last_exchange': 'BINANCE' # 新增，默认交易所
            }
        if 'GENERAL' not in self.config: # 用于未来可能的通用设置
             self.config['GENERAL'] = {}


        # 设置对话框布局
        main_layout = QVBoxLayout(self)

        # 创建标签页
        self.tabs = QTabWidget()

        # 创建各个设置页面
        self.setup_api_tab()
        self.setup_withdrawal_tab() # 重命名，原interval_tab

        # 添加标签页到布局
        main_layout.addWidget(self.tabs)

        # 添加底部按钮
        button_layout = QHBoxLayout()

        self.reset_button = QPushButton("恢复默认设置")
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #7F8C8D;
                color: white;
            }
            QPushButton:hover {
                background-color: #95A5A6;
            }
        """)
        self.reset_button.clicked.connect(self.reset_all_settings)

        self.save_button = QPushButton("保存设置")
        self.save_button.clicked.connect(self.save_settings)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.reset_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)

        main_layout.addLayout(button_layout)

    def setup_api_tab(self):
        """设置API配置标签页"""
        api_tab = QWidget()
        api_scroll_area = QVBoxLayout(api_tab) # 使用QVBoxLayout以便内容超出时可滚动
        
        # --- 币安 API 设置组 ---
        binance_api_group = QGroupBox("币安 (Binance) API 配置")
        binance_api_layout = QGridLayout(binance_api_group)

        binance_api_layout.addWidget(QLabel("API Key:"), 0, 0)
        self.binance_api_key_entry = QLineEdit(self.config['BINANCE'].get('api_key', ''))
        self.binance_api_key_entry.setEchoMode(QLineEdit.EchoMode.Password)
        binance_api_layout.addWidget(self.binance_api_key_entry, 0, 1)

        self.show_binance_api_key_btn = QPushButton("显示")
        self.show_binance_api_key_btn.setCheckable(True)
        self.show_binance_api_key_btn.clicked.connect(
            lambda checked: self.toggle_visibility(self.binance_api_key_entry, self.show_binance_api_key_btn, checked)
        )
        self.show_binance_api_key_btn.setFixedWidth(60)
        binance_api_layout.addWidget(self.show_binance_api_key_btn, 0, 2)

        binance_api_layout.addWidget(QLabel("API Secret:"), 1, 0)
        self.binance_api_secret_entry = QLineEdit(self.config['BINANCE'].get('api_secret', ''))
        self.binance_api_secret_entry.setEchoMode(QLineEdit.EchoMode.Password)
        binance_api_layout.addWidget(self.binance_api_secret_entry, 1, 1)

        self.show_binance_api_secret_btn = QPushButton("显示")
        self.show_binance_api_secret_btn.setCheckable(True)
        self.show_binance_api_secret_btn.clicked.connect(
            lambda checked: self.toggle_visibility(self.binance_api_secret_entry, self.show_binance_api_secret_btn, checked)
        )
        self.show_binance_api_secret_btn.setFixedWidth(60)
        binance_api_layout.addWidget(self.show_binance_api_secret_btn, 1, 2)
        
        api_scroll_area.addWidget(binance_api_group)

        # --- OKX API 设置组 ---
        okx_api_group = QGroupBox("欧易 (OKX) API 配置")
        okx_api_layout = QGridLayout(okx_api_group)

        okx_api_layout.addWidget(QLabel("API Key:"), 0, 0)
        self.okx_api_key_entry = QLineEdit(self.config['OKX'].get('api_key', ''))
        self.okx_api_key_entry.setEchoMode(QLineEdit.EchoMode.Password)
        okx_api_layout.addWidget(self.okx_api_key_entry, 0, 1)

        self.show_okx_api_key_btn = QPushButton("显示")
        self.show_okx_api_key_btn.setCheckable(True)
        self.show_okx_api_key_btn.clicked.connect(
            lambda checked: self.toggle_visibility(self.okx_api_key_entry, self.show_okx_api_key_btn, checked)
        )
        self.show_okx_api_key_btn.setFixedWidth(60)
        okx_api_layout.addWidget(self.show_okx_api_key_btn, 0, 2)

        okx_api_layout.addWidget(QLabel("API Secret:"), 1, 0)
        self.okx_api_secret_entry = QLineEdit(self.config['OKX'].get('api_secret', ''))
        self.okx_api_secret_entry.setEchoMode(QLineEdit.EchoMode.Password)
        okx_api_layout.addWidget(self.okx_api_secret_entry, 1, 1)

        self.show_okx_api_secret_btn = QPushButton("显示")
        self.show_okx_api_secret_btn.setCheckable(True)
        self.show_okx_api_secret_btn.clicked.connect(
            lambda checked: self.toggle_visibility(self.okx_api_secret_entry, self.show_okx_api_secret_btn, checked)
        )
        self.show_okx_api_secret_btn.setFixedWidth(60)
        okx_api_layout.addWidget(self.show_okx_api_secret_btn, 1, 2)

        okx_api_layout.addWidget(QLabel("Passphrase:"), 2, 0)
        self.okx_passphrase_entry = QLineEdit(self.config['OKX'].get('passphrase', ''))
        self.okx_passphrase_entry.setEchoMode(QLineEdit.EchoMode.Password)
        okx_api_layout.addWidget(self.okx_passphrase_entry, 2, 1)

        self.show_okx_passphrase_btn = QPushButton("显示")
        self.show_okx_passphrase_btn.setCheckable(True)
        self.show_okx_passphrase_btn.clicked.connect(
            lambda checked: self.toggle_visibility(self.okx_passphrase_entry, self.show_okx_passphrase_btn, checked)
        )
        self.show_okx_passphrase_btn.setFixedWidth(60)
        okx_api_layout.addWidget(self.show_okx_passphrase_btn, 2, 2)

        # OKX 模拟盘选择 (如果需要，可以从主界面移到这里或同步)
        self.okx_simulated_checkbox = QCheckBox("OKX使用模拟盘交易")
        # 模拟盘状态的加载和保存将在 save_settings 和 __init__ 中与 'simulated_okx' 这样的配置项关联
        # 假设 'GENERAL' section 用于存储这个状态
        is_simulated = self.config['GENERAL'].get('okx_simulated', 'False') == 'True'
        self.okx_simulated_checkbox.setChecked(is_simulated)
        okx_api_layout.addWidget(self.okx_simulated_checkbox, 3, 0, 1, 3) # 跨3列

        api_scroll_area.addWidget(okx_api_group)
        
        # 添加通用说明文本
        api_note = QLabel("注意: API密钥是敏感信息，请确保仅在安全的环境中使用。\n"
                         "API信息仅保存至本地文件，不会上传至任何服务器。\n"
                         "建议为API密钥绑定IP白名单以增强安全性。")
        api_note.setStyleSheet("color: #F5DEB3; font-size: 12px;") # Khaki color
        api_note.setWordWrap(True)
        api_scroll_area.addWidget(api_note)
        
        api_scroll_area.addStretch(1) # 确保内容靠上
        self.tabs.addTab(api_tab, "API密钥设置")

    def setup_withdrawal_tab(self): # 重命名方法
        """设置提币时间间隔和预警阈值标签页"""
        withdrawal_tab = QWidget() # 重命名变量
        withdrawal_layout = QVBoxLayout(withdrawal_tab) # 重命名变量

        # 时间间隔设置组
        interval_group = QGroupBox("提币时间间隔设置")
        interval_group_layout = QGridLayout(interval_group)

        interval_group_layout.addWidget(QLabel("最小间隔(秒):"), 0, 0)
        self.min_interval_spinbox = QSpinBox() # 重命名变量
        self.min_interval_spinbox.setRange(10, 3600)
        self.min_interval_spinbox.setSingleStep(10)
        self.min_interval_spinbox.setValue(int(self.config['WITHDRAWAL_PARAMS'].get('min_interval', '60')))
        interval_group_layout.addWidget(self.min_interval_spinbox, 0, 1)

        interval_group_layout.addWidget(QLabel("最大间隔(秒):"), 1, 0)
        self.max_interval_spinbox = QSpinBox() # 重命名变量
        self.max_interval_spinbox.setRange(30, 7200)
        self.max_interval_spinbox.setSingleStep(30)
        self.max_interval_spinbox.setValue(int(self.config['WITHDRAWAL_PARAMS'].get('max_interval', '600')))
        interval_group_layout.addWidget(self.max_interval_spinbox, 1, 1)

        interval_note = QLabel("提示: 每次提币操作后，程序将在此时间范围内随机等待。")
        interval_note.setStyleSheet("color: #F5DEB3; font-size: 12px;")
        interval_note.setWordWrap(True)
        
        withdrawal_layout.addWidget(interval_group)
        withdrawal_layout.addWidget(interval_note)

        # 提币阈值设置组
        threshold_group = QGroupBox("大额提币预警设置")
        threshold_group_layout = QGridLayout(threshold_group)

        threshold_group_layout.addWidget(QLabel("预警阈值(美元):"), 0, 0)
        self.warning_threshold_spinbox = QDoubleSpinBox() # 重命名变量
        self.warning_threshold_spinbox.setRange(10.0, 100000.0) # 范围调整
        self.warning_threshold_spinbox.setSingleStep(50.0)    # 步长调整
        self.warning_threshold_spinbox.setPrefix("$ ")
        self.warning_threshold_spinbox.setDecimals(2) # 显示两位小数
        self.warning_threshold_spinbox.setValue(float(self.config['WITHDRAWAL_PARAMS'].get('warning_threshold', '1000')))
        threshold_group_layout.addWidget(self.warning_threshold_spinbox, 0, 1)

        self.enable_threshold_checkbox = QCheckBox("启用大额提币预警") # 重命名变量
        is_enabled = self.config['WITHDRAWAL_PARAMS'].get('enable_warning', 'True') == 'True'
        self.enable_threshold_checkbox.setChecked(is_enabled)
        threshold_group_layout.addWidget(self.enable_threshold_checkbox, 1, 0, 1, 2)

        threshold_note = QLabel("提示: 当单次提币的估算价值超过此阈值时，将弹窗要求二次确认。")
        threshold_note.setStyleSheet("color: #F5DEB3; font-size: 12px;")
        threshold_note.setWordWrap(True)

        withdrawal_layout.addWidget(threshold_group)
        withdrawal_layout.addWidget(threshold_note)
        withdrawal_layout.addStretch(1)
        self.tabs.addTab(withdrawal_tab, "提币参数")


    def toggle_visibility(self, line_edit: QLineEdit, button: QPushButton, checked: bool):
        """通用切换密码可见性方法"""
        if checked:
            line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            button.setText("隐藏")
        else:
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            button.setText("显示")

    def save_settings(self):
        """保存所有设置到配置文件"""
        try:
            min_interval = self.min_interval_spinbox.value()
            max_interval = self.max_interval_spinbox.value()

            if min_interval >= max_interval:
                QMessageBox.warning(self, "设置错误", "最小间隔必须小于最大间隔！")
                return

            # --- 保存币安设置 ---
            self.config['BINANCE']['api_key'] = self.binance_api_key_entry.text().strip()
            self.config['BINANCE']['api_secret'] = self.binance_api_secret_entry.text().strip()

            # --- 保存OKX设置 ---
            if 'OKX' not in self.config: # 确保section存在
                self.config.add_section('OKX')
            self.config['OKX']['api_key'] = self.okx_api_key_entry.text().strip()
            self.config['OKX']['api_secret'] = self.okx_api_secret_entry.text().strip()
            self.config['OKX']['passphrase'] = self.okx_passphrase_entry.text().strip()
            
            # --- 保存OKX模拟盘设置 ---
            if 'GENERAL' not in self.config:
                self.config.add_section('GENERAL')
            self.config['GENERAL']['okx_simulated'] = str(self.okx_simulated_checkbox.isChecked())


            # --- 保存提币设置 ---
            if 'WITHDRAWAL_PARAMS' not in self.config: # 确保section存在
                self.config.add_section('WITHDRAWAL_PARAMS')
            self.config['WITHDRAWAL_PARAMS']['min_interval'] = str(min_interval)
            self.config['WITHDRAWAL_PARAMS']['max_interval'] = str(max_interval)
            self.config['WITHDRAWAL_PARAMS']['warning_threshold'] = str(self.warning_threshold_spinbox.value())
            self.config['WITHDRAWAL_PARAMS']['enable_warning'] = str(self.enable_threshold_checkbox.isChecked())
            # last_exchange 的保存应该在主窗口处理，这里不改

            # 保存到文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config.write(f)

            QMessageBox.information(self, "保存成功", "设置已成功保存！")

            # 信号通知主窗口重新加载配置并可能重新连接API
            if self.parent_window and hasattr(self.parent_window, 'config_updated_and_reconnect'):
                 self.parent_window.config_updated_and_reconnect() # 调用新的方法来处理重连逻辑
            elif self.parent_window and hasattr(self.parent_window, 'load_config'): # 兼容旧的
                 self.parent_window.load_config()


            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存设置时出错：{str(e)}")

    def reset_all_settings(self):
        """恢复默认设置，清除所有用户数据"""
        reply = QMessageBox.question(
            self,
            "恢复默认设置",
            "此操作将重置所有配置项并可能清除相关用户数据，确定要继续吗？\n\n"
            "- API密钥将从配置文件中清除。\n"
            "- 提币参数将恢复为默认值。\n"
            # "- 其他本地缓存数据（如地址文件路径）不会在此处直接删除，但主程序行为可能受影响。\n\n"
            "此操作后，您需要重新配置API信息才能使用相关功能。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 清除币安API信息
                self.config['BINANCE']['api_key'] = ''
                self.config['BINANCE']['api_secret'] = ''
                self.binance_api_key_entry.setText('')
                self.binance_api_secret_entry.setText('')

                # 清除OKX API信息
                self.config['OKX']['api_key'] = ''
                self.config['OKX']['api_secret'] = ''
                self.config['OKX']['passphrase'] = ''
                self.okx_api_key_entry.setText('')
                self.okx_api_secret_entry.setText('')
                self.okx_passphrase_entry.setText('')
                self.okx_simulated_checkbox.setChecked(False) # 默认不使用模拟盘
                self.config['GENERAL']['okx_simulated'] = 'False'


                # 重置提币设置
                self.min_interval_spinbox.setValue(60)
                self.max_interval_spinbox.setValue(600)
                self.warning_threshold_spinbox.setValue(1000.00)
                self.enable_threshold_checkbox.setChecked(True)

                self.config['WITHDRAWAL_PARAMS']['min_interval'] = '60'
                self.config['WITHDRAWAL_PARAMS']['max_interval'] = '600'
                self.config['WITHDRAWAL_PARAMS']['warning_threshold'] = '1000.0'
                self.config['WITHDRAWAL_PARAMS']['enable_warning'] = 'True'
                self.config['WITHDRAWAL_PARAMS']['last_exchange'] = 'BINANCE'


                # 保存清空后的配置
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    self.config.write(f)

                QMessageBox.information(self, "恢复成功", "设置已恢复为默认值。")

                # 通知主窗口
                if self.parent_window and hasattr(self.parent_window, 'config_updated_and_reconnect'):
                    self.parent_window.config_updated_and_reconnect(resetting=True)
                elif self.parent_window and hasattr(self.parent_window, 'load_config'):
                    self.parent_window.load_config()
                    if hasattr(self.parent_window, 'update_api_status_indicator'):
                         self.parent_window.update_api_status_indicator(False) # API信息已清除
                         self.parent_window.api_available = False


                self.accept() # 关闭对话框

            except Exception as e:
                QMessageBox.critical(self, "恢复失败", f"恢复默认设置时出错：{str(e)}")
