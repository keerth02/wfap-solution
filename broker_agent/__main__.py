"""Broker Agent Main Entry Point"""
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

from broker_executor import BrokerAgentExecutor

# Load environment variables
load_dotenv()

class BrokerRequestHandler(DefaultRequestHandler):
    """A2A Request Handler for the Broker Agent."""

    def __init__(
        self, agent_executor: BrokerAgentExecutor, task_store: InMemoryTaskStore
    ):
        super().__init__(agent_executor, task_store)

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=8000)
def main(host: str, port: int):
    """Start the WFAP Broker Agent server.

    This function initializes the Broker Agent server as a pure message router.
    It creates an agent card with the broker's capabilities for message routing
    and response aggregation.

    Args:
        host (str): The host address to run the server on.
        port (int): The port number to run the server on.
    """
    
    # Broker skills
    message_routing_skill = AgentSkill(
        id='message_routing',
        name='Message Routing to Banks',
        description='Routes messages to all registered bank agents',
        tags=['routing', 'banks', 'messages'],
        examples=['Route credit intent to Wells Fargo', 'Send request to Bank of America'],
    )
    
    response_aggregation_skill = AgentSkill(
        id='response_aggregation',
        name='Response Aggregation',
        description='Aggregates responses from multiple bank agents',
        tags=['aggregation', 'responses'],
        examples=['Collect bank offers', 'Aggregate bank responses'],
    )
    
    audit_logging_skill = AgentSkill(
        id='audit_logging',
        name='Audit Trail Logging',
        description='Maintains audit trail of all routing communications',
        tags=['audit', 'logging', 'compliance'],
        examples=['Log message routing', 'Track request routing'],
    )

    agent_card = AgentCard(
        name='WFAP Broker Agent',
        description='Pure message routing broker for Wells Fargo Agent Protocol. Routes messages to bank agents and aggregates responses with audit trail.',
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
            message_routing_skill,
            response_aggregation_skill,
            audit_logging_skill
        ],
        examples=[
            'Route credit intent to all bank agents',
            'Aggregate bank offers',
            'Track message routing'
        ],
    )

    task_store = InMemoryTaskStore()
    request_handler = BrokerRequestHandler(
        agent_executor=BrokerAgentExecutor(),
        task_store=task_store,
    )

    server = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    
    print(f"🚀 Starting WFAP Broker Agent on http://{host}:{port}")
    print(f"📋 Agent Card available at: http://{host}:{port}/.well-known/agent-card.json")
    print(f"🔄 Pure message routing enabled")
    print(f"🏦 Bank endpoints: Wells Fargo (8001), Bank of America (8002)")
    
    uvicorn.run(server.build(), host=host, port=port)

if __name__ == '__main__':
    main()
