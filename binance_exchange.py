import time
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from decimal import Decimal, ROUND_DOWN
import logging
from configparser import ConfigParser
from exchange_api_base import BaseExchangeAPI

# 自定义币安特定的异常，如果需要的话
class BinanceExchangeAPIException(Exception):
    pass

class BinanceAPI(BaseExchangeAPI):
    """币安交易所API实现"""

    def __init__(self, config: ConfigParser, logger: logging.Logger):
        super().__init__(config, logger)
        self.api_key = None
        self.api_secret = None
        self.client = None # Will be initialized in connect()
        self.timestamp_error_detected = False # 新增标志位

    def get_server_time_offset(self) -> int:
        """
        获取本地时间与币安服务器时间的毫秒级偏移。
        计算方式: 本地时间戳 - 服务器时间戳。
        """
        if not self.client:
            self.logger.error("币安客户端未初始化，无法获取服务器时间偏移。")
            return 0 # 或者抛出异常，但返回0可以避免在 connect 早期阶段崩溃
        try:
            server_time_response = self.client.get_server_time()
            server_time_ms = int(server_time_response['serverTime'])
            local_time_ms = int(time.time() * 1000)
            offset = local_time_ms - server_time_ms
            self.logger.debug(f"计算出的服务器时间偏移 (本地 - 服务器): {offset} ms")
            return offset
        except BinanceAPIException as e:
            self.logger.error(f"获取币安服务器时间失败 (API Exception): {e}")
            return 0
        except Exception as e:
            self.logger.error(f"获取币安服务器时间时发生未知错误: {e}", exc_info=True)
            return 0

    def connect(self) -> tuple[bool, str]:
        self.api_key = self.config.get('BINANCE', 'api_key', fallback=None)
        self.api_secret = self.config.get('BINANCE', 'api_secret', fallback=None)
        self.timestamp_error_detected = False # 重置标志位

        if not self.api_key or not self.api_secret:
            self.logger.error("币安 API Key 或 Secret 未在配置文件中设置。")
            return False, "API Key 或 Secret 未配置"

        try:
            self.client = Client(self.api_key, self.api_secret)
            self.client.ping()
            self.logger.info("成功 ping 通币安服务器。")
            
            # 获取并设置时间偏移
            self.time_offset = self.get_server_time_offset() 
            self.logger.info(f"成功连接到币安。计算出的时间偏移已设置为: {self.time_offset} ms (本地 - 服务器)")
            # 连接成功，确保时间戳错误标志是False (尽管前面已重置，双重保险)
            self.timestamp_error_detected = False 
            return True, "连接成功"
        except BinanceAPIException as e:
            self.logger.error(f"连接币安 API 失败: {e}")
            err_msg = e.message.lower()
            if e.status_code == 400 and ("timestamp" in err_msg or "ahead of server" in err_msg or "behind server" in err_msg):
                self.timestamp_error_detected = True
                self.logger.error("检测到币安API时间戳错误。请检查系统时间与币安服务器时间是否同步。")
                return False, f"API 连接失败: {e.message} (错误码: {e.status_code} - 时间戳可能不同步，请检查系统时间)"
            return False, f"API 连接失败: {e.message} (错误码: {e.status_code})"
        except Exception as e:
            self.logger.error(f"连接币安时发生未知错误: {e}", exc_info=True)
            return False, f"未知错误: {e}"

    def close(self):
        # Binance client does not require explicit closing of a session typically,
        # but good to have for consistency and future needs (e.g., if using websockets)
        self.logger.info("BinanceAPI: 无需显式关闭连接。")
        # If there were session objects or websockets, close them here.
        pass

    def get_all_tradable_coins(self) -> list[str]:
        if not self.client:
            self.logger.warning("币安客户端未初始化。")
            return []
        # 在尝试API调用前，不应该重置timestamp_error_detected，因为它可能由connect()设置
        # self.timestamp_error_detected = False 
        try:
            self.logger.debug("调用 self.client.get_all_coins_info() 获取币安所有币种信息...")
            all_coins_info = self.client.get_all_coins_info()
            
            if not isinstance(all_coins_info, list):
                self.logger.error(f"self.client.get_all_coins_info() 返回的不是列表，而是: {type(all_coins_info)}。内容: {str(all_coins_info)[:200]}...") # 记录类型和部分内容
                return []

            self.logger.info(f"self.client.get_all_coins_info() 返回了 {len(all_coins_info)} 条币种原始数据。")
            if all_coins_info: # 如果列表不为空
                self.logger.debug(f"币种原始数据示例 (前1条): {str(all_coins_info[0])[:500]}") # 记录第一条数据的部分内容

            # Filter for coins that are tradable or have networks, indicating they can be withdrawn
            tradable_coins = []
            if all_coins_info: # 确保 all_coins_info 是列表且非空才进行迭代
                for coin in all_coins_info:
                    if isinstance(coin, dict) and coin.get('networkList') and isinstance(coin.get('networkList'), list):
                        if any(isinstance(nw, dict) and nw.get('withdrawEnable') for nw in coin['networkList']):
                            if 'coin' in coin: # 确保 'coin' 键存在
                                tradable_coins.append(coin['coin'])
                            else:
                                self.logger.warning(f"币种条目中缺少 'coin' 键: {str(coin)[:200]}")
                    else:
                        self.logger.warning(f"发现格式不正确的币种条目或networkList: {str(coin)[:200]}")

            self.logger.info(f"经过过滤后，得到 {len(tradable_coins)} 个可交易/可提币的币种。")
            return sorted(list(set(tradable_coins))) # Unique and sorted
        except BinanceAPIException as e:
            self.logger.error(f"获取币安所有币种信息失败 (BinanceAPIException): {e.status_code} - {e.message}") # 记录更详细的API错误信息
            err_msg = e.message.lower()
            if e.status_code == 400 and ("timestamp" in err_msg or "ahead of server" in err_msg or "behind server" in err_msg):
                self.timestamp_error_detected = True
                self.logger.error("检测到币安API时间戳错误 (在获取币种信息时)。请检查系统时间与币安服务器时间是否同步。")
            return []
        except Exception as e:
            self.logger.error(f"获取币安币种信息时发生未知错误: {e}", exc_info=True)
            return []

    def get_balance(self, asset: str) -> str | None:
        self.logger.info(f"BinanceAPI.get_balance called for asset: {asset}")
        if not self.client:
            self.logger.warning("币安客户端未初始化。")
            return None
        try:
            spot_balance_data = self.client.get_asset_balance(asset=asset.upper())
            self.logger.debug(f"Binance spot balance data for {asset}: {spot_balance_data}")
            spot_free = Decimal(spot_balance_data['free']) if spot_balance_data else Decimal(0)

            funding_free = Decimal(0)
            try:
                funding_assets = self.client.get_funding_wallet()
                self.logger.debug(f"Binance funding wallet assets: {funding_assets}")
                for fund_asset_info in funding_assets:
                    if fund_asset_info['asset'].upper() == asset.upper():
                        funding_free = Decimal(fund_asset_info['free'])
                        self.logger.info(f"Found {asset} in funding wallet: {funding_free}")
                        break
            except Exception as e:
                self.logger.warning(f"Could not retrieve Binance funding wallet balance for {asset}: {e}. Assuming 0.")

            total_balance = spot_free + funding_free
            self.logger.info(f"Binance total balance for {asset} (spot: {spot_free}, funding: {funding_free}) = {total_balance}")
            return str(total_balance)

        except BinanceAPIException as e:
            self.logger.error(f"Binance API exception when getting balance for {asset}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Generic exception when getting balance for {asset} in BinanceAPI: {e}", exc_info=True)
            return None

    def get_networks_for_coin(self, coin: str) -> list[str]:
        if not self.client:
            self.logger.warning("币安客户端未初始化。")
            return []
        try:
            all_coins_info = self.client.get_all_coins_info() # Consider caching this if called frequently
            for coin_info in all_coins_info:
                if coin_info['coin'] == coin:
                    return [network['network'] for network in coin_info['networkList'] if network.get('withdrawEnable')]
            return []
        except BinanceAPIException as e:
            self.logger.error(f"获取币安 {coin} 网络信息失败: {e}")
            return []
        except Exception as e:
            self.logger.error(f"获取币安 {coin} 网络信息时发生未知错误: {e}", exc_info=True)
            return []

    def get_withdrawal_fee(self, coin: str, network: str, amount: float | None = None) -> str | dict | None:
        if not self.client:
            self.logger.warning("币安客户端未初始化。")
            return None
        try:
            all_coins_info = self.client.get_all_coins_info()
            for coin_info in all_coins_info:
                if coin_info['coin'] == coin:
                    for net_info in coin_info['networkList']:
                        if net_info['network'] == network and net_info['withdrawEnable']:
                            # Binance provides fee as a string, asset name is the coin itself
                            return net_info['withdrawFee'] # This is just the fee amount as string
            return None # Not found or not enabled
        except BinanceAPIException as e:
            self.logger.error(f"获取币安 {coin} ({network}) 提现手续费失败: {e}")
            return None
        except Exception as e:
            self.logger.error(f"获取币安 {coin} ({network}) 提现手续费时发生未知错误: {e}", exc_info=True)
            return None

    def get_withdraw_precision(self, coin: str, network: str) -> int | None:
        """获取币安指定币种在特定网络上的提现精度（小数位数）。"""
        if not self.client:
            self.logger.warning("币安客户端未初始化，无法获取提现精度。")
            return None
        try:
            # 尝试从缓存获取，减少API调用 (需要实现缓存机制，暂时不加)
            # coin_network_key = f"{coin}_{network}"
            # if coin_network_key in self._precision_cache:
            #    return self._precision_cache[coin_network_key]

            all_coins_info = self.client.get_all_coins_info()
            for coin_info in all_coins_info:
                if coin_info['coin'] == coin.upper():
                    for net_info in coin_info.get('networkList', []):
                        if net_info.get('network') == network.upper():
                            # 币安API通常不直接提供小数位数，而是提供最小提现单位或倍数
                            # 1. 尝试 'withdrawIntegerMultiple' 字段 (如果存在)
                            multiple_str = net_info.get('withdrawIntegerMultiple')
                            if multiple_str:
                                try:
                                    # 去掉尾随的0和小数点来计算精度
                                    if '.' in multiple_str:
                                        precision = len(multiple_str.split('.')[1].rstrip('0'))
                                    else:
                                        precision = 0 # 是整数倍
                                    self.logger.debug(f"通过 withdrawIntegerMultiple '{multiple_str}' 确定 {coin}-{network} 精度为: {precision}")
                                    # TODO: Add caching
                                    return precision
                                except Exception as e_mul:
                                    self.logger.warning(f"解析 withdrawIntegerMultiple '{multiple_str}' 出错: {e_mul}，尝试其他方法。")

                            # 2. 尝试根据 'withdrawMin' 或 'withdrawFee' 的小数位数推断 (不太可靠)
                            # 找到包含小数点的字段来尝试推断
                            field_to_infer = None
                            if net_info.get('withdrawMin') and '.' in net_info['withdrawMin']:
                                field_to_infer = net_info['withdrawMin']
                            elif net_info.get('withdrawFee') and '.' in net_info['withdrawFee']:
                                field_to_infer = net_info['withdrawFee']
                               
                            if field_to_infer:
                                try:
                                    # 计算小数位数 (去掉尾随0)
                                    precision = len(field_to_infer.split('.')[1].rstrip('0'))
                                    self.logger.debug(f"通过字段 '{field_to_infer}' 推断 {coin}-{network} 精度为: {precision}")
                                    # TODO: Add caching
                                    return precision
                                except Exception as e_infer:
                                    self.logger.warning(f"通过字段 '{field_to_infer}' 推断精度出错: {e_infer}")

                            # 3. 如果以上都失败，返回一个通用默认值或None
                            self.logger.warning(f"无法明确确定 {coin}-{network} 的提现精度，将返回默认值 None。")
                            return None # 或者返回一个通用默认值，如 8，但None更安全
                    # 如果找到币但没找到网络
                    self.logger.warning(f"在币安 {coin} 的网络列表中未找到网络 {network}。")
                    return None
            # 如果没找到币
            self.logger.warning(f"在币安所有币种信息中未找到币种 {coin}。")
            return None
        except BinanceAPIException as e:
            self.logger.error(f"获取币安币种信息以确定精度时出错: {e}")
            return None
        except Exception as e:
            self.logger.error(f"确定币安 {coin}-{network} 提现精度时发生未知错误: {e}", exc_info=True)
            return None

    def withdraw(self, coin: str, network: str, address: str, amount: str, memo: str | None = None) -> tuple[bool, str]:
        if not self.client:
            self.logger.error("无法提币：币安客户端未初始化。")
            return False, "客户端未初始化"
        
        try:
            # 确保 amount 是字符串类型，因为API对精度敏感
            params = {
                'coin': coin.upper(),
                'network': network.upper(),
                'address': address,
                'amount': amount # 直接使用传入的、已精确格式化的字符串
            }
            if memo and memo.strip():
                params['addressTag'] = memo

            self.logger.info(f"向币安发起提币请求 (使用精确字符串金额): {params}")
            response = self.client.withdraw(**params)
            self.logger.info(f"币安提币响应: {response}")
            if response and response.get('id'):
                return True, response.get('id') # Return withdrawal ID
            # The response format might vary, check Binance documentation for success indicators
            # Example: sometimes it might not have 'id' on immediate success but implies submitted.
            # For now, assuming 'id' means success.
            return False, response.get('msg', "提币请求提交，但未收到明确ID，请检查交易所记录。") if response else "未知响应"

        except BinanceAPIException as e:
            self.logger.error(f"币安提币API错误 (Coin: {coin}, Network: {network}, Amount: {amount}): {e}")
            return False, f"API错误: {e.message}"
        except BinanceOrderException as e:
            self.logger.error(f"币安提币订单错误 (Coin: {coin}, Network: {network}, Amount: {amount}): {e}")
            return False, f"订单错误: {e.message}"
        except Exception as e:
            self.logger.error(f"币安提币时发生未知错误 (Coin: {coin}, Network: {network}, Amount: {amount}): {e}", exc_info=True)
            return False, f"未知错误: {e}"

    def get_symbol_ticker(self, symbol: str) -> str | None:
        if not self.client:
            self.logger.warning("币安客户端未初始化。")
            return None
        try:
            ticker_info = self.client.get_symbol_ticker(symbol=symbol)
            if ticker_info and 'price' in ticker_info:
                return ticker_info['price']
            return None
        except BinanceAPIException as e:
            self.logger.error(f"获取币安 {symbol}价格失败: {e}")
            return None
        except Exception as e:
            self.logger.error(f"获取币安 {symbol}价格时发生未知错误: {e}", exc_info=True)
            return None

    # Implement other abstract methods from BaseExchangeAPI if they were not covered by the above
    # For example, get_all_coins_info was a method in the previous BaseExchangeAPI version
    # If it is still required by the new BaseExchangeAPI or used elsewhere, implement it.
    def get_all_coins_info(self) -> list:
        if not self.client: return []
        try:
            return self.client.get_all_coins_info()
        except Exception as e:
            self.logger.error(f"获取币安所有币种详细信息失败: {e}")
            return []

    def get_symbol_price_ticker(self, symbol: str) -> float | None:
        price_str = self.get_symbol_ticker(symbol)
        if price_str:
            try:
                return float(price_str)
            except ValueError:
                self.logger.error(f"无法将价格 '{price_str}' 转换为浮点数 for symbol {symbol}")
                return None
        return None

    def get_withdrawal_history(self, coin: str = None) -> list:
        if not self.client: return []
        try:
            params = {}
            if coin: params['coin'] = coin
            # Add other params like startTime, endTime if needed based on BaseExchangeAPI or usage
            return self.client.get_withdraw_history(**params)
        except Exception as e:
            self.logger.error(f"获取币安提现历史失败 (coin: {coin}): {e}")
            return []

    # This method was in the old BaseExchangeAPI, ensure its logic is covered or adapted.
    # The new get_withdrawal_fee is simpler.
    def get_withdrawal_fee_and_min(self, coin: str, network: str) -> tuple[float | None, float | None]:
        fee_str = self.get_withdrawal_fee(coin, network) # This now returns only the fee amount as string
        min_withdraw_val = None # Need to find min withdraw from coin_info

        if not self.client: return None, None
        try:
            all_coins_info = self.client.get_all_coins_info()
            for coin_info_item in all_coins_info:
                if coin_info_item['coin'] == coin:
                    for net_info in coin_info_item['networkList']:
                        if net_info['network'] == network and net_info['withdrawEnable']:
                            min_withdraw_str = net_info.get('withdrawMin')
                            if min_withdraw_str:
                                try:
                                    min_withdraw_val = float(min_withdraw_str)
                                except ValueError:
                                    self.logger.error(f"无法转换最小提现金额 '{min_withdraw_str}' 为浮点数 for {coin} on {network}")
                            fee_val = None
                            if fee_str:
                                try:
                                    fee_val = float(fee_str)
                                except ValueError:
                                     self.logger.error(f"无法转换手续费 '{fee_str}' 为浮点数 for {coin} on {network}")
                            return fee_val, min_withdraw_val
            return None, None # Fallback if not found
        except Exception as e:
            self.logger.error(f"获取币安 {coin} ({network}) 手续费和最小提现额时出错: {e}")
            return None, None

# 使用示例 (用于测试，实际使用时由主程序调用)
if __name__ == '__main__':
    # 需要替换为真实的API Key和Secret进行测试
    # 请勿在生产代码中硬编码密钥
    API_KEY = "YOUR_BINANCE_API_KEY"
    API_SECRET = "YOUR_BINANCE_API_SECRET"

    if API_KEY == "YOUR_BINANCE_API_KEY" or API_SECRET == "YOUR_BINANCE_API_SECRET":
        print("请替换为真实的币安API Key和Secret以进行测试。")
    else:
        binance_api = BinanceAPI(config=None, logger=None)
        if binance_api.connect():
            print("成功连接到币安API。")

            # 测试获取服务器时间偏移
            # print(f"服务器时间偏移: {binance_api.time_offset} ms")
            # print(f"补偿后时间戳: {binance_api.get_timestamp()}")

            # 测试获取所有币种信息
            # try:
            #     all_coins = binance_api.get_all_coins_info()
            #     print(f"获取到 {len(all_coins)} 个币种的信息。")
            #     if all_coins:
            #         print(f"例如，第一个币种: {all_coins[0]['coin']}, 网络: {all_coins[0]['networkList'][0]['network']}")
            # except BinanceExchangeAPIException as e:
            #     print(f"获取币种信息失败: {e}")

            # 测试获取特定币种网络
            # try:
            #     eth_networks = binance_api.get_networks_for_coin("ETH")
            #     print(f"ETH 支持的网络: {eth_networks}")
            #     usdt_networks = binance_api.get_networks_for_coin("USDT")
            #     print(f"USDT 支持的网络: {usdt_networks}")
            #     non_exist_networks = binance_api.get_networks_for_coin("NONEXISTCOIN")
            #     print(f"NONEXISTCOIN 支持的网络: {non_exist_networks}")
            # except BinanceExchangeAPIException as e:
            #     print(f"获取网络列表失败: {e}")


            # 测试获取余额
            # try:
            #     usdt_balance = binance_api.get_balance("USDT")
            #     print(f"USDT 余额: {usdt_balance}")
            #     btc_balance = binance_api.get_balance("BTC")
            #     print(f"BTC 余额: {btc_balance}")
            # except BinanceExchangeAPIException as e:
            #     print(f"获取余额失败: {e}")

            # 测试获取提币费用和最小提币量
            # try:
            #     fee, min_w = binance_api.get_withdrawal_fee_and_min("USDT", "TRX") # TRC20
            #     if fee is not None:
            #         print(f"USDT on TRX: Fee={fee}, Min Withdraw={min_w}")
            #     else:
            #         print("未能获取USDT on TRX的费用信息")
                
            #     fee_eth, min_w_eth = binance_api.get_withdrawal_fee_and_min("ETH", "ETH") # ERC20
            #     if fee_eth is not None:
            #         print(f"ETH on ETH (ERC20): Fee={fee_eth}, Min Withdraw={min_w_eth}")
            #     else:
            #         print("未能获取ETH on ETH的费用信息")
            # except BinanceExchangeAPIException as e:
            #     print(f"获取提币费用失败: {e}")

            # 测试获取价格
            # try:
            #     eth_price = binance_api.get_symbol_price_ticker("ETHUSDT")
            #     print(f"ETHUSDT 当前价格: {eth_price}")
            # except BinanceExchangeAPIException as e: # get_symbol_price_ticker 内部已打印错误
            #     pass
            
            # 测试提币历史
            # try:
            #     withdraw_history = binance_api.get_withdrawal_history("USDT")
            #     print(f"获取到 {len(withdraw_history)} 条USDT提币历史。")
            #     if withdraw_history:
            #         print("最近一条提币历史:", withdraw_history[0])
            # except BinanceExchangeAPIException as e:
            #     print(f"获取提币历史失败: {e}")


            # 注意：实际提币测试需要有效的地址、足够的金额，并且API密钥有提币权限
            # 请谨慎操作，避免资金损失
            # try:
            #     # 替换为真实的测试参数
            #     # result = binance_api.withdraw("USDT", "TEST_ADDRESS", 10.0, "TRX", name="TestWithdraw")
            #     # print(f"提币请求结果: {result}")
            #     pass
            # except BinanceAPIException as e: # 明确捕获Binance的异常
            #     print(f"提币失败 (BinanceAPIException): {e.status_code} - {e.message}")
            # except BinanceExchangeAPIException as e: # 捕获自定义的包装异常
            #     print(f"提币失败 (BinanceExchangeAPIException): {e}")
            # except Exception as e:
            #     print(f"提币过程中发生未知错误: {e}")

        else:
            print("连接到币安API失败。") 