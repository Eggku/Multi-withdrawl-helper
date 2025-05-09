import re
from eth_utils import is_hex_address, to_checksum_address
import base58
import base64
import binascii

class AddressValidator:
    """加密货币地址验证器类，用于验证不同类型的地址格式"""
    
    def __init__(self, logger):
        self.logger = logger
        self.logger.debug("AddressValidator initialized.")

    @staticmethod
    def requires_api(coin):
        """判断特定币种是否需要API进行地址验证
        
        参数:
            coin: 币种名称
            
        返回:
            bool: 是否需要API验证
        """
        # 一些币种可以通过正则表达式等本地方式验证，无需API
        # 而另一些币种可能需要通过API验证地址的有效性
        # 这里根据币种类型返回是否需要API
        local_validation_coins = ['ETH', 'BTC', 'LTC', 'DOGE', 'BCH']
        
        # 默认返回False，只有特殊币种需要API验证
        return coin not in local_validation_coins
    
    @staticmethod
    def validate_address(coin_type, address):
        """验证地址格式是否符合指定币种的要求
        
        参数:
            coin_type: 币种类型 (ETH, USDT, USDC, SUI, SOL, G等)
            address: 待验证的地址
            
        返回:
            (bool, str): (是否有效, 错误信息或成功消息)
        """
        # 去除地址首尾空格
        address = address.strip()
        
        # 根据币种选择不同的验证方法
        if coin_type in ['ETH', 'USDT', 'USDC', 'G']:  # EVM兼容链
            return AddressValidator.validate_evm_address(address)
        elif coin_type == 'SUI':
            return AddressValidator.validate_sui_address(address)
        elif coin_type == 'SOL':
            return AddressValidator.validate_solana_address(address)
        else:
            return False, f"未知币种: {coin_type}"

    @staticmethod
    def validate_evm_address(address):
        """验证以太坊(EVM)地址格式
        
        参数:
            address: 待验证的以太坊地址
            
        返回:
            (bool, str): (是否有效, 错误信息或成功消息)
        """
        # 检查地址长度
        if len(address) != 42:
            return False, "以太坊地址长度必须为42个字符(包含0x前缀)"
            
        # 检查前缀
        if not address.startswith('0x'):
            return False, "以太坊地址必须以0x开头"
            
        # 使用eth_utils验证地址
        try:
            if not is_hex_address(address):
                return False, "无效的以太坊地址格式"
                
            # 尝试转换为校验和地址(这会进一步验证地址的有效性)
            checksum_address = to_checksum_address(address)
            return True, "有效的以太坊地址"
        except Exception as e:
            return False, f"以太坊地址验证错误: {str(e)}"

    @staticmethod
    def validate_sui_address(address):
        """验证SUI地址格式
        
        参数:
            address: 待验证的SUI地址
            
        返回:
            (bool, str): (是否有效, 错误信息或成功消息)
        """
        # SUI地址格式: 0x开头，后跟64个十六进制字符
        sui_pattern = re.compile(r'^0x[0-9a-fA-F]{64}$')
        
        if not sui_pattern.match(address):
            return False, "地址不符合要求"
            
        return True, "有效的SUI地址"

    @staticmethod
    def validate_solana_address(address):
        """验证Solana地址格式
        
        参数:
            address: 待验证的Solana地址
            
        返回:
            (bool, str): (是否有效, 错误信息或成功消息)
        """
        # Solana地址一般是base58编码的32字节公钥
        try:
            # 检查地址是否以0x开头(这不符合Solana地址格式)
            if address.startswith('0x'):
                return False, "地址不符合要求"
                
            # 检查地址长度，标准Solana地址大约为32-44个字符
            if len(address) < 32 or len(address) > 44:
                return False, "地址不符合要求"
                
            # 尝试Base58解码
            decoded = base58.b58decode(address)
            
            # 验证解码后的长度为32字节
            if len(decoded) != 32:
                return False, "地址不符合要求"
                
            return True, "有效的Solana地址"
        except Exception as e:
            # 统一错误消息
            return False, "地址不符合要求"
            
    @staticmethod
    def batch_validate_addresses(coin_type, addresses):
        """批量验证地址
        
        参数:
            coin_type: 币种类型
            addresses: 地址列表
            
        返回:
            (bool, list): (是否全部有效, 无效地址的详细信息列表)
        """
        invalid_addresses = []
        all_valid = True
        
        for i, address in enumerate(addresses):
            valid, message = AddressValidator.validate_address(coin_type, address)
            if not valid:
                all_valid = False
                invalid_addresses.append({
                    'index': i + 1,  # 使用1-索引以便于用户理解
                    'address': address,
                    'error': message
                })
                
        return all_valid, invalid_addresses 