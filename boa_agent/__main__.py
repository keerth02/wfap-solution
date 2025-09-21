"""Bank of America Agent Main Entry Point"""
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

from agent_executor import BOAAgentExecutor

# Load environment variables
load_dotenv()

class BOARequestHandler(DefaultRequestHandler):
    """A2A Request Handler for the Bank of America Agent."""

    def __init__(
        self, agent_executor: BOAAgentExecutor, task_store: InMemoryTaskStore
    ):
        super().__init__(agent_executor, task_store)

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=8002)
def main(host: str, port: int):
    """Start the WFAP Bank of America Agent server.

    This function initializes the Bank of America Agent server.
    It creates an agent card with Bank of America's capabilities for credit evaluation,
    ESG assessment, and competitive offer generation.

    Args:
        host (str): The host address to run the server on.
        port (int): The port number to run the server on.
    """
    
    # Bank of America agent skills
    credit_evaluation_skill = AgentSkill(
        id='credit_evaluation',
        name='Credit Evaluation',
        description='Evaluate corporate creditworthiness using Bank of America policies with innovation focus',
        tags=['credit', 'evaluation', 'innovation'],
        examples=['Evaluate credit application', 'Assess creditworthiness'],
    )
    
    offer_generation_skill = AgentSkill(
        id='offer_generation',
        name='Generate Bank Offer',
        description='Generate competitive bank offers with JWT signatures and innovation-focused terms',
        tags=['offer', 'terms', 'jwt', 'competitive'],
        examples=['Generate credit offer', 'Create competitive line of credit terms'],
    )
    
    esg_assessment_skill = AgentSkill(
        id='esg_assessment',
        name='ESG Assessment',
        description='Generate ESG impact assessments using LLM with innovation and carbon footprint analysis',
        tags=['esg', 'sustainability', 'assessment', 'innovation'],
        examples=['Assess ESG impact', 'Calculate carbon footprint'],
    )

    agent_card = AgentCard(
        name='WFAP Bank of America Agent',
        description='Bank of America Agent specializing in corporate credit evaluation with a focus on innovation and technology, using JWT-signed responses. Processes credit intents, assesses creditworthiness with innovation focus, generates ESG assessments, and creates competitive offers with detailed reasoning.',
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
            'Evaluate credit application for TechStartup',
            'Generate competitive offer for $2M innovation funding',
            'Assess ESG impact of fintech company'
        ],
    )

    task_store = InMemoryTaskStore()
    request_handler = BOARequestHandler(
        agent_executor=BOAAgentExecutor(),
        task_store=task_store,
    )

    server = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    
    print(f"🏦 Starting WFAP Bank of America Agent on http://{host}:{port}")
    print(f"📋 Agent Card available at: http://{host}:{port}/.well-known/agent-card.json")
    print(f"🔐 Bank of America agent ready")
    print(f"💼 Innovation-focused credit policies: Min score 600, Preferred industries: Tech/Fintech/Innovation")
    print(f"🌱 ESG bonus: +0.5% rate reduction for ESG score > 7.5")
    print(f"🚀 Innovation bonus: +0.25% rate reduction for tech companies")
    
    uvicorn.run(server.build(), host=host, port=port)

if __name__ == '__main__':
    main()
