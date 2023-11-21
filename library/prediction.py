import requests
from web3 import Web3
import os
import json
from functools import wraps


class Token:
    # bnb
    ETH_ADDRESS = Web3.toChecksumAddress('0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c')

    MAX_AMOUNT = int('0x' + 'f' * 64, 16)

    def __init__(self, address, provider=None):
        self.address = Web3.toChecksumAddress(address)
        self.provider = os.environ['PROVIDER'] if not provider else provider
        adapter = requests.adapters.HTTPAdapter(pool_connections=1000, pool_maxsize=1000)
        session = requests.Session()
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        self.i = 0
        self.j = 0
        self.web3 = Web3(Web3.HTTPProvider(self.provider, session=session))
        self.signed_tx = None
        self.signed_tx_bear = None
        self.signed_tx_bull = None

        # bnb
        self.router = self.web3.eth.contract(
            address=Web3.toChecksumAddress('0x10ed43c718714eb63d5aa57b78b54704e256024e'),
            abi=json.load(open("library/abi_files_bnb/" + "router.abi")))
        self.prediction_router = self.web3.eth.contract(
            address=Web3.toChecksumAddress('0x18B2A687610328590Bc8F2e5fEdDe3b582A49cdA'),
            abi=json.load(open("library/abi_files_bnb/" + "prediction.abi")))
        self.oracle_router = self.web3.eth.contract(
            address=Web3.toChecksumAddress('0xD276fCF34D54A926773c399eBAa772C12ec394aC'),
            abi=json.load(open("library/abi_files_bnb/" + "oracle.abi")))
        self.erc20_abi = json.load(
            open("library/abi_files_bnb/" + "erc20.abi"))

        self.gas_limit = 500000
        self.gas_price = 5 * 10**9

    def decimals(self, address=None):
        address = self.wallet_address if not address else Web3.toChecksumAddress(address)
        if not address:
            raise RuntimeError('Please provide the wallet address!')
        erc20_contract = self.web3.eth.contract(address=self.address, abi=self.erc20_abi)
        return erc20_contract.functions.decimals().call()

    def set_gas_limit(self, gas_price=5, gas_limit=500000):
        self.gas_limit = int(gas_limit)
        self.gas_price = int(gas_price*10**9)

    def connect_wallet(self, wallet_address='', private_key=''):
        self.wallet_address = Web3.toChecksumAddress(wallet_address)
        self.private_key = private_key

    def is_connected(self):
        return False if not self.wallet_address else True

    def require_connected(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not self.is_connected():
                raise RuntimeError('Please connect the wallet first!')
            return func(self, *args, **kwargs)

        return wrapper

    def create_transaction_params(self, value=0):
        return {
            "from": self.wallet_address,
            "value": value,
            'gasPrice': self.gas_price,
            "gas": self.gas_limit,
            "nonce": self.web3.eth.getTransactionCount(self.wallet_address)
        }

    def send_transaction(self, func, params):
        # tx = func.buildTransaction(params)
        # signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)
        # tx_hash = self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        # tx = tx_hash.hex()
        # self.web3.eth.waitForTransactionReceipt(tx)
        # return tx_hash
        tx = func.buildTransaction(params)
        signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)
        return self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)

    def send_bet_bull(self):
        return self.web3.eth.sendRawTransaction(self.signed_tx_bull.rawTransaction)

    def send_bet_bear(self):
        return self.web3.eth.sendRawTransaction(self.signed_tx_bear.rawTransaction)

    def tx_bull(self, id=0, amount=0):
        func = self.prediction_router.functions.betBull(id)
        params = self.create_transaction_params(value=amount)
        tx = func.buildTransaction(params)
        self.signed_tx_bull = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)
        # print(self.signed_tx_bull)
        func = self.prediction_router.functions.betBear(id)
        tx = func.buildTransaction(params)
        self.signed_tx_bear = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)

    def tx_bear(self, id=0, amount=0):
        func = self.prediction_router.functions.betBear(id)
        params = self.create_transaction_params(value=amount)
        tx = func.buildTransaction(params)
        self.signed_tx_bear = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)

    def price(self):
        data = self.oracle_router.functions.latestRoundData().call()
        return (int(data[1]))

    def balance(self, address=None):
        address = self.wallet_address if not address else Web3.toChecksumAddress(address)
        if not address:
            raise RuntimeError('Please provide the wallet address!')
        erc20_contract = self.web3.eth.contract(address=self.address, abi=self.erc20_abi)
        return erc20_contract.functions.balanceOf(self.wallet_address).call()

    @require_connected
    def get_round(self, id=0):
        return self.prediction_router.functions.rounds(id).call()

    def get_current_Epoch(self):
        return self.prediction_router.functions.currentEpoch().call()

    def bet_bull(self, amount=0, id=0):
        func = self.prediction_router.functions.betBull(id)
        params = self.create_transaction_params(value=amount)
        return self.send_transaction(func, params)

    def bet_bear(self, amount=0, id=0):
        func = self.prediction_router.functions.betBear(id)
        params = self.create_transaction_params(value=amount)
        return self.send_transaction(func, params)

    def claim(self, id=0):
        func = self.prediction_router.functions.claim([id])
        params = self.create_transaction_params()
        return self.send_transaction(func, params)

    def claimAble(self, claim_id=1):
        return self.prediction_router.functions.claimable(claim_id, self.wallet_address).call()

    def cancel_bet(self):
        try:
            tx = {
                'to': self.wallet_address,
                "value": 0,
                'gasPrice': self.gas_price,
                "gas": 200000,
                "nonce": self.web3.eth.getTransactionCount(self.wallet_address)
            }
            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)
            print(self.web3.toHex(tx_hash))
        except Exception as err:
            print(err)

    # def claim(self):
    #     func = self.prediction_router.functions.claim([id])
    #     params = self.create_transaction_params()
    #     return self.send_transaction(func, params)


