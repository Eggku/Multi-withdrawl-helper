from abc import ABC, abstractmethod
import time
from configparser import ConfigParser
import logging

class BaseExchangeAPI(ABC):
    """
    交易所API交互的抽象基类。
    定义了所有具体交易所API实现类必须提供的方法。
    """

    def __init__(self, config: ConfigParser, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.client = None # 具体交易所的SDK客户端实例
        self.time_offset = 0 # 与服务器的时间差

    @abstractmethod
    def connect(self) -> tuple[bool, str]:
        """连接到交易所API。返回 (success_bool, message_str)."""
        pass

    @abstractmethod
    def close(self):
        """关闭与交易所的连接或清理资源."""
        self.logger.info(f"Closing connection for {self.__class__.__name__}")
        # Default implementation can be empty if not all APIs need explicit closing
        pass

    @abstractmethod
    def get_server_time_offset(self) -> int:
        """
        获取本地时间与服务器时间的毫秒级偏移。

        Returns:
            int: 时间偏移量 (本地时间戳 - 服务器时间戳)。
        """
        pass

    def get_timestamp(self) -> int:
        """
        获取经过时间补偿的毫秒级时间戳，用于API请求。

        Returns:
            int: 同步后的时间戳。
        """
        return int(time.time() * 1000) - self.time_offset

    @abstractmethod
    def get_all_tradable_coins(self) -> list[str]:
        """获取所有可交易的币种列表 (e.g., ['BTC', 'ETH'])."""
        pass

    @abstractmethod
    def get_balance(self, asset: str) -> str | None:
        """获取指定资产的余额。返回字符串形式的余额，或在出错时返回None."""
        pass

    @abstractmethod
    def get_networks_for_coin(self, coin: str) -> list[str]:
        """获取指定币种支持的提现网络列表 (e.g., ['BSC', 'ERC20'])."""
        pass

    @abstractmethod
    def get_withdrawal_fee(self, coin: str, network: str, amount: float | None = None) -> str | dict | None:
        """获取提现手续费。可以返回格式化字符串 "fee asset" 或包含手续费信息的字典，或None."""
        pass

    @abstractmethod
    def get_withdraw_precision(self, coin: str, network: str) -> int | None:
        """
        获取指定币种在特定网络上的提现精度（允许的小数位数）。

        Args:
            coin (str): 币种代码 (e.g., 'USDT').
            network (str): 网络代码 (e.g., 'OPTIMISM').

        Returns:
            int | None: 允许的小数位数。如果无法获取则返回 None。
        """
        pass

    @abstractmethod
    def withdraw(self, coin: str, network: str, address: str, amount: str, memo: str | None = None) -> tuple[bool, str]:
        """执行提币操作。返回 (success_bool, message_or_txid_str). amount 应为精确格式化的字符串。"""
        pass

    @abstractmethod
    def get_symbol_ticker(self, symbol: str) -> str | None:
        """获取交易对的当前价格 (e.g., symbol='BTCUSDT')。返回价格字符串或None."""
        pass

    @abstractmethod
    def get_all_coins_info(self) -> list:
        """
        获取交易所支持的所有币种信息，包括其网络列表。

        Returns:
            list: 包含币种信息的字典列表。每个字典应至少包含 'coin' (币种代码)
                  和 'networkList' (网络列表)。网络列表中的每个元素应包含
                  'network' (网络代码), 'withdrawEnable' (是否可提币), 'withdrawFee' (提币费用),
                  'withdrawMin' (最小提币数量)。
        """
        pass

    @abstractmethod
    def get_withdrawal_history(self, coin: str = None) -> list:
        """
        获取提币历史记录。

        Args:
            coin (str, optional): 特定币种的提币历史。如果为 None，则获取所有币种。

        Returns:
            list: 提币历史记录列表。
        """
        pass

    # 可以根据需要添加更多通用的API方法，例如：
    # @abstractmethod
    # def get_deposit_address(self, coin: str, network: str = None) -> dict:
    #     pass

    # @abstractmethod
    # def get_order_status(self, order_id: str, symbol: str) -> dict:
    #     pass
