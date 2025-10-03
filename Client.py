import os
import requests
import hashlib
import webbrowser
import http.server
import socketserver
import threading
import time
from dotenv import load_dotenv
from typing import Optional, Union
import socket

load_dotenv()

BASE_URL = "https://a3.aliceblueonline.com"
LOGIN_URL = "https://ant.aliceblueonline.com/?appcode="
REDIRECT_PORT = 8080
LOGIN_TIMEOUT = 60 

user_id = os.getenv("ALICE_USER_ID")
app_key = os.getenv("ALICE_APP_KEY")
api_secret = os.getenv("ALICE_API_SECRET")

class RedirectHandler(http.server.SimpleHTTPRequestHandler):
    """Handles redirect response to capture authCode and userId."""
    auth_code = None
    user_id = None
    login_received = threading.Event()
    current_server = None
    
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        query = parse_qs(urlparse(self.path).query)
        RedirectHandler.auth_code = query.get("authCode", [None])[0]
        RedirectHandler.user_id = query.get("userId", [None])[0]
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>Login successful. You may close this tab.</h2>")
        RedirectHandler.login_received.set()
    

class AliceBlue:
    def __init__(self, app_key: str, api_secret: str):
        self.app_key = app_key
        self.api_secret = api_secret
        self.user_id = None
        self.auth_code = None
        self.user_session = None
        self.headers = None
        self.login_timeout = LOGIN_TIMEOUT
        self.current_server = None
        self.server_thread = None

    def _is_port_available(self, port):
        """Check if port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.bind(('localhost', port))
                return True
        except OSError:
            return False

    def _force_close_port(self, port):
        """Force close the port by creating a temporary connection"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                if result == 0:
                    s.shutdown(socket.SHUT_RDWR)
        except:
            pass
        time.sleep(0.5)

    def _close_previous_login(self):
        """Close any previous login attempt"""
        if RedirectHandler.current_server:
            try:
                RedirectHandler.current_server.shutdown()
                RedirectHandler.current_server.server_close()
                print("Previous login attempt closed")
            except Exception as e:
                print(f"Error closing previous server: {e}")
            finally:
                RedirectHandler.current_server = None
                RedirectHandler.login_received.clear()
                RedirectHandler.auth_code = None
                RedirectHandler.user_id = None
        
        if self.current_server:
            try:
                self.current_server.shutdown()
                self.current_server.server_close()
            except:
                pass
            finally:
                self.current_server = None

    def login_and_get_auth_code(self):
        self._close_previous_login()
        if not self._is_port_available(REDIRECT_PORT):
            print("Port 8080 is busy, forcing closure...")
            self._force_close_port(REDIRECT_PORT)
            time.sleep(1)
        
        RedirectHandler.login_received.clear()
        RedirectHandler.auth_code = None
        RedirectHandler.user_id = None
        
        try:
            self.current_server = socketserver.TCPServer(("localhost", REDIRECT_PORT), RedirectHandler, bind_and_activate=False)
            self.current_server.allow_reuse_address = True
            self.current_server.server_bind()
            self.current_server.server_activate()
            
            RedirectHandler.current_server = self.current_server
            
            self.server_thread = threading.Thread(target=self.current_server.serve_forever, daemon=True)
            self.server_thread.start()
            
            login_url = f"{LOGIN_URL}{self.app_key}&redirect_uri=http://localhost:{REDIRECT_PORT}"
            print(f"Opening browser for login: {login_url}")
            webbrowser.open(login_url)
            
            print(f"Waiting for login (timeout: {self.login_timeout} seconds)...")
            print("Please complete the login in the browser window...")
            
            login_success = RedirectHandler.login_received.wait(timeout=self.login_timeout)
            
            if not login_success:
                self._close_previous_login()
                raise TimeoutError(f"Login timeout: No login received within {self.login_timeout} seconds")
            
            self.auth_code = RedirectHandler.auth_code
            self.user_id = RedirectHandler.user_id
            
            if not self.auth_code or not self.user_id:
                self._close_previous_login()
                raise ValueError("Login failed: Missing authCode or userId")
                
            print(f"Auth Code received, User ID: {self.user_id}")
            self._close_previous_login()
            
        except OSError as e:
            if "10048" in str(e) or "Address already in use" in str(e):
                self._close_previous_login()
                raise OSError(f"Port {REDIRECT_PORT} is busy. Please close other applications or wait a few seconds before retrying.")
            else:
                self._close_previous_login()
                raise e
        except Exception as e:
            self._close_previous_login()
            raise e

    def authenticate(self):
        try:
            if not self.auth_code or not self.user_id:
                self.login_and_get_auth_code()
                
            raw_string = f"{self.user_id}{self.auth_code}{self.api_secret}"
            checksum = hashlib.sha256(raw_string.encode()).hexdigest()
            url = f"{BASE_URL}/open-api/od/v1/vendor/getUserDetails"
            payload = {"checkSum": checksum}
            res = requests.post(url, json=payload)
            
            if res.status_code != 200:
                raise Exception(f"API Error: {res.text}")
                
            data = res.json()
            if data.get("stat") == "Ok":
                self.user_session = data["userSession"]
                self.headers = {"Authorization": f"Bearer {self.user_session}"}
                print("Authentication Successful")
            else:
                raise Exception(f"Authentication failed: {data}")
        except Exception as e:
            self._close_previous_login()
            raise e

    def get_session(self):
        return self.user_session

    def close(self):
        """Cleanup method to close any ongoing login attempts"""
        self._close_previous_login()
    

    def get_profile(self):
        url = f"{BASE_URL}/open-api/od/v1/profile"
        res = requests.get(url, headers=self.headers)
        
        if res.status_code != 200:
            raise Exception(f"Profile Error {res.status_code}: {res.text}")
        try:
            return res.json()
        except Exception:
            raise Exception(f"Non-JSON response: {res.text}")
    
    def get_holdings(self):
        url = f"{BASE_URL}/open-api/od/v1/holdings/CNC"
        res = requests.get(url, headers=self.headers)
        
        if res.status_code != 200:
            raise Exception(f"Holding Error {res.status_code}: {res.text}")
        try:
            return res.json()
        except Exception:
            raise Exception(f"Non-JSON response: {res.text}")
    
    def get_positions(self):
        url = f"{BASE_URL}/open-api/od/v1/positions"
        res = requests.get(url, headers=self.headers)
        
        if res.status_code != 200:
            raise Exception(f"Position Error {res.status_code}: {res.text}")
        try:
            return res.json()
        except Exception:
            raise Exception(f"Non-JSON response: {res.text}")
    
    def get_positions_sqroff(self, exch, symbol, qty, product, transaction_type):
        url = f"{BASE_URL}/open-api/od/v1/orders/positions/sqroff"
        payload = {
            "exch": exch,
            "symbol": symbol,
            "qty": qty,
            "product": product,
            "transaction_type": transaction_type
        }
        res = requests.post(url, headers=self.headers, json=payload)
        
        if res.status_code != 200:
            raise Exception(f"Position Square Off Error {res.status_code}: {res.text}")
        try:
            return res.json()
        except Exception:
            raise Exception(f"Non-JSON response: {res.text}")

    def get_position_conversion(self, exchange, validity, prevProduct, product, quantity, tradingSymbol, transactionType,orderSource):
        url = f"{BASE_URL}/open-api/od/v1/conversion"
        payload = {
            "exchange": exchange,
            "validity": validity,
            "prevProduct": prevProduct,
            "product": product,
            "quantity": quantity,
            "tradingSymbol": tradingSymbol,
            "transactionType": transactionType,
            "orderSource":orderSource
        }
        res = requests.post(url, headers=self.headers, json=payload)
        
        if res.status_code != 200:
            raise Exception(f"Position Conversion Error {res.status_code}: {res.text}")
        try:
            return res.json()
        except Exception:
            raise Exception(f"Non-JSON response: {res.text}")
    
    def get_place_order(self,instrument_id: str, exchange: str, transaction_type: str, quantity: int, order_type: str, product: str,
                    order_complexity: str, price: float, validity: str, sl_leg_price: Optional[float] = None,
                    target_leg_price: Optional[float] = None, sl_trigger_price: Optional[float] = None, trailing_sl_amount: Optional[float] = None,
                    disclosed_quantity: int = 0,source: str = "API"):
        """Place an order with Alice Blue API."""

        url = f"{BASE_URL}/open-api/od/v1/orders/placeorder"

        payload = [{
            "instrumentId": instrument_id,
            "exchange": exchange,
            "transactionType": transaction_type.upper(),
            "quantity": quantity,
            "orderType": order_type.upper(),
            "product": product.upper(),
            "orderComplexity": order_complexity.upper(),
            "price": price,
            "validity": validity.upper(),
            "disclosedQuantity": disclosed_quantity,
            "source": source.upper()
        }]

        if sl_leg_price is not None:
            payload[0]["slLegPrice"] = sl_leg_price
        if target_leg_price is not None:
            payload[0]["targetLegPrice"] = target_leg_price
        if sl_trigger_price is not None:
            payload[0]["slTriggerPrice"] = sl_trigger_price
        if trailing_sl_amount is not None:
            payload[0]["trailingSlAmount"] = trailing_sl_amount

        res = requests.post(url, headers=self.headers, json=payload)

        if res.status_code != 200:
            raise Exception(f"Order Place Error {res.status_code}: {res.text}")
        try:
            return res.json()
        except Exception:
            raise Exception(f"Non-JSON response: {res.text}")
    
    def get_order_book(self):
        url = f"{BASE_URL}/open-api/od/v1/orders/book"
        res = requests.get(url, headers=self.headers)
        
        if res.status_code != 200:
            raise Exception(f"Order Book Error {res.status_code}: {res.text}")
        try:
            return res.json()
        except Exception:
            raise Exception(f"Non-JSON response: {res.text}")
    
    def get_order_history(self, brokerOrderId: str):
        url = f"{BASE_URL}/open-api/od/v1/orders/history"
        payload = {"brokerOrderId": brokerOrderId}
        res = requests.post(url, headers=self.headers, json = payload)
        
        if res.status_code != 200:
            raise Exception(f"Order History Error {res.status_code}: {res.text}")
        try:
            return res.json()
        except Exception:
            raise Exception(f"Non-JSON response: {res.text}")
    
    def get_modify_order(self, brokerOrderId:str, validity: str , quantity: Optional[int] = None,price: Optional[Union[int, float]] = None, 
                         triggerPrice: Optional[float] = None
                         ):
        url = f"{BASE_URL}/open-api/od/v1/orders/modify"
        payload = [{
            "brokerOrderId": brokerOrderId,
            "quantity": quantity if quantity else "",
            "price": price if price else "",
            "triggerPrice": triggerPrice if triggerPrice else "",
            "validity": validity.upper()
        }]
        res = requests.post(url, headers=self.headers, json=payload)
        if res.status_code != 200:
            raise Exception(f"Order Modify Error {res.status_code}: {res.text}")

        try:
            return res.json()
        except Exception:
            raise Exception(f"Non-JSON response: {res.text}")
    
    def get_cancel_order(self, brokerOrderId):
        """Cancel an order."""
        url = f"{BASE_URL}/open-api/od/v1/orders/cancel"
        payload = {"brokerOrderId":brokerOrderId}
        res = requests.post(url, headers=self.headers, json=payload)
        
        if res.status_code != 200:
            raise Exception(f"Order Cancel Error {res.status_code}: {res.text}")
        try:
            return res.json()
        except Exception:
            raise Exception(f"Non-JSON response: {res.text}")
    
    def get_trade_book(self):
        url = f"{BASE_URL}/open-api/od/v1/orders/trades"
        res = requests.get(url, headers=self.headers)
        
        if res.status_code != 200:
            raise Exception(f"Trade Book Error {res.status_code}: {res.text}")
        try:
            return res.json()
        except Exception:
            raise Exception(f"Non-JSON response: {res.text}")
    
    def get_order_margin(self, exchange:str, instrumentId:str, transactionType:str, quantity:int, product:str, 
                         orderComplexity:str, orderType:str, validity:str, price=0.0, slTriggerPrice: Optional[Union[int, float]] = None):
        url = f"{BASE_URL}/open-api/od/v1/orders/checkMargin"
        payload = [{
            "exchange": exchange.upper(),
            "instrumentId": instrumentId.upper(),
            "transactionType": transactionType.upper(),
            "quantity": quantity,
            "product": product.upper(),
            "orderComplexity": orderComplexity.upper(),
            "orderType": orderType.upper(),
            "price": price,
            "validity": validity.upper(),
            "slTriggerPrice": slTriggerPrice if slTriggerPrice is not None else ""
        }]
        res = requests.post(url, headers=self.headers, json=payload)
        
        if res.status_code != 200:
            raise Exception(f"Order Margin Error {res.status_code}: {res.text}")
        try:
            return res.json()
        except Exception:
            raise Exception(f"Non-JSON response: {res.text}")
    
    def get_exit_bracket_order(self, brokerOrderId: str, orderComplexity: str):
        url = f"{BASE_URL}/open-api/od/v1/orders/exit/sno"
        payload = [{
            "brokerOrderId": brokerOrderId,
            "orderComplexity": orderComplexity.upper()
        }]
        res = requests.post(url, headers=self.headers, json=payload)
        
        if res.status_code != 200:
            raise Exception(f"Exit Bracket Order Error {res.status_code}: {res.text}")
        
        try:
            return res.json()
        except Exception:
            raise Exception(f"Non-JSON response: {res.text}")
    
    def get_place_gtt_order(self, tradingSymbol: str, exchange: str, transactionType: str, orderType: str,
                            product: str, validity: str, quantity: int, price: float, orderComplexity: str, 
                            instrumentId: str, gttType: str, gttValue: float):
        
        url = f"{BASE_URL}/open-api/od/v1/orders/gtt/execute"
        
        payload = {
            "tradingSymbol": tradingSymbol.upper(),
            "exchange": exchange.upper(),
            "transactionType": transactionType.upper(),
            "orderType": orderType.upper(),
            "product": product.upper(),
            "validity": validity.upper(),
            "quantity": quantity, 
            "price": price, 
            "orderComplexity": orderComplexity.upper(),
            "instrumentId": instrumentId,
            "gttType": gttType.upper(),
            "gttValue": gttValue 
        }
        try:
            res = requests.post(url, headers=self.headers, json=payload)
            res.raise_for_status()
            return res.json()
        except requests.exceptions.HTTPError as e:
            try:
                error_data = res.json()
                error_msg = error_data.get("message") or error_data.get("emsg") or res.text
            except:
                error_msg = res.text
            raise Exception(f"GTT Order Place Error {res.status_code}: {error_msg}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {str(e)}")
    
    def get_gtt_order_book(self):
        url = f"{BASE_URL}/open-api/od/v1/orders/gtt/orderbook"
        res = requests.get(url, headers=self.headers)
        
        if res.status_code != 200:
            raise Exception(f"GTT Order Book Error {res.status_code}: {res.text}")
        
        try:
            return res.json()
        except Exception:
            raise Exception(f"Non-JSON response: {res.text}")
    
    def get_modify_gtt_order(self, brokerOrderId: str, instrumentId: str, tradingSymbol: str, 
                            exchange: str, orderType: str, product: str, validity: str, 
                            quantity: int, price: float, orderComplexity: str, 
                            gttType: str, gttValue: float):
        
        url = f"{BASE_URL}/open-api/od/v1/orders/gtt/modify"
        
        payload = {
            "brokerOrderId": brokerOrderId,
            "instrumentId": instrumentId,
            "tradingSymbol": tradingSymbol.upper(),
            "exchange": exchange.upper(),
            "orderType": orderType.upper(),
            "product": product.upper(),
            "validity": validity.upper(),
            "quantity": quantity,
            "price": price,
            "orderComplexity": orderComplexity.upper(),
            "gttType": gttType.upper(),
            "gttValue": gttValue
        }
        
        try:
            res = requests.post(url, headers=self.headers, json=payload)
            res.raise_for_status()
            return res.json()
            
        except requests.exceptions.HTTPError as e:
            try:
                error_data = res.json()
                error_msg = error_data.get("message") or error_data.get("emsg") or res.text
            except:
                error_msg = res.text
            raise Exception(f"GTT Modify Order Error {res.status_code}: {error_msg}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {str(e)}")
    
    def get_cancel_gtt_order(self, brokerOrderId):
        url = f"{BASE_URL}/open-api/od/v1/orders/gtt/cancel"
        payload = {"brokerOrderId": brokerOrderId}
        res = requests.post(url, headers=self.headers, json=payload)
        
        if res.status_code != 200:
            raise Exception(f"GTT Cancel Order Error {res.status_code}: {res.text}")
        try:
            return res.json()
        except Exception:
            raise Exception(f"Non-JSON response: {res.text}")
    
    def get_limits(self):
        url = f"{BASE_URL}/open-api/od/v1/limits"
        res = requests.get(url, headers=self.headers)
        
        if res.status_code != 200:
            raise Exception(f"Limits Error {res.status_code}: {res.text}")   
        try:
            return res.json()
        except Exception:
            raise Exception(f"Non-JSON response: {res.text}")

if __name__ == "__main__":
    alice = AliceBlue(app_key, api_secret)
    alice.authenticate()
    print("User Session:", alice.get_session())