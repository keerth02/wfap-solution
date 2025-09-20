"""Wells Fargo Agent Main Entry Point"""
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

from agent_executor import WellsFargoAgentExecutor

# Load environment variables
load_dotenv()

class WellsFargoRequestHandler(DefaultRequestHandler):
    """A2A Request Handler for the Wells Fargo Agent."""

    def __init__(
        self, agent_executor: WellsFargoAgentExecutor, task_store: InMemoryTaskStore
    ):
        super().__init__(agent_executor, task_store)

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=8001)
def main(host: str, port: int):
    """Start the WFAP Wells Fargo Agent server.

    This function initializes the Wells Fargo Bank Agent server with JWT signing capabilities.
    It creates an agent card with Wells Fargo's capabilities for credit evaluation,
    ESG assessment, and offer generation.

    Args:
        host (str): The host address to run the server on.
        port (int): The port number to run the server on.
    """
    
    # Wells Fargo agent skills
    credit_evaluation_skill = AgentSkill(
        id='credit_evaluation',
        name='Credit Evaluation',
        description='Evaluate corporate creditworthiness using Wells Fargo policies and criteria',
        tags=['credit', 'evaluation', 'risk'],
        examples=['Evaluate credit application', 'Assess creditworthiness'],
    )
    
    offer_generation_skill = AgentSkill(
        id='offer_generation',
        name='Generate Bank Offer',
        description='Generate structured bank offers with JWT signatures and detailed terms',
        tags=['offer', 'terms', 'jwt'],
        examples=['Generate credit offer', 'Create loan terms'],
    )
    
    esg_assessment_skill = AgentSkill(
        id='esg_assessment',
        name='ESG Assessment',
        description='Generate ESG impact assessments using LLM with carbon footprint analysis',
        tags=['esg', 'sustainability', 'assessment'],
        examples=['Assess ESG impact', 'Calculate carbon footprint'],
    )

    agent_card = AgentCard(
        name='WFAP Wells Fargo Agent',
        description='Wells Fargo Bank Agent specializing in corporate credit evaluation with JWT-signed responses. Processes credit intents, assesses creditworthiness using conservative policies, generates ESG assessments, and creates structured offers with detailed reasoning.',
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
            credit_evaluation_skill,
            offer_generation_skill,
            esg_assessment_skill
        ],
        examples=[
            'Evaluate credit application for TechCorp',
            'Generate offer for $1M working capital',
            'Assess ESG impact of manufacturing company'
        ],
    )

    task_store = InMemoryTaskStore()
    request_handler = WellsFargoRequestHandler(
        agent_executor=WellsFargoAgentExecutor(),
        task_store=task_store,
    )

    server = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    
    print(f"🏦 Starting WFAP Wells Fargo Agent on http://{host}:{port}")
    print(f"📋 Agent Card available at: http://{host}:{port}/.well-known/agent-card.json")
    print(f"🔐 JWT signing enabled for wells-fargo")
    print(f"💼 Conservative credit policies: Min score 650, Preferred industries: Tech/Healthcare/Manufacturing")
    print(f"🌱 ESG bonus: +0.25% rate reduction for ESG score > 8.0")
    
    uvicorn.run(server.build(), host=host, port=port)

if __name__ == '__main__':
    main()
