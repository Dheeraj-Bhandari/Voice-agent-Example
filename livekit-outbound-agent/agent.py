"""
LiveKit Outbound Voice Agent
Makes outbound calls with AI-powered voice conversation.
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


class OutboundCallAgent(Agent):
    """AI agent for outbound phone calls."""
    
    def __init__(self, caller_name: str = "Assistant", company_name: str = "Company") -> None:
        self.caller_name = caller_name
        self.company_name = company_name
        
        super().__init__(
            instructions=f"""You are a friendly AI assistant making an outbound call on behalf of {caller_name} from {company_name}.
            
            IMPORTANT: Start speaking immediately when the call connects.
            
            Your greeting: "Hello! This is a call from {company_name}, initiated by {caller_name}. I'm an AI voice assistant. How can I help you today?"
            
            Guidelines:
            - Keep responses concise and natural for phone conversations
            - Do not use emojis, markdown, or special characters
            - Be polite and professional
            - If the user wants to end the call, say goodbye politely""",
        )

    async def on_enter(self):
        """Called when agent joins the call - immediately greet the user."""
        logger.info(f"Agent entered call - caller: {self.caller_name}, company: {self.company_name}")
        self.session.generate_reply(allow_interruptions=False)

    @function_tool
    async def end_call(self, context: RunContext):
        """End the call when conversation is complete."""
        logger.info("Call ended by agent")
        return "Goodbye! Have a great day."


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
    caller_name = "Dheeraj"
    company_name = "Insybit"
    
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
