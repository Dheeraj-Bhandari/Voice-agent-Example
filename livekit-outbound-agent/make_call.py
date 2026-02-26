"""
Initiate outbound calls via LiveKit SIP.
Dispatches an AI agent and dials the specified phone number.
"""
import argparse
import asyncio
import logging
import os
import json

from dotenv import load_dotenv
from livekit import api

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("make-call")

AGENT_NAME = os.getenv("LIVEKIT_AGENT_NAME", "outbound-agent")
OUTBOUND_TRUNK_ID = os.getenv("SIP_OUTBOUND_TRUNK_ID")


async def make_outbound_call(
    phone_number: str,
    caller_name: str = "Assistant",
    company_name: str = "Company",
    call_purpose: str = "outbound call"
) -> None:
    """
    Make an outbound call via LiveKit SIP.
    
    Args:
        phone_number: E.164 format (e.g., +919988536242)
        caller_name: Name of the caller
        company_name: Company name
        call_purpose: Purpose of the call
    """
    room_name = f"call-{phone_number[-4:]}-{int(asyncio.get_event_loop().time())}"
    
    metadata = json.dumps({
        "caller_name": caller_name,
        "company_name": company_name,
        "call_purpose": call_purpose,
    })
    
    lkapi = api.LiveKitAPI()

    try:
        # Validate trunk ID
        if not OUTBOUND_TRUNK_ID or not OUTBOUND_TRUNK_ID.startswith("ST_"):
            raise ValueError("SIP_OUTBOUND_TRUNK_ID not configured. Check your .env file.")

        # Create agent dispatch
        logger.info(f"Starting call: {caller_name} from {company_name}")
        dispatch = await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=AGENT_NAME,
                room=room_name,
                metadata=metadata,
            )
        )
        logger.info(f"Agent dispatched: {dispatch.id}")

        # Dial the phone number
        masked = f"***{phone_number[-4:]}"
        logger.info(f"Dialing {masked}...")
        
        sip_participant = await lkapi.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=room_name,
                sip_trunk_id=OUTBOUND_TRUNK_ID,
                sip_call_to=phone_number,
                participant_identity="phone_user",
            )
        )
        logger.info(f"Call initiated: {sip_participant.sip_call_id}")

    except Exception as e:
        logger.error(f"Call failed: {e}")
        raise
    finally:
        await lkapi.aclose()


def main():
    parser = argparse.ArgumentParser(description="Make outbound call via LiveKit")
    parser.add_argument("phone_number", help="Phone number (E.164 format)")
    parser.add_argument("--caller", default="Oktivo AI", help="Caller name")
    parser.add_argument("--company", default="Oktivo", help="Company name")
    parser.add_argument("--purpose", default="demo call", help="Call purpose")
    
    args = parser.parse_args()
    
    asyncio.run(make_outbound_call(
        args.phone_number,
        args.caller,
        args.company,
        args.purpose
    ))


if __name__ == "__main__":
    main()
