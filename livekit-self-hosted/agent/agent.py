"""
LiveKit Outbound Voice Agent for Oktivo
AI-powered voice agent that speaks naturally on calls.
"""
import logging
import json
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    inference,
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero

logger = logging.getLogger("outbound-agent")
load_dotenv()

# Default company info
DEFAULT_COMPANY = "Oktivo"
DEFAULT_CALLER = "Oktivo AI"

COMPANY_INFO = """
Oktivo is an AI-powered omnichannel voice agent platform by Insybit.

Key Features:
- AI voice calls that sound natural and human-like
- Sends real-time info on WhatsApp or email during calls
- Handles follow-ups over chat after calls
- Integrates with CRM, LMS, and websites
- Multilingual support (English, Hindi, Hinglish)
- Memory-aware - remembers past interactions

Use Cases:
- Automotive: Book test drives, send dealership details
- Healthcare: Schedule appointments, send instructions
- E-commerce: Order support, product recommendations
- Real Estate: Schedule site visits, send property brochures
- Banking: Loan applications, balance inquiries

Website: https://oktivo.com
Contact: contact@insybit.com | +91 8010545225
"""


class OutboundCallAgent(Agent):
    """AI agent for outbound phone calls."""
    
    def __init__(self, caller_name: str = DEFAULT_CALLER, company_name: str = DEFAULT_COMPANY) -> None:
        self.caller_name = caller_name
        self.company_name = company_name
        
        super().__init__(
            instructions=f"""You are a friendly AI voice assistant from {company_name}, calling on behalf of {caller_name}.

IMPORTANT: Start speaking immediately when the call connects.

Your greeting: "Hello! This is {caller_name} calling from {company_name}. I'm an AI voice assistant. How can I help you today?"

About {company_name}:
{COMPANY_INFO}

Guidelines:
- Keep responses concise and natural for phone conversations
- Do not use emojis, markdown, or special characters
- Be polite, professional, and helpful
- If asked about Oktivo, explain our AI voice agent capabilities
- If the user wants to end the call, say goodbye politely
- You can offer to send more information via WhatsApp or email""",
        )

    async def on_enter(self):
        """Called when agent joins the call - immediately greet the user."""
        logger.info(f"Agent entered call - caller: {self.caller_name}, company: {self.company_name}")
        self.session.generate_reply(allow_interruptions=False)

    @function_tool
    async def send_info_via_whatsapp(self, context: RunContext, info_type: str):
        """Offer to send information via WhatsApp.
        
        Args:
            info_type: Type of information to send (brochure, pricing, demo link, etc.)
        """
        logger.info(f"User requested {info_type} via WhatsApp")
        return f"I'll send the {info_type} to your WhatsApp right away. You should receive it in a moment."

    @function_tool
    async def schedule_demo(self, context: RunContext, preferred_time: str):
        """Schedule a demo call.
        
        Args:
            preferred_time: User's preferred time for the demo
        """
        logger.info(f"Demo scheduled for: {preferred_time}")
        return f"I've noted your preference for {preferred_time}. Our team will confirm the demo booking and send you a calendar invite."

    @function_tool
    async def end_call(self, context: RunContext):
        """End the call when conversation is complete."""
        logger.info("Call ended by agent")
        return "Thank you for your time! Have a great day. Goodbye!"


# Initialize server
server = AgentServer()


def prewarm(proc: JobProcess):
    """Preload VAD model for faster startup."""
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Main entry point for each call session."""
    ctx.log_context_fields = {"room": ctx.room.name}
    
    # Parse metadata from dispatch
    caller_name = DEFAULT_CALLER
    company_name = DEFAULT_COMPANY
    
    if ctx.room.metadata:
        try:
            metadata = json.loads(ctx.room.metadata)
            caller_name = metadata.get("caller_name", caller_name)
            company_name = metadata.get("company_name", company_name)
            logger.info(f"Call metadata: {metadata}")
        except json.JSONDecodeError:
            logger.warning("Could not parse room metadata")
    
    # Create agent session with STT, LLM, and TTS
    session = AgentSession(
        stt=inference.STT("deepgram/nova-3", language="multi"),
        llm=inference.LLM("openai/gpt-4.1-mini"),
        tts=inference.TTS("cartesia/sonic-3", voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"),
        vad=ctx.proc.userdata["vad"],
    )

    # Start the agent with custom params
    agent = OutboundCallAgent(caller_name=caller_name, company_name=company_name)
    await session.start(agent=agent, room=ctx.room)


if __name__ == "__main__":
    cli.run_app(server)
