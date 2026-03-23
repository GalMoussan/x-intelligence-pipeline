"""Layer 2: CrewAI task definitions — Content Strategist → Post Writer → Publisher."""

from crewai import Crew, Task

from config import settings


def create_tasks(crew: Crew, newsletter_data: dict) -> list[Task]:
    """
    Build the three sequential tasks and wire them into `crew.tasks`.

    Pipeline:
        1. strategist  — picks 3–5 insights from the newsletter markdown
        2. writer      — turns each insight into a draft X post (≤280 chars)
        3. publisher   — reviews drafts, outputs a final JSON array of approved posts

    Args:
        crew:            The Crew returned by agents.create_crew().
        newsletter_data: Parsed latest.json — must contain 'markdown' and 'week_date'.

    Returns:
        List of Task objects (also assigned to crew.tasks in-place).
    """
    strategist, writer, publisher = crew.agents
    markdown = newsletter_data.get("markdown", "")
    week_date = newsletter_data.get("week_date", "this week")

    # ------------------------------------------------------------------
    # Task 1 — Content Strategist: select insights
    # ------------------------------------------------------------------
    task_select = Task(
        name="select_insights",
        description=(
            f"You have the following AI newsletter for the week of {week_date}:\n\n"
            f"---\n{markdown}\n---\n\n"
            "Identify the 3–5 most share-worthy insights from this newsletter. "
            "For each, write a one-sentence summary of the core idea and why it is "
            "worth posting on X this week. Number them 1–5."
        ),
        expected_output=(
            "A numbered list of 3–5 insight summaries, each on its own line. "
            "Example:\n1. <insight summary>\n2. <insight summary>"
        ),
        agent=strategist,
    )

    # ------------------------------------------------------------------
    # Task 2 — Post Writer: draft one X post per insight
    # ------------------------------------------------------------------
    task_write = Task(
        name="write_posts",
        description=(
            "Using the insight list from the previous task, write one X post "
            "for each insight. Rules:\n"
            "- Maximum 280 characters per post (hard limit)\n"
            "- No hashtag spam (at most one relevant hashtag per post)\n"
            "- No em-dashes, no buzzword fluff\n"
            "- Sound like a thoughtful practitioner, not a marketer\n"
            "- Each post must stand alone — no thread numbering\n\n"
            "Return each draft post on its own numbered line."
        ),
        expected_output=(
            "A numbered list of draft X posts, one per line, each ≤280 chars. "
            "Example:\n1. <post text>\n2. <post text>"
        ),
        agent=writer,
        context=[task_select],
    )

    # ------------------------------------------------------------------
    # Task 3 — Publisher: review and output final JSON
    # ------------------------------------------------------------------
    task_publish = Task(
        name="approve_posts",
        description=(
            "Review each draft post from the previous task against these criteria:\n"
            "1. ≤280 characters (reject any that exceed this)\n"
            "2. Does not quote source tweets verbatim\n"
            "3. Does not make unverifiable factual claims\n"
            "4. Adds genuine value to the reader\n\n"
            "Approve posts that pass all criteria. Reject others with a brief reason.\n\n"
            "Output ONLY a valid JSON array of approved post strings. "
            "No explanation, no wrapper keys — just the array.\n"
            'Example: ["Post one text.", "Post two text."]'
        ),
        expected_output=(
            'A valid JSON array of approved post strings. '
            'Example: ["Post one.", "Post two."]'
        ),
        agent=publisher,
        context=[task_write],
    )

    tasks = [task_select, task_write, task_publish]
    crew.tasks = tasks
    return tasks
