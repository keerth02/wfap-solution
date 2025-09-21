"""Chase Bank Agent Main Entry Point"""
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

from agent_executor import ChaseBankAgentExecutor

# Load environment variables
load_dotenv()

class ChaseBankRequestHandler(DefaultRequestHandler):
    """A2A Request Handler for the Chase Bank Agent."""

    def __init__(
        self, agent_executor: ChaseBankAgentExecutor, task_store: InMemoryTaskStore
    ):
        super().__init__(agent_executor, task_store)

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=8003)
def main(host: str, port: int):
    """Start the WFAP Chase Bank Agent server.

    This function initializes the Chase Bank Agent server.
    It creates an agent card with Chase Bank's capabilities for credit evaluation,
    ESG assessment, and offer generation.

    Args:
        host (str): The host address to run the server on.
        port (int): The port number to run the server on.
    """
    
    # Chase Bank agent skills
    credit_evaluation_skill = AgentSkill(
        id='credit_evaluation',
        name='Credit Evaluation',
        description='Evaluate corporate creditworthiness using Chase Bank policies and criteria',
        tags=['credit', 'evaluation', 'risk'],
        examples=['Evaluate credit application', 'Assess creditworthiness'],
    )
    
    offer_generation_skill = AgentSkill(
        id='offer_generation',
        name='Generate Bank Offer',
        description='Generate structured bank offers with detailed terms',
        tags=['offer', 'terms'],
        examples=['Generate credit offer', 'Create line of credit terms'],
    )
    
    esg_assessment_skill = AgentSkill(
        id='esg_assessment',
        name='ESG Assessment',
        description='Generate ESG impact assessments using LLM with carbon footprint analysis',
        tags=['esg', 'sustainability', 'assessment'],
        examples=['Assess ESG impact', 'Calculate carbon footprint'],
    )

    agent_card = AgentCard(
        name='WFAP Chase Bank Agent',
        description='Chase Bank Agent specializing in corporate credit evaluation. Processes credit intents, assesses creditworthiness using competitive policies, generates ESG assessments, and creates structured offers with detailed reasoning.',
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
    request_handler = ChaseBankRequestHandler(
        agent_executor=ChaseBankAgentExecutor(),
        task_store=task_store,
    )

    server = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    
    print(f"🏦 Starting WFAP Chase Bank Agent on http://{host}:{port}")
    print(f"📋 Agent Card available at: http://{host}:{port}/.well-known/agent-card.json")
    print(f"🔐 Chase Bank agent ready")
    print(f"💼 Competitive credit policies: Min score 680, Preferred industries: Tech/Healthcare/Finance/Real Estate")
    print(f"🌱 ESG bonus: +0.30% rate reduction for ESG score > 8.5")
    
    uvicorn.run(server.build(), host=host, port=port)

if __name__ == '__main__':
    main()
