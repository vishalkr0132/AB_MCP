import os
import socket
import time
from fastmcp import FastMCP
from Client import AliceBlue
from typing import Optional, Union
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP(
    name="New AliceBlue Portfolio Agent",
    dependencies=["python-dotenv", "requests"]
)
_alice_client = None


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def get_alice_client(force_refresh: bool = False) -> AliceBlue:
    """Return a cached AliceBlue client, authenticate only once unless forced."""
    global _alice_client

    if _alice_client and not force_refresh:
        return _alice_client

    app_key = os.getenv("ALICE_APP_KEY")
    api_secret = os.getenv("ALICE_API_SECRET")

    if not app_key or not api_secret:
        raise Exception("Missing credentials. Please set ALICE_APP_KEY and ALICE_API_SECRET in .env file")

    alice = AliceBlue(app_key=app_key, api_secret=api_secret)
    alice.authenticate() 
    _alice_client = alice
    return _alice_client

def kill_port_process(port=8080):
    """Kill process using the specified port (Windows)"""
    try:
        import subprocess
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                pid = parts[-1]
                subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                print(f"Killed process {pid} using port {port}")
                return True
    except Exception as e:
        print(f"Error killing process: {e}")
    return False


@mcp.tool()
def check_and_authenticate() -> dict:
    """Check if AliceBlue session is active."""
    global _alice_client
    try:
        if not _alice_client:
            return {
                "status": "error",
                "authenticated": False,
                "message": "No active session. Please run initiate_login first."
            }

        session_id = _alice_client.get_session()
        return {
            "status": "success",
            "authenticated": True,
            "session_id": session_id,
            "user_id": _alice_client.user_id,
            "message": "Session is active"
        }
    except Exception as e:
        return {
            "status": "error",
            "authenticated": False,
            "message": str(e)
        }


@mcp.tool()
def initiate_login(force_refresh: bool = False) -> dict:
    """Login and create a new AliceBlue session if none exists or forced."""
    try:
        alice = get_alice_client(force_refresh=force_refresh)

        return {
            "status": "success",
            "message": "Login successful! New session created" if force_refresh else "Session active",
            "session_id": alice.get_session(),
            "user_id": alice.user_id,
            "action": "login_completed" if force_refresh else "no_login_needed"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Login failed: {e}"
        }

@mcp.tool()
def close_session() -> dict:
    """Explicitly close the current session (forces next call to re-authenticate)."""
    global _alice_client
    _alice_client = None
    return {
        "status": "success",
        "message": "Session closed. Next call will require re-authentication."
    }


@mcp.tool()
def get_profile() -> dict:
    """Fetches the user's profile details."""
    try:
        alice = get_alice_client()
        return {"status": "success", "data": alice.get_profile()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def get_holdings() -> dict:
    """Fetches the user's Holdings Stock"""
    try:
        alice = get_alice_client()
        return {"status": "success", "data": alice.get_holdings()}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@mcp.tool()
def get_positions()-> dict:
    """Fetches the user's Positions"""
    try:
        alice = get_alice_client()
        return{"status": "success", "data": alice.get_positions()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def get_positions_sqroff(exch: str, symbol: str, qty: str, product: str, 
                         transaction_type: str)-> dict:
    """Position Square Off"""
    try:
        alice = get_alice_client()
        return {
            "status":"success",
            "data": alice.get_positions_sqroff(
                exch=exch,
                symbol=symbol,
                qty=qty,
                product=product,
                transaction_type=transaction_type
            )
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def get_position_conversion(exchange: str, validity: str, prevProduct: str, product: str, quantity: int, 
                            tradingSymbol: str, transactionType: str, orderSource: str)->dict:
    """Position conversion"""
    try:
        alice = get_alice_client()
        return{
            "status":"success",
            "data": alice.get_position_conversion(
                exchange=exchange,
                validity=validity,
                prevProduct=prevProduct,
                product=product,
                quantity=quantity,
                tradingSymbol=tradingSymbol,
                transactionType=transactionType,
                orderSource=orderSource
            )
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@mcp.tool()
def place_order(instrument_id: str, exchange: str, transaction_type: str, quantity: int, order_type: str, product: str,
                    order_complexity: str, price: float, validity: str) -> dict:
    """Places an order for the given stock."""
    try:
        alice = get_alice_client()
        return {
            "status": "success",
            "data": alice.get_place_order(
                instrument_id = instrument_id,
                exchange=exchange,
                transaction_type=transaction_type,
                quantity = quantity,
                order_type = order_type,
                product = product,
                order_complexity = order_complexity,
                price=price,
                validity = validity
            )
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def get_order_book()-> dict:
    """Fetches Order Book"""
    try:
        alice = get_alice_client()
        return {
            "status": "success",
            "data": alice.get_order_book()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@mcp.tool()
def get_order_history(brokerOrderId: str)-> dict:
    """Fetchs Orders History"""
    try:
        alice = get_alice_client()
        return{
            "status": "success",
            "data": alice.get_order_history(
                brokerOrderId=brokerOrderId
            )
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def get_modify_order(brokerOrderId:str, validity: str , quantity: Optional[int] = None,
                     price: Optional[Union[int, float]] = None, triggerPrice: Optional[float] = None)-> dict:
    """Modify Order"""
    try:
        alice = get_alice_client()
        return {
            "status": "success",
            "data": alice.get_modify_order(
                brokerOrderId = brokerOrderId,
                quantity= quantity if quantity else "",
                validity= validity,
                price= price if price else "",
                triggerPrice=triggerPrice if triggerPrice else ""
            )
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def get_cancel_order(brokerOrderId: str)-> dict:
    """Cancel Order"""
    try:
        alice = get_alice_client()
        return {
            "status": "success",
            "data": alice.get_cancel_order(
                brokerOrderId=brokerOrderId
            )
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def get_trade_book()-> dict:
    """Fetches Trade Book"""
    try:
        alice = get_alice_client()
        return{
            "status": "success",
            "data": alice.get_trade_book()
        }
    except Exception as e:
        return {"status": "error", "message" : str(e)}

@mcp.tool()
def get_order_margin(exchange:str, instrumentId:str, transactionType:str, quantity:int, product:str, 
                         orderComplexity:str, orderType:str, validity:str, price=0.0, 
                         slTriggerPrice: Optional[Union[int, float]] = None)-> dict:
    """Order Margin"""
    try:
        alice = get_alice_client()
        return{
            "status": "success",
            "data": alice.get_order_margin(
                exchange=exchange,
                instrumentId = instrumentId,
                transactionType=transactionType,
                quantity=quantity,
                product=product,
                orderComplexity=orderComplexity,
                orderType=orderType,
                validity=validity,
                price=price,
                slTriggerPrice= slTriggerPrice if slTriggerPrice is not None else ""
            )
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def get_exit_bracket_order(brokerOrderId: str, orderComplexity:str)->dict:
    """Exit Bracket Order"""
    try:
        alice = get_alice_client()
        return {
            "status": "success",
            "data": alice.get_exit_bracket_order(
                brokerOrderId=brokerOrderId,
                orderComplexity=orderComplexity
            )
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def get_place_gtt_order(tradingSymbol: str, exchange: str, transactionType: str, orderType: str,
                            product: str, validity: str, quantity: int, price: float, orderComplexity: str, 
                            instrumentId: str, gttType: str, gttValue: float)->dict:
    """Place GTT Order"""
    try:
        alice = get_alice_client()
        return {
            "status": "success",
            "data": alice.get_place_gtt_order(
                tradingSymbol=tradingSymbol,
                exchange=exchange,
                transactionType=transactionType,
                orderType=orderType,
                product=product,
                validity=validity,
                quantity=quantity,
                price=price,
                orderComplexity=orderComplexity,
                instrumentId = instrumentId,
                gttType=gttType,
                gttValue=gttValue
            )
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def get_gtt_order_book(self):
    """Fetches GTT Order Book"""
    try:
        alice = get_alice_client()
        return{
            "status": "success",
            "data": alice.get_gtt_order_book()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def get_modify_gtt_order(brokerOrderId: str, instrumentId: str, tradingSymbol: str, 
                            exchange: str, orderType: str, product: str, validity: str, 
                            quantity: int, price: float, orderComplexity: str, 
                            gttType: str, gttValue: float)->dict:
    """Modify GTT Order"""
    try:
        alice = get_alice_client()
        return{
            "status": "success",
            "data": alice.get_modify_gtt_order(
                brokerOrderId=brokerOrderId,
                instrumentId = instrumentId,
                tradingSymbol=tradingSymbol,
                exchange=exchange,
                orderType=orderType,
                product=product,
                validity=validity,
                quantity=quantity,
                price=price,
                orderComplexity=orderComplexity,
                gttType=gttType,
                gttValue=gttValue,
            )
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def get_cancel_gtt_order(brokerOrderId: str):
    """Cancel Order"""
    try:
        alice = get_alice_client()
        return{
            "status": "success",
            "data": alice.get_cancel_gtt_order(
                brokerOrderId=brokerOrderId
            )
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def get_limits():
    """Get Limits"""
    try:
        alice = get_alice_client()
        return{
            "status": "success",
            "data": alice.get_limits()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
if __name__ == "__main__":
    app_key = os.getenv("ALICE_APP_KEY")
    api_secret = os.getenv("ALICE_API_SECRET")
    if not app_key or not api_secret:
        raise Exception("Missing credentials. Please set ALICE_APP_KEY and ALICE_API_SECRET in .env file")
    if not AliceBlue(app_key, api_secret)._is_port_available(8080):
        print(f"Port 8080 is busy. Attempting to free it...")
        kill_port_process(8080)
        time.sleep(2)
    port = get_free_port()
    mcp.run(transport="sse", host="127.0.0.1", port=port)

