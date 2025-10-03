import os
import json
from Client import AliceBlue
from typing import Optional, Union
from dotenv import load_dotenv

load_dotenv()

_alice_client = None

def get_alice_client(force_refresh: bool = False) -> AliceBlue:
    """Return a cached AliceBlue client, authenticate only once unless forced."""
    global _alice_client

    if _alice_client and not force_refresh:
        return _alice_client

    app_key = os.getenv("ALICE_APP_KEY")
    api_secret = os.getenv("ALICE_API_SECRET")

    if not app_key or not api_secret:
        raise Exception("Missing credentials. Please set ALICE_APP_KEY and ALICE_API_SECRET in environment variables")

    alice = AliceBlue(app_key=app_key, api_secret=api_secret)
    alice.authenticate() 
    _alice_client = alice
    return _alice_client

def handle_request(body):
    """Handle incoming API requests"""
    try:
        action = body.get('action')
        params = body.get('params', {})
        
        alice = get_alice_client()
        
        if action == 'get_profile':
            result = alice.get_profile()
        elif action == 'get_holdings':
            result = alice.get_holdings()
        elif action == 'get_positions':
            result = alice.get_positions()
        elif action == 'get_order_book':
            result = alice.get_order_book()
        elif action == 'get_trade_book':
            result = alice.get_trade_book()
        elif action == 'get_limits':
            result = alice.get_limits()
        elif action == 'place_order':
            result = alice.get_place_order(**params)
        elif action == 'get_cancel_order':
            result = alice.get_cancel_order(params.get('brokerOrderId'))
        elif action == 'get_modify_order':
            result = alice.get_modify_order(**params)
        elif action == 'get_positions_sqroff':
            result = alice.get_positions_sqroff(**params)
        elif action == 'get_position_conversion':
            result = alice.get_position_conversion(**params)
        elif action == 'get_order_margin':
            result = alice.get_order_margin(**params)
        elif action == 'get_exit_bracket_order':
            result = alice.get_exit_bracket_order(**params)
        elif action == 'get_place_gtt_order':
            result = alice.get_place_gtt_order(**params)
        elif action == 'get_gtt_order_book':
            result = alice.get_gtt_order_book()
        elif action == 'get_modify_gtt_order':
            result = alice.get_modify_gtt_order(**params)
        elif action == 'get_cancel_gtt_order':
            result = alice.get_cancel_gtt_order(params.get('brokerOrderId'))
        elif action == 'check_session':
            session_id = alice.get_session()
            result = {
                "authenticated": True,
                "session_id": session_id,
                "user_id": alice.user_id
            }
        elif action == 'close_session':
            global _alice_client
            _alice_client = None
            result = {"message": "Session closed"}
        elif action == 'get_order_history':
            result = alice.get_order_history(params.get('brokerOrderId'))
        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}"
            }
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }