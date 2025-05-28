import time
import okx.Account as Account # OKX SDK 的账户模块
import okx.Funding as Funding # OKX SDK 的资金模块
import okx.PublicData as PublicData # OKX SDK 的公共数据模块
# 可能还需要其他模块，例如 Trade

from exchange_api_base import BaseExchangeAPI
from decimal import Decimal
import logging # Added
from configparser import ConfigParser # Added

# 自定义OKX特定的异常
class OKXExchangeAPIException(Exception):
    pass

class OKXAPI(BaseExchangeAPI):
    """OKX交易所API实现"""

    def __init__(self, config: ConfigParser, logger: logging.Logger):
        super().__init__(config, logger)
        self.api_key = ""
        self.api_secret = ""
        self.passphrase = ""
        self.simulated = False # 0 for real trading, 1 for demo trading
        self.timestamp_error_detected = False # 新增标志位
        
        # OKX SDK clients will be initialized in connect()
        self.accountAPI = None
        self.fundingAPI = None
        self.publicDataAPI = None
        # self.tradeAPI = None

    def connect(self) -> tuple[bool, str]:
        self.api_key = self.config.get('OKX', 'api_key', fallback='')
        self.api_secret = self.config.get('OKX', 'api_secret', fallback='')
        self.passphrase = self.config.get('OKX', 'passphrase', fallback='')
        simulated_str = self.config.get('GENERAL', 'okx_simulated', fallback='False')
        self.simulated = True if simulated_str.lower() == 'true' else False
        self.timestamp_error_detected = False # 重置标志位
        
        flag = "1" if self.simulated else "0" # 0:real trading; 1:demo trading

        if not self.api_key or not self.api_secret or not self.passphrase:
            self.logger.error("OKX API Key, Secret, 或 Passphrase 未在配置文件中设置。")
            return False, "API Key, Secret, 或 Passphrase 未配置"

        try:
            # Initialize APIs
            self.accountAPI = Account.AccountAPI(self.api_key, self.api_secret, self.passphrase, False, flag)
            self.fundingAPI = Funding.FundingAPI(self.api_key, self.api_secret, self.passphrase, False, flag)
            self.publicDataAPI = PublicData.PublicAPI(flag=flag) # debug=False is default
            # self.tradeAPI = Trade.TradeAPI(self.api_key, self.api_secret, self.passphrase, False, flag)

            test_call = self.accountAPI.get_account_balance() # Use a call that requires auth
            if test_call and test_call.get('code') == '0': # '0' indicates success for OKX
                self.logger.info(f"成功连接到 OKX ({'模拟盘' if self.simulated else '实盘'})。")
                # 计算并存储时间偏移，确保 get_server_time_offset 已正确实现
                self.time_offset = self.get_server_time_offset() 
                self.logger.info(f"OKX 服务器时间偏移已计算并设置: {self.time_offset} ms (本地 - 服务器)")
                self.timestamp_error_detected = False # 确保连接成功时重置
                return True, "连接成功"
            else:
                error_msg = test_call.get('msg', '连接测试失败，未知响应。')
                error_code = test_call.get('code')
                self.logger.error(f"连接 OKX 失败: {error_msg} (Code: {error_code})")
                # 检查时间戳相关错误
                l_error_msg = error_msg.lower()
                # OKX 错误码 50100: "Request time is earlier than server time or later than server time (request time needs to be within plus or minus 30s compared to server time)"
                # OKX 错误码 50101: "Request timestamp expired" (旧版或特定场景)
                # OKX 错误码 50011: "Invalid Signature" (也可能由时间戳问题间接触发)
                # 关键词: "timestamp", "expired", "invalid key", "time", "date", "signature"
                if error_code == '50100' or error_code == '50101' or \
                   ("timestamp" in l_error_msg or "expired" in l_error_msg or "time" in l_error_msg or "date" in l_error_msg) or \
                   (error_code == '50011' and ("timestamp" in l_error_msg or "time" in l_error_msg)): # Invalid Signature 也可能与时间有关
                    self.timestamp_error_detected = True
                    self.logger.error("检测到OKX API时间戳错误或相关问题 (连接测试时)。请检查系统时间。")
                    return False, f"连接测试失败: {error_msg} (错误码: {error_code} - 时间戳可能不同步，请检查系统时间)"
                return False, f"连接测试失败: {error_msg} (错误码: {error_code})"

        except Exception as e: # 通常SDK会捕获API异常并返回上述的 code/msg 结构
            self.logger.error(f"连接 OKX 时发生未知错误: {e}", exc_info=True)
            # 未知错误也可能与时间戳有关，如果错误信息包含关键词
            l_e_str = str(e).lower()
            if "timestamp" in l_e_str or "expired" in l_e_str or "time" in l_e_str or "date" in l_e_str:
                self.timestamp_error_detected = True
                self.logger.error("检测到OKX API时间戳错误或相关问题 (连接时发生未知异常)。请检查系统时间。")
                return False, f"未知连接错误: {e} (时间戳可能不同步，请检查系统时间)"
            return False, f"未知连接错误: {e}"

    def close(self):
        self.logger.info(f"OKXAPI: 清理客户端实例。")
        self.accountAPI = None
        self.fundingAPI = None
        self.publicDataAPI = None
        pass

    def get_all_tradable_coins(self) -> list[str]:
        if not self.fundingAPI:
            self.logger.warning("OKX FundingAPI 未初始化 (get_all_tradable_coins)。")
            return []
        try:
            result = self.fundingAPI.get_currencies() 
            if result and result.get('code') == '0' and result.get('data'):
                tradable_coins = [
                    item['ccy'] for item in result['data'] 
                    if item.get('canWd') # Ensure it can be withdrawn
                ]
                unique_coins = sorted(list(set(tradable_coins)))
                self.logger.info(f"OKX: 获取到 {len(unique_coins)} 个可提币种。")
                self.timestamp_error_detected = False # 获取成功，重置标志 (如果之前被其他错误调用设为True)
                return unique_coins
            else:
                error_msg = result.get('msg', '未能获取币种信息')
                error_code = result.get('code')
                self.logger.error(f"获取OKX币种列表失败: {error_msg} (Code: {error_code})")
                # 检查时间戳相关错误
                l_error_msg = error_msg.lower()
                if error_code == '50100' or error_code == '50101' or \
                   ("timestamp" in l_error_msg or "expired" in l_error_msg or "time" in l_error_msg or "date" in l_error_msg) or \
                   (error_code == '50011' and ("timestamp" in l_error_msg or "time" in l_error_msg)):
                    self.timestamp_error_detected = True
                    self.logger.error("检测到OKX API时间戳错误或相关问题 (获取币种列表时)。请检查系统时间。")
                return []
        except Exception as e:
            self.logger.error(f"获取OKX币种列表时发生未知错误: {e}", exc_info=True)
            l_e_str = str(e).lower()
            if "timestamp" in l_e_str or "expired" in l_e_str or "time" in l_e_str or "date" in l_e_str:
                self.timestamp_error_detected = True
                self.logger.error("检测到OKX API时间戳错误或相关问题 (获取币种列表时发生未知异常)。请检查系统时间。")
            return []
            
    def get_balance(self, asset: str) -> str | None:
        self.logger.info(f"OKXAPI.get_balance called for asset: {asset}")
        if not self.fundingAPI:
            self.logger.error("OKX FundingAPI not initialized.")
            return None
        try:
            result = self.fundingAPI.get_balances(ccy=asset.upper())
            self.logger.debug(f"OKX get_balances response for {asset}: {result}")

            if result and result.get('code') == '0' and result.get('data'):
                data = result['data']
                if data and isinstance(data, list) and len(data) > 0:
                    asset_details = data[0] 
                    balance = asset_details.get('bal') 
                    if balance is None: 
                        balance = asset_details.get('availBal')
                    
                    if balance is not None:
                        self.logger.info(f"OKX balance for {asset}: {balance}")
                        return str(balance)
                    else:
                        self.logger.warning(f"No 'bal' or 'availBal' field found for {asset} in OKX response data[0]: {asset_details}. Assuming 0 balance.")
                        return "0"
                else: 
                    self.logger.warning(f"OKX get_balances data for {asset} is empty or not a list: {data}. Assuming 0 balance.")
                    return "0"
            else:
                self.logger.error(f"Failed to get balance for {asset} from OKX. Code: {result.get('code')}, Msg: {result.get('msg')}")
                return None
        except Exception as e:
            self.logger.error(f"Exception getting balance for {asset} from OKX: {e}", exc_info=True)
            return None

    def get_networks_for_coin(self, coin: str) -> list[str]:
        if not self.fundingAPI:
            self.logger.warning("OKX FundingAPI 未初始化 (get_networks_for_coin)。")
            return []
        try:
            result = self.fundingAPI.get_currencies(ccy=coin)
            networks = []
            self.logger.debug(f"OKX raw currency info for {coin}: {result}") # Log raw response
            if result and result.get('code') == '0' and result.get('data'):
                for item in result['data']:
                    # Log each item being processed for the specific coin
                    if item.get('ccy') == coin:
                        raw_chain_name = item.get('chain')
                        can_withdraw = item.get('canWd')
                        self.logger.debug(f"  Processing item for {coin}: chain='{raw_chain_name}', canWd={can_withdraw}")

                        # Only proceed if withdraw is enabled and chain name exists
                        if can_withdraw and raw_chain_name:
                            # Normalization logic
                            normalized_network = raw_chain_name # Default to raw name
                            if f"{coin}-" in raw_chain_name: 
                                normalized_network = raw_chain_name.split(f"{coin}-", 1)[-1]
                                self.logger.debug(f"    Normalized '{raw_chain_name}' to '{normalized_network}'")
                            else:
                                self.logger.debug(f"    Using raw chain name '{normalized_network}' as network.")
                            
                            # Log before adding
                            self.logger.debug(f"    Adding network '{normalized_network}' to list for {coin}.")
                            networks.append(normalized_network)
                        elif raw_chain_name: # Log why it was skipped if chain name exists but canWd is false
                             self.logger.debug(f"  Skipping chain '{raw_chain_name}' for {coin} because canWd is {can_withdraw}.")
                        else:
                             self.logger.debug(f"  Skipping item for {coin} due to missing chain name.")
                       
                unique_networks = sorted(list(set(networks)))
                self.logger.info(f"OKX: 为币种 {coin} 获取到网络: {unique_networks}")
                return unique_networks
            else:
                error_msg = result.get('msg', f'未能获取 {coin} 的网络信息')
                self.logger.error(f"获取OKX {coin} 网络信息失败: {error_msg} (Code: {result.get('code')})")
                return []
        except Exception as e:
            self.logger.error(f"获取OKX {coin} 网络信息时发生未知错误: {e}", exc_info=True)
            return []

    def get_withdrawal_fee(self, coin: str, network: str, amount: float | None = None) -> str | dict | None:
        if not self.fundingAPI:
            self.logger.warning("OKX FundingAPI 未初始化 (get_withdrawal_fee)。")
            return None
        try:
            currencies_info = self.fundingAPI.get_currencies(ccy=coin)
            if currencies_info and currencies_info.get('code') == '0' and currencies_info.get('data'):
                for item in currencies_info['data']:
                    if item.get('ccy') == coin and item.get('canWd'):
                        normalized_chain_name = item['chain']
                        if f"{coin}-" in normalized_chain_name:
                            normalized_chain_name = normalized_chain_name.split(f"{coin}-", 1)[-1]

                        if normalized_chain_name == network:
                            fee_amount = item.get('minFee') 
                            if fee_amount is not None:
                                self.logger.info(f"OKX: {coin} 在网络 {network} (原始链: {item['chain']}) 的手续费: {fee_amount}")
                                return str(Decimal(fee_amount)) 
                            else:
                                self.logger.warning(f"OKX: 未找到 {coin} ({network}) 的手续费信息 (minFee is None)。")
                                return None
                self.logger.warning(f"OKX: 未找到币种 {coin} 对应的网络 {network} 或该网络不可提现。")
                return None
            else:
                error_msg = currencies_info.get('msg', '获取币种/手续费信息失败')
                self.logger.error(f"获取OKX {coin} ({network}) 提现手续费失败 (API): {error_msg}")
                return None
        except Exception as e:
            self.logger.error(f"获取OKX {coin} ({network}) 提现手续费时发生未知错误: {e}", exc_info=True)
            return None

    def get_withdraw_precision(self, coin: str, network: str) -> int | None:
        """获取OKX指定币种在特定网络上的提现精度（小数位数）。"""
        if not self.fundingAPI:
            self.logger.warning("OKX FundingAPI 未初始化 (get_withdraw_precision)。")
            return None
        try:
            result = self.fundingAPI.get_currencies(ccy=coin)
            if result and result.get('code') == '0' and result.get('data'):
                for item in result['data']:
                    if item.get('ccy') == coin.upper() and item.get('canWd'): # Check if withdraw is enabled
                        # Normalize the chain name from OKX API
                        raw_chain_name = item.get('chain', '')
                        normalized_network = raw_chain_name
                        if f"{coin.upper()}-" in raw_chain_name:
                            normalized_network = raw_chain_name.split(f"{coin.upper()}-", 1)[-1]
                        
                        if normalized_network.upper() == network.upper():
                            # Found the matching coin and network
                            min_wd_str = item.get('minWd') # Minimum withdrawal amount string
                            if min_wd_str and isinstance(min_wd_str, str):
                                try:
                                    if '.' in min_wd_str:
                                        # Precision is the number of digits after the decimal point
                                        precision = len(min_wd_str.split('.', 1)[1])
                                        self.logger.debug(f"根据 minWd '{min_wd_str}' 确定 OKX {coin}-{network} 精度为: {precision}")
                                        return precision
                                    else:
                                        # If minWd is an integer string, precision is 0
                                        self.logger.debug(f"根据 minWd '{min_wd_str}' 确定 OKX {coin}-{network} 精度为: 0")
                                        return 0
                                except Exception as e_prec:
                                    self.logger.warning(f"解析 minWd '{min_wd_str}' 以获取精度时出错: {e_prec}")
                            else:
                                self.logger.warning(f"未在 OKX {coin}-{network} 的信息中找到 minWd 字段。")
                            
                            # Fallback if minWd parsing fails or is missing
                            break # Found the network, stop searching item list
                        
                # If loop finished without finding the network or precision
                self.logger.warning(f"无法确定 OKX {coin}-{network} 的提现精度 (未找到匹配网络或minWd信息)。")
                return None # Or return a default like 8?
            else:
                error_msg = result.get('msg', '获取币种信息失败')
                self.logger.error(f"获取OKX币种信息以确定精度失败: {error_msg} (Code: {result.get('code')})")
                return None
        except Exception as e:
            self.logger.error(f"确定OKX {coin}-{network} 提现精度时发生未知错误: {e}", exc_info=True)
            return None

    def withdraw(self, coin: str, network: str, address: str, amount: str, memo: str | None = None) -> tuple[bool, str]: # amount type hint is str
        if not self.fundingAPI:
            self.logger.error("无法提币：OKX FundingAPI 未初始化。")
            return False, "客户端未初始化"

        # --- (Keep existing logic to find chain_to_use and actual_fee_for_chain_str) ---
        chain_to_use = None
        actual_fee_for_chain_str = None # Initialize
        try:
            # Find the correct chain name (e.g., ETH-ERC20) and fee
            currencies_info = self.fundingAPI.get_currencies(ccy=coin)
            if currencies_info and currencies_info.get('code') == '0' and currencies_info.get('data'):
                for item in currencies_info['data']:
                    if item.get('ccy') == coin.upper() and item.get('canWd'):
                        raw_chain_name = item.get('chain', '')
                        normalized_network = raw_chain_name
                        if f"{coin.upper()}-" in raw_chain_name:
                            normalized_network = raw_chain_name.split(f"{coin.upper()}-", 1)[-1]
                        
                        if normalized_network.upper() == network.upper():
                            chain_to_use = item['chain']
                            actual_fee_for_chain_str = item.get('minFee') # Assuming minFee is the fee to use
                            break # Found the network
            
            if not chain_to_use:
                self.logger.error(f"OKX提币失败：无法确定币种 {coin} 在网络 {network} 上的有效链名称({chain_to_use})。")
                return False, f"无效网络/币种组合: {coin}-{network}"

            if actual_fee_for_chain_str is None: # Check if fee was found
                 self.logger.error(f"OKX提币失败：无法获取链 {chain_to_use} 的提现手续费 (minFee)。")
                 return False, f"无法获取手续费 for {chain_to_use}"

        except Exception as e_chain_fee:
            self.logger.error(f"查找 OKX 链名或手续费时出错: {e_chain_fee}", exc_info=True)
            return False, f"查找链名/手续费错误: {e_chain_fee}"
        # --- (End of existing logic finding chain_to_use and fee) ---

        try:
            self.logger.info(f"向OKX发起提币请求: Coin={coin}, Chain={chain_to_use}, Addr={address}, Amt={amount}, Fee={actual_fee_for_chain_str}, Memo={memo}")
            
            # The amount is already a formatted string
            # OKX SDK Funding.FundingAPI.withdrawal params: ccy, amt, dest, toAddr, fee, chain
            # dest: 3-Unified account, 4-Funding account. For external, toAddr implies dest.
            # fee: Use the fee obtained earlier.
            # toAddr: The address, potentially with memo included based on OKX rules for the coin.
            
            result = self.fundingAPI.withdrawal(
                ccy=coin.upper(),
                amt=amount, # Pass the formatted string amount
                dest='4', # 4: Digital currency address (external on-chain withdrawal)
                toAddr=address, # Address might include memo/tag (e.g., addr:tag)
                chain=chain_to_use # Pass the specific chain name found
                # If memo/tag is separate for this coin/network on OKX API, pass it as **kwargs if SDK allows
                # memo=memo, # Example if SDK had a memo kwarg
                # tag=memo, # Example if SDK had a tag kwarg
            )
            
            self.logger.info(f"OKX提币响应: {result}")

            if result and result.get('code') == '0' and result.get('data'):
                data = result['data']
                if data and isinstance(data, list) and data[0].get('wdId'):
                    return True, data[0]['wdId'] # Return withdrawal ID
                else:
                    # Success code '0' but no wdId found? Treat as submitted? 
                    self.logger.warning(f"OKX提币请求成功 (Code 0)，但未找到wdId。Data: {data}")
                    return True, "请求已提交，但未返回提币ID" # Or False? Let's be optimistic
            else:
                error_msg = result.get('msg', '未知API错误')
                error_code = result.get('code', 'N/A')
                self.logger.error(f"OKX提币API错误 (Code: {error_code}): {error_msg}")
                return False, f"OKX错误 (Code: {error_code}): {error_msg}"

        except Exception as e:
            self.logger.error(f"OKX提币时发生未知错误: {e}", exc_info=True)
            return False, f"未知错误: {e}"

    def get_symbol_ticker(self, symbol: str) -> str | None: # symbol e.g. BTC-USDT
        if not self.publicDataAPI:
            self.logger.warning("OKX PublicDataAPI 未初始化 (get_symbol_ticker)。")
            return None
        try:
            # OKX symbol format is "COIN-QUOTE", e.g., "BTC-USDT".
            # Main app should provide it in this format.
            self.logger.debug(f"OKX: 请求获取价格，交易对: {symbol}")
            result = self.publicDataAPI.get_ticker(instId=symbol) 
            
            # 添加详细日志，帮助调试
            self.logger.debug(f"OKX get_ticker 原始响应 for {symbol}: {result}") # 明确是哪个symbol的响应
            
            if result and result.get('code') == '0' and result.get('data'):
                ticker_data = result['data'] 
                # 确保ticker_data是列表并且非空
                if isinstance(ticker_data, list) and ticker_data: 
                    # 检查第一个元素是否包含'last'键
                    if 'last' in ticker_data[0] and ticker_data[0]['last'] is not None:
                        price = ticker_data[0]['last']
                        # 确保价格不是一个空字符串或其他无效值，再尝试Decimal转换
                        if isinstance(price, (str, int, float)) and str(price).strip():
                            try:
                                decimal_price = Decimal(str(price))
                                self.logger.info(f"OKX: 获取到 {symbol} 的价格: {decimal_price}")
                                return str(decimal_price) 
                            except Exception as e:
                                self.logger.error(f"OKX: 转换价格 '{price}' 为Decimal失败 for {symbol}: {e}")
                                return None
                        else:
                            self.logger.warning(f"OKX: {symbol} 的价格字段 'last' 值无效: '{price}'。 ticker_data[0]: {ticker_data[0]}")
                            return None
                    else:
                        self.logger.warning(f"OKX: 在 {symbol} 的ticker_data[0]中未找到'last'键或其值为None。 ticker_data[0]: {ticker_data[0]}")
                        return None
                else: # ticker_data 不是列表，或为空列表
                    self.logger.warning(f"OKX: {symbol} 的ticker_data格式不符合预期（非列表或空列表）。 ticker_data: {ticker_data}")
                    return None
            else: # API调用失败或data字段不存在/为空
                error_msg = result.get('msg', f'未能获取 {symbol} 的价格')
                error_code = result.get('code', 'N/A') # 使用N/A如果code也没有
                self.logger.error(f"获取OKX {symbol} 价格失败: {error_msg} (Code: {error_code})")
                return None
        except Exception as e:
            self.logger.error(f"获取OKX {symbol} 价格时发生未知严重错误: {e}", exc_info=True)
            return None

    def get_all_coins_info(self) -> list: 
        if not self.fundingAPI:
            self.logger.warning("OKX FundingAPI 未初始化 (get_all_coins_info)。")
            return []
        try:
            result = self.fundingAPI.get_currencies()
            if result and result.get('code') == '0' and result.get('data'):
                okx_data = result['data']
                coins_dict = {} 
                for item in okx_data:
                    coin_code = item.get('ccy')
                    if not coin_code: continue

                    if coin_code not in coins_dict:
                        coins_dict[coin_code] = {'coin': coin_code, 'networkList': []}
                    
                    chain_full = item.get('chain', '')
                    network_part = chain_full
                    if f"{coin_code}-" in chain_full: # Normalize e.g. "USDT-TRC20" -> "TRC20"
                        network_part = chain_full.split(f"{coin_code}-", 1)[-1]
                    
                    if not network_part: continue # Skip if no distinct network part

                    network_info = {
                        'network': network_part, 
                        'originalChain': chain_full, 
                        'withdrawEnable': item.get('canWd', False),
                        'withdrawFee': item.get('minFee'), 
                        'withdrawMin': item.get('minWd'), 
                    }
                    coins_dict[coin_code]['networkList'].append(network_info)
                
                self.logger.info(f"OKX: 成功转换 {len(coins_dict)} 种币种的详细信息。")
                return list(coins_dict.values())
            else:
                error_msg = result.get('msg', '获取所有币种详细信息失败')
                self.logger.error(f"OKX get_all_coins_info API error: {error_msg} (Code: {result.get('code')})")
                return []
        except Exception as e:
            self.logger.error(f"OKX get_all_coins_info 未知错误: {e}", exc_info=True)
            return []

    def get_withdrawal_history(self, coin: str = None) -> list:
        if not self.fundingAPI:
            self.logger.warning("OKX FundingAPI 未初始化 (get_withdrawal_history)。")
            return []
        try:
            params = {}
            if coin:
                params['ccy'] = coin
            
            result = self.fundingAPI.get_withdrawal_history(**params)
            if result and result.get('code') == '0' and result.get('data'):
                history_data = result['data']
                formatted_history = []
                for item in history_data:
                    status_text = self._map_okx_withdraw_status(item.get('state'))
                    apply_time_ms = int(item.get('ts', 0)) 

                    formatted_item = {
                        'id': item.get('wdId'),
                        'amount': str(Decimal(item.get('amt', '0'))),
                        'address': item.get('to'), 
                        'coin': item.get('ccy'),
                        'network': item.get('chain'), 
                        'status_code': item.get('state'),
                        'status_text': status_text,
                        'txId': item.get('txId'),
                        'applyTime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(apply_time_ms / 1000)) if apply_time_ms else None,
                        'transactionFee': str(Decimal(item.get('fee', '0')))
                    }
                    formatted_history.append(formatted_item)
                self.logger.info(f"OKX: 获取到 {len(formatted_history)} 条提现历史记录。")
                return formatted_history
            else:
                error_msg = result.get('msg', '获取提现历史失败')
                self.logger.error(f"获取OKX提现历史失败: {error_msg} (Code: {result.get('code')})")
                return []
        except Exception as e:
            self.logger.error(f"获取OKX提现历史时发生未知错误: {e}", exc_info=True)
            return []
            
    def _map_okx_withdraw_status(self, status_code_str: str) -> str:
        status_map = {
            "-2": "已取消", "-1": "失败", "0": "等待提现", 
            "1": "提现中", "2": "提现成功", "7": "已批准", 
            "8": "等待转账", "10": "等待划拨"
        }
        return status_map.get(status_code_str, f"未知状态 ({status_code_str})")

    def get_server_time_offset(self) -> int:
        """
        获取本地时间与OKX服务器时间的毫秒级偏移。
        计算方式: 本地时间戳 - 服务器时间戳。
        """
        if not self.publicDataAPI:
            self.logger.error("OKX PublicDataAPI (PublicAPI) 未初始化，无法获取服务器时间偏移。")
            return 0
        try:
            # 获取服务器时间
            result = self.publicDataAPI.get_system_time()
            self.logger.debug(f"OKX get_system_time response: {result}")
            if result and result.get('code') == '0' and result.get('data'):
                server_time_ms = int(result['data'][0]['ts'])
                local_time_ms = int(time.time() * 1000)
                offset = local_time_ms - server_time_ms
                self.logger.debug(f"计算出的OKX服务器时间偏移 (本地 - 服务器): {offset} ms")
                return offset
            else:
                error_msg = result.get('msg', '未能从OKX获取有效的服务器时间')
                self.logger.error(f"获取OKX服务器时间失败: {error_msg} (Code: {result.get('code')})")
                return 0
        except Exception as e:
            self.logger.error(f"获取OKX服务器时间时发生未知错误: {e}", exc_info=True)
            return 0

    def get_symbol_price_ticker(self, symbol: str) -> float | None:
        price_str = self.get_symbol_ticker(symbol) # Returns string
        if price_str:
            try:
                return float(price_str)
            except ValueError:
                self.logger.error(f"OKX: 无法将价格 '{price_str}' 转换为浮点数 for symbol {symbol}")
                return None
        return None

    def get_withdrawal_fee_and_min(self, coin: str, network: str) -> tuple[float | None, float | None]:
        fee_str = self.get_withdrawal_fee(coin, network) 
        min_w_val = None

        all_coin_details = self.get_all_coins_info() 
        for coin_detail in all_coin_details:
            if coin_detail.get('coin') == coin:
                for net_info in coin_detail.get('networkList', []):
                    if net_info.get('network') == network and net_info.get('withdrawEnable'):
                        min_w_str = net_info.get('withdrawMin')
                        if min_w_str is not None:
                            try: min_w_val = float(min_w_str)
                            except ValueError: self.logger.error(f"OKX: 无法转换最小提现额 '{min_w_str}' for {coin}-{network}")
                        break 
                break 
        
        fee_val = None
        if fee_str is not None:
            try: fee_val = float(fee_str)
            except ValueError: self.logger.error(f"OKX: 无法转换手续费 '{fee_str}' for {coin}-{network}")
        
        if fee_val is None and min_w_val is None:
             self.logger.debug(f"OKX: 未能解析 {coin}-{network} 的手续费或最小提现额。 Fee str: {fee_str}")
        return fee_val, min_w_val

# 使用示例 (用于测试)
if __name__ == '__main__':
    # 替换为真实的OKX API Key, Secret, Passphrase
    # 确保在模拟盘测试，或使用小额资金在实盘测试，并注意安全
    OKX_API_KEY = "YOUR_OKX_API_KEY"
    OKX_API_SECRET = "YOUR_OKX_API_SECRET"
    OKX_PASSPHRASE = "YOUR_OKX_PASSPHRASE"
    IS_SIMULATED = True # True 使用模拟盘, False 使用实盘

    if OKX_API_KEY == "YOUR_OKX_API_KEY":
        print("请替换为真实的OKX API凭证进行测试。")
    else:
        okx_api = OKXAPI(config=ConfigParser(), logger=logging.getLogger(__name__))
        if okx_api.connect():
            print(f"成功连接到OKX API ({'模拟盘' if IS_SIMULATED else '实盘'})。")
            
            # 测试获取服务器时间
            # server_offset = okx_api.get_server_time_offset()
            # if server_offset is not None:
            #     print(f"OKX服务器时间偏移: {server_offset} ms")
            # else:
            #     print("未能获取OKX服务器时间偏移。")

            # 测试获取所有币种信息
            # try:
            #     all_okx_coins = okx_api.get_all_coins_info()
            #     print(f"获取到 {len(all_okx_coins)} 个OKX币种的信息。")
            #     if all_okx_coins:
            #         for c in all_okx_coins[:2]: # 打印前两个币种信息
            #             print(f"  Coin: {c['coin']}, Name: {c.get('name')}, CanWd: {c.get('canWd')}")
            #             if c.get('networkList'):
            #                 print(f"    Networks for {c['coin']}:")
            #                 for net in c['networkList'][:2]: # 打印前两个网络
            #                     print(f"      - {net['network']}: Fee={net['withdrawFee']}, MinWd={net['withdrawMin']}, Enabled={net['withdrawEnable']}")
            # except OKXExchangeAPIException as e:
            #     print(f"获取OKX币种信息失败: {e}")

            # 测试获取特定币种网络
            # try:
            #     usdt_nets = okx_api.get_networks_for_coin("USDT")
            #     print(f"USDT on OKX supports networks: {usdt_nets}")
            # except OKXExchangeAPIException as e:
            #     print(f"获取USDT网络列表失败: {e}")
            
            # 测试获取余额
            # try:
            #     usdt_bal = okx_api.get_balance("USDT")
            #     print(f"USDT balance on OKX: {usdt_bal}")
            #     btc_bal = okx_api.get_balance("BTC")
            #     print(f"BTC balance on OKX: {btc_bal}")
            # except OKXExchangeAPIException as e:
            #     print(f"获取OKX余额失败: {e}")

            # 测试获取提币费用和最小提币量
            # try:
            #     # 注意：网络名称需要与get_all_coins_info返回的networkList中的名称一致
            #     # 例如，对于USDT的TRC20网络，如果get_all_coins_info中networkList的network是'TRC20'，则用'TRC20'
            #     fee, min_w = okx_api.get_withdrawal_fee_and_min("USDT", "USDT-TRC20") # 或者 "TRC20"，取决于get_all_coins_info的解析
            #     if fee is not None:
            #         print(f"USDT on TRC20 (OKX): Fee={fee}, Min Withdraw={min_w}")
            #     else:
            #         print("未能获取USDT on TRC20 (OKX)的费用信息")
            # except OKXExchangeAPIException as e:
            #     print(f"获取提币费用失败 (OKX): {e}")

            # 测试获取价格
            # try:
            #     btc_price = okx_api.get_symbol_price_ticker("BTC-USDT")
            #     print(f"BTC-USDT price on OKX: {btc_price}")
            # except Exception as e:
            #     print(f"获取价格失败: {e}")

            # 测试提币历史
            # try:
            #     okx_history = okx_api.get_withdrawal_history("USDT")
            #     print(f"获取到 {len(okx_history)} 条OKX USDT提币历史。")
            #     if okx_history:
            #         print("最近一条OKX提币历史:", okx_history[0])
            # except OKXExchangeAPIException as e:
            #     print(f"获取OKX提币历史失败: {e}")
            
            # 提币测试 (请极其小心，确保是模拟盘或小额)
            # try:
            #     # withdraw_amount = 0.01 # 测试金额
            #     # withdraw_address = "YOUR_TEST_ADDRESS_FOR_USDT_ON_SELECTED_NETWORK"
            #     # withdraw_network_okx = "USDT-TRC20" # 或其他你查询到的可用网络，如 "TRC20"
            #     # withdraw_coin_okx = "USDT"
            #     # fee_for_withdraw, _ = okx_api.get_withdrawal_fee_and_min(withdraw_coin_okx, withdraw_network_okx)
            #     # if fee_for_withdraw is not None:
            #     #     print(f"Attempting to withdraw {withdraw_amount} {withdraw_coin_okx} to {withdraw_address} via {withdraw_network_okx} with fee {fee_for_withdraw}")
            #     #     result = okx_api.withdraw(withdraw_coin_okx, withdraw_network_okx, withdraw_address, withdraw_amount)
            #     #     print(f"OKX withdrawal result: {result}")
            #     # else:
            #     #     print(f"Could not determine fee for withdrawal, aborting test.")
            #     pass
            # except OKXExchangeAPIException as e:
            #     print(f"OKX withdrawal test failed: {e}")

        else:
            print("连接到OKX API失败。") 