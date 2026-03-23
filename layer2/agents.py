"""Layer 2: CrewAI agent definitions — Content Strategist, Post Writer, Publisher."""

from crewai import Agent, Crew, LLM, Process

from config import settings


def _llm() -> LLM:
    """Return the shared Claude LLM for all agents."""
    return LLM(
        model=f"anthropic/{settings.CLAUDE_MODEL}",
        api_key=settings.ANTHROPIC_API_KEY,
        max_tokens=1024,
    )


def make_content_strategist(llm) -> Agent:
    return Agent(
        role="Content Strategist",
        goal=(
            "Read the weekly AI newsletter and decide which 3–5 insights "
            "are most worth sharing as standalone X posts this week."
        ),
        backstory=(
            "You are a seasoned social media strategist who understands what "
            "resonates with an AI-curious, entrepreneurial audience on X. "
            "You prioritise actionable, specific, and timely content over hype."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )


def make_post_writer(llm) -> Agent:
    return Agent(
        role="Post Writer",
        goal=(
            "Transform each selected insight into a punchy, native X post "
            "(max 280 chars). No hashtag spam. No em-dashes. Sound human."
        ),
        backstory=(
            "You write like a thoughtful practitioner, not a marketer. "
            "You know that the best X posts are either a sharp take, a concrete "
            "tip, or a surprising fact — never a press release. "
            "You always stay under 280 characters."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )


def make_publisher(llm) -> Agent:
    return Agent(
        role="Publisher",
        goal=(
            "Review the drafted posts for quality and compliance, then output "
            "a final JSON list of approved posts ready for the X API."
        ),
        backstory=(
            "You are the last line of defence before content goes live. "
            "You check: under 280 chars, no sensitive claims, no plagiarism of "
            "source tweets verbatim, and that posts add genuine value. "
            "You output ONLY a valid JSON array of approved post strings."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )


def create_crew() -> Crew:
    """
    Build and return the CrewAI crew.

    The crew runs sequentially:
        Content Strategist → Post Writer → Publisher

    Tasks are wired in layer2/tasks.py and injected at runtime.
    Returns the Crew object (not yet kicked off — caller does crew.kickoff()).
    """
    settings.validate(["ANTHROPIC_API_KEY"])
    llm = _llm()

    strategist = make_content_strategist(llm)
    writer = make_post_writer(llm)
    publisher = make_publisher(llm)

    return Crew(
        agents=[strategist, writer, publisher],
        tasks=[],           # populated by tasks.create_tasks()
        process=Process.sequential,
        verbose=True,
    )
