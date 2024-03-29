import json
import requests
import sys
import threading
import time
from datetime import datetime
import math
from library.prediction import Token
import os
import logging.config

if not os.path.exists('logs'):
    os.mkdir('logs')
today = datetime.today()
logging.config.dictConfig({
    "version":                  1,
    "disable_existing_loggers": False,
    "formatters":               {
        "default": {
            "format": "%(asctime)s %(message)s"
        }
    },
    "handlers":                 {
        "console": {
            "class":     "logging.StreamHandler",
            "level":     "INFO",
            "formatter": "default",
            "stream":    "ext://sys.stdout"
        },
        "file":    {
            "class":     "logging.FileHandler",
            "level":     "INFO",
            "formatter": "default",
            "filename":  f"logs/debug-{today.year}-{today.month}-{today.day}-{today.hour}.log",
            "mode":      "a",
            "encoding":  "utf-8"
        }
    },
    "root":                     {
        "level":    "INFO",
        "handlers": [
            "console",
            "file"
        ]
    }
})
LOGGER = logging.getLogger()

class PredictionBot():
    def __init__(self):
        self.wallet = None
        self.w3 = None
        self.w3_wss = None
        self.wallet_connected = False
        self.wallet_address = ""
        self.private_key = ""
        self.prediction_address = "0x516ffd7D1e0Ca40b1879935B2De87cb20Fc1124b"
        self.usdt = "0x55d398326f99059ff775485246999027b3197955"
        self.provider = ""
        self.provider_wss = ""
        self.current_price = 0
        self.current_id = 1
        self.current_bet_id = 1
        self.current_round = None
        self.current_up_rate = 1
        self.current_down_rate = 1
        self.current_prize = 0
        self.up_amount = 0
        self.down_amount = 0
        self.remain_time = 300
        self.claim_id = 6591
        self.balance = 0
        self.bot_flag = False
        self.bet_amount = 0
        self.limit = 0
        self.time_limit = 8
        self.up = 0
        self.down = 0
        self.interval = 30
        self.bear = 0
        self.bull = 0
        self.event_time = 10
        self.old_price = 0
        self.period_time = 0
        self.lock_price = 0
        self.gas_limit = 500000
        
        self.target_address = '0x3c7a328f62493b6038dcb381f9766ed0500532b0'
        self.id_list = list()
        #self.wallet_connect()

    def read_config(self):
        try:
            with open('config.json') as f:
                data = json.load(f)
                self.provider = data['provider_bsc']
                self.wallet_address = data['address']
                self.private_key = data['private_key']
                self.target_address = data['target_address']
                self.target_address = self.target_address.lower()
                self.event_time = int(data['event_time'])
                self.gas_limit = int(data['gas_limit'])
                self.bet_amount = int(float(data['bet_amount'])*10**18)
                print('Read Config Success')
        except Exception as e:
            print(e)
            print("Config file read failed...")

    def wallet_connect(self):
        self.wallet_connected = False
        self.read_config()
        try:
            self.wallet = Token(
                address=self.usdt,
                provider=self.provider
            )
            self.wallet.connect_wallet(self.wallet_address, self.private_key)
            if self.wallet.is_connected():
                self.wallet_connected = True
                self.balance = self.wallet.web3.eth.get_balance(
                    self.wallet.web3.toChecksumAddress(self.wallet_address.lower()))
                print(
                    f'Balance : {round(self.balance / (10 ** 18), 3)}, Target : {self.target_address}, Gas_limit : {self.gas_limit}, Time_limit : {self.event_time}, Bet_amount : {self.bet_amount / 10 ** 18}')
                print("Wallet Connect!")
                # threading.Thread(target=self.set_price).start()
                self.wallet.set_gas_limit(gas_price=10, gas_limit=self.gas_limit)
                # self.start_prediction()
                threading.Thread(target=self.count_down).start()
                threading.Thread(target=self.start_prediction, args=[self.event_time]).start()
        except Exception as e:
            self.wallet_connected = False
            print('Wallet Not Connected')
            print(e)
    def start_prediction(self, event_time):
        print(event_time)
        #self.get_round()
        while True:
            # self.remain_time = self.get_remain_time()
            if self.remain_time == 30:
                threading.Thread(target=self.bet_tx).start()
            if self.remain_time == event_time:
                self.bot_flag = True
                threading.Thread(target=self.mempool, args=[event_time]).start()
            if self.remain_time > event_time and self.bot_flag:
                self.bot_flag = False
            # self.remain_time -= 1
            # if self.remain_time <= 0:
            #     self.get_round()
            if self.remain_time == 260:
                threading.Thread(target=self.claim).start()
            time.sleep(1)

            # response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT")
            # if self.remain_time == 9:
            #     if float(response.json()['price']) - self.current_price >= 0.4:
            #         self.send_bet_bull()
            #     elif -float(response.json()['price']) + self.current_price >= 0.4:
            #         self.send_bet_bear()
    def count_down(self):
        self.get_round()
        while True:
            self.remain_time = self.get_remain_time()
            self.remain_time -= 1
            if self.remain_time <= 0:
                self.get_round()
            print("  " + str(self.remain_time)+"   ", end='\r')
            time.sleep(1)

    def start_predictions(self):
        self.get_round()
        while True:
            self.remain_time = self.get_remain_time()
            if self.remain_time == 30:
                threading.Thread(target=self.bet_tx).start()
            if self.remain_time == self.event_time:
                self.bot_flag = True
                threading.Thread(target=self.mempool).start()
            if self.remain_time > self.event_time and self.bot_flag:
                self.bot_flag = False
            self.remain_time -= 1
            if self.remain_time <= 0:
                self.get_round()
            if self.remain_time == 260:
                threading.Thread(target=self.claim).start()
            time.sleep(1)

            # response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT")
            # if self.remain_time == 9:
            #     if float(response.json()['price']) - self.current_price >= 0.4:
            #         self.send_bet_bull()
            #     elif -float(response.json()['price']) + self.current_price >= 0.4:
            #         self.send_bet_bear()

    def get_remain_time(self):
        d_time = int(self.current_round[2] - datetime.now().timestamp())
        remain_time = d_time
        return remain_time

    def get_round(self):
        self.current_id = self.wallet.get_current_Epoch()
        self.current_round = self.wallet.get_round(id=self.current_id)

    def mempool(self, event_time=None):
        event_filter = self.wallet.web3.eth.filter("pending")
        while self.bot_flag:
            try:
                new_entries = event_filter.get_new_entries()
                threading.Thread(target=self.get_events, args=(new_entries, event_time, )).start()
            except Exception as err:
                print(err)
                pass

    def get_events(self, new_entries, event_time=None):
        try:
            for event in new_entries[::-1]:
                try:
                    threading.Thread(target=self.handle_event, args=(event, event_time, )).start()
                    if self.bot_flag == False:
                        break
                except Exception as e:
                    print(e)
                    pass
        except:
            pass

    def handle_event(self, event, event_time=None):
        try:
            transaction = self.wallet.web3.eth.getTransaction(event)
            #print(transaction.input[:10].lower())
            if transaction['from'].lower() == self.target_address:
                print("catch address")
            if transaction['from'].lower() == self.target_address and transaction.input[:10].lower() == '0xaa6b873a':
                print(event_time, "bear")
                if self.bot_flag:
                    threading.Thread(target=self.send_bet_bear).start()
                self.bot_flag = False
            elif transaction['from'].lower() == self.target_address and transaction.input[:10].lower() == '0x57fb096f':
                print(event_time, "bull")
                if self.bot_flag:
                    threading.Thread(target=self.send_bet_bull).start()
                self.bot_flag = False
        except Exception as e:
            pass

    def bet_tx(self):
        self.wallet.tx_bull(id=self.current_id, amount=self.bet_amount)

    def send_bet_bull(self):
        result = self.wallet.send_bet_bull()
        LOGGER.info(f'{self.current_id}-Bull : {result.hex()}')
        # time.sleep(10)
        # self.set_balance()

    def send_bet_bear(self):
        result = self.wallet.send_bet_bear()
        LOGGER.info(f'{self.current_id}-Bear : {result.hex()}')
        # time.sleep(10)
        # self.set_balance()

    def claim(self):
        claim_id = self.current_id-2
        claim_flag = self.wallet.claimAble(claim_id)
        if claim_flag:
            result = self.wallet.claim(id=int(claim_id))
            LOGGER.info(f'Claim ID - {claim_id}, You Win! {result.hex()}')
            LOGGER.info(f'Claim ID - {claim_id}, You Win! {result.hex()}')
            # time.sleep(10)
        else:
            LOGGER.info(f'Claim ID - {claim_id}, You Lost!')

if __name__ == '__main__':
    bot = PredictionBot()
    bot.wallet_connect()
