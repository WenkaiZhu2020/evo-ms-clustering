"""Entry point for the Stage 1 Leiden baseline experiment."""

from evo_ms.utils.logging import get_logger


def main() -> None:
    """Run the Stage 1 Leiden baseline placeholder."""
    logger = get_logger(__name__)
    # TODO: Load G_ssa, run Leiden baseline, and write cluster summaries.
    logger.info("Stage 1 Leiden baseline runner is not implemented yet.")


if __name__ == "__main__":
    main()
