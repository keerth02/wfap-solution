"""Company Agent Main Entry Point"""
import click
import uvicorn
import os
from dotenv import load_dotenv

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers.default_request_handler import (
    DefaultRequestHandler,
)
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

from agent_executor import CompanyAgentExecutor

# Load environment variables
load_dotenv()

class CompanyRequestHandler(DefaultRequestHandler):
    """A2A Request Handler for the Company Agent."""

    def __init__(
        self, agent_executor: CompanyAgentExecutor, task_store: InMemoryTaskStore
    ):
        super().__init__(agent_executor, task_store)

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=8003)
def main(host: str, port: int):
    """Start the WFAP Company Agent server.

    This function initializes the Company Agent server with A2A communication capabilities.
    It creates an agent card with the company's capabilities for credit request management,
    offer evaluation, and negotiation.

    Args:
        host (str): The host address to run the server on.
        port (int): The port number to run the server on.
    """
    
    # Company agent skills
    credit_intent_skill = AgentSkill(
        id='create_credit_intent',
        name='Create Credit Intent',
        description='Create structured credit intent with company information',
        tags=['credit', 'intent'],
        examples=['Create credit intent for $1M working capital', 'Generate intent for expansion funding'],
    )
    
    broker_communication_skill = AgentSkill(
        id='send_to_broker',
        name='Send to Broker',
        description='Send JWT-signed credit requests to broker agent for routing to banks',
        tags=['broker', 'routing', 'jwt'],
        examples=['Send intent to broker', 'Route request to banks'],
    )
    
    offer_evaluation_skill = AgentSkill(
        id='evaluate_offers',
        name='Evaluate Bank Offers',
        description='Evaluate received offers based on ESG and financial criteria with carbon-adjusted rates',
        tags=['evaluation', 'esg', 'financial'],
        examples=['Evaluate bank offers', 'Compare ESG scores'],
    )
    
    offer_selection_skill = AgentSkill(
        id='select_best_offer',
        name='Select Best Offer',
        description='Select the best offer based on evaluation criteria and provide reasoning',
        tags=['selection', 'decision', 'reasoning'],
        examples=['Select best offer', 'Choose optimal bank'],
    )
    
    negotiation_skill = AgentSkill(
        id='negotiate_offer',
        name='Negotiate Offer',
        description='Send counter-offers for negotiation with banks via broker',
        tags=['negotiation', 'counter-offer', 'broker'],
        examples=['Negotiate interest rate', 'Counter-offer terms'],
    )

    agent_card = AgentCard(
        name='WFAP Company Agent',
        description='Corporate credit request management agent using JWT-signed A2A protocol communication. Creates structured credit intents, sends them to banks via broker, evaluates offers based on ESG and financial criteria, and selects the best offer.',
        url=f'http://{host}:{port}/',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(
            input_modes=['text'],
            output_modes=['text'],
            streaming=True,
        ),
        skills=[
            credit_intent_skill,
            broker_communication_skill,
            offer_evaluation_skill,
            offer_selection_skill,
            negotiation_skill
        ],
        examples=[
            'I need a $1M credit line for working capital',
            'Create credit intent for expansion funding',
            'Evaluate received bank offers',
            'Select the best offer based on ESG criteria'
        ],
    )

    task_store = InMemoryTaskStore()
    request_handler = CompanyRequestHandler(
        agent_executor=CompanyAgentExecutor(),
        task_store=task_store,
    )

    server = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    
    print(f"🏢 Starting WFAP Company Agent on http://{host}:{port}")
    print(f"📋 Agent Card available at: http://{host}:{port}/.well-known/agent-card.json")
    print(f"🔐 Company agent ready")
    print(f"🌐 Broker endpoint: http://localhost:8000")
    print(f"💼 Ready to handle credit requests with ESG evaluation")
    
    uvicorn.run(server.build(), host=host, port=port)

if __name__ == '__main__':
    main()
